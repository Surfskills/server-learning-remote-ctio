from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('health/', views.HealthCheckView.as_view(), name='health-check'),
    path('admin/stats/', views.admin_stats, name='admin-stats'),
    path('health/extended/', views.ExtendedHealthCheckView.as_view(), name='extended-health-check'),
]