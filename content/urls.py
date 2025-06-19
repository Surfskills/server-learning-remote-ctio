from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(
    r'courses/(?P<course_pk>[^/.]+)/sections', 
    views.CourseSectionViewSet, 
    basename='course-sections'
)
router.register(
    r'sections/(?P<section_pk>[^/.]+)/lectures', 
    views.LectureViewSet, 
    basename='section-lectures'
)
router.register(
    r'lectures/(?P<lecture_pk>[^/.]+)/resources', 
    views.LectureResourceViewSet, 
    basename='lecture-resources'
)

urlpatterns = [
    path('content/', include(router.urls)),
]