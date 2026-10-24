from django.conf import settings

from core.auth.cookies import (
    blacklist_refresh_cookie,
    clear_jwt_cookies,
    issue_jwt_cookies,
)


class SessionJWTCookieMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not self._is_session_surface(request.path):
            return response

        action = getattr(request, "_session_jwt_action", None)
        if action == "set" and request.user.is_authenticated:
            issue_jwt_cookies(response, request.user)
        elif action == "clear":
            blacklist_refresh_cookie(request)
            clear_jwt_cookies(response)
        return response

    @staticmethod
    def _is_session_surface(path):
        root = "/" + (settings.RELATIVE_URL_ROOT or "")
        return path.startswith((f"{root}admin/", f"{root}api/auth/allauth/"))
