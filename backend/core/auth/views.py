import secrets
from contextlib import suppress
from urllib.parse import urlencode
from uuid import uuid4

from allauth.socialaccount.providers.gitlab.views import GitLabOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.app_settings import api_settings
from dj_rest_auth.jwt_auth import JWTCookieAuthentication, get_refresh_view
from dj_rest_auth.registration.views import SocialLoginView
from dj_rest_auth.views import LoginView
from django.conf import settings
from django.contrib.auth import logout as django_logout
from django.core import signing
from django.core.signing import BadSignature, SignatureExpired
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from core.auth.serializers import PasswordRevokingCookieTokenRefreshSerializer
from core.models import Conference

OAUTH_STATE_SALT = "gitlab-oauth"
OAUTH_STATE_MAX_AGE = 600
OAUTH_NONCE_COOKIE = "gitlab_oauth_nonce"


def _jwt_cookie_path():
    return "/" + (settings.RELATIVE_URL_ROOT or "")


def _scope_access_cookie(response):
    cookie_name = api_settings.JWT_AUTH_COOKIE
    if cookie_name and cookie_name in response.cookies:
        response.cookies[cookie_name]["path"] = _jwt_cookie_path()


def _clear_jwt_cookies(response):
    access_cookie = api_settings.JWT_AUTH_COOKIE
    if access_cookie:
        response.delete_cookie(
            access_cookie,
            path=_jwt_cookie_path(),
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


def get_gitlab_oauth_settings():
    # Read at call time so override_settings works in tests.
    return {
        "url": settings.GITLAB_URL,
        "client_id": settings.GITLAB_CLIENT_ID,
        "callback_url": settings.GITLAB_OAUTH_CALLBACK_URL,
    }


def _oauth_nonce_cookie_path():
    # Read at call time so override_settings works in tests.
    return "/" + (settings.RELATIVE_URL_ROOT or "")


def _delete_oauth_nonce_cookie(response):
    response.delete_cookie(OAUTH_NONCE_COOKIE, path=_oauth_nonce_cookie_path())


def build_frontend_admin_url(slug):
    root = settings.RELATIVE_URL_ROOT or ""
    if root and not root.endswith("/"):
        root += "/"
    if not slug:
        return f"/{root}"
    return f"/{root}{slug}/#/admin-panel"


class AuthConfigView(APIView):
    """Which admin login methods the frontend should offer."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "password_login_enabled": settings.AUTH_PASSWORD_LOGIN_ENABLED,
                "gitlab_login_enabled": settings.AUTH_GITLAB_LOGIN_ENABLED,
            }
        )


class GitLabAuthorizeView(APIView):
    """Hands the SPA the GitLab authorize URL; the target conference slug

    rides along in the signed state so the callback can rebuild the link.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        slug = request.query_params.get("next", "")
        if not Conference.objects.filter(slug=slug).exists():
            slug = ""
        nonce = uuid4().hex
        state = signing.dumps(
            {
                "slug": slug,
                "nonce": nonce,
                "iat": timezone.now().timestamp(),
            },
            salt=OAUTH_STATE_SALT,
            compress=True,
        )
        oauth = get_gitlab_oauth_settings()
        query = urlencode(
            {
                "client_id": oauth["client_id"],
                "redirect_uri": oauth["callback_url"],
                "response_type": "code",
                "scope": "read_user",
                "state": state,
            }
        )
        url = f"{oauth['url'].rstrip('/')}/oauth/authorize?{query}"
        response = Response({"url": url, "state": state})
        # The nonce binds the signed state to this browser; the login view
        # requires it and consumes it, making each state single-use.
        response.set_cookie(
            OAUTH_NONCE_COOKIE,
            nonce,
            max_age=OAUTH_STATE_MAX_AGE,
            httponly=True,
            samesite="Lax",
            secure=settings.SESSION_COOKIE_SECURE,
            path=_oauth_nonce_cookie_path(),
        )
        return response


class CookieLoginView(LoginView):
    def get_response(self):
        response = super().get_response()
        _scope_access_cookie(response)
        return response


class GitLabLoginView(SocialLoginView):
    adapter_class = GitLabOAuth2Adapter
    client_class = OAuth2Client
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_response(self):
        response = super().get_response()
        _scope_access_cookie(response)
        return response

    @property
    def callback_url(self):
        return get_gitlab_oauth_settings()["callback_url"]

    def post(self, request, *args, **kwargs):
        data = request.data if isinstance(request.data, dict) else {}
        state = data.get("state")
        if not state:
            return Response({"detail": "Missing state."}, status=400)
        if not isinstance(state, str):
            return Response({"detail": "Invalid or expired state."}, status=400)
        try:
            payload = signing.loads(
                state, salt=OAUTH_STATE_SALT, max_age=OAUTH_STATE_MAX_AGE
            )
        except (BadSignature, SignatureExpired):
            return Response({"detail": "Invalid or expired state."}, status=400)
        cookie_nonce = request.COOKIES.get(OAUTH_NONCE_COOKIE, "")
        state_nonce = str(payload.get("nonce", "")) if isinstance(payload, dict) else ""
        if not cookie_nonce or not secrets.compare_digest(state_nonce, cookie_nonce):
            response = Response({"detail": "Invalid or expired state."}, status=400)
            _delete_oauth_nonce_cookie(response)
            return response
        response = super().post(request, *args, **kwargs)
        # Single-use: every response from this view drops the nonce cookie.
        _delete_oauth_nonce_cookie(response)
        if response.status_code == 200:
            response.data["next"] = build_frontend_admin_url(payload.get("slug", ""))
        return response


class CookieRefreshView(get_refresh_view()):
    """Refresh from the HttpOnly cookie without echoing either token."""

    serializer_class = PasswordRevokingCookieTokenRefreshSerializer

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if response.status_code == 200:
            _scope_access_cookie(response)
        if response.status_code == 200 and isinstance(response.data, dict):
            response.data.pop("access", None)
            response.data.pop("refresh", None)
        return response


class LogoutView(APIView):
    """Requires a valid cookie JWT. Blacklists the refresh token from its

    HttpOnly cookie and flushes the session created by a login.
    """

    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_cookie = api_settings.JWT_AUTH_REFRESH_COOKIE
        refresh = request.COOKIES.get(refresh_cookie) if refresh_cookie else None
        # Invalid or already-expired refresh: nothing to blacklist then.
        with suppress(TokenError):
            if refresh:
                RefreshToken(refresh).blacklist()
        django_logout(request)
        response = Response(status=204)
        _clear_jwt_cookies(response)
        return response
