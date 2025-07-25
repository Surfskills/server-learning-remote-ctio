from rest_framework import serializers
from django.db import models 

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
    prerequisites = serializers.PrimaryKeyRelatedField(
            many=True, 
            queryset=Course.objects.all(), 
            required=False
        )
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'level', 'language', 'price',
            'instructor', 'instructor_id', 'category', 'category_id', 'slug',
    'banner_url', 'preview_video_url', 'duration','thumbnail',
            'what_you_will_learn', 'who_is_this_for',
            'prerequisites', 'long_description', 'certificate_available',
            'lifetime_access', 'is_published', 'is_active'
        ]
        read_only_fields = ['id', 'instructor', 'category', 'created_at', 'updated_at']
    def update(self, instance, validated_data):
        thumbnail = validated_data.pop('thumbnail', None)
        
        # Handle many-to-many fields separately
        prerequisites = validated_data.pop('prerequisites', None)
        # Add other M2M fields as needed
        
        # Update all other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Handle thumbnail if provided
        if thumbnail:
            instance.thumbnail = thumbnail
        
        instance.save()
        
        # Handle many-to-many relationships
        if prerequisites is not None:
            instance.prerequisites.set(prerequisites)
        
        return instance
    def create(self, validated_data):
        # Handle thumbnail file upload
        thumbnail = validated_data.pop('thumbnail', None)
        
        # Extract many-to-many fields before creating the instance
        prerequisites = validated_data.pop('prerequisites', None)
        # Add any other M2M fields you might have, for example:
        # tags = validated_data.pop('tags', None)
        # related_courses = validated_data.pop('related_courses', None)
        
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
        
        # Create course instance (without M2M fields)
        course = Course.objects.create(
            instructor=instructor,
            category=category,
            **validated_data
        )
        
        # Handle thumbnail if provided
        if thumbnail:
            course.thumbnail = thumbnail
            course.save()
        
        # Handle many-to-many relationships after the instance is created
        if prerequisites is not None:
            course.prerequisites.set(prerequisites)
        
        # Handle other M2M fields if you have them:
        # if tags is not None:
        #     course.tags.set(tags)
        # if related_courses is not None:
        #     course.related_courses.set(related_courses)
        
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

class CourseListSerializer(serializers.ModelSerializer):
    instructor = InstructorSerializer(read_only=True)
    category = CourseCategorySerializer(read_only=True)
    is_enrolled = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()
    total_lectures = serializers.SerializerMethodField()
    completed_lectures = serializers.SerializerMethodField()
    duration_hours = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'description',
            'level',
            'language',
            'price',
            'instructor',
            'category',
            'slug',
            'banner_url',
            'duration',
            'duration_hours',
            'rating',
            'review_count',
            'students_enrolled',
            'is_enrolled',
            'progress_percentage',
            'total_lectures',
            'completed_lectures',
            'created_at'
        ]
        read_only_fields = fields

    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.enrollments.filter(student=request.user).exists()
        return False

    def get_progress_percentage(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            enrollment = obj.enrollments.filter(student=request.user).first()
            if enrollment:
                return enrollment.progress_percentage
        return 0

    def get_total_lectures(self, obj):
        return obj.lectures.count()

    def get_completed_lectures(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            enrollment = obj.enrollments.filter(student=request.user).first()
            if enrollment and hasattr(enrollment, 'progress'):
                return enrollment.progress.completed_lectures.count()
        return 0

    def get_duration_hours(self, obj):
        if obj.duration:
            return round(obj.duration / 60, 1)
        return 0

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
    """
    Extended serializer that includes all nested data for the course detail page.
    """
    sections = CourseSectionSerializer(many=True, read_only=True)
    instructor = UserSerializer(read_only=True)  # You'll need a UserSerializer
    is_enrolled = serializers.SerializerMethodField()
    resources_count = serializers.SerializerMethodField()
    qa_items = serializers.SerializerMethodField()
    qa_items_count = serializers.SerializerMethodField()
    project_tools = serializers.SerializerMethodField()
    project_tools_count = serializers.SerializerMethodField()
    quiz = serializers.SerializerMethodField()
    quizzes_count = serializers.SerializerMethodField()
    has_quiz = serializers.SerializerMethodField()
    
    class Meta(CourseSerializer.Meta):
        fields = CourseSerializer.Meta.fields + [
            'long_description',
            'banner_url',
            'preview_video_url',
            'sections',
            'instructor',
            'is_enrolled',
            'rating',
            'review_count',
            'students_enrolled',
            'duration',
            'created_at',
            'updated_at',
            'language',
            'level',
            'prerequisites',
            'what_you_will_learn',
            'who_is_this_for',
            'certificate_available',
            'resources_available',
            'lifetime_access',
        ]
    
    def get_resources_count(self, obj):
        return obj.sections.aggregate(
            count=models.Count('lectures__resources')
        )['count'] or 0
    
    def get_qa_items(self, obj):
        return obj.sections.aggregate(
            count=models.Count('lectures__qa_items')
        )['count'] or 0
    
    def get_qa_items_count(self, obj):
        return self.get_qa_items(obj)
    
    def get_project_tools(self, obj):
        return obj.sections.aggregate(
            count=models.Count('lectures__project_tools')
        )['count'] or 0
    
    def get_project_tools_count(self, obj):
        return self.get_project_tools(obj)
    
    def get_quiz(self, obj):
        # Count quizzes at all levels
        lecture_quizzes = obj.sections.aggregate(
            count=models.Count('lectures__quiz')
        )['count'] or 0
        
        section_quizzes = obj.sections.filter(quiz__isnull=False).count()
        course_quizzes = Quiz.objects.filter(course=obj, section__isnull=True, lecture__isnull=True).count()
        
        return lecture_quizzes + section_quizzes + course_quizzes
    
    def get_quizzes_count(self, obj):
        return self.get_quiz(obj)
    
    def get_has_quiz(self, obj):
        return self.get_quiz(obj) > 0

    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.enrollments.filter(student=request.user).exists()
        return False
    


class DetailQuizQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestion
        fields = '__all__'

class DetailQuizTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizTask
        fields = '__all__'

class DetailQuizSerializer(serializers.ModelSerializer):
    questions = DetailQuizQuestionSerializer(many=True, read_only=True)
    tasks = DetailQuizTaskSerializer(many=True, read_only=True)
    questions_count = serializers.SerializerMethodField()
    tasks_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Quiz
        fields = '__all__'
    
    def get_questions_count(self, obj):
        return obj.questions.count()
    
    def get_tasks_count(self, obj):
        return obj.tasks.count()

class DetailQaItemSerializer(serializers.ModelSerializer):
    asked_by = UserSerializer(read_only=True)
    answers_count = serializers.SerializerMethodField()
    
    class Meta:
        model = QaItem
        fields = '__all__'
    
    def get_answers_count(self, obj):
        # If you have answers related to QA items, count them here
        # return obj.answers.count()
        return 0  # Placeholder

class DetailProjectToolSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectTool
        fields = '__all__'

class DetailLectureResourceSerializer(serializers.ModelSerializer):
    resource_type = serializers.CharField(source='kind')
    file_url = serializers.URLField(source='url', required=False)
    external_url = serializers.URLField(source='url', required=False)
    file_size_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = LectureResource
        fields = [
            'id', 'title', 'resource_type', 'kind', 'url', 'file_url', 
            'external_url', 'provider', 'duration_seconds', 'is_downloadable', 
            'file_size', 'file_size_formatted', 'mime_type', 'created_at', 'updated_at'
        ]
    
    def get_file_size_formatted(self, obj):
        """Convert file size to human readable format"""
        if not obj.file_size:
            return None
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if obj.file_size < 1024.0:
                return f"{obj.file_size:.1f} {unit}"
            obj.file_size /= 1024.0
        return f"{obj.file_size:.1f} TB"

class DetailLectureSerializer(serializers.ModelSerializer):
    resources = DetailLectureResourceSerializer(many=True, read_only=True)
    qa_items = DetailQaItemSerializer(many=True, read_only=True)
    project_tools = DetailProjectToolSerializer(many=True, read_only=True)
    quiz = DetailQuizSerializer(read_only=True)
    is_completed = serializers.SerializerMethodField()
    video_url = serializers.URLField(required=False, allow_blank=True)
    description = serializers.CharField(source='overview', required=False, allow_blank=True, allow_null=True, default='')
    previewAvailable = serializers.BooleanField(source='preview_available', read_only=True)
    
    # Additional computed fields
    resources_count = serializers.SerializerMethodField()
    qa_items_count = serializers.SerializerMethodField()
    project_tools_count = serializers.SerializerMethodField()
    has_quiz = serializers.SerializerMethodField()
    duration_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Lecture
        fields = [
            'id', 'title', 'order', 'duration', 'duration_formatted', 'overview', 'description',
            'preview_available', 'previewAvailable', 'video_url', 'resources',
            'is_completed', 'created_at', 'updated_at', 'qa_items', 'project_tools', 'quiz',
            'resources_count', 'qa_items_count', 'project_tools_count', 'has_quiz'
        ]

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
    
    def get_resources_count(self, obj):
        return obj.resources.count()
    
    def get_qa_items_count(self, obj):
        return obj.qa_items.count()
    
    def get_project_tools_count(self, obj):
        return obj.project_tools.count()
    
    def get_has_quiz(self, obj):
        return hasattr(obj, 'quiz') and obj.quiz is not None
    
    def get_duration_formatted(self, obj):
        """Convert duration in minutes to human readable format"""
        try:
            duration = int(obj.duration)
        except (TypeError, ValueError):
            return "0 min"
        
        hours = duration // 60
        minutes = duration % 60

        if hours > 0:
            return f"{hours}h {minutes}min" if minutes > 0 else f"{hours}h"
        return f"{minutes}min"


class DetailCourseSectionSerializer(serializers.ModelSerializer):
    lectures = DetailLectureSerializer(many=True, read_only=True)
    lectures_count = serializers.SerializerMethodField()
    total_duration = serializers.SerializerMethodField()
    completed_lectures_count = serializers.SerializerMethodField()
    section_progress = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseSection
        fields = [
            'id', 'title', 'description', 'order', 'created_at', 'updated_at',
            'lectures', 'lectures_count', 'total_duration', 'completed_lectures_count',
            'section_progress'
        ]

    def get_lectures_count(self, obj):
        return obj.lectures.count()
    
    def get_total_duration(self, obj):
        """Calculate total duration of all lectures in this section"""
        total_minutes = obj.lectures.aggregate(
            total=models.Sum('duration')
        )['total'] or 0
        
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        if hours > 0:
            return f"{hours}h {minutes}min" if minutes > 0 else f"{hours}h"
        return f"{minutes}min"
    
    def get_completed_lectures_count(self, obj):
        """Count completed lectures for authenticated user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                from enrollments.models import Enrollment
                enrollment = Enrollment.objects.filter(
                    student=request.user,
                    course=obj.course
                ).first()
                if enrollment and hasattr(enrollment, 'progress'):
                    return enrollment.progress.completed_lectures.filter(
                        section=obj
                    ).count()
            except ImportError:
                pass
        return 0
    
    def get_section_progress(self, obj):
        """Calculate section progress percentage"""
        total_lectures = self.get_lectures_count(obj)
        completed_lectures = self.get_completed_lectures_count(obj)
        
        if total_lectures == 0:
            return 0
        
        return round((completed_lectures / total_lectures) * 100, 1)

class CourseDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer that includes ALL nested data for the course detail page.
    This includes sections, lectures, resources, Q&A, quizzes, questions, tasks, etc.
    """
    sections = DetailCourseSectionSerializer(many=True, read_only=True)
    instructor = InstructorSerializer(read_only=True)
    category = CourseCategorySerializer(read_only=True)
    
    # Enrollment and progress data
    is_enrolled = serializers.SerializerMethodField()
    enrollment_date = serializers.SerializerMethodField()
    course_progress = serializers.SerializerMethodField()
    
    # Course statistics
    total_lectures = serializers.SerializerMethodField()
    total_duration = serializers.SerializerMethodField()
    total_resources = serializers.SerializerMethodField()
    total_quizzes = serializers.SerializerMethodField()
    total_qa_items = serializers.SerializerMethodField()
    
    # Course structure summary
    sections_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            # Basic course info
            'id', 'title', 'description', 'long_description', 'level', 'language', 'price',
            'slug', 'banner_url', 'preview_video_url', 'duration', 'rating', 'review_count',
            'students_enrolled', 'created_at', 'updated_at', 'is_published', 'is_active',
            
            # Related objects
            'instructor', 'category', 'sections',
            
            # Course features/metadata
            'prerequisites', 'what_you_will_learn', 'who_is_this_for',
            'certificate_available',  'lifetime_access',
            
            # Enrollment and progress
            'is_enrolled', 'enrollment_date', 'course_progress',
            
            # Statistics
            'total_lectures', 'total_duration', 'total_resources', 'total_quizzes',
            'total_qa_items', 'sections_count'
        ]
    
    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                from enrollments.models import Enrollment
                return Enrollment.objects.filter(student=request.user, course=obj).exists()
            except ImportError:
                pass
        return False
    
    def get_enrollment_date(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                from enrollments.models import Enrollment
                enrollment = Enrollment.objects.filter(
                    student=request.user, 
                    course=obj
                ).first()
                return enrollment.created_at if enrollment else None
            except ImportError:
                pass
        return None
    
    def get_course_progress(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                from enrollments.models import Enrollment
                enrollment = Enrollment.objects.filter(
                    student=request.user,
                    course=obj
                ).first()
                if enrollment and hasattr(enrollment, 'progress'):
                    total_lectures = obj.sections.aggregate(
                        total=models.Count('lectures')
                    )['total'] or 0
                    completed_lectures = enrollment.progress.completed_lectures.count()
                    
                    if total_lectures == 0:
                        return 0
                    
                    return round((completed_lectures / total_lectures) * 100, 1)
            except ImportError:
                pass
        return 0
    
    def get_total_lectures(self, obj):
        return obj.sections.aggregate(
            total=models.Count('lectures')
        )['total'] or 0
    
    def get_total_duration(self, obj):
        """Calculate total course duration from all lectures"""
        from django.db.models import Sum
        total_minutes = obj.sections.aggregate(
            total=Sum('lectures__duration')
        )['total'] or 0
        
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        if hours > 0:
            return f"{hours}h {minutes}min" if minutes > 0 else f"{hours}h"
        return f"{minutes}min"
    
    def get_total_resources(self, obj):
        return LectureResource.objects.filter(
            lecture__section__course=obj
        ).count()
    
    def get_total_quizzes(self, obj):
        return Quiz.objects.filter(course=obj).count()
    
    def get_total_qa_items(self, obj):
        return QaItem.objects.filter(
            lecture__section__course=obj
        ).count()
    
    def get_sections_count(self, obj):
        return obj.sections.count()
    
class QaItemSerializer(serializers.ModelSerializer):
    asked_by = UserSerializer(read_only=True)
    
    class Meta:
        model = QaItem
        fields = ['id', 'question', 'answer', 'upvotes', 'resolved', 'created_at', 'asked_by', 'lecture']
        read_only_fields = ['lecture', 'asked_by', 'upvotes']

class FullQaItemSerializer(QaItemSerializer):
    """Full Q&A serializer with all details for enrolled users"""
    asked_by = UserSerializer(read_only=True)
    lecture = serializers.SerializerMethodField()
    
    class Meta(QaItemSerializer.Meta):
        fields = QaItemSerializer.Meta.fields  # Just use the same fields since we already included lecture
    
    def get_lecture(self, obj):
        return {
            'id': obj.lecture.id,
            'title': obj.lecture.title,
            'section': {
                'id': obj.lecture.section.id,
                'title': obj.lecture.section.title
            }
        }

class QuizSerializer(serializers.ModelSerializer):
    questions = QuizQuestionSerializer(many=True, read_only=True)
    tasks = QuizTaskSerializer(many=True, read_only=True)
    
    class Meta:
        model = Quiz
        fields = ['id', 'title', 'description', 'instructions', 'points_possible', 
                 'due_date', 'is_published', 'allow_multiple_attempts', 
                 'max_attempts', 'time_limit_minutes', 'questions', 'tasks']
        read_only_fields = ['course', 'section', 'lecture']

class FullQuizSerializer(QuizSerializer):
    """Full quiz serializer with questions and tasks for enrolled users"""
    questions = QuizQuestionSerializer(many=True, read_only=True)
    tasks = QuizTaskSerializer(many=True, read_only=True)
    
    class Meta(QuizSerializer.Meta):
        fields = QuizSerializer.Meta.fields  # Just use the same fields since we already included questions/tasks