from rest_framework import serializers


from .models import Course, CourseCategory, CourseSection, Lecture, LectureResource, ProjectTool, QaItem, Quiz, QuizQuestion, QuizTask
from authentication.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'user_type', 'is_active', 'profile_picture']
        read_only_fields = ['id', 'user_type', 'is_active']

class CourseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseCategory
        fields = '__all__'

class InstructorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'profile_picture']

class QuizQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestion
        fields = '__all__'
        read_only_fields = ['quiz', 'order']

class QuizTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizTask
        fields = '__all__'
        read_only_fields = ['quiz', 'order']

class QuizSerializer(serializers.ModelSerializer):
    questions = QuizQuestionSerializer(many=True, read_only=True)
    tasks = QuizTaskSerializer(many=True, read_only=True)
    
    class Meta:
        model = Quiz
        fields = '__all__'
        read_only_fields = ['course', 'section', 'lecture']

class QaItemSerializer(serializers.ModelSerializer):
    asked_by = UserSerializer(read_only=True)
    
    class Meta:
        model = QaItem
        fields = '__all__'
        read_only_fields = ['lecture', 'asked_by', 'upvotes']

class ProjectToolSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectTool
        fields = '__all__'
        read_only_fields = ['lecture']

class LectureResourceSerializer(serializers.ModelSerializer):
    resource_type = serializers.CharField(source='kind')
    file_url = serializers.URLField(source='url', required=False)
    external_url = serializers.URLField(source='url', required=False)
    
    class Meta:
        model = LectureResource
        fields = [
            'id', 'title', 'resource_type', 'kind', 'url', 'file_url', 
            'external_url', 'provider', 'duration_seconds', 'is_downloadable', 
            'file_size', 'mime_type', 'created_at', 'updated_at'
        ]
        read_only_fields = ['lecture', 'created_at', 'updated_at']

    def create(self, validated_data):
        if 'kind' in validated_data:
            validated_data['kind'] = validated_data.get('kind', validated_data.get('resource_type'))
        if 'url' in validated_data:
            validated_data['url'] = validated_data.get('url', validated_data.get('file_url') or validated_data.get('external_url'))
        return super().create(validated_data)

class LectureSerializer(serializers.ModelSerializer):
    resources = LectureResourceSerializer(many=True, read_only=True)
    qa_items = QaItemSerializer(many=True, read_only=True)
    project_tools = ProjectToolSerializer(many=True, read_only=True)
    quiz = QuizSerializer(read_only=True)
    is_completed = serializers.SerializerMethodField()
    video_url = serializers.URLField(required=False, allow_blank=True)
    description = serializers.CharField(source='overview', required=False, allow_blank=True, allow_null=True, default='')
    previewAvailable = serializers.BooleanField(source='preview_available', read_only=True)

    class Meta:
        model = Lecture
        fields = [
            'id', 'title', 'order', 'duration', 'overview', 'description',
            'preview_available', 'previewAvailable', 'video_url', 'resources',
            'is_completed', 'created_at', 'updated_at', 'qa_items', 'project_tools', 'quiz'
        ]
        read_only_fields = ['section', 'order', 'created_at', 'updated_at']

    def get_is_completed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                from enrollments.models import Enrollment
                enrollment = Enrollment.objects.filter(
                    student=request.user,
                    course=obj.section.course
                ).first()
                if enrollment and hasattr(enrollment, 'progress'):
                    return enrollment.progress.completed_lectures.filter(id=obj.id).exists()
            except ImportError:
                pass
        return False

class LectureCreateSerializer(serializers.ModelSerializer):
    description = serializers.CharField(source='overview', required=False, allow_blank=True)
    video_url = serializers.URLField(required=False, allow_blank=True)
    quiz = QuizSerializer(required=False) 
    
    class Meta:
        model = Lecture
        fields = ['title', 'duration', 'overview', 'description', 'preview_available', 'video_url', 'quiz']

    def create(self, validated_data):
        quiz_data = validated_data.pop('quiz', None)
        section_id = self.context['view'].kwargs.get('section_pk')
        
        lecture = super().create(validated_data)
        
        if quiz_data:
            quiz_data['lecture'] = lecture.id
            quiz_data['section'] = lecture.section.id
            quiz_data['course'] = lecture.section.course.id
            
            quiz_serializer = QuizSerializer(data=quiz_data, context=self.context)
            if quiz_serializer.is_valid():
                quiz_serializer.save()
        
        return lecture

class CourseSerializer(serializers.ModelSerializer):
    instructor = InstructorSerializer(read_only=True)
    category = CourseCategorySerializer(read_only=True)
    instructor_id = serializers.IntegerField(write_only=True, required=False)  # Make it optional
    category_id = serializers.UUIDField(write_only=True)
    thumbnail = serializers.ImageField(required=False, write_only=True)
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'level', 'language', 'price',
            'instructor', 'instructor_id', 'category', 'category_id',
            'thumbnail', 'banner_url', 'preview_video_url', 'duration',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'instructor', 'category', 'banner_url', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Handle thumbnail file upload
        thumbnail = validated_data.pop('thumbnail', None)
        
        # Get instructor - either from validated_data or from the view
        instructor_id = validated_data.pop('instructor_id', None)
        instructor = validated_data.pop('instructor', None)  # This comes from perform_create
        
        # If instructor is not provided via perform_create, get it from instructor_id
        if not instructor and instructor_id:
            try:
                instructor = User.objects.get(id=instructor_id)
            except User.DoesNotExist:
                raise serializers.ValidationError({'instructor_id': 'Instructor not found'})
        
        if not instructor:
            raise serializers.ValidationError({'instructor': 'Instructor is required'})
        
        # Get category
        try:
            category = CourseCategory.objects.get(id=validated_data.pop('category_id'))
        except CourseCategory.DoesNotExist:
            raise serializers.ValidationError({'category_id': 'Category not found'})
        
        # Create course instance
        course = Course.objects.create(
            instructor=instructor,
            category=category,
            **validated_data
        )
        
        # Handle thumbnail if provided
        if thumbnail:
            course.thumbnail = thumbnail
            course.save()
        
        return course

    def validate_level(self, value):
        """
        Clean and validate the level field:
        1. Remove surrounding quotes if present
        2. Convert to lowercase
        3. Validate against choices
        """
        if isinstance(value, str):
            # Strip quotes and convert to lowercase
            cleaned_value = value.strip('"\' ').lower()
            
            # Get valid choices from model
            valid_levels = [choice[0] for choice in Course.LEVEL_CHOICES]
            
            if cleaned_value not in valid_levels:
                raise serializers.ValidationError(
                    f"'{value}' is not a valid choice. Must be one of: {valid_levels}"
                )
            return cleaned_value
        return value

    def validate(self, data):
        """Ensure level gets validated if present"""
        if 'level' in data:
            data['level'] = self.validate_level(data['level'])
        return data

    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Import here to avoid circular imports
            try:
                from enrollments.models import Enrollment
                return Enrollment.objects.filter(student=request.user, course=obj).exists()
            except ImportError:
                return False
        return False



class AdminCourseSerializer(CourseSerializer):
    """Extended serializer for admin views with additional fields"""
    enrollment_count = serializers.IntegerField(source='students_enrolled', read_only=True)
    status = serializers.SerializerMethodField()
    
    class Meta(CourseSerializer.Meta):
        fields = CourseSerializer.Meta.fields + ['enrollment_count', 'status']
    
    def get_status(self, obj):
        if not obj.is_published:
            return 'draft'
        elif not getattr(obj, 'is_active', True):  # Assuming you have is_active field
            return 'archived'
        else:
            return 'published'

class CourseSectionSerializer(serializers.ModelSerializer):
    lectures_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseSection
        fields = '__all__'
        read_only_fields = ['course', 'order']

    def get_lectures_count(self, obj):
        return obj.lectures.count()



# Additional serializers for detailed responses
class CourseDetailSerializer(CourseSerializer):
    """Detailed course serializer with sections and lectures"""
    sections = serializers.SerializerMethodField()
    
    class Meta(CourseSerializer.Meta):
        fields = CourseSerializer.Meta.fields + ['sections']
    
    def get_sections(self, obj):
        sections = obj.sections.all().order_by('order')
        return [
            {
                'id': section.id,
                'title': section.title,
                'order': section.order,
                'lectures': [
                    {
                        'id': lecture.id,
                        'title': lecture.title,
                        'duration': lecture.duration,
                        'previewAvailable': lecture.preview_available
                    }
                    for lecture in section.lectures.all().order_by('order')
                ]
            }
            for section in sections
        ]