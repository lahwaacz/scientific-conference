from dj_rest_auth.jwt_auth import JWTCookieAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied


class OptionalJWTCookieAuthentication(JWTCookieAuthentication):
    """Ignore stale or CSRF-failing cookies so public endpoints stay public.

    Admin views use the strict JWTCookieAuthentication directly, so an
    expired, malformed, or CSRF-less token still fails there.
    """

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except (AuthenticationFailed, PermissionDenied):
            return None
