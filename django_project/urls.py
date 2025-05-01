"""
URL configuration for django_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from credit_workflow.views import DashboardView
    2. Add a URL to urlpatterns:    path('', DashboardView.as_view(), name='dashboard'),
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

# Automated API documentation endpoints (Swagger UI and Redoc)
# These provide live, interactive documentation for your API, always up-to-date with your codebase.
# Swagger UI (/swagger/) and Redoc (/redoc/) allow you and your team to browse, test, and explore the API interactively.
schema_view = get_schema_view(
    openapi.Info(
        title="Credit Risk Workflow API",
        default_version='v1',
        description="REST API for Credit Risk Workflow system, including credit requests, workflow transitions, documents, notifications, and PDF download.",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('users/', include('users.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('', include('credit_workflow.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
