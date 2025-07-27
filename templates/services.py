# templates/services.py - Enhanced version with better error handling
import json
from typing import Dict, Any, Optional
from django.contrib.auth import get_user_model
from django.db import transaction
from ebooks.models import EbookProject, Chapter
from .models import EbookTemplate, UserTemplate

User = get_user_model()

class TemplateService:
    @staticmethod
    @transaction.atomic
    def apply_template(ebook: EbookProject, template_id: str, is_system_template: bool = True) -> EbookProject:
        """
        Apply a template to an ebook project
        """
        try:
            # Get the template
            if is_system_template:
                template = EbookTemplate.objects.get(id=template_id)
                template_styles = template.styles or {}
                template_structure = template.structure or {}
                template_name = template.name
            else:
                user_template = UserTemplate.objects.get(id=template_id)
                template_styles = user_template.styles or {}
                template_structure = user_template.structure or {}
                template_name = user_template.name

            # Validate template data
            if not isinstance(template_styles, dict):
                template_styles = {}
            if not isinstance(template_structure, dict):
                template_structure = {}

            # Apply styles to ebook with deep merge
            ebook.template_styles = TemplateService._merge_styles(
                ebook.template_styles or {}, 
                template_styles
            )
            ebook.template_structure = TemplateService._merge_structure(
                ebook.template_structure or {}, 
                template_structure
            )
            
            # Update ebook metadata if template has specific settings
            if 'metadata' in template_structure:
                metadata_settings = template_structure['metadata']
                if metadata_settings.get('title_case'):
                    ebook.title = ebook.title.title()

            # Apply template to existing chapters
            chapters = ebook.chapters.all()
            for chapter in chapters:
                TemplateService._apply_template_to_chapter(
                    chapter, 
                    template_styles, 
                    template_structure
                )

            ebook.save()
            
            # Log template application (optional)
            print(f"Template '{template_name}' applied to ebook '{ebook.title}'")
            
            return ebook

        except (EbookTemplate.DoesNotExist, UserTemplate.DoesNotExist) as e:
            raise ValueError(f"Template not found: {e}")
        except Exception as e:
            raise ValueError(f"Failed to apply template: {e}")

    @staticmethod
    def _merge_styles(existing_styles: Dict, new_styles: Dict) -> Dict:
        """
        Deep merge template styles
        """
        result = existing_styles.copy()
        
        for key, value in new_styles.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = TemplateService._merge_styles(result[key], value)
            else:
                result[key] = value
        
        return result

    @staticmethod
    def _merge_structure(existing_structure: Dict, new_structure: Dict) -> Dict:
        """
        Merge template structure settings
        """
        result = existing_structure.copy()
        result.update(new_structure)
        return result

    @staticmethod
    def _apply_template_to_chapter(chapter: Chapter, styles: Dict, structure: Dict):
        """
        Apply template formatting to a chapter's content
        """
        if not chapter.content or not isinstance(chapter.content, dict):
            return

        # Apply text formatting based on template styles
        if 'content' in chapter.content:
            content = chapter.content['content']
            
            # Process each content block
            for block in content:
                TemplateService._apply_styles_to_block(block, styles)

        chapter.save()

    @staticmethod
    def _apply_styles_to_block(block: Dict, styles: Dict):
        """
        Apply styles to a content block
        """
        if not isinstance(block, dict):
            return

        block_type = block.get('type')
        typography = styles.get('typography', {})
        colors = styles.get('colors', {})

        if block_type == 'paragraph':
            # Apply paragraph styles
            if 'attrs' not in block:
                block['attrs'] = {}
            
            block['attrs'].update({
                'style': TemplateService._build_style_string({
                    'font-family': typography.get('body_font', 'inherit'),
                    'font-size': typography.get('body_size', '16px'),
                    'line-height': typography.get('line_height', '1.6'),
                    'color': colors.get('text', '#000000'),
                    'margin-bottom': typography.get('paragraph_spacing', '12px')
                })
            })

        elif block_type in ['heading']:
            # Apply heading styles
            if 'attrs' not in block:
                block['attrs'] = {}
            
            level = block.get('attrs', {}).get('level', 1)
            heading_size = typography.get('heading_size', '24px')
            
            # Adjust size based on heading level
            if level > 1:
                base_size = int(heading_size.replace('px', ''))
                adjusted_size = max(base_size - (level - 1) * 2, 14)
                heading_size = f'{adjusted_size}px'
            
            block['attrs'].update({
                'style': TemplateService._build_style_string({
                    'font-family': typography.get('heading_font', 'inherit'),
                    'font-size': heading_size,
                    'color': colors.get('headings', '#000000'),
                    'margin-bottom': typography.get('heading_spacing', '16px')
                })
            })

        # Recursively apply to nested content
        if 'content' in block and isinstance(block['content'], list):
            for child_block in block['content']:
                TemplateService._apply_styles_to_block(child_block, styles)

    @staticmethod
    def _build_style_string(style_dict: Dict[str, str]) -> str:
        """
        Build CSS style string from dictionary
        """
        return '; '.join([f'{key}: {value}' for key, value in style_dict.items() if value])

    @staticmethod
    def get_templates_for_user(user: User, template_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all templates available to a user (system + user templates)
        """
        # Get system templates
        system_templates = EbookTemplate.objects.all()
        
        # Filter by user permissions
        if not hasattr(user, 'has_premium_access') or not user.has_premium_access:
            system_templates = system_templates.filter(is_premium=False)
        
        if template_type:
            system_templates = system_templates.filter(type=template_type)

        # Get user's custom templates
        user_templates = UserTemplate.objects.filter(user=user)
        if template_type and hasattr(UserTemplate, 'type'):
            # If UserTemplate has a type field
            user_templates = user_templates.filter(type=template_type)
        elif template_type:
            # Filter by base template type
            user_templates = user_templates.filter(
                base_template__type=template_type
            )

        return {
            'system_templates': system_templates,
            'user_templates': user_templates
        }

    @staticmethod
    @transaction.atomic
    def duplicate_template(template_id: str, user: User, new_name: str, is_system_template: bool = True) -> UserTemplate:
        """
        Create a user template based on a system template or another user template
        """
        try:
            if is_system_template:
                original_template = EbookTemplate.objects.get(id=template_id)
                base_template = original_template
                styles = original_template.styles or {}
                structure = original_template.structure or {}
            else:
                original_template = UserTemplate.objects.get(id=template_id, user=user)
                base_template = original_template.base_template
                styles = original_template.styles or {}
                structure = original_template.structure or {}

            # Validate name uniqueness for user
            if UserTemplate.objects.filter(user=user, name=new_name).exists():
                raise ValueError(f"Template with name '{new_name}' already exists")

            user_template = UserTemplate.objects.create(
                user=user,
                base_template=base_template,
                name=new_name,
                styles=styles,
                structure=structure
            )

            return user_template

        except (EbookTemplate.DoesNotExist, UserTemplate.DoesNotExist) as e:
            raise ValueError(f"Original template not found: {e}")
        except Exception as e:
            raise ValueError(f"Failed to duplicate template: {e}")

    @staticmethod
    def get_template_preview(template_id: str, is_system_template: bool = True) -> Dict:
        """
        Generate preview data for a template
        """
        try:
            if is_system_template:
                template = EbookTemplate.objects.get(id=template_id)
                styles = template.styles or {}
                structure = template.structure or {}
                name = template.name
            else:
                template = UserTemplate.objects.get(id=template_id)
                styles = template.styles or {}
                structure = template.structure or {}
                name = template.name

            # Create sample content with template applied
            sample_content = {
                "type": "doc",
                "content": [
                    {
                        "type": "heading",
                        "attrs": {"level": 1},
                        "content": [{"type": "text", "text": "Chapter Title"}]
                    },
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text", 
                                "text": "This is how your content will look with this template applied. The typography, spacing, and colors will match this preview."
                            }
                        ]
                    },
                    {
                        "type": "heading",
                        "attrs": {"level": 2},
                        "content": [{"type": "text", "text": "Subheading"}]
                    },
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text", 
                                "text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
                            }
                        ]
                    }
                ]
            }
            
            # Apply styles to sample content
            for block in sample_content['content']:
                TemplateService._apply_styles_to_block(block, styles)

            return {
                'name': name,
                'preview_content': sample_content,
                'styles': styles,
                'structure': structure
            }

        except (EbookTemplate.DoesNotExist, UserTemplate.DoesNotExist) as e:
            raise ValueError(f"Template not found: {e}")

    @staticmethod
    def validate_template_data(styles: Dict, structure: Dict) -> tuple[bool, list]:
        """
        Validate template styles and structure data
        """
        errors = []

        # Validate styles
        if not isinstance(styles, dict):
            errors.append("Styles must be a JSON object")
        else:
            # Check required style sections
            typography = styles.get('typography', {})
            if not isinstance(typography, dict):
                errors.append("Typography section must be a JSON object")

            colors = styles.get('colors', {})
            if not isinstance(colors, dict):
                errors.append("Colors section must be a JSON object")

            layout = styles.get('layout', {})
            if not isinstance(layout, dict):
                errors.append("Layout section must be a JSON object")

        # Validate structure
        if not isinstance(structure, dict):
            errors.append("Structure must be a JSON object")

        return len(errors) == 0, errors

    @staticmethod
    def create_default_style_template() -> Dict:
        """
        Create a default style template structure
        """
        return {
            'typography': {
                'body_font': 'Georgia, serif',
                'heading_font': 'Times New Roman, serif',
                'body_size': '16px',
                'heading_size': '24px',
                'line_height': '1.6',
                'paragraph_spacing': '12px',
                'heading_spacing': '16px'
            },
            'layout': {
                'page_margins': '1.5in',
                'paragraph_spacing': '12px',
                'chapter_break': 'page-break',
                'text_align': 'left'
            },
            'colors': {
                'text': '#2D3748',
                'headings': '#1A202C',
                'background': '#FFFFFF',
                'accent': '#3B82F6'
            }
        }

    @staticmethod
    def create_default_structure_template() -> Dict:
        """
        Create a default structure template
        """
        return {
            'title_page': True,
            'table_of_contents': True,
            'chapter_headers': True,
            'page_numbers': True,
            'section_breaks': True,
            'metadata': {
                'title_case': False,
                'author_page': True,
                'copyright_page': True
            }
        }