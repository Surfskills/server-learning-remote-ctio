from rest_framework import serializers
from .models import EbookProject, Chapter, EbookExport, EbookCollaborator
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'display_name', 'profile_picture']

class EbookProjectSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    collaborators = serializers.SerializerMethodField()
    chapter_count = serializers.SerializerMethodField()
    
    class Meta:
        model = EbookProject
        fields = [
            'id', 'title', 'description', 'status', 
            'cover_image', 'created_at', 'updated_at',
            'author', 'collaborators', 'chapter_count'
        ]
    
    def get_collaborators(self, obj):
        return EbookCollaboratorSerializer(
            obj.ebookcollaborator_set.all(),
            many=True
        ).data
    
    def get_chapter_count(self, obj):
        return obj.chapters.count()

class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = [
            'id', 'title', 'content', 'order',
            'is_draft', 'created_at', 'updated_at'
        ]
    
    def validate_content(self, value):
        # Basic validation for TipTap JSON structure
        if not isinstance(value, dict):
            raise serializers.ValidationError("Content must be a JSON object")
        return value

class EbookExportSerializer(serializers.ModelSerializer):
    generated_by = UserSerializer(read_only=True)
    download_url = serializers.SerializerMethodField()
    
    class Meta:
        model = EbookExport
        fields = [
            'id', 'format', 'file', 'generated_at',
            'version', 'file_size', 'download_count',
            'generated_by', 'download_url'
        ]
    
    def get_download_url(self, obj):
        return obj.file.url if obj.file else None

class EbookCollaboratorSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    
    class Meta:
        model = EbookCollaborator
        fields = ['id', 'user', 'role', 'can_edit', 'can_export', 'joined_at']