from datetime import timedelta
from unittest.mock import patch

from dj_rest_auth.app_settings import api_settings
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from core.models import Conference

from .conftest import api

SLUG = "cookie-auth-test"
ACCESS_COOKIE = "conference-jwt-access"
REFRESH_COOKIE = "conference-jwt-refresh"


class CookieAuthTestCase(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.user = User.objects.create_user(
            username="cookie-admin", password="pw", is_staff=True
        )
        self.conference = Conference.objects.create(slug=SLUG)

    def login(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "cookie-admin", "password": "pw"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        return response

    def post_logout(self):
        return self.client.post(
            "/api/auth/logout/",
            HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
        )


class TestCookieLogin(CookieAuthTestCase):
    def test_login_sets_httponly_cookies_without_tokens_in_json(self):
        response = self.login()
        body = response.json()

        self.assertNotIn("access", body)
        self.assertNotIn("refresh", body)
        self.assertTrue(response.cookies[ACCESS_COOKIE]["httponly"])
        self.assertTrue(response.cookies[REFRESH_COOKIE]["httponly"])
        self.assertEqual(response.cookies[ACCESS_COOKIE]["samesite"], "Lax")
        self.assertEqual(response.cookies[ACCESS_COOKIE]["path"], "/")
        self.assertIn("csrftoken", response.cookies)
        self.assertFalse(response.cookies["csrftoken"]["httponly"])

    def test_cookie_authenticates_scoped_admin_endpoint(self):
        self.login()

        response = self.client.get(api("admin-panel/", slug=SLUG))

        self.assertEqual(response.status_code, 200)

    def test_expired_access_cookie_is_ignored_by_public_endpoint(self):
        self.login()
        expired = AccessToken.for_user(self.user)
        # Expire beyond the configured 5-second leeway.
        expired.set_exp(lifetime=timedelta(seconds=-10))
        self.client.cookies[ACCESS_COOKIE] = str(expired)

        public_response = self.client.get("/api/conferences/")
        admin_response = self.client.get(api("admin-panel/", slug=SLUG))

        self.assertEqual(public_response.status_code, 200)
        self.assertEqual(admin_response.status_code, 401)


class TestCookieRefresh(CookieAuthTestCase):
    def test_refresh_reads_cookie_and_returns_no_access_token(self):
        self.login()
        del self.client.cookies[ACCESS_COOKIE]

        response = self.client.post("/api/auth/refresh/", {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access", response.json())
        self.assertIn(ACCESS_COOKIE, response.cookies)
        self.assertTrue(response.cookies[ACCESS_COOKIE]["httponly"])
        self.assertEqual(self.client.get("/api/auth/user/").status_code, 200)


class TestCookieLogout(CookieAuthTestCase):
    def test_logout_clears_jwt_cookies_and_session(self):
        self.login()
        self.assertIn("_auth_user_id", self.client.session)

        response = self.post_logout()

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.cookies[ACCESS_COOKIE].value, "")
        self.assertEqual(response.cookies[REFRESH_COOKIE].value, "")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.post("/api/auth/refresh/").status_code, 401)

    def test_logout_without_access_cookie_is_rejected(self):
        self.login()
        del self.client.cookies[ACCESS_COOKIE]

        response = self.client.post("/api/auth/logout/")

        self.assertEqual(response.status_code, 401)
        self.assertIn("_auth_user_id", self.client.session)

    def test_logout_without_csrf_is_rejected(self):
        self.login()

        response = self.client.post("/api/auth/logout/")

        self.assertEqual(response.status_code, 403)
        self.assertIn("_auth_user_id", self.client.session)


class TestCookieScope(CookieAuthTestCase):
    def test_login_scopes_both_cookies_to_the_deployed_subpath(self):
        with (
            patch(
                "core.auth.views._jwt_cookie_path",
                return_value="/conference/",
            ),
            patch.object(api_settings, "JWT_AUTH_REFRESH_COOKIE_PATH", "/conference/"),
        ):
            response = self.login()

        self.assertEqual(response.cookies[ACCESS_COOKIE]["path"], "/conference/")
        self.assertEqual(response.cookies[REFRESH_COOKIE]["path"], "/conference/")


class TestTokenRevocation(CookieAuthTestCase):
    def test_password_change_revokes_existing_tokens(self):
        self.client.cookies[ACCESS_COOKIE] = str(
            RefreshToken.for_user(self.user).access_token
        )
        self.user.set_password("new-password")
        self.user.save()

        response = self.client.get(api("admin-panel/", slug=SLUG))

        self.assertEqual(response.status_code, 401)

    def test_password_change_rejects_refresh_token(self):
        self.client.cookies[REFRESH_COOKIE] = str(RefreshToken.for_user(self.user))
        self.user.set_password("new-password")
        self.user.save()

        response = self.client.post("/api/auth/refresh/", {}, format="json")

        self.assertEqual(response.status_code, 401)


class TestPublicCsrfBypass(CookieAuthTestCase):
    def test_public_write_does_not_require_csrf_with_a_valid_cookie(self):
        self.login()

        response = self.client.post(api("submit/", slug=SLUG), {}, format="json")

        self.assertNotEqual(response.status_code, 403)
