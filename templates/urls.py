# templates/urls.py - Updated to match view actions
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router
router = DefaultRouter()

# Register viewsets
router.register(r'system', views.EbookTemplateViewSet, basename='ebook-template')
router.register(r'user', views.UserTemplateViewSet, basename='user-template')

# URL patterns
urlpatterns = [
    path('', include(router.urls)),
]

# This creates the following URL patterns:
#
# System Templates:
# GET /api/templates/system/ - List all system templates (with filtering: ?type=&is_default=&is_premium=)
# GET /api/templates/system/{id}/ - Get specific system template
# POST /api/templates/system/{id}/apply/ - Apply template to ebook
# POST /api/templates/system/{id}/duplicate/ - Duplicate as user template
# GET /api/templates/system/defaults/ - Get default templates (?type= optional)
# GET /api/templates/system/{id}/preview/ - Get template preview
#
# User Templates:
# GET /api/templates/user/ - List user's templates
# POST /api/templates/user/ - Create new user template
# GET /api/templates/user/{id}/ - Get specific user template
# PUT /api/templates/user/{id}/ - Update user template
# PATCH /api/templates/user/{id}/ - Partial update user template
# DELETE /api/templates/user/{id}/ - Delete user template
# POST /api/templates/user/{id}/apply/ - Apply template to ebook
# POST /api/templates/user/{id}/duplicate/ - Duplicate user template
# GET /api/templates/user/available_templates/ - Get all available templates (?type= optional)
# PATCH /api/templates/user/{id}/customize/ - Customize template styles/structure
# GET /api/templates/user/{id}/preview/ - Get template preview
# GET /api/templates/user/style_defaults/ - Get default style and structure templates