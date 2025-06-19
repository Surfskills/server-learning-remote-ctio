from rest_framework import serializers
from .models import Enrollment, CourseProgress
from courses.serializers import CourseSerializer
from authentication.models import User
from core.serializers import EmptySerializer

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']
        read_only_fields = fields

class EnrollmentSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = '__all__'
        read_only_fields = [
            'student', 'course', 'enrolled_at', 
            'progress_percentage', 'last_accessed'
        ]

class CourseProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseProgress
        fields = '__all__'
        read_only_fields = ['enrollment']

class EnrollmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ['course']
        extra_kwargs = {'course': {'required': True}}

    def create(self, validated_data):
        request = self.context.get('request')
        course = validated_data['course']
        
        if Enrollment.objects.filter(student=request.user, course=course).exists():
            raise serializers.ValidationError("Already enrolled in this course")
        
        enrollment = Enrollment.objects.create(
            student=request.user,
            course=course
        )
        CourseProgress.objects.create(enrollment=enrollment)
        return enrollment