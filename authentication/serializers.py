from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenVerifySerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Profile


class SignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    user_type = serializers.ChoiceField(
        choices=User.Types.choices, 
        required=False, 
        default=User.Types.STUDENT
    )

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'user_type', 'first_name', 'last_name']
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
        }
    
    def create(self, validated_data):
        user_type = validated_data.get('user_type', User.Types.STUDENT)
        validated_data['user_type'] = user_type
        
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            user_type=user_type,
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user


class SignInSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError("Invalid credentials")

        if not user.check_password(password):
            raise ValidationError("Invalid credentials")
        
        if not user.is_active:
            raise ValidationError("User account is disabled")

        attrs['user'] = user
        return attrs


class ProfileSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField()
    
    class Meta:
        model = Profile
        fields = ['id', 'bio', 'location', 'website', 'company', 'timezone',
                 'linkedin_url', 'github_url', 'twitter_url',
                 'email_notifications', 'sms_notifications',
                 'created_at', 'updated_at', 'name']
        read_only_fields = ['id', 'name', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    display_name = serializers.ReadOnlyField()
    profile_completion_percentage = serializers.ReadOnlyField()
    is_profile_complete = serializers.ReadOnlyField()
    
    # Role check properties
    is_admin = serializers.ReadOnlyField()
    is_instructor = serializers.ReadOnlyField()
    is_student = serializers.ReadOnlyField()
    is_support_agent = serializers.ReadOnlyField()
    is_ebook_creator = serializers.ReadOnlyField()
    is_premium_member = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'display_name',
            'user_type', 'is_staff', 'is_active', 'phone_number', 'profile_picture',
            'profile_completion_percentage', 'is_profile_complete',
            'is_admin', 'is_instructor', 'is_student', 'is_support_agent',
            'is_ebook_creator', 'is_premium_member',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InstructorSerializer(serializers.ModelSerializer):
    """Simplified serializer for instructor listings"""
    full_name = serializers.ReadOnlyField()
    profile_completion = serializers.IntegerField(source='profile_completion_percentage')
    
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'profile_picture', 'profile_completion']
        

class UserProfileSerializer(serializers.ModelSerializer):
    """Combined serializer for User and Profile data"""
    profile = ProfileSerializer(read_only=True)
    full_name = serializers.ReadOnlyField()
    display_name = serializers.ReadOnlyField()
    profile_completion_percentage = serializers.ReadOnlyField()
    is_profile_complete = serializers.ReadOnlyField()
    
    # Role check properties
    is_admin = serializers.ReadOnlyField()
    is_instructor = serializers.ReadOnlyField()
    is_student = serializers.ReadOnlyField()
    is_support_agent = serializers.ReadOnlyField()
    is_ebook_creator = serializers.ReadOnlyField()
    is_premium_member = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'display_name',
            'user_type', 'is_staff', 'is_active', 'phone_number', 'profile_picture',
            'profile_completion_percentage', 'is_profile_complete',
            'is_admin', 'is_instructor', 'is_student', 'is_support_agent',
            'is_ebook_creator', 'is_premium_member',
            'profile', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CustomTokenVerifySerializer(TokenVerifySerializer):
    """Custom token verify serializer that provides better error messages"""
    def validate(self, attrs):
        try:
            return super().validate(attrs)
        except Exception as e:
            raise ValidationError({
                'token': ['Token is invalid or expired']
            })


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    """Custom token refresh serializer that provides better error messages"""
    def validate(self, attrs):
        try:
            return super().validate(attrs)
        except Exception as e:
            raise ValidationError({
                'refresh': ['Refresh token is invalid or expired']
            })


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for password reset requests"""
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
            if not user.is_active:
                raise ValidationError("User account is disabled")
        except User.DoesNotExist:
            raise ValidationError("No user found with this email address")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user information"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'profile_picture']
        
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        # Trigger profile completion calculation
        instance.calculate_profile_completion()
        return instance


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating profile information"""
    class Meta:
        model = Profile
        fields = [
            'bio', 'location', 'website', 'company', 'timezone',
            'linkedin_url', 'github_url', 'twitter_url', 
            'email_notifications', 'sms_notifications'
        ]
        
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        # Trigger profile completion calculation for the user
        instance.user.calculate_profile_completion()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing user password"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise ValidationError("Old password is incorrect")
        return value
    
    def validate_new_password(self, value):
        if len(value) < 8:
            raise ValidationError("New password must be at least 8 characters long")
        return value