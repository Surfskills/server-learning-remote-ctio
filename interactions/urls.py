from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(
    r'courses/(?P<course_pk>[^/.]+)/discussions', 
    views.DiscussionThreadViewSet, 
    basename='course-discussions'
)
router.register(
    r'discussions/(?P<thread_pk>[^/.]+)/replies', 
    views.ThreadReplyViewSet, 
    basename='thread-replies'
)
router.register(r'upvotes', views.UpvoteViewSet, basename='upvotes')
router.register(r'engagements', views.UserEngagementViewSet, basename='engagements')

urlpatterns = [
    path('interactions/', include(router.urls)),
]