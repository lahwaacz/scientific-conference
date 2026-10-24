from contextlib import suppress

from dj_rest_auth.app_settings import api_settings
from dj_rest_auth.jwt_auth import set_jwt_cookies
from django.conf import settings
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


def jwt_cookie_path():
    return "/" + (settings.RELATIVE_URL_ROOT or "")


def scope_access_cookie(response):
    cookie_name = api_settings.JWT_AUTH_COOKIE
    if cookie_name and cookie_name in response.cookies:
        response.cookies[cookie_name]["path"] = jwt_cookie_path()


def issue_jwt_cookies(response, user):
    refresh = RefreshToken.for_user(user)
    set_jwt_cookies(response, str(refresh.access_token), str(refresh))
    scope_access_cookie(response)


def blacklist_refresh_cookie(request):
    cookie_name = api_settings.JWT_AUTH_REFRESH_COOKIE
    if not cookie_name:
        return
    raw_refresh = request.COOKIES.get(cookie_name)
    if not raw_refresh:
        return
    with suppress(TokenError):
        RefreshToken(raw_refresh).blacklist()


def clear_jwt_cookies(response):
    access_cookie = api_settings.JWT_AUTH_COOKIE
    if access_cookie:
        response.delete_cookie(
            access_cookie,
            path=jwt_cookie_path(),
            samesite=api_settings.JWT_AUTH_SAMESITE,
            domain=api_settings.JWT_AUTH_COOKIE_DOMAIN,
        )
    refresh_cookie = api_settings.JWT_AUTH_REFRESH_COOKIE
    if refresh_cookie:
        response.delete_cookie(
            refresh_cookie,
            path=api_settings.JWT_AUTH_REFRESH_COOKIE_PATH,
            samesite=api_settings.JWT_AUTH_SAMESITE,
            domain=api_settings.JWT_AUTH_COOKIE_DOMAIN,
        )
