# from rest_framework import serializers
# from .models import CourseSection, Lecture, LectureResource


# class CourseSectionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CourseSection
#         fields = '__all__'
#         read_only_fields = ['course']

# class LectureResourceSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = LectureResource
#         fields = '__all__'
#         read_only_fields = ['lecture']

# class LectureSerializer(serializers.ModelSerializer):
#     resources = LectureResourceSerializer(many=True, read_only=True)
#     is_completed = serializers.SerializerMethodField()

#     class Meta:
#         model = Lecture
#         fields = '__all__'
#         read_only_fields = ['section']

#     def get_is_completed(self, obj):
#         request = self.context.get('request')
#         if request and request.user.is_authenticated:
#             enrollment = request.user.enrollments.filter(
#                 course=obj.section.course
#             ).first()
#             if enrollment and hasattr(enrollment, 'progress'):
#                 return enrollment.progress.completed_lectures.filter(id=obj.id).exists()
#         return False

# class LectureCreateSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Lecture
#         fields = ['title', 'duration', 'overview', 'preview_available']

#     def create(self, validated_data):
#         section_id = self.context['view'].kwargs.get('section_pk')
#         last_lecture = Lecture.objects.filter(section_id=section_id).order_by('-order').first()
#         validated_data['order'] = (last_lecture.order + 1) if last_lecture else 1
#         validated_data['section_id'] = section_id
#         return super().create(validated_data)