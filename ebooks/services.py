from datetime import datetime
from io import BytesIO
from django.core.files.base import ContentFile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate
from ebooklib import epub
from bs4 import BeautifulSoup
import tempfile
import os

class EbookExportService:
    @staticmethod
    def export_to_pdf(ebook_project):
        """Generate PDF version of the ebook"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Add title
        title = Paragraph(ebook_project.title, styles['Title'])
        story.append(title)
        
        # Add chapters
        for chapter in ebook_project.chapters.all().order_by('order'):
            # Convert JSON content to plain text (simplified)
            content_text = EbookExportService._convert_content_to_text(chapter.content)
            chapter_para = Paragraph(f"<b>{chapter.title}</b><br/><br/>{content_text}", styles['Normal'])
            story.append(chapter_para)
        
        doc.build(story)
        buffer.seek(0)
        
        filename = f"{ebook_project.title}_{datetime.now().strftime('%Y%m%d')}.pdf"
        return ContentFile(buffer.read(), name=filename)

    @staticmethod
    def export_to_epub(ebook_project):
        """Generate EPUB version of the ebook"""
        book = epub.EpubBook()
        
        # Set metadata
        book.set_identifier(str(ebook_project.id))
        book.set_title(ebook_project.title)
        book.add_author(ebook_project.author.display_name)
        
        # Add cover
        if ebook_project.cover_image:
            try:
                with ebook_project.cover_image.open('rb') as cover_file:
                    book.set_cover("cover.jpg", cover_file.read())
            except Exception as e:
                print(f"Error adding cover: {e}")
        
        # Create chapters
        chapters = []
        for i, chapter in enumerate(ebook_project.chapters.all().order_by('order'), 1):
            content_html = EbookExportService._convert_content_to_html(chapter.content)
            
            epub_chapter = epub.EpubHtml(
                title=chapter.title,
                file_name=f'chapter_{i}.xhtml',
                lang='en'
            )
            epub_chapter.content = f"""
                <html>
                    <body>
                        <h1>{chapter.title}</h1>
                        {content_html}
                    </body>
                </html>
            """
            book.add_item(epub_chapter)
            chapters.append(epub_chapter)
        
        # Define Table of Contents
        book.toc = tuple(chapters)
        
        # Add navigation files
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        
        # Create spine
        book.spine = ['nav'] + chapters
        
        # Generate file
        temp_dir = tempfile.mkdtemp()
        epub_path = os.path.join(temp_dir, f"{ebook_project.title}.epub")
        epub.write_epub(epub_path, book, {})
        
        with open(epub_path, 'rb') as f:
            content = f.read()
        
        filename = f"{ebook_project.title}_{datetime.now().strftime('%Y%m%d')}.epub"
        return ContentFile(content, name=filename)

    @staticmethod
    def _convert_content_to_text(content_json):
        """Convert TipTap JSON to plain text (simplified)"""
        if not content_json or not content_json.get('content'):
            return ""
        
        text_parts = []
        for node in content_json['content']:
            if node['type'] == 'paragraph':
                text = ""
                for child in node.get('content', []):
                    if child['type'] == 'text':
                        text += child['text']
                text_parts.append(text)
        
        return "\n\n".join(text_parts)

    @staticmethod
    def _convert_content_to_html(content_json):
        """Convert TipTap JSON to HTML (simplified)"""
        if not content_json or not content_json.get('content'):
            return ""
        
        html_parts = []
        for node in content_json['content']:
            if node['type'] == 'paragraph':
                text = ""
                for child in node.get('content', []):
                    if child['type'] == 'text':
                        text += child['text']
                html_parts.append(f"<p>{text}</p>")
        
        return "".join(html_parts)