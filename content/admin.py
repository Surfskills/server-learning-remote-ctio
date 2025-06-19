from django.contrib import admin
from .models import CourseSection, Lecture, LectureResource

@admin.register(CourseSection)
class CourseSectionAdmin(admin.ModelAdmin):
    list_display = ('course', 'title', 'order', 'created_at')
    list_filter = ('course',)
    search_fields = ('title', 'course__title')
    raw_id_fields = ('course',)
    ordering = ('course', 'order')

@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    list_display = ('section', 'title', 'order', 'duration', 'created_at')
    list_filter = ('section__course', 'section')
    search_fields = ('title', 'section__title')
    raw_id_fields = ('section',)
    ordering = ('section', 'order')

@admin.register(LectureResource)
class LectureResourceAdmin(admin.ModelAdmin):
    list_display = ('lecture', 'title', 'kind', 'provider', 'is_downloadable')
    list_filter = ('kind', 'provider', 'lecture__section__course')
    search_fields = ('title', 'lecture__title')
    raw_id_fields = ('lecture',)