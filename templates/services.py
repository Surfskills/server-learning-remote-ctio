# templates/services.py
import uuid
import logging
from django.core.files.base import ContentFile
from django.core.exceptions import ObjectDoesNotExist
from .models import EbookTemplate, UserTemplate

logger = logging.getLogger(__name__)


class TemplateService:
    
    @staticmethod
    def apply_template(ebook_project, template_id):
        """
        Apply a template to an ebook project
        Handles both EbookTemplate and UserTemplate IDs
        """
        try:
            # First try to get as EbookTemplate
            template = EbookTemplate.objects.get(pk=template_id)
            return TemplateService._apply_ebook_template(ebook_project, template)
        except EbookTemplate.DoesNotExist:
            try:
                # Then try as UserTemplate
                user_template = UserTemplate.objects.get(pk=template_id)
                return TemplateService._apply_user_template(ebook_project, user_template)
            except UserTemplate.DoesNotExist:
                raise ObjectDoesNotExist(f"Template with ID {template_id} not found")

    @staticmethod
    def _apply_ebook_template(ebook_project, template):
        """Apply an EbookTemplate to an ebook project"""
        try:
            if template.type == EbookTemplate.TemplateType.COVER:
                return TemplateService._apply_cover_template(ebook_project, template)
            elif template.type == EbookTemplate.TemplateType.CHAPTER:
                return TemplateService._apply_chapter_template(ebook_project, template)
            else:  # FULL template
                return TemplateService._apply_full_template(ebook_project, template)
        except Exception as e:
            logger.error(f"Error applying template {template.id} to ebook {ebook_project.id}: {str(e)}")
            raise

    @staticmethod
    def _apply_user_template(ebook_project, user_template):
        """Apply a UserTemplate to an ebook project"""
        try:
            # Apply structure to all chapters
            for chapter in ebook_project.chapters.all():
                # Merge template structure with existing content
                existing_content = chapter.content.get("content", []) if chapter.content else []
                chapter.content = {
                    **user_template.structure,
                    "content": existing_content
                }
                chapter.save()
            
            logger.info(f"Applied user template {user_template.id} to ebook {ebook_project.id}")
            return ebook_project
        except Exception as e:
            logger.error(f"Error applying user template {user_template.id} to ebook {ebook_project.id}: {str(e)}")
            raise

    @staticmethod
    def _apply_cover_template(ebook_project, template):
        """Apply cover template to ebook"""
        try:
            if template.cover_image:
                # Generate unique filename
                filename = f"cover_{uuid.uuid4()}.jpg"
                
                # Copy template cover to ebook
                with template.cover_image.open('rb') as cover_file:
                    ebook_project.cover_image.save(
                        filename,
                        ContentFile(cover_file.read()),
                        save=False
                    )
                ebook_project.save()
                
            logger.info(f"Applied cover template {template.id} to ebook {ebook_project.id}")
            return ebook_project
        except Exception as e:
            logger.error(f"Error applying cover template {template.id}: {str(e)}")
            raise

    @staticmethod
    def _apply_chapter_template(ebook_project, template):
        """Apply chapter template to all chapters"""
        try:
            for chapter in ebook_project.chapters.all():
                # Preserve existing content while applying template structure
                existing_content = chapter.content.get("content", []) if chapter.content else []
                
                # Apply template structure
                chapter.content = {
                    **template.structure,
                    "content": existing_content,
                    # Apply template styles if they exist
                    "styles": template.styles if template.styles else chapter.content.get("styles", {})
                }
                chapter.save()
                
            logger.info(f"Applied chapter template {template.id} to ebook {ebook_project.id}")
            return ebook_project
        except Exception as e:
            logger.error(f"Error applying chapter template {template.id}: {str(e)}")
            raise

    @staticmethod
    def _apply_full_template(ebook_project, template):
        """Apply full template to entire ebook (cover + chapters)"""
        try:
            # Apply cover if available
            if template.cover_image:
                filename = f"cover_{uuid.uuid4()}.jpg"
                with template.cover_image.open('rb') as cover_file:
                    ebook_project.cover_image.save(
                        filename,
                        ContentFile(cover_file.read()),
                        save=False
                    )
            
            # Apply template to all chapters
            for chapter in ebook_project.chapters.all():
                existing_content = chapter.content.get("content", []) if chapter.content else []
                chapter.content = {
                    **template.structure,
                    "content": existing_content,
                    "styles": template.styles if template.styles else chapter.content.get("styles", {})
                }
                chapter.save()
            
            # Save ebook project
            ebook_project.save()
            
            logger.info(f"Applied full template {template.id} to ebook {ebook_project.id}")
            return ebook_project
        except Exception as e:
            logger.error(f"Error applying full template {template.id}: {str(e)}")
            raise

    @staticmethod
    def create_user_template(user, name, styles=None, structure=None, base_template_id=None):
        """Create a custom user template"""
        try:
            data = {
                'user': user,
                'name': name,
                'styles': styles or {},
                'structure': structure or {}
            }
            
            if base_template_id:
                try:
                    base_template = EbookTemplate.objects.get(pk=base_template_id)
                    data['base_template'] = base_template
                    
                    # If no custom styles/structure provided, inherit from base template
                    if not styles and base_template.styles:
                        data['styles'] = base_template.styles
                    if not structure and base_template.structure:
                        data['structure'] = base_template.structure
                        
                except EbookTemplate.DoesNotExist:
                    raise ObjectDoesNotExist(f"Base template with ID {base_template_id} not found")
            
            user_template = UserTemplate.objects.create(**data)
            logger.info(f"Created user template {user_template.id} for user {user.id}")
            return user_template
            
        except Exception as e:
            logger.error(f"Error creating user template: {str(e)}")
            raise

    @staticmethod
    def get_templates_for_user(user, template_type=None):
        """Get all available templates for a user (both system and user templates)"""
        # Get system templates
        system_templates = EbookTemplate.objects.all()
        if template_type:
            system_templates = system_templates.filter(type=template_type)
        
        # Get user's custom templates
        user_templates = UserTemplate.objects.filter(user=user)
        
        return {
            'system_templates': system_templates,
            'user_templates': user_templates
        }

    @staticmethod
    def duplicate_template(template_id, user, new_name):
        """Duplicate a system template as a user template"""
        try:
            template = EbookTemplate.objects.get(pk=template_id)
            
            user_template = UserTemplate.objects.create(
                user=user,
                base_template=template,
                name=new_name,
                styles=template.styles,
                structure=template.structure
            )
            
            logger.info(f"Duplicated template {template_id} as user template {user_template.id}")
            return user_template
            
        except EbookTemplate.DoesNotExist:
            raise ObjectDoesNotExist(f"Template with ID {template_id} not found")
        except Exception as e:
            logger.error(f"Error duplicating template {template_id}: {str(e)}")
            raise