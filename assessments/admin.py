from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Quiz, QuizQuestion, QuizTask, GradingCriterion, 
    QuizSubmission, QuestionResponse, SubmissionFile, 
    QuizGrade, TaskGrade, CriteriaGrade
)


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    fields = ('question_type', 'question', 'points', 'order')
    extra = 0
    ordering = ['order']


class QuizTaskInline(admin.TabularInline):
    model = QuizTask
    fields = ('title', 'required', 'accepts_files', 'accepts_text', 'points', 'order')
    extra = 0
    ordering = ['order']


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'course', 'section', 'lecture', 'due_date', 
        'points_possible', 'is_published', 'submission_count'
    ]
    list_filter = [
        'is_published', 'allow_multiple_attempts', 'course', 
        'section', 'created_at', 'due_date'
    ]
    search_fields = ['title', 'description', 'course__title']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'due_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('course', 'section', 'lecture', 'title', 'description', 'instructions')
        }),
        ('Quiz Settings', {
            'fields': (
                'due_date', 'points_possible', 'is_published',
                'allow_multiple_attempts', 'max_attempts', 'time_limit_minutes'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [QuizQuestionInline, QuizTaskInline]
    
    def submission_count(self, obj):
        count = obj.submissions.count()
        if count > 0:
            url = reverse('admin:quizzes_quizsubmission_changelist') + f'?quiz__id__exact={obj.id}'
            return format_html('<a href="{}">{} submissions</a>', url, count)
        return '0 submissions'
    submission_count.short_description = 'Submissions'


class GradingCriterionInline(admin.TabularInline):
    model = GradingCriterion
    fields = ('description', 'points', 'order')
    extra = 0
    ordering = ['order']


@admin.register(QuizTask)
class QuizTaskAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'quiz', 'required', 'accepts_files', 
        'accepts_text', 'points', 'order'
    ]
    list_filter = ['required', 'accepts_files', 'accepts_text', 'quiz__course']
    search_fields = ['title', 'description', 'quiz__title']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('quiz', 'title', 'description', 'required', 'order')
        }),
        ('Submission Settings', {
            'fields': (
                'accepts_files', 'accepted_file_types', 'max_file_size', 
                'max_files', 'accepts_text'
            )
        }),
        ('Grading', {
            'fields': ('points', 'sample_answer')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [GradingCriterionInline]


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = [
        'quiz', 'question_type', 'truncated_question', 
        'points', 'order'
    ]
    list_filter = ['question_type', 'quiz__course', 'points']
    search_fields = ['question', 'quiz__title']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Question Details', {
            'fields': ('quiz', 'question_type', 'question', 'order', 'points')
        }),
        ('Answer Configuration', {
            'fields': ('options', 'correct_option_index', 'correct_answer', 'explanation')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def truncated_question(self, obj):
        return obj.question[:50] + '...' if len(obj.question) > 50 else obj.question
    truncated_question.short_description = 'Question'


class QuestionResponseInline(admin.TabularInline):
    model = QuestionResponse
    fields = ('question', 'answer', 'is_correct', 'points_awarded')
    readonly_fields = ('question',)
    extra = 0


class SubmissionFileInline(admin.TabularInline):
    model = SubmissionFile
    fields = ('task', 'name', 'type', 'size', 'file_link')
    readonly_fields = ('file_link', 'size')
    extra = 0
    
    def file_link(self, obj):
        if obj.url:
            return format_html('<a href="{}" target="_blank">View File</a>', obj.url)
        return '-'
    file_link.short_description = 'File'


@admin.register(QuizSubmission)
class QuizSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'student_email', 'quiz_title', 'attempt_number', 
        'status', 'grade', 'submitted_at', 'time_spent_display'
    ]
    list_filter = [
        'status', 'quiz__course', 'submitted_at', 'quiz'
    ]
    search_fields = [
        'student__email', 'student__first_name', 'student__last_name', 
        'quiz__title'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'started_at', 'time_spent_seconds'
    ]
    date_hierarchy = 'submitted_at'
    
    fieldsets = (
        ('Submission Info', {
            'fields': (
                'student', 'quiz', 'attempt_number', 'status', 
                'started_at', 'submitted_at'
            )
        }),
        ('Response', {
            'fields': ('text_response',)
        }),
        ('Grading', {
            'fields': ('grade', 'feedback', 'instructor_notes')
        }),
        ('Metadata', {
            'fields': ('time_spent_seconds', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [QuestionResponseInline, SubmissionFileInline]
    
    def student_email(self, obj):
        return obj.student.email
    student_email.short_description = 'Student'
    student_email.admin_order_field = 'student__email'
    
    def quiz_title(self, obj):
        return obj.quiz.title
    quiz_title.short_description = 'Quiz'
    quiz_title.admin_order_field = 'quiz__title'
    
    def time_spent_display(self, obj):
        if obj.time_spent_seconds:
            minutes = obj.time_spent_seconds // 60
            seconds = obj.time_spent_seconds % 60
            return f"{minutes}m {seconds}s"
        return '-'
    time_spent_display.short_description = 'Time Spent'


@admin.register(QuestionResponse)
class QuestionResponseAdmin(admin.ModelAdmin):
    list_display = [
        'submission_student', 'question_text', 'answer_display', 
        'is_correct', 'points_awarded'
    ]
    list_filter = [
        'is_correct', 'submission__quiz', 'question__question_type'
    ]
    search_fields = [
        'submission__student__email', 'question__question'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    def submission_student(self, obj):
        return obj.submission.student.email
    submission_student.short_description = 'Student'
    
    def question_text(self, obj):
        return obj.question.question[:50] + '...' if len(obj.question.question) > 50 else obj.question.question
    question_text.short_description = 'Question'
    
    def answer_display(self, obj):
        if isinstance(obj.answer, list):
            return ', '.join(str(item) for item in obj.answer)
        return str(obj.answer) if obj.answer else '-'
    answer_display.short_description = 'Answer'


class TaskGradeInline(admin.TabularInline):
    model = TaskGrade
    fields = ('task', 'score', 'feedback')
    extra = 0


@admin.register(QuizGrade)
class QuizGradeAdmin(admin.ModelAdmin):
    list_display = [
        'student_email', 'quiz_title', 'overall_score', 
        'graded_by', 'graded_at', 'is_final'
    ]
    list_filter = [
        'is_final', 'quiz__course', 'graded_at', 'graded_by'
    ]
    search_fields = [
        'student__email', 'student__first_name', 'student__last_name',
        'quiz__title'
    ]
    readonly_fields = ['created_at', 'updated_at', 'graded_at']
    date_hierarchy = 'graded_at'
    
    fieldsets = (
        ('Grade Information', {
            'fields': (
                'quiz', 'student', 'overall_score', 'is_final'
            )
        }),
        ('Grading Details', {
            'fields': ('graded_by', 'graded_at', 'feedback')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [TaskGradeInline]
    
    def student_email(self, obj):
        return obj.student.email
    student_email.short_description = 'Student'
    student_email.admin_order_field = 'student__email'
    
    def quiz_title(self, obj):
        return obj.quiz.title
    quiz_title.short_description = 'Quiz'
    quiz_title.admin_order_field = 'quiz__title'


class CriteriaGradeInline(admin.TabularInline):
    model = CriteriaGrade
    fields = ('criterion', 'awarded_points', 'comments')
    extra = 0


@admin.register(TaskGrade)
class TaskGradeAdmin(admin.ModelAdmin):
    list_display = ['grade_info', 'task_title', 'score', 'max_points']
    list_filter = ['task__quiz__course', 'grade__graded_at']
    search_fields = [
        'grade__student__email', 'task__title', 'grade__quiz__title'
    ]
    
    inlines = [CriteriaGradeInline]
    
    def grade_info(self, obj):
        return f"{obj.grade.student.email} - {obj.grade.quiz.title}"
    grade_info.short_description = 'Student - Quiz'
    
    def task_title(self, obj):
        return obj.task.title
    task_title.short_description = 'Task'
    
    def max_points(self, obj):
        return obj.task.points
    max_points.short_description = 'Max Points'


@admin.register(GradingCriterion)
class GradingCriterionAdmin(admin.ModelAdmin):
    list_display = ['task_info', 'description_short', 'points', 'order']
    list_filter = ['task__quiz__course', 'points']
    search_fields = ['description', 'task__title', 'task__quiz__title']
    
    def task_info(self, obj):
        return f"{obj.task.quiz.title} - {obj.task.title}"
    task_info.short_description = 'Quiz - Task'
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Description'


@admin.register(SubmissionFile)
class SubmissionFileAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'submission_info', 'type', 'size_display', 
        'file_link', 'created_at'
    ]
    list_filter = ['type', 'submission__quiz__course', 'created_at']
    search_fields = [
        'name', 'submission__student__email', 'submission__quiz__title'
    ]
    readonly_fields = ['created_at', 'updated_at', 'size']
    
    def submission_info(self, obj):
        return f"{obj.submission.student.email} - {obj.submission.quiz.title}"
    submission_info.short_description = 'Student - Quiz'
    
    def size_display(self, obj):
        size = obj.size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    size_display.short_description = 'Size'
    
    def file_link(self, obj):
        if obj.url:
            return format_html('<a href="{}" target="_blank">View</a>', obj.url)
        return '-'
    file_link.short_description = 'File'


@admin.register(CriteriaGrade)
class CriteriaGradeAdmin(admin.ModelAdmin):
    list_display = [
        'student_info', 'criterion_description', 'awarded_points', 
        'max_points'
    ]
    list_filter = ['task_grade__grade__quiz__course']
    search_fields = [
        'task_grade__grade__student__email', 'criterion__description'
    ]
    
    def student_info(self, obj):
        return f"{obj.task_grade.grade.student.email} - {obj.task_grade.task.title}"
    student_info.short_description = 'Student - Task'
    
    def criterion_description(self, obj):
        return obj.criterion.description[:50] + '...' if len(obj.criterion.description) > 50 else obj.criterion.description
    criterion_description.short_description = 'Criterion'
    
    def max_points(self, obj):
        return obj.criterion.points
    max_points.short_description = 'Max Points'