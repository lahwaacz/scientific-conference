"""
URL configuration for backend project.

Global routes only (admin/, api/auth/*, api/conferences/) plus the
slug include: api/<slug:conference_slug>/ -> core.urls. The auth routes are
conditional on the login-method flags in settings; build_urlpatterns()
re-reads them so tests can toggle them via override_settings.
"""

import re

from allauth.account import views as account_views
from allauth.account.decorators import secure_admin_login
from allauth.socialaccount import views as socialaccount_views
from dj_rest_auth.views import UserDetailsView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponseNotFound
from django.urls import include, path, re_path
from django.views.decorators.csrf import ensure_csrf_cookie

from core.auth.views import (
    AuthConfigView,
    CookieLoginView,
    CookieRefreshView,
    GitLabAuthorizeView,
    GitLabLoginView,
    LogoutView,
)
from core.views import ConferenceListView


def disabled_gitlab_provider_view(request):
    # The GitLab provider routes stay named in every mode so reverse() and
    # the admin login page keep working; disable them with a 404.
    return HttpResponseNotFound()


allauth_urlpatterns = [
    path("login/", account_views.login, name="account_login"),
    path("logout/", account_views.logout, name="account_logout"),
    path(
        "3rdparty/login/cancelled/",
        socialaccount_views.login_cancelled,
        name="socialaccount_login_cancelled",
    ),
    path(
        "3rdparty/login/error/",
        socialaccount_views.login_error,
        name="socialaccount_login_error",
    ),
    path(
        "3rdparty/signup/",
        socialaccount_views.signup,
        name="socialaccount_signup",
    ),
    # The GitLab provider's URLconf already prefixes its routes with
    # "gitlab/"; do not add another prefix here.
    path("", include("allauth.socialaccount.providers.gitlab.urls")),
]


def build_urlpatterns():
    # Support deployment in a subpath
    prefix = settings.RELATIVE_URL_ROOT or ""
    urls = [
        path(f"{prefix}admin/", admin.site.urls),
        path(
            f"{prefix}api/auth/refresh/",
            ensure_csrf_cookie(CookieRefreshView.as_view()),
            name="token_refresh",
        ),
    ]
    if settings.AUTH_PASSWORD_LOGIN_ENABLED:
        urls.append(
            path(
                f"{prefix}api/auth/login/",
                ensure_csrf_cookie(CookieLoginView.as_view()),
                name="token_obtain_pair",
            )
        )
    urls += [
        path(
            f"{prefix}api/auth/config/",
            ensure_csrf_cookie(AuthConfigView.as_view()),
            name="auth-config",
        ),
        path(
            f"{prefix}api/auth/user/",
            UserDetailsView.as_view(),
            name="auth-user",
        ),
        path(
            f"{prefix}api/auth/logout/",
            LogoutView.as_view(),
            name="auth-logout",
        ),
    ]
    if not settings.AUTH_GITLAB_LOGIN_ENABLED:
        urls.append(
            re_path(
                rf"^{re.escape(prefix)}api/auth/allauth/.*gitlab.*$",
                disabled_gitlab_provider_view,
            )
        )
    # Only the routes used by the admin sign-in and GitLab social flow are
    # exposed; password reset/email/account-management pages stay absent.
    urls.append(path(f"{prefix}api/auth/allauth/", include(allauth_urlpatterns)))
    if settings.AUTH_GITLAB_LOGIN_ENABLED:
        urls += [
            path(
                f"{prefix}api/auth/gitlab/authorize/",
                GitLabAuthorizeView.as_view(),
                name="gitlab-authorize",
            ),
            path(
                f"{prefix}api/auth/gitlab/",
                ensure_csrf_cookie(GitLabLoginView.as_view()),
                name="gitlab-login",
            ),
        ]
    # Global conference list (unscoped) — MUST stay registered BEFORE the
    # slug include below, or `api/conferences/` is captured as a
    # conference_slug prefix and 404s (core/urls has no empty tail).
    urls += [
        path(
            f"{prefix}api/conferences/",
            ConferenceListView.as_view(),
            name="conference-list",
        ),
        path(f"{prefix}api/<slug:conference_slug>/", include("core.urls")),
    ]
    if settings.DEBUG:
        urls += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    return urls


admin.autodiscover()
# Anonymous admin hits go to the allauth login page (which offers every
# enabled login method); non-staff authenticated users get 403.
admin.site.login = secure_admin_login(admin.site.login)

urlpatterns = build_urlpatterns()
