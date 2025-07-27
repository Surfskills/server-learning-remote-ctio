# management/commands/create_default_templates.py
from django.core.management.base import BaseCommand
from templates.models import EbookTemplate

class Command(BaseCommand):
    help = 'Create default ebook templates'

    def handle(self, *args, **options):
        templates_data = [
            {
                'name': 'Classic Novel',
                'type': 'FULL',  # Changed from 'NOVEL' to match TemplateType choices
                'description': 'Traditional book layout with elegant typography and chapter formatting',
                'is_default': True,
                'is_premium': False,
                'styles': {
                    'typography': {
                        'body_font': 'Georgia, serif',
                        'heading_font': 'Times New Roman, serif',
                        'body_size': '16px',
                        'heading_size': '24px',
                        'line_height': '1.6'
                    },
                    'layout': {
                        'page_margins': '1.5in',
                        'paragraph_spacing': '12px',
                        'chapter_break': 'page-break'
                    },
                    'colors': {
                        'text': '#2D3748',
                        'headings': '#1A202C',
                        'background': '#FFFFFF'
                    }
                },
                'structure': {
                    'title_page': True,
                    'table_of_contents': True,
                    'chapter_headers': True,
                    'page_numbers': True,
                    'section_breaks': True
                }
            },
            {
                'name': 'Modern Business',
                'type': 'FULL',  # Changed from 'BUSINESS' to match TemplateType choices
                'description': 'Clean, professional layout perfect for business books and guides',
                'is_default': True,
                'is_premium': False,
                'styles': {
                    'typography': {
                        'body_font': 'Arial, sans-serif',
                        'heading_font': 'Helvetica, sans-serif',
                        'body_size': '14px',
                        'heading_size': '20px',
                        'line_height': '1.5'
                    },
                    'layout': {
                        'page_margins': '1in',
                        'paragraph_spacing': '10px',
                        'chapter_break': 'section-break'
                    },
                    'colors': {
                        'text': '#374151',
                        'headings': '#111827',
                        'background': '#F9FAFB',
                        'accent': '#3B82F6'
                    }
                },
                'structure': {
                    'title_page': True,
                    'table_of_contents': True,
                    'chapter_headers': True,
                    'page_numbers': True,
                    'sidebar_boxes': True
                }
            },
            {
                'name': 'Children\'s Book',
                'type': 'FULL',  # Changed from 'CHILDREN' to match TemplateType choices
                'description': 'Colorful, friendly design with large text and image support',
                'is_default': False,
                'is_premium': True,
                'styles': {
                    'typography': {
                        'body_font': 'Comic Sans MS, cursive',
                        'heading_font': 'Arial Rounded, sans-serif',
                        'body_size': '18px',
                        'heading_size': '28px',
                        'line_height': '1.8'
                    },
                    'layout': {
                        'page_margins': '0.75in',
                        'paragraph_spacing': '15px',
                        'chapter_break': 'page-break'
                    },
                    'colors': {
                        'text': '#2D3748',
                        'headings': '#E53E3E',
                        'background': '#FFFBF0',
                        'accent': '#38A169'
                    }
                },
                'structure': {
                    'title_page': True,
                    'table_of_contents': False,
                    'chapter_headers': True,
                    'page_numbers': False,
                    'image_placeholders': True
                }
            }
        ]

        for template_data in templates_data:
            template, created = EbookTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults=template_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created template: {template.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Template already exists: {template.name}')
                )