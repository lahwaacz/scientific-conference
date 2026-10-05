"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from core.views import ConferenceListView

# Support deployment in a subpath
_prefix = settings.RELATIVE_URL_ROOT or ""

urlpatterns = [
    path(f"{_prefix}admin/", admin.site.urls),
    # JWT Authentication
    path(
        f"{_prefix}api/auth/login/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        f"{_prefix}api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"
    ),
    # Global conference list (unscoped) — MUST stay registered BEFORE the
    # slug include below, or `api/conferences/` is captured as a
    # conference_slug prefix and 404s (core/urls has no empty tail).
    path(
        f"{_prefix}api/conferences/",
        ConferenceListView.as_view(),
        name="conference-list",
    ),
    path(f"{_prefix}api/<slug:conference_slug>/", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
