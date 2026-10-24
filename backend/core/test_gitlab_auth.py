"""GitLab OAuth admin login, password-login flag, config and logout.

All GitLab HTTP traffic is mocked (token exchange + profile fetch); the
tests pin the authorize/state contract, code exchange + auto-provisioning,
session coupling, refresh blacklisting and the runtime login-method flags.
"""

import time
from contextlib import contextmanager
from datetime import timedelta
from unittest import mock
from urllib.parse import parse_qs, urlparse

import requests
from allauth.socialaccount.models import SocialAccount
from dj_rest_auth.app_settings import api_settings
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core import signing
from django.test import Client, TestCase, override_settings
from django.urls import clear_url_caches, reverse
from rest_framework.test import APIClient

from backend import urls as root_urls
from core.auth.views import OAUTH_STATE_SALT, build_frontend_admin_url
from core.models import Conference, ConferenceManagers

from .conftest import api

SLUG = "wsc2026-test"
ACCESS_COOKIE = "conference-jwt-access"
REFRESH_COOKIE = "conference-jwt-refresh"

GITLAB_SETTINGS = {
    "GITLAB_CLIENT_ID": "test-client-id",
    "GITLAB_CLIENT_SECRET": "test-client-secret",
    "GITLAB_URL": "https://gitlab.test",
    "GITLAB_OAUTH_CALLBACK_URL": "http://testserver/oauth/callback",
    "AUTH_GITLAB_LOGIN_ENABLED": True,
    "SOCIALACCOUNT_PROVIDERS": {
        "gitlab": {
            "APPS": [
                {
                    "client_id": "test-client-id",
                    "secret": "test-client-secret",
                    "settings": {"gitlab_url": "https://gitlab.test"},
                }
            ],
            "SCOPE": ["read_user"],
            "VERIFIED_EMAIL": True,
        }
    },
}

TOKEN_PAYLOAD = {
    "access_token": "test-token",
    "token_type": "bearer",
    "scope": "read_user",
}
PROFILE_PAYLOAD = {
    "id": 123,
    "username": "alice",
    "name": "Alice Example",
    "email": "alice@example.com",
}


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200
        self.headers = {"content-type": "application/json"}
        self.text = ""
        self.content = b""

    def json(self):
        return self._payload


def _fake_gitlab_request(method, url, **kwargs):
    if url.endswith("/oauth/token"):
        assert method == "POST", method
        return _FakeResponse(TOKEN_PAYLOAD)
    if url.endswith("/api/v4/user"):
        assert method == "GET", method
        return _FakeResponse(PROFILE_PAYLOAD)
    raise AssertionError(f"unexpected GitLab request: {method} {url}")


def mock_gitlab_http():
    return mock.patch.object(
        requests.Session, "request", side_effect=_fake_gitlab_request
    )


@contextmanager
def _rebuilt_urls(settings_overrides):
    with override_settings(**settings_overrides):
        previous = root_urls.urlpatterns
        try:
            root_urls.urlpatterns = root_urls.build_urlpatterns()
            clear_url_caches()
            yield
        finally:
            root_urls.urlpatterns = previous
            clear_url_caches()


def gitlab_urls(**overrides):
    return _rebuilt_urls({**GITLAB_SETTINGS, **overrides})


def password_only_urls(**overrides):
    return _rebuilt_urls(
        {
            "AUTH_PASSWORD_LOGIN_ENABLED": True,
            "AUTH_GITLAB_LOGIN_ENABLED": False,
            **overrides,
        }
    )


def gitlab_only_urls(**overrides):
    return gitlab_urls(AUTH_PASSWORD_LOGIN_ENABLED=False, **overrides)


class GitLabAuthTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.conference = Conference.objects.get_or_create(slug=SLUG)[0]

    def authorize_state(self, slug=SLUG):
        response = self.client.get("/api/auth/gitlab/authorize/", {"next": slug})
        return response.json()["state"]

    def post_code(self, state, code="test-code"):
        with mock_gitlab_http():
            return self.client.post(
                "/api/auth/gitlab/", {"code": code, "state": state}, format="json"
            )


class TestGitLabAuthorize(GitLabAuthTestCase):
    def test_authorize_url_params_and_signed_state(self):
        with gitlab_urls():
            response = self.client.get("/api/auth/gitlab/authorize/", {"next": SLUG})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        url = urlparse(body["url"])
        self.assertEqual(
            f"{url.scheme}://{url.netloc}{url.path}",
            "https://gitlab.test/oauth/authorize",
        )
        query = parse_qs(url.query)
        self.assertEqual(query["client_id"], ["test-client-id"])
        self.assertEqual(query["redirect_uri"], ["http://testserver/oauth/callback"])
        self.assertEqual(query["response_type"], ["code"])
        self.assertEqual(query["scope"], ["read_user"])
        self.assertEqual(query["state"], [body["state"]])
        state = signing.loads(body["state"], salt=OAUTH_STATE_SALT)
        self.assertEqual(state["slug"], SLUG)
        self.assertTrue(state["nonce"])
        self.assertIn("iat", state)

    def test_unknown_slug_is_dropped_from_state(self):
        with gitlab_urls():
            response = self.client.get(
                "/api/auth/gitlab/authorize/", {"next": "no-such-conf"}
            )
        self.assertEqual(response.status_code, 200)
        state = signing.loads(response.json()["state"], salt=OAUTH_STATE_SALT)
        self.assertEqual(state["slug"], "")


class TestGitLabLogin(GitLabAuthTestCase):
    def test_missing_state_rejected_before_any_http(self):
        with gitlab_urls():
            response = self.post_code("")
        self.assertEqual(response.status_code, 400)

    def test_non_string_state_rejected_before_any_http(self):
        with gitlab_urls():
            response = self.post_code(["not-a-string"])
        self.assertEqual(response.status_code, 400)

    def test_non_object_body_rejected(self):
        with gitlab_urls():
            response = self.client.post("/api/auth/gitlab/", [], format="json")
        self.assertEqual(response.status_code, 400)

    def test_tampered_state_rejected_before_any_http(self):
        with gitlab_urls():
            response = self.post_code("garbage-state")
        self.assertEqual(response.status_code, 400)

    def test_expired_state_rejected(self):
        with gitlab_urls():
            state = self.authorize_state()
            with mock.patch("time.time", return_value=time.time() + 601):
                response = self.post_code(state)
        self.assertEqual(response.status_code, 400)

    def test_callback_creates_user_returns_jwt_next_and_session(self):
        with gitlab_urls():
            state = self.authorize_state()
            response = self.post_code(state)
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertNotIn("access", body)
        self.assertNotIn("refresh", body)
        self.assertTrue(response.cookies[ACCESS_COOKIE]["httponly"])
        self.assertTrue(response.cookies[REFRESH_COOKIE]["httponly"])
        self.assertEqual(response.cookies[ACCESS_COOKIE]["samesite"], "Lax")
        self.assertEqual(response.cookies[ACCESS_COOKIE]["path"], "/")
        self.assertEqual(response.cookies[REFRESH_COOKIE]["path"], "/")
        user = User.objects.get(username="alice")
        self.assertFalse(user.is_staff)
        self.assertEqual(body["user"]["username"], "alice")
        self.assertEqual(body["user"]["email"], "alice@example.com")
        self.assertEqual(body["user"]["first_name"], "Alice")
        self.assertEqual(body["user"]["last_name"], "Example")
        self.assertFalse(body["user"]["is_staff"])
        self.assertEqual(body["next"], f"/{SLUG}/#/admin-panel")
        self.assertEqual(self.client.session["_auth_user_id"], str(user.id))
        account = SocialAccount.objects.get(user=user, provider="gitlab")
        self.assertEqual(account.uid, "123")
        # A brand-new social user is not staff: the admin API rejects it.
        self.assertEqual(
            self.client.get(api("admin-panel/", slug=SLUG)).status_code, 403
        )

    def test_existing_social_account_logs_in_its_user_and_keeps_staff(self):
        staff = User.objects.create_user(
            username="alice-local", password="pw", is_staff=True
        )
        ConferenceManagers.objects.create(conference=self.conference, user=staff)
        SocialAccount.objects.create(
            provider="gitlab", uid="123", user=staff, extra_data={"username": "alice"}
        )
        with gitlab_urls():
            state = self.authorize_state()
            response = self.post_code(state)
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["user"]["username"], "alice-local")
        self.assertTrue(body["user"]["is_staff"])
        self.assertEqual(self.client.session["_auth_user_id"], str(staff.id))
        self.assertEqual(
            SocialAccount.objects.get(provider="gitlab", uid="123").user, staff
        )
        staff.refresh_from_db()
        self.assertTrue(staff.is_staff)
        self.assertEqual(
            self.client.get(api("admin-panel/", slug=SLUG)).status_code, 200
        )

    def test_next_defaults_to_root_when_slug_unknown(self):
        with gitlab_urls():
            state = self.authorize_state(slug="no-such-conf")
            response = self.post_code(state)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["next"], "/")


class TestOAuthStateNonce(GitLabAuthTestCase):
    """The authorize endpoint binds the signed state to the browser via an

    HttpOnly nonce cookie; the login endpoint must verify and consume it.
    """

    def test_authorize_sets_httponly_nonce_cookie_matching_state(self):
        with gitlab_urls():
            response = self.client.get("/api/auth/gitlab/authorize/", {"next": SLUG})
        self.assertEqual(response.status_code, 200)
        cookie = response.cookies["gitlab_oauth_nonce"]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(int(cookie["max-age"]), 600)
        payload = signing.loads(response.json()["state"], salt=OAUTH_STATE_SALT)
        self.assertEqual(payload["nonce"], cookie.value)

    def test_state_from_another_browser_is_rejected(self):
        with gitlab_urls():
            state = self.authorize_state()
            attacker = APIClient()  # a different browser: no nonce cookie
            with mock_gitlab_http():
                response = attacker.post(
                    "/api/auth/gitlab/",
                    {"code": "test-code", "state": state},
                    format="json",
                )
        self.assertEqual(response.status_code, 400)

    def test_state_replay_is_rejected_after_successful_exchange(self):
        with gitlab_urls():
            state = self.authorize_state()
            first = self.post_code(state)
            self.assertEqual(first.status_code, 200, first.content)
            # A successful exchange consumes the nonce cookie.
            self.assertEqual(first.cookies["gitlab_oauth_nonce"].value, "")
            second = self.post_code(state)
        self.assertEqual(second.status_code, 400)

    def test_missing_nonce_cookie_is_rejected(self):
        with gitlab_urls():
            state = self.authorize_state()
            del self.client.cookies["gitlab_oauth_nonce"]
            response = self.post_code(state)
        self.assertEqual(response.status_code, 400)


class TestLogout(GitLabAuthTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient(enforce_csrf_checks=True)

    def gitlab_login(self):
        with gitlab_urls():
            state = self.authorize_state()
            response = self.post_code(state)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def post_logout(self):
        return self.client.post(
            "/api/auth/logout/",
            HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
        )

    def test_logout_blacklists_refresh_and_flushes_session(self):
        self.gitlab_login()
        self.assertIn("_auth_user_id", self.client.session)
        response = self.post_logout()
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.cookies[ACCESS_COOKIE].value, "")
        self.assertEqual(response.cookies[REFRESH_COOKIE].value, "")
        self.assertNotIn("_auth_user_id", self.client.session)
        refreshed = self.client.post("/api/auth/refresh/")
        self.assertEqual(refreshed.status_code, 401)

    def test_logout_without_refresh_just_clears_session(self):
        self.gitlab_login()
        del self.client.cookies[REFRESH_COOKIE]
        response = self.post_logout()
        self.assertEqual(response.status_code, 204)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_with_invalid_refresh_still_returns_204(self):
        self.gitlab_login()
        self.client.cookies[REFRESH_COOKIE] = "not-a-token"
        response = self.post_logout()
        self.assertEqual(response.status_code, 204)

    def test_logout_without_csrf_is_rejected(self):
        self.gitlab_login()
        self.assertIn("_auth_user_id", self.client.session)

        response = self.client.post("/api/auth/logout/")

        self.assertEqual(response.status_code, 403)
        self.assertIn("_auth_user_id", self.client.session)

    def test_unauthenticated_logout_is_rejected_and_keeps_session(self):
        self.gitlab_login()
        self.assertIn("_auth_user_id", self.client.session)
        response = APIClient().post("/api/auth/logout/")
        self.assertEqual(response.status_code, 401)
        # A cross-site logout CSRF attempt must not flush the session.
        self.assertIn("_auth_user_id", self.client.session)


class TestAuthConfig(GitLabAuthTestCase):
    def test_config_reports_password_only_by_default(self):
        response = self.client.get("/api/auth/config/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"password_login_enabled": True, "gitlab_login_enabled": False},
        )

    def test_config_reports_gitlab_when_credentials_present(self):
        with gitlab_urls():
            response = self.client.get("/api/auth/config/")
        self.assertEqual(
            response.json(),
            {"password_login_enabled": True, "gitlab_login_enabled": True},
        )

    def test_config_is_not_conference_scoped(self):
        with gitlab_urls():
            response = self.client.get(api("auth/config/", slug=SLUG))
        self.assertEqual(response.status_code, 404)


class TestPasswordLoginFlag(TestCase):
    def setUp(self):
        self.client = APIClient()
        User.objects.create_user(username="pw-admin", password="pw", is_staff=True)

    def test_password_login_works_when_enabled(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "pw-admin", "password": "pw"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertNotIn("access", body)
        self.assertNotIn("refresh", body)
        self.assertTrue(response.cookies[ACCESS_COOKIE]["httponly"])
        self.assertEqual(self.client.get("/api/auth/user/").status_code, 200)

    def test_password_authenticate_works_when_enabled(self):
        self.assertIsNotNone(authenticate(username="pw-admin", password="pw"))

    def test_password_authenticate_rejected_when_disabled(self):
        # The allauth backend subclasses ModelBackend, so the flag must be
        # enforced inside the backends, not by the backend list alone.
        with override_settings(AUTH_PASSWORD_LOGIN_ENABLED=False):
            self.assertIsNone(authenticate(username="pw-admin", password="pw"))

    def test_password_login_route_gone_when_disabled(self):
        with gitlab_urls(AUTH_PASSWORD_LOGIN_ENABLED=False):
            response = self.client.post(
                "/api/auth/login/",
                {"username": "pw-admin", "password": "pw"},
                format="json",
            )
            self.assertEqual(response.status_code, 404)
            # Refresh and config stay registered in every mode.
            refresh = self.client.post("/api/auth/refresh/", {}, format="json")
            self.assertEqual(refresh.status_code, 401)
            config = self.client.get("/api/auth/config/")
            self.assertEqual(config.status_code, 200)

    def test_gitlab_routes_gone_when_disabled(self):
        # Default test settings carry no GITLAB_CLIENT_ID -> disabled.
        self.assertEqual(
            self.client.get("/api/auth/gitlab/authorize/").status_code, 404
        )
        self.assertEqual(self.client.post("/api/auth/gitlab/", {}).status_code, 404)


class TestGitLabProviderRoutes(TestCase):
    """The allauth GitLab provider pages must be unreachable when the

    GitLab login method is disabled, even though the provider app stays in
    INSTALLED_APPS for the password-only admin login page.
    """

    def setUp(self):
        self.client = Client()

    def test_provider_apps_empty_without_gitlab_credentials(self):
        self.assertEqual(settings.SOCIALACCOUNT_PROVIDERS["gitlab"]["APPS"], [])

    def test_allauth_gitlab_login_route_404_when_disabled(self):
        with password_only_urls():
            response = self.client.get(reverse("gitlab_login"))
        self.assertEqual(response.status_code, 404)

    def test_provider_route_404_when_flag_off_even_with_credentials(self):
        # The kill switch must win even when a provider app is configured.
        with gitlab_urls(AUTH_GITLAB_LOGIN_ENABLED=False):
            response = self.client.get(reverse("gitlab_login"))
        self.assertEqual(response.status_code, 404)

    def test_allauth_gitlab_callback_route_404_when_disabled(self):
        with password_only_urls():
            response = self.client.get(reverse("gitlab_callback"))
        self.assertEqual(response.status_code, 404)

    def test_allauth_gitlab_routes_resolve_when_enabled(self):
        with gitlab_urls():
            self.assertEqual(reverse("gitlab_login"), "/api/auth/allauth/gitlab/login/")
            self.assertEqual(
                reverse("gitlab_callback"),
                "/api/auth/allauth/gitlab/login/callback/",
            )
            response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("gitlab_login"))

    def test_allauth_gitlab_login_page_is_styled(self):
        with gitlab_urls():
            response = self.client.get(reverse("gitlab_login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="panel"')
        self.assertContains(response, "Sign in via GitLab")
        self.assertContains(response, "Continue")


class TestCookieSecuritySettings(TestCase):
    def test_session_and_csrf_cookies_are_samesite_lax(self):
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, "Lax")
        self.assertEqual(settings.CSRF_COOKIE_SAMESITE, "Lax")
        self.assertEqual(settings.CSRF_COOKIE_HTTPONLY, False)

    def test_cookie_authentication_enforces_csrf(self):
        self.assertTrue(api_settings.JWT_AUTH_COOKIE_USE_CSRF)
        self.assertEqual(api_settings.JWT_AUTH_COOKIE, ACCESS_COOKIE)
        self.assertEqual(api_settings.JWT_AUTH_REFRESH_COOKIE, REFRESH_COOKIE)

    def test_jwt_hardening_settings(self):
        self.assertTrue(settings.SIMPLE_JWT["CHECK_REVOKE_TOKEN"])
        self.assertEqual(settings.SIMPLE_JWT["LEEWAY"], timedelta(seconds=5))
        self.assertEqual(
            settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"], timedelta(days=3)
        )
        self.assertTrue(settings.SIMPLE_JWT["UPDATE_LAST_LOGIN"])


class TestBuildFrontendAdminUrl(TestCase):
    def test_empty_root(self):
        with override_settings(RELATIVE_URL_ROOT=""):
            self.assertEqual(build_frontend_admin_url(""), "/")

    def test_empty_root_with_slug(self):
        with override_settings(RELATIVE_URL_ROOT=""):
            self.assertEqual(
                build_frontend_admin_url("wsc2026-test"),
                "/wsc2026-test/#/admin-panel",
            )

    def test_subpath_root(self):
        with override_settings(RELATIVE_URL_ROOT="conference/"):
            self.assertEqual(build_frontend_admin_url(""), "/conference/")

    def test_subpath_root_with_slug(self):
        with override_settings(RELATIVE_URL_ROOT="conference/"):
            self.assertEqual(
                build_frontend_admin_url("wsc2026-test"),
                "/conference/wsc2026-test/#/admin-panel",
            )
