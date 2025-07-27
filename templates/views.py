# templates/views.py - Complete implementation
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import CanUseTemplates
from ebooks.models import EbookProject
from ebooks.serializers import EbookProjectSerializer
from .models import EbookTemplate, UserTemplate
from .serializers import (
    EbookTemplateSerializer,
    UserTemplateSerializer,
    TemplateApplicationSerializer
)
from .services import TemplateService


class EbookTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for system ebook templates.
    Users can view and apply templates but not create/modify them.
    """
    queryset = EbookTemplate.objects.all()
    serializer_class = EbookTemplateSerializer
    permission_classes = [IsAuthenticated, CanUseTemplates]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'is_default', 'is_premium']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'is_default']
    ordering = ['-is_default', 'name']

    def get_queryset(self):
        """Filter templates based on user permissions"""
        queryset = self.queryset
        
        # If user doesn't have premium access, exclude premium templates
        user = self.request.user
        if not hasattr(user, 'has_premium_access') or not user.has_premium_access:
            queryset = queryset.filter(is_premium=False)
            
        return queryset

    @action(detail=True, methods=['post'], url_path='apply')
    def apply_to_ebook(self, request, pk=None):
        """Apply template to an ebook - matches frontend URL: /templates/system/{id}/apply/"""
        template = self.get_object()
        serializer = TemplateApplicationSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ebook_id = serializer.validated_data['ebook_id']
        
        try:
            ebook = get_object_or_404(EbookProject, pk=ebook_id)
            
            # Check permissions - user must be author or have edit access
            if not self._can_apply_template_to_ebook(ebook, request.user):
                return Response(
                    {'error': 'You do not have permission to apply templates to this ebook'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Apply the template
            updated_ebook = TemplateService.apply_template(ebook, str(template.id), True)
            
            # Return updated ebook data
            ebook_serializer = EbookProjectSerializer(
                updated_ebook,
                context={'request': request}
            )
            
            return Response({
                'message': f'Template "{template.name}" applied successfully',
                'ebook': ebook_serializer.data
            })
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to apply template: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Create a user template based on this system template"""
        template = self.get_object()
        new_name = request.data.get('name')
        
        if not new_name:
            return Response(
                {'error': 'Name is required for the duplicated template'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user_template = TemplateService.duplicate_template(
                str(template.id),
                request.user,
                new_name,
                True
            )
            
            serializer = UserTemplateSerializer(
                user_template,
                context={'request': request}
            )
            
            return Response({
                'message': f'Template duplicated as "{new_name}"',
                'template': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to duplicate template: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def defaults(self, request):
        """Get default templates by type"""
        template_type = request.query_params.get('type')
        queryset = self.get_queryset().filter(is_default=True)
        
        if template_type:
            queryset = queryset.filter(type=template_type)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Generate a preview of what this template looks like"""
        template = self.get_object()
        
        try:
            preview_data = TemplateService.get_template_preview(str(template.id), True)
            return Response(preview_data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _can_apply_template_to_ebook(self, ebook, user):
        """Check if user can apply template to ebook"""
        return (
            ebook.author == user or 
            ebook.ebookcollaborator_set.filter(user=user, can_edit=True).exists()
        )


class UserTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user's custom templates.
    Users can create, modify, and manage their own templates.
    """
    serializer_class = UserTemplateSerializer
    permission_classes = [IsAuthenticated, CanUseTemplates]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-updated_at']

    def get_queryset(self):
        """Return only current user's templates"""
        return UserTemplate.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Set current user when creating template"""
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Create with validation"""
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate template data
        styles = serializer.validated_data.get('styles', {})
        structure = serializer.validated_data.get('structure', {})
        
        is_valid, errors = TemplateService.validate_template_data(styles, structure)
        if not is_valid:
            return Response(
                {'validation_errors': errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If no styles provided, use defaults
        if not styles:
            serializer.validated_data['styles'] = TemplateService.create_default_style_template()
        
        if not structure:
            serializer.validated_data['structure'] = TemplateService.create_default_structure_template()
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        return Response(
            serializer.data, 
            status=status.HTTP_201_CREATED, 
            headers=headers
        )

    @action(detail=True, methods=['post'], url_path='apply')
    def apply_to_ebook(self, request, pk=None):
        """Apply user template to an ebook - matches frontend URL: /templates/user/{id}/apply/"""
        user_template = self.get_object()
        serializer = TemplateApplicationSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ebook_id = serializer.validated_data['ebook_id']
        
        try:
            ebook = get_object_or_404(EbookProject, pk=ebook_id)
            
            # Check permissions - user must be author or have edit access
            if not self._can_apply_template_to_ebook(ebook, request.user):
                return Response(
                    {'error': 'You do not have permission to apply templates to this ebook'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Apply the template
            updated_ebook = TemplateService.apply_template(ebook, str(user_template.id), False)
            
            # Return updated ebook data
            ebook_serializer = EbookProjectSerializer(
                updated_ebook,
                context={'request': request}
            )
            
            return Response({
                'message': f'Template "{user_template.name}" applied successfully',
                'ebook': ebook_serializer.data
            })
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to apply template: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Create a copy of this user template"""
        original_template = self.get_object()
        new_name = request.data.get('name')
        
        if not new_name:
            return Response(
                {'error': 'Name is required for the duplicated template'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_template = TemplateService.duplicate_template(
                str(original_template.id),
                request.user,
                new_name,
                False
            )
            
            serializer = self.get_serializer(new_template)
            
            return Response({
                'message': f'Template duplicated as "{new_name}"',
                'template': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to duplicate template: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def available_templates(self, request):
        """Get all templates available to the user (system + user templates)"""
        template_type = request.query_params.get('type')
        
        try:
            templates_data = TemplateService.get_templates_for_user(
                request.user,
                template_type
            )
            
            system_serializer = EbookTemplateSerializer(
                templates_data['system_templates'],
                many=True,
                context={'request': request}
            )
            
            user_serializer = UserTemplateSerializer(
                templates_data['user_templates'],
                many=True,
                context={'request': request}
            )
            
            return Response({
                'system_templates': system_serializer.data,
                'user_templates': user_serializer.data
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch templates: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['patch'])
    def customize(self, request, pk=None):
        """Customize a user template's styles and structure"""
        template = self.get_object()
        
        new_styles = request.data.get('styles', {})
        new_structure = request.data.get('structure', {})
        
        # Validate new data
        current_styles = template.styles or {}
        current_structure = template.structure or {}
        
        # Merge with existing data
        if new_styles:
            current_styles.update(new_styles)
        if new_structure:
            current_structure.update(new_structure)
        
        # Validate merged data
        is_valid, errors = TemplateService.validate_template_data(
            current_styles, 
            current_structure
        )
        
        if not is_valid:
            return Response(
                {'validation_errors': errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update template
        template.styles = current_styles
        template.structure = current_structure
        template.save()
        
        serializer = self.get_serializer(template)
        return Response({
            'message': 'Template customized successfully',
            'template': serializer.data
        })

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Generate a preview of what this user template looks like"""
        template = self.get_object()
        
        try:
            preview_data = TemplateService.get_template_preview(str(template.id), False)
            return Response(preview_data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def style_defaults(self, request):
        """Get default style and structure templates for creating new templates"""
        return Response({
            'default_styles': TemplateService.create_default_style_template(),
            'default_structure': TemplateService.create_default_structure_template()
        })

    def _can_apply_template_to_ebook(self, ebook, user):
        """Check if user can apply template to ebook"""
        return (
            ebook.author == user or 
            ebook.ebookcollaborator_set.filter(user=user, can_edit=True).exists()
        )