# ebooks/urls.py - Updated with dashboard endpoint
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from . import views

# Main router for ebooks
router = DefaultRouter()
router.register(r'ebooks', views.EbookProjectViewSet, basename='ebook-project')

# Nested router for chapters under ebooks
chapters_router = routers.NestedDefaultRouter(router, r'ebooks', lookup='ebook')
chapters_router.register(r'chapters', views.ChapterViewSet, basename='ebook-chapters')

# Nested router for collaborators under ebooks
collaborators_router = routers.NestedDefaultRouter(router, r'ebooks', lookup='ebook')
collaborators_router.register(r'collaborators', views.EbookCollaboratorViewSet, basename='ebook-collaborators')

urlpatterns = [
    # Dashboard endpoint - NEW
    path('dashboard/', views.dashboard_summary, name='ebooks-dashboard'),
    
    # Router URLs
    path('', include(router.urls)),
    path('', include(chapters_router.urls)),
    path('', include(collaborators_router.urls)),
]

# This creates the following URL patterns:
# NEW: GET /api/ebooks/dashboard/ - Dashboard summary
#
# GET/POST /api/ebooks/ebooks/ - List/Create ebooks
# GET/PUT/PATCH/DELETE /api/ebooks/ebooks/{id}/ - Retrieve/Update/Delete ebook
# POST /api/ebooks/ebooks/{id}/publish/ - Publish ebook
# POST /api/ebooks/ebooks/{id}/apply_template/ - Apply template to ebook
# POST /api/ebooks/ebooks/{id}/export_pdf/ - Export as PDF
# POST /api/ebooks/ebooks/{id}/export_epub/ - Export as EPUB
# GET /api/ebooks/ebooks/{id}/exports/ - Get all exports for ebook
#
# GET/POST /api/ebooks/ebooks/{ebook_pk}/chapters/ - List/Create chapters
# GET/PUT/PATCH/DELETE /api/ebooks/ebooks/{ebook_pk}/chapters/{id}/ - Manage chapters
# POST /api/ebooks/ebooks/{ebook_pk}/chapters/reorder/ - Reorder chapters
#
# GET/POST /api/ebooks/ebooks/{ebook_pk}/collaborators/ - List/Create collaborators
# GET/PUT/PATCH/DELETE /api/ebooks/ebooks/{ebook_pk}/collaborators/{id}/ - Manage collaborators