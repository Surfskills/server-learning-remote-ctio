# ebooks/serializers.py - Updated with template support
from rest_framework import serializers
from .models import EbookProject, Chapter, EbookExport, EbookCollaborator
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'display_name', 'profile_picture']

class EbookCollaboratorSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    
    class Meta:
        model = EbookCollaborator
        fields = ['id', 'user', 'role', 'can_edit', 'can_export', 'joined_at']

class EbookProjectSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    collaborators = serializers.SerializerMethodField()
    chapter_count = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    export_count = serializers.SerializerMethodField()
    
    class Meta:
        model = EbookProject
        fields = [
            'id', 'title', 'description', 'status', 
            'cover_image', 'cover_image_url', 'created_at', 'updated_at',
            'author', 'collaborators', 'chapter_count', 'export_count',
            'template_styles', 'template_structure'
        ]
        read_only_fields = ['author', 'created_at', 'updated_at']
    
    def get_collaborators(self, obj):
        return EbookCollaboratorSerializer(
            obj.ebookcollaborator_set.all(),
            many=True
        ).data
    
    def get_chapter_count(self, obj):
        return obj.chapters.count()
    
    def get_cover_image_url(self, obj):
        """Get absolute URL for cover image"""
        request = self.context.get('request')
        if obj.cover_image and request:
            return request.build_absolute_uri(obj.cover_image.url)
        return None
    
    def get_export_count(self, obj):
        return obj.exports.count()

    def validate_template_styles(self, value):
        """Validate template styles JSON structure"""
        if value and not isinstance(value, dict):
            raise serializers.ValidationError("Template styles must be a JSON object")
        return value

    def validate_template_structure(self, value):
        """Validate template structure JSON"""
        if value and not isinstance(value, dict):
            raise serializers.ValidationError("Template structure must be a JSON object")
        return value

class ChapterSerializer(serializers.ModelSerializer):
    word_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Chapter
        fields = [
            'id', 'title', 'content', 'order',
            'is_draft', 'created_at', 'updated_at', 'word_count'
        ]
        read_only_fields = ['created_at', 'updated_at', 'word_count']
    
    def validate_content(self, value):
        # Basic validation for TipTap JSON structure
        if not isinstance(value, dict):
            raise serializers.ValidationError("Content must be a JSON object")
        return value
    
    def get_word_count(self, obj):
        """Estimate word count from content"""
        if not obj.content or not obj.content.get('content'):
            return 0
        
        text_content = ""
        for node in obj.content.get('content', []):
            if node.get('type') == 'paragraph':
                for child in node.get('content', []):
                    if child.get('type') == 'text':
                        text_content += child.get('text', '') + " "
        
        return len(text_content.split())

class EbookExportSerializer(serializers.ModelSerializer):
    generated_by = UserSerializer(read_only=True)
    download_url = serializers.SerializerMethodField()
    ebook_title = serializers.CharField(source='ebook.title', read_only=True)
    
    class Meta:
        model = EbookExport
        fields = [
            'id', 'format', 'file', 'generated_at',
            'version', 'file_size', 'download_count',
            'generated_by', 'download_url', 'ebook_title'
        ]
        read_only_fields = ['generated_at', 'file_size', 'download_count']
    
    def get_download_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None

class EbookCreateSerializer(serializers.ModelSerializer):
    """Separate serializer for creating ebooks with template support"""
    template_id = serializers.UUIDField(required=False, write_only=True)
    is_system_template = serializers.BooleanField(default=True, write_only=True)
    
    class Meta:
        model = EbookProject
        fields = [
            'title', 'description', 'cover_image',
            'template_id', 'is_system_template'
        ]
    
    def create(self, validated_data):
        template_id = validated_data.pop('template_id', None)
        is_system_template = validated_data.pop('is_system_template', True)
        
        # Create the ebook
        ebook = super().create(validated_data)
        
        # Apply template if provided
        if template_id:
            from templates.services import TemplateService
            try:
                ebook = TemplateService.apply_template(
                    ebook, 
                    str(template_id), 
                    is_system_template
                )
            except Exception as e:
                # Log error but don't fail creation
                print(f"Warning: Failed to apply template {template_id}: {e}")
        
        return ebook