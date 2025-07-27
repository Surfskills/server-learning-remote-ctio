# templates/urls.py
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
# GET    /templates/system/                      - List all system templates
# GET    /templates/system/{id}/                 - Get specific system template
# POST   /templates/system/{id}/apply_to_ebook/  - Apply template to ebook
# POST   /templates/system/{id}/duplicate/       - Duplicate as user template
# GET    /templates/system/defaults/             - Get default templates
# 
# User Templates:
# GET    /templates/user/                        - List user's templates
# POST   /templates/user/                        - Create new user template
# GET    /templates/user/{id}/                   - Get specific user template
# PUT    /templates/user/{id}/                   - Update user template
# PATCH  /templates/user/{id}/                   - Partial update user template
# DELETE /templates/user/{id}/                   - Delete user template
# POST   /templates/user/{id}/apply_to_ebook/    - Apply template to ebook
# POST   /templates/user/{id}/duplicate/         - Duplicate user template
# GET    /templates/user/available_templates/    - Get all available templates