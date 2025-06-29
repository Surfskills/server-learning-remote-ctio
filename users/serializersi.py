# from rest_framework import serializers
# from authentication.serializers import UserSerializer as BaseUserSerializer
# from .models import UserProfile, UserActivity, UserPreference, UserRole, UserDevice
# from django.contrib.auth import get_user_model

# User = get_user_model()

# class ExtendedUserSerializer(BaseUserSerializer):
#     """
#     Extends the base UserSerializer with additional fields
#     """
#     class Meta(BaseUserSerializer.Meta):
#         fields = BaseUserSerializer.Meta.fields + [
#             'is_profile_complete',
#             'profile_completion_percentage'
#         ]

# class UserProfileSerializer(serializers.ModelSerializer):
#     user = ExtendedUserSerializer(read_only=True)

#     class Meta:
#         model = UserProfile
#         fields = ['user', 'bio', 'profile_picture', 'created_at', 'updated_at']
#         extra_kwargs = {
#             'bio': {'required': False, 'allow_blank': True},
#             # ... other field configurations ...
#         }


# class UserActivitySerializer(serializers.ModelSerializer):
#     user = ExtendedUserSerializer(read_only=True)

#     class Meta:
#         model = UserActivity
#         fields = '__all__'
#         read_only_fields = ['user', 'ip_address', 'user_agent']

# class UserPreferenceSerializer(serializers.ModelSerializer):
#     user = ExtendedUserSerializer(read_only=True)

#     class Meta:
#         model = UserPreference
#         fields = '__all__'
#         read_only_fields = ['user']

# class UserRoleSerializer(serializers.ModelSerializer):
#     user = ExtendedUserSerializer(read_only=True)
#     granted_by = ExtendedUserSerializer(read_only=True)

#     class Meta:
#         model = UserRole
#         fields = '__all__'

# class UserDeviceSerializer(serializers.ModelSerializer):
#     user = ExtendedUserSerializer(read_only=True)

#     class Meta:
#         model = UserDevice
#         fields = '__all__'
#         read_only_fields = ['user', 'last_active']

# class UserDetailSerializer(ExtendedUserSerializer):
#     """
#     Comprehensive user details serializer that includes all related data
#     """
#     profile = UserProfileSerializer(source='extended_profile', read_only=True)
#     preferences = UserPreferenceSerializer(read_only=True)
#     roles = UserRoleSerializer(many=True, read_only=True)
#     devices = UserDeviceSerializer(many=True, read_only=True)

#     class Meta(ExtendedUserSerializer.Meta):
#         fields = ExtendedUserSerializer.Meta.fields + [
#             'profile',
#             'preferences',
#             'roles',
#             'devices'
#         ]