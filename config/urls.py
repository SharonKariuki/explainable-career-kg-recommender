"""
Root URL configuration.

All API routes live under /api/v1/. In Sprint 1 every API view is a stub that
returns HTTP 501 Not Implemented; see docs/02-architecture.md for the planned
behaviour of each route.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/profiles/", include("apps.profiles.urls")),
    path("api/v1/recommendations/", include("apps.recommendations.urls")),
]
