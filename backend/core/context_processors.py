from django.conf import settings


def auth_config(request):
    return {
        "password_login_enabled": settings.AUTH_PASSWORD_LOGIN_ENABLED,
        "gitlab_login_enabled": settings.AUTH_GITLAB_LOGIN_ENABLED,
        "frontend_root": "/" + (settings.RELATIVE_URL_ROOT or ""),
    }
