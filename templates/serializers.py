# templates/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import EbookTemplate, UserTemplate

User = get_user_model()


class EbookTemplateSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = EbookTemplate
        fields = [
            'id', 'name', 'description', 'type',
            'thumbnail', 'thumbnail_url', 'is_default', 'is_premium',
            'cover_image', 'cover_image_url', 'styles', 'structure',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_thumbnail_url(self, obj):
        """Get absolute URL for thumbnail"""
        request = self.context.get('request')
        if obj.thumbnail and request:
            return request.build_absolute_uri(obj.thumbnail.url)
        return None

    def get_cover_image_url(self, obj):
        """Get absolute URL for cover image"""
        request = self.context.get('request')
        if obj.cover_image and request:
            return request.build_absolute_uri(obj.cover_image.url)
        return None

    def validate_styles(self, value):
        """Validate styles JSON structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Styles must be a JSON object")
        return value

    def validate_structure(self, value):
        """Validate structure JSON"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Structure must be a JSON object")
        return value


class UserTemplateSerializer(serializers.ModelSerializer):
    base_template = EbookTemplateSerializer(read_only=True)
    base_template_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = UserTemplate
        fields = [
            'id', 'base_template', 'base_template_id', 'name',
            'styles', 'structure', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

    def validate_styles(self, value):
        """Validate styles JSON structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Styles must be a JSON object")
        return value

    def validate_structure(self, value):
        """Validate structure JSON"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Structure must be a JSON object")
        return value

    def create(self, validated_data):
        """Handle base_template_id during creation"""
        base_template_id = validated_data.pop('base_template_id', None)
        
        if base_template_id:
            try:
                base_template = EbookTemplate.objects.get(pk=base_template_id)
                validated_data['base_template'] = base_template
            except EbookTemplate.DoesNotExist:
                raise serializers.ValidationError({
                    'base_template_id': 'Invalid template ID'
                })
        
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Handle base_template_id during update"""
        base_template_id = validated_data.pop('base_template_id', None)
        
        if base_template_id is not None:
            if base_template_id:
                try:
                    base_template = EbookTemplate.objects.get(pk=base_template_id)
                    validated_data['base_template'] = base_template
                except EbookTemplate.DoesNotExist:
                    raise serializers.ValidationError({
                        'base_template_id': 'Invalid template ID'
                    })
            else:
                validated_data['base_template'] = None
        
        return super().update(instance, validated_data)


class TemplateApplicationSerializer(serializers.Serializer):
    """Serializer for applying templates to ebooks"""
    ebook_id = serializers.UUIDField()
    
    def validate_ebook_id(self, value):
        """Validate that ebook exists and user has access"""
        from ebooks.models import EbookProject
        
        try:
            ebook = EbookProject.objects.get(pk=value)
            user = self.context['request'].user
            
            # Check if user is author or has edit permissions
            if (ebook.author != user and 
                not ebook.ebookcollaborator_set.filter(user=user, can_edit=True).exists()):
                raise serializers.ValidationError("You don't have permission to apply templates to this ebook")
            
            return value
        except EbookProject.DoesNotExist:
            raise serializers.ValidationError("Ebook not found")