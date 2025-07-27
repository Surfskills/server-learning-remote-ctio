# ebooks/views.py - Updated with consistent URL methods
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import models
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import CanExportEbook, CanManageEbooks
from .models import EbookProject, Chapter, EbookExport, EbookCollaborator
from .services import EbookExportService
from .serializers import (
    EbookCollaboratorSerializer,
    EbookProjectSerializer,
    ChapterSerializer,
)


class EbookProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ebook projects.
    Provides CRUD operations plus publish and export actions.
    """
    serializer_class = EbookProjectSerializer
    permission_classes = [IsAuthenticated, CanManageEbooks]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'created_at']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'title']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter to show only user's ebooks or collaborations"""
        user = self.request.user
        
        return EbookProject.objects.filter(
            models.Q(author=user) |
            models.Q(ebookcollaborator__user=user)
        ).distinct().select_related('author').prefetch_related(
            'ebookcollaborator_set__user'
        )

    def perform_create(self, serializer):
        """Set the current user as author when creating"""
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish an ebook (author only)"""
        ebook = self.get_object()
        
        if ebook.author != request.user:
            return Response(
                {'error': 'Only the author can publish this ebook'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not ebook.chapters.exists():
            return Response(
                {'error': 'Cannot publish an ebook without chapters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ebook.status = EbookProject.Status.PUBLISHED
        ebook.save()
        
        return Response({
            'status': 'published',
            'message': 'Ebook published successfully'
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanExportEbook])
    def export_pdf(self, request, pk=None):
        """Export ebook as PDF"""
        return self._handle_export(request, pk, EbookExport.Format.PDF)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanExportEbook])
    def export_epub(self, request, pk=None):
        """Export ebook as EPUB"""
        return self._handle_export(request, pk, EbookExport.Format.EPUB)

    def _handle_export(self, request, pk, format_type):
        """Handle export operations (PDF/EPUB)"""
        ebook = self.get_object()
        
        # Check export permissions
        if not self._can_export(ebook, request.user):
            return Response(
                {'error': 'You do not have permission to export this ebook'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not ebook.chapters.exists():
            return Response(
                {'error': 'Cannot export an ebook without chapters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Generate export file
            export_service = EbookExportService()
            if format_type == EbookExport.Format.PDF:
                file_obj = export_service.export_to_pdf(ebook)
                content_type = 'application/pdf'
                filename = f"{ebook.title}.pdf"
            else:
                file_obj = export_service.export_to_epub(ebook)
                content_type = 'application/epub+zip'
                filename = f"{ebook.title}.epub"
            
            # Create export record
            export = EbookExport.objects.create(
                ebook=ebook,
                format=format_type,
                file=file_obj,
                generated_by=request.user,
                version="1.0",
                file_size=file_obj.size if hasattr(file_obj, 'size') else 0
            )
            
            # Return download response
            response = HttpResponse(
                file_obj.read(),
                content_type=content_type
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        except Exception as e:
            return Response(
                {'error': f'Export failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _can_export(self, ebook, user):
        """Check if user can export the ebook"""
        return (
            ebook.author == user or 
            ebook.ebookcollaborator_set.filter(user=user, can_export=True).exists()
        )


class ChapterViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing chapters within an ebook.
    Nested under ebook projects.
    """
    serializer_class = ChapterSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['order', 'created_at']

    def get_queryset(self):
        """Get chapters for the specific ebook"""
        ebook_pk = self.kwargs.get('ebook_pk')
        ebook = get_object_or_404(EbookProject, pk=ebook_pk)
        
        # Check edit permissions
        if not self._can_edit_ebook(ebook, self.request.user):
            return Chapter.objects.none()
        
        return Chapter.objects.filter(ebook=ebook)

    def perform_create(self, serializer):
        """Create chapter for the specific ebook"""
        ebook_pk = self.kwargs.get('ebook_pk')
        ebook = get_object_or_404(EbookProject, pk=ebook_pk)
        
        if not self._can_edit_ebook(ebook, self.request.user):
            raise PermissionError("You don't have permission to edit this ebook")
        
        # Auto-assign order if not provided
        if not serializer.validated_data.get('order'):
            last_chapter = ebook.chapters.order_by('-order').first()
            next_order = (last_chapter.order + 1) if last_chapter else 1
            serializer.validated_data['order'] = next_order
        
        serializer.save(ebook=ebook)

    def perform_update(self, serializer):
        """Ensure user can edit before updating"""
        chapter = self.get_object()
        if not self._can_edit_ebook(chapter.ebook, self.request.user):
            raise PermissionError("You don't have permission to edit this chapter")
        serializer.save()

    def perform_destroy(self, instance):
        """Ensure user can edit before deleting"""
        if not self._can_edit_ebook(instance.ebook, self.request.user):
            raise PermissionError("You don't have permission to delete this chapter")
        instance.delete()

    def _can_edit_ebook(self, ebook, user):
        """Check if user can edit the ebook"""
        return (
            ebook.author == user or 
            ebook.ebookcollaborator_set.filter(user=user, can_edit=True).exists()
        )


class EbookCollaboratorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ebook collaborators.
    Only ebook authors can manage collaborators.
    """
    serializer_class = EbookCollaboratorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Get collaborators for the specific ebook (author only)"""
        ebook_pk = self.kwargs.get('ebook_pk')
        ebook = get_object_or_404(EbookProject, pk=ebook_pk)
        
        if ebook.author != self.request.user:
            return EbookCollaborator.objects.none()
        
        return EbookCollaborator.objects.filter(ebook=ebook)

    def perform_create(self, serializer):
        """Add collaborator to the specific ebook"""
        ebook_pk = self.kwargs.get('ebook_pk')
        ebook = get_object_or_404(EbookProject, pk=ebook_pk)
        
        if ebook.author != self.request.user:
            raise PermissionError("Only the author can manage collaborators")
        
        serializer.save(ebook=ebook)

    def perform_update(self, serializer):
        """Update collaborator permissions (author only)"""
        collaborator = self.get_object()
        if collaborator.ebook.author != self.request.user:
            raise PermissionError("Only the author can manage collaborators")
        serializer.save()

    def perform_destroy(self, instance):
        """Remove collaborator (author only)"""
        if instance.ebook.author != self.request.user:
            raise PermissionError("Only the author can manage collaborators")
        instance.delete()



from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import EbookProject
from templates.models import EbookTemplate, UserTemplate


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    """
    Get dashboard summary with key metrics and recent activity
    URL: GET /api/ebooks/dashboard/
    """
    user = request.user
    
    # Get date ranges for filtering
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    try:
        # ============= EBOOK STATISTICS =============
        
        # Get user's ebooks (authored + collaborated)
        user_ebooks = EbookProject.objects.filter(
            Q(author=user) | Q(ebookcollaborator__user=user),
            deleted_at__isnull=True
        ).distinct()
        
        # Basic ebook counts
        total_ebooks = user_ebooks.count()
        published_ebooks = user_ebooks.filter(status=EbookProject.Status.PUBLISHED).count()
        draft_ebooks = user_ebooks.filter(status=EbookProject.Status.DRAFT).count()
        
        # Recent activity counts
        recent_ebooks = user_ebooks.filter(
            created_at__date__gte=week_ago
        ).count()
        
        # Collaboration stats
        authored_count = user_ebooks.filter(author=user).count()
        collaborating_count = user_ebooks.filter(
            ebookcollaborator__user=user
        ).exclude(author=user).distinct().count()
        
        # ============= CHAPTER STATISTICS =============
        
        # Get chapters from user's ebooks
        user_chapters = Chapter.objects.filter(ebook__in=user_ebooks)
        total_chapters = user_chapters.count()
        draft_chapters = user_chapters.filter(is_draft=True).count()
        published_chapters = user_chapters.filter(is_draft=False).count()
        
        # Recent chapter activity
        recent_chapters = user_chapters.filter(
            updated_at__date__gte=week_ago
        ).count()
        
        # ============= EXPORT STATISTICS =============
        
        # Get exports for user's ebooks
        user_exports = EbookExport.objects.filter(ebook__in=user_ebooks)
        total_exports = user_exports.count()
        recent_exports = user_exports.filter(
            generated_at__date__gte=week_ago
        ).count()
        
        # Export format breakdown
        export_formats = user_exports.values('format').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Total downloads
        total_downloads = sum(export.download_count for export in user_exports)
        
        # ============= TEMPLATE STATISTICS =============
        
        # User's custom templates
        user_templates_count = UserTemplate.objects.filter(user=user).count()
        recent_user_templates = UserTemplate.objects.filter(
            user=user,
            created_at__date__gte=week_ago
        ).count()
        
        # Available system templates
        available_system_templates = EbookTemplate.objects.filter(
            Q(is_premium=False) | Q(is_premium=True, is_default=True)
        ).count()
        
        if hasattr(user, 'has_premium_access') and user.has_premium_access:
            available_system_templates = EbookTemplate.objects.count()
        
        # ============= RECENT ACTIVITY =============
        
        # Recent ebooks (last 5)
        recent_ebook_list = user_ebooks.select_related('author').order_by('-updated_at')[:5]
        recent_ebooks_data = []
        
        for ebook in recent_ebook_list:
            recent_ebooks_data.append({
                'id': str(ebook.id),
                'title': ebook.title,
                'status': ebook.status,
                'updated_at': ebook.updated_at,
                'chapter_count': ebook.chapters.count(),
                'is_author': ebook.author == user
            })
        
        # Recent chapters (last 5)
        recent_chapter_list = user_chapters.select_related('ebook').order_by('-updated_at')[:5]
        recent_chapters_data = []
        
        for chapter in recent_chapter_list:
            recent_chapters_data.append({
                'id': str(chapter.id),
                'title': chapter.title,
                'ebook_title': chapter.ebook.title,
                'ebook_id': str(chapter.ebook.id),
                'is_draft': chapter.is_draft,
                'updated_at': chapter.updated_at,
                'order': chapter.order
            })
        
        # Recent exports (last 5)
        recent_export_list = user_exports.select_related('ebook', 'generated_by').order_by('-generated_at')[:5]
        recent_exports_data = []
        
        for export in recent_export_list:
            recent_exports_data.append({
                'id': str(export.id),
                'ebook_title': export.ebook.title,
                'ebook_id': str(export.ebook.id),
                'format': export.format,
                'generated_at': export.generated_at,
                'file_size': export.file_size,
                'download_count': export.download_count,
                'generated_by': export.generated_by.display_name if export.generated_by else 'Unknown'
            })
        
        # Recent user templates (last 3)
        recent_template_list = UserTemplate.objects.filter(user=user).order_by('-updated_at')[:3]
        recent_templates_data = []
        
        for template in recent_template_list:
            recent_templates_data.append({
                'id': str(template.id),
                'name': template.name,
                'updated_at': template.updated_at,
                'base_template_name': template.base_template.name if template.base_template else None
            })
        
        # ============= QUICK ACTIONS DATA =============
        
        # Get default templates for quick creation
        default_templates = EbookTemplate.objects.filter(is_default=True).order_by('type')
        default_templates_data = []
        
        for template in default_templates:
            default_templates_data.append({
                'id': str(template.id),
                'name': template.name,
                'type': template.type,
                'thumbnail_url': template.thumbnail.url if template.thumbnail else None
            })
        
        # ============= BUILD RESPONSE =============
        
        dashboard_data = {
            # Summary statistics
            'statistics': {
                'ebooks': {
                    'total': total_ebooks,
                    'published': published_ebooks,
                    'drafts': draft_ebooks,
                    'recent': recent_ebooks,
                    'authored': authored_count,
                    'collaborating': collaborating_count
                },
                'chapters': {
                    'total': total_chapters,
                    'published': published_chapters,
                    'drafts': draft_chapters,
                    'recent': recent_chapters
                },
                'exports': {
                    'total': total_exports,
                    'recent': recent_exports,
                    'total_downloads': total_downloads,
                    'formats': [
                        {'format': item['format'], 'count': item['count']}
                        for item in export_formats
                    ]
                },
                'templates': {
                    'user_templates': user_templates_count,
                    'recent_user_templates': recent_user_templates,
                    'available_system_templates': available_system_templates
                }
            },
            
            # Recent activity
            'recent_activity': {
                'ebooks': recent_ebooks_data,
                'chapters': recent_chapters_data,
                'exports': recent_exports_data,
                'templates': recent_templates_data
            },
            
            # Quick actions
            'quick_actions': {
                'default_templates': default_templates_data
            },
            
            # User info
            'user': {
                'id': str(user.id),
                'display_name': user.display_name,
                'has_premium_access': getattr(user, 'has_premium_access', False)
            },
            
            # Metadata
            'generated_at': timezone.now(),
            'date_ranges': {
                'week_ago': week_ago,
                'month_ago': month_ago
            }
        }
        
        return Response(dashboard_data)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to generate dashboard: {str(e)}'},
            status=500
        )