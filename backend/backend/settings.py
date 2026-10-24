"""
Django settings for backend project.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/6.1/ref/settings/
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse_lazy
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# development-only defaults (secret key, debug); production images never
# contain this file (see .dockerignore) and must set the variables themselves
load_dotenv(BASE_DIR / ".env.development")


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is not set: provide it in the environment "
        "(or in backend/.env.development for local development)"
    )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DJANGO_DEBUG", "False") == "True"

ALLOWED_HOSTS = [
    host for host in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if host
]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",  # required by allauth.socialaccount
    "rest_framework",  # DRF
    "rest_framework_simplejwt.token_blacklist",  # refresh-token blacklist (BLACKLIST_AFTER_ROTATION)
    "core.apps.CoreConfig",  # core app
    "corsheaders",  # for CORS
    "allauth",  # social login (GitLab) + allauth login page for Django admin
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.gitlab",
    "dj_rest_auth",  # JWT social login endpoint
    "dj_rest_auth.registration",  # SocialLoginView/Serializer for GitLab
]

SITE_ID = 1

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # add for CORS
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",  # after session/auth
    "core.auth.middleware.SessionJWTCookieMiddleware",  # keeps admin session and JWT cookies in sync
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Login-method flags for the Django admin sign-in page.
                "core.context_processors.auth_config",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("DJANGO_DB_PATH", BASE_DIR / "db.sqlite3"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Custom variable to support deployment in a subpath
RELATIVE_URL_ROOT = os.getenv("RELATIVE_URL_ROOT", "")
if RELATIVE_URL_ROOT:
    # Ensure that it ends with "/", but does not start with "/"
    RELATIVE_URL_ROOT = RELATIVE_URL_ROOT.strip("/") + "/"

STATIC_URL = os.getenv("DJANGO_STATIC_URL") or RELATIVE_URL_ROOT + "static/"
STATIC_ROOT = os.getenv("DJANGO_STATIC_ROOT", BASE_DIR / "staticfiles")
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = RELATIVE_URL_ROOT + "media/"
MEDIA_ROOT = os.getenv("DJANGO_MEDIA_ROOT", BASE_DIR / "media")


# Default primary key field type
# https://docs.djangoproject.com/en/6.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

from datetime import timedelta

# JWT settings
SIMPLE_JWT = {
    # 15-minute access token.
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    # 3-day refresh token; rotated and blacklisted on use.
    "REFRESH_TOKEN_LIFETIME": timedelta(days=3),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "LEEWAY": timedelta(seconds=5),
    # Invalidate existing tokens after a password change.
    "CHECK_REVOKE_TOKEN": True,
}


# Admin login methods; at least one must stay usable or admins lock out.
AUTH_PASSWORD_LOGIN_ENABLED = os.getenv("AUTH_PASSWORD_LOGIN_ENABLED", "True") == "True"
GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.fjfi.cvut.cz")
GITLAB_CLIENT_ID = os.getenv("GITLAB_CLIENT_ID", "")
GITLAB_CLIENT_SECRET = os.getenv("GITLAB_CLIENT_SECRET", "")
GITLAB_OAUTH_CALLBACK_URL = os.getenv("GITLAB_OAUTH_CALLBACK_URL", "")
AUTH_GITLAB_LOGIN_ENABLED = (
    os.getenv("AUTH_GITLAB_LOGIN_ENABLED", "True") == "True"
    and bool(GITLAB_CLIENT_ID)
    and bool(GITLAB_CLIENT_SECRET)
)
if not (AUTH_PASSWORD_LOGIN_ENABLED or AUTH_GITLAB_LOGIN_ENABLED):
    raise ImproperlyConfigured("At least one admin login method must be enabled")
if AUTH_GITLAB_LOGIN_ENABLED and not GITLAB_OAUTH_CALLBACK_URL:
    raise ImproperlyConfigured(
        "GITLAB_OAUTH_CALLBACK_URL is required when GitLab login is enabled"
    )

# The flag is enforced by the backends at call time (allauth's backend
# subclasses ModelBackend, so a list-level condition cannot disable password
# authentication through /api/auth/allauth/).
AUTHENTICATION_BACKENDS = [
    "core.auth.backends.FlagAwareModelBackend",
    "core.auth.backends.FlagAwareAllauthBackend",
]

# No provider app when the login method is off: an APPS entry with None
# credentials would still accept OAuth redirects on the allauth routes.
GITLAB_PROVIDER_APPS = []
if AUTH_GITLAB_LOGIN_ENABLED:
    GITLAB_PROVIDER_APPS = [
        {
            "client_id": GITLAB_CLIENT_ID or None,
            "secret": GITLAB_CLIENT_SECRET or None,
            "settings": {"gitlab_url": GITLAB_URL},
        }
    ]
SOCIALACCOUNT_PROVIDERS = {
    "gitlab": {
        "APPS": GITLAB_PROVIDER_APPS,
        "SCOPE": ["read_user"],
        "VERIFIED_EMAIL": True,
    }
}
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = False
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = False
ACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"

ACCOUNT_ADAPTER = "core.auth.adapters.NoSignupAccountAdapter"
SOCIALACCOUNT_ADAPTER = "core.auth.adapters.ConferenceSocialAccountAdapter"

REST_AUTH = {
    "USE_JWT": True,
    "SESSION_LOGIN": True,
    "TOKEN_MODEL": None,
    "JWT_AUTH_COOKIE": "conference-jwt-access",
    "JWT_AUTH_REFRESH_COOKIE": "conference-jwt-refresh",
    "JWT_AUTH_REFRESH_COOKIE_PATH": "/" + RELATIVE_URL_ROOT,
    "JWT_AUTH_COOKIE_USE_CSRF": True,
    "JWT_AUTH_HTTPONLY": True,
    "JWT_AUTH_RETURN_EXPIRATION": True,
    "JWT_AUTH_SAMESITE": "Lax",
    "JWT_AUTH_SECURE": not DEBUG,
    # The stock login serializers include the access token in JSON (plus a
    # refresh field), which defeats HttpOnly. These custom serializers
    # return only the user and optional expiration times.
    "JWT_SERIALIZER": "core.auth.serializers.CookieJWTSerializer",
    # Selected when JWT_AUTH_RETURN_EXPIRATION=True; it must stay token-free.
    "JWT_SERIALIZER_WITH_EXPIRATION": (
        "core.auth.serializers.CookieJWTSerializerWithExpiration"
    ),
    "USER_DETAILS_SERIALIZER": "core.auth.serializers.AuthUserSerializer",
}

# secure_admin_login (urls.py) redirects anonymous admin hits to this page.
LOGIN_URL = reverse_lazy("account_login")
FRONTEND_ROOT = "/" + RELATIVE_URL_ROOT  # "/" or "/conference/"
LOGIN_REDIRECT_URL = FRONTEND_ROOT
ACCOUNT_LOGOUT_REDIRECT_URL = FRONTEND_ROOT


EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "noreply@conference.local"


# CORS settings
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.auth.authentication.OptionalJWTCookieAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

# Security
# The SPA must read this token to send it in X-CSRFToken; it is not a secret.
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_PATH = "/" + RELATIVE_URL_ROOT
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_PATH = "/" + RELATIVE_URL_ROOT
SESSION_COOKIE_SAMESITE = "Lax"
if os.getenv("DJANGO_USE_HTTPS") == "True":
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# this may need to be set to avoid CSRF errors due to port forwarding for development
# https://docs.djangoproject.com/en/6.1/ref/csrf/
_csrf_origins = os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "")
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = _csrf_origins.split(",")
else:
    CSRF_TRUSTED_ORIGINS = [
        "http://localhost:3000",
    ]
CORS_ALLOWED_ORIGINS = CSRF_TRUSTED_ORIGINS

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

CORS_ALLOW_CREDENTIALS = True
