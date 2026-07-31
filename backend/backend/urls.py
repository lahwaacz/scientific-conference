"""
URL configuration for quotes project.

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
from django.contrib import admin
from django.urls import path, include
from core.views import ReactView, delete_session, update_session
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


# Support deployment in a subpath
_prefix = settings.RELATIVE_URL_ROOT or ""

urlpatterns = [
    path(f'{_prefix}admin/', admin.site.urls),
    path(f'{_prefix}wel/', ReactView.as_view(), name="something"),
    path(f"{_prefix}api/", include("core.urls")),
# JWT Authentication
    path(f'{_prefix}api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path(f'{_prefix}api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path(f'{_prefix}api/admin/sessions/<int:pk>/', update_session),
    path(f'{_prefix}api/admin/sessions/<int:pk>/delete/', delete_session),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

