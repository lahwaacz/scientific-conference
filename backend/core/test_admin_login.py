"""Django admin login gating via allauth's secure_admin_login.

Anonymous visitors are redirected to the allauth login page (which offers
every enabled login method); authenticated non-staff get 403; staff pass.

The allauth pages are registered in every mode, but the GitLab API routes and
the password login API route are conditional; these tests rebuild the URLconf
per deployment mode to pin both.
"""

from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount, SocialLogin
from dj_rest_auth.app_settings import api_settings
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from core.auth.adapters import ConferenceSocialAccountAdapter, NoSignupAccountAdapter
from core.auth.middleware import SessionJWTCookieMiddleware
from core.context_processors import auth_config
from core.models import Conference

from .test_gitlab_auth import (
    gitlab_only_urls,
    gitlab_urls,
    mock_gitlab_http,
    password_only_urls,
)

SLUG = "wsc2026-test"


class TestAdminLoginRedirect(TestCase):
    def setUp(self):
        self.client = Client()

    def test_anonymous_redirects_to_allauth_login(self):
        with gitlab_urls():
            login_url = reverse("account_login")
            response = self.client.get("/admin/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.redirect_chain)
        last_target = response.redirect_chain[-1][0]
        self.assertTrue(last_target.startswith(login_url))

    def test_allauth_login_page_offers_both_methods(self):
        with gitlab_urls():
            response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in with GitLab")
        self.assertContains(response, 'name="login"')
        self.assertContains(response, 'name="password"')

    def test_authenticated_non_staff_gets_403(self):
        # /admin/ 302s non-staff to the wrapped admin login view, whose
        # secure_admin_login turns the authenticated non-staff hit into 403.
        user = User.objects.create_user(
            username="not-staff", password="pw", is_staff=False
        )
        self.client.force_login(user)
        with gitlab_urls():
            response = self.client.get("/admin/", follow=True)
        self.assertEqual(response.status_code, 403)

    def test_anonymous_login_view_redirects_to_allauth_login(self):
        with gitlab_urls():
            login_url = reverse("account_login")
            response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(login_url))

    def test_staff_gets_the_admin_index(self):
        staff = User.objects.create_user(
            username="staffer", password="pw", is_staff=True
        )
        self.client.force_login(staff)
        with gitlab_urls():
            response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)


class TestGitlabSessionLoginReachesDjangoAdmin(TestCase):
    """The GitLab JWT flow also creates a session (SESSION_LOGIN)."""

    def setUp(self):
        self.client = APIClient()
        self.conference = Conference.objects.get_or_create(slug=SLUG)[0]

    def test_gitlab_logged_in_staff_passes_django_admin_gate(self):
        staff = User.objects.create_user(
            username="gitlab-staff", password="pw", is_staff=True
        )
        SocialAccount.objects.create(
            provider="gitlab", uid="123", user=staff, extra_data={"username": "alice"}
        )
        with gitlab_urls():
            state = self.client.get("/api/auth/gitlab/authorize/", {"next": SLUG})
            with mock_gitlab_http():
                response = self.client.post(
                    "/api/auth/gitlab/",
                    {"code": "test-code", "state": state.json()["state"]},
                    format="json",
                )
            self.assertEqual(response.status_code, 200, response.content)
            # The API client shares the session: Django admin accepts staff.
            admin_response = self.client.get("/admin/")
        self.assertEqual(admin_response.status_code, 200)

    def test_password_login_redirected_back_to_admin(self):
        User.objects.create_user(username="pw-staff", password="pw", is_staff=True)
        with gitlab_urls():
            login_url = reverse("account_login")
            response = self.client.post(
                login_url,
                {"login": "pw-staff", "password": "pw", "next": "/admin/"},
                follow=True,
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.redirect_chain)
        self.assertEqual(response.redirect_chain[-1][0], "/admin/")

    def test_bad_password_renders_errors_on_the_login_page(self):
        User.objects.create_user(username="pw-mistake", password="pw", is_staff=True)
        with gitlab_urls():
            response = self.client.post(
                reverse("account_login"),
                {"login": "pw-mistake", "password": "wrong"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())


class TestAdminSessionJWTCookieSync(TestCase):
    def setUp(self):
        self.client = Client()
        User.objects.create_user(username="sync-admin", password="pw", is_staff=True)

    def test_admin_login_issues_jwt_cookies_for_the_frontend(self):
        with password_only_urls():
            response = self.client.post(
                reverse("account_login"),
                {"login": "sync-admin", "password": "pw", "next": "/admin/"},
            )

        self.assertEqual(response.status_code, 302)
        self.assertIn("conference-jwt-access", response.cookies)
        self.assertIn("conference-jwt-refresh", response.cookies)
        self.assertTrue(response.cookies["conference-jwt-access"]["httponly"])
        self.assertEqual(self.client.get("/api/auth/user/").status_code, 200)

    def test_admin_logout_clears_and_blacklists_frontend_tokens(self):
        with password_only_urls():
            self.client.post(
                reverse("account_login"),
                {"login": "sync-admin", "password": "pw", "next": "/admin/"},
            )

        refresh = self.client.cookies["conference-jwt-refresh"].value
        response = self.client.post("/admin/logout/")

        self.assertEqual(response.cookies["conference-jwt-access"].value, "")
        self.assertEqual(response.cookies["conference-jwt-refresh"].value, "")
        self.assertEqual(self.client.get("/api/auth/user/").status_code, 401)

        self.client.cookies["conference-jwt-refresh"] = refresh
        self.assertEqual(self.client.post("/api/auth/refresh/", {}).status_code, 401)

    def test_allauth_logout_clears_and_blacklists_frontend_tokens(self):
        with password_only_urls():
            self.client.post(
                reverse("account_login"),
                {"login": "sync-admin", "password": "pw", "next": "/admin/"},
            )
            refresh = self.client.cookies["conference-jwt-refresh"].value
            response = self.client.post(reverse("account_logout"))

        self.assertEqual(response.cookies["conference-jwt-access"].value, "")
        self.assertEqual(response.cookies["conference-jwt-refresh"].value, "")
        self.assertEqual(self.client.get("/api/auth/user/").status_code, 401)

        self.client.cookies["conference-jwt-refresh"] = refresh
        self.assertEqual(self.client.post("/api/auth/refresh/", {}).status_code, 401)

    def test_failed_admin_login_does_not_issue_frontend_tokens(self):
        with password_only_urls():
            response = self.client.post(
                reverse("account_login"),
                {"login": "sync-admin", "password": "wrong", "next": "/admin/"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("conference-jwt-access", response.cookies)
        self.assertNotIn("conference-jwt-refresh", response.cookies)

    def test_session_bridge_ignores_spa_auth_routes(self):
        self.assertFalse(
            SessionJWTCookieMiddleware._is_session_surface("/api/auth/login/")
        )
        self.assertFalse(
            SessionJWTCookieMiddleware._is_session_surface("/api/auth/logout/")
        )
        self.assertTrue(
            SessionJWTCookieMiddleware._is_session_surface("/admin/logout/")
        )
        self.assertTrue(
            SessionJWTCookieMiddleware._is_session_surface(
                "/api/auth/allauth/gitlab/login/callback/"
            )
        )

    def test_spa_login_does_not_use_the_session_bridge(self):
        api = APIClient()
        with (
            password_only_urls(),
            patch("core.auth.middleware.issue_jwt_cookies") as bridge_set,
        ):
            response = api.post(
                "/api/auth/login/",
                {"username": "sync-admin", "password": "pw"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        bridge_set.assert_not_called()

    def test_session_bridge_honors_relative_url_root(self):
        with (
            password_only_urls(RELATIVE_URL_ROOT="conference/"),
            patch.object(
                api_settings,
                "JWT_AUTH_REFRESH_COOKIE_PATH",
                "/conference/",
            ),
        ):
            response = self.client.post(
                reverse("account_login"),
                {"login": "sync-admin", "password": "pw"},
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                response.cookies["conference-jwt-access"]["path"], "/conference/"
            )
            self.assertEqual(
                response.cookies["conference-jwt-refresh"]["path"], "/conference/"
            )
            self.assertEqual(
                self.client.get("/conference/api/auth/user/").status_code, 200
            )


class TestPasswordOnlyDeployment(TestCase):
    """Password-only mode (no GitLab credentials): the allauth pages still

    work, the password API stays up, and the GitLab API routes are absent.
    """

    def setUp(self):
        self.client = Client()
        self.api = APIClient()
        User.objects.create_user(username="pw-admin", password="pw", is_staff=True)

    def test_account_login_resolves_without_gitlab_credentials(self):
        with password_only_urls():
            self.assertTrue(reverse("account_login"))

    def test_anonymous_admin_reaches_working_login_page(self):
        with password_only_urls():
            login_url = reverse("account_login")
            response = self.client.get("/admin/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.redirect_chain)
        self.assertTrue(response.redirect_chain[-1][0].startswith(login_url))
        self.assertContains(response, 'name="login"')
        self.assertContains(response, 'name="password"')
        self.assertNotContains(response, "Sign in with GitLab")

    def test_password_login_api_still_registered(self):
        with password_only_urls():
            response = self.api.post(
                "/api/auth/login/",
                {"username": "pw-admin", "password": "pw"},
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertNotIn("access", body)
        self.assertNotIn("refresh", body)
        self.assertTrue(response.cookies["conference-jwt-access"]["httponly"])
        self.assertEqual(self.api.get("/api/auth/user/").status_code, 200)

    def test_gitlab_api_routes_are_absent(self):
        with password_only_urls():
            self.assertEqual(
                self.api.get("/api/auth/gitlab/authorize/").status_code, 404
            )
            self.assertEqual(self.api.post("/api/auth/gitlab/", {}).status_code, 404)

    def test_unused_allauth_routes_are_absent(self):
        with password_only_urls():
            for path in (
                "/api/auth/allauth/signup/",
                "/api/auth/allauth/password/reset/",
                "/api/auth/allauth/email/",
            ):
                self.assertEqual(self.client.get(path).status_code, 404)


class TestGitlabOnlyDeployment(TestCase):
    """GitLab-only mode (password login disabled): the GitLab page and JWT

    flow stay up; the password login route and form field are absent.
    """

    def setUp(self):
        self.client = Client()
        self.api = APIClient()

    def test_password_login_route_gone_and_config_reports_flags(self):
        with gitlab_only_urls():
            login_response = self.api.post(
                "/api/auth/login/", {"username": "x", "password": "y"}
            )
            self.assertEqual(login_response.status_code, 404)
            config_response = self.api.get("/api/auth/config/")
        self.assertEqual(
            config_response.json(),
            {"password_login_enabled": False, "gitlab_login_enabled": True},
        )

    def test_password_form_post_rejected_when_password_login_disabled(self):
        # The allauth login page is registered in every mode, so the flag
        # must also block password authentication through the form POST.
        User.objects.create_user(username="pw-denied", password="pw", is_staff=True)
        with gitlab_only_urls():
            response = self.client.post(
                reverse("account_login"),
                {"login": "pw-denied", "password": "pw"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_allauth_page_offers_only_gitlab(self):
        with gitlab_only_urls():
            response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in with GitLab")
        self.assertNotContains(response, 'name="password"')

    def test_anonymous_admin_reaches_gitlab_login_page(self):
        with gitlab_only_urls():
            login_url = reverse("account_login")
            response = self.client.get("/admin/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.redirect_chain)
        self.assertTrue(response.redirect_chain[-1][0].startswith(login_url))


class TestFrontendRoot(TestCase):
    """The allauth login page's back link honors RELATIVE_URL_ROOT."""

    def setUp(self):
        self.client = Client()

    def test_frontend_root_defaults_to_server_root(self):
        request = RequestFactory().get("/")
        with override_settings(RELATIVE_URL_ROOT=""):
            context = auth_config(request)
        self.assertEqual(context["frontend_root"], "/")

    def test_frontend_root_includes_relative_url_root(self):
        request = RequestFactory().get("/")
        with override_settings(RELATIVE_URL_ROOT="conference/"):
            context = auth_config(request)
        self.assertEqual(context["frontend_root"], "/conference/")

    def test_auth_redirect_urls_follow_relative_url_root(self):
        self.assertEqual(settings.LOGIN_REDIRECT_URL, "/" + settings.RELATIVE_URL_ROOT)
        self.assertEqual(
            settings.ACCOUNT_LOGOUT_REDIRECT_URL, "/" + settings.RELATIVE_URL_ROOT
        )

    def test_login_page_back_link_points_at_the_subpath_root(self):
        with gitlab_urls(RELATIVE_URL_ROOT="conference/"):
            response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/conference/"')


class TestAdapterGuards(TestCase):
    def test_validate_disconnect_always_refused(self):
        user = User.objects.create_user(username="linked", password="pw")
        account = SocialAccount.objects.create(
            provider="gitlab", uid="123", user=user, extra_data={"username": "alice"}
        )
        adapter = ConferenceSocialAccountAdapter()
        with self.assertRaisesMessage(
            ValidationError, "Cannot disconnect the university account."
        ):
            adapter.validate_disconnect(account, SocialAccount.objects.all())

    def test_social_signup_open_despite_closed_account_signup(self):
        request = RequestFactory().get("/")
        self.assertFalse(NoSignupAccountAdapter().is_open_for_signup(request))
        self.assertTrue(
            ConferenceSocialAccountAdapter().is_open_for_signup(request, SocialLogin())
        )
