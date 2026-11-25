"""Tests for the sponsors endpoints (public list + admin CRUD)."""

from io import BytesIO

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .conftest import api
from .models import Sponsor


def make_superuser():
    return User.objects.create_user(
        username="sponsor-admin", password="pw", is_staff=True, is_superuser=True
    )


def bearer_client(user):
    token = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.mark.django_db
class TestSponsorList:
    def setup_method(self):
        self.client = APIClient()

    def test_anonymous_get_returns_only_own_conference_sponsors(self, wsc, other):
        Sponsor.objects.create(conference=other, name="Foreign Sponsor", order=0)
        Sponsor.objects.create(conference=wsc, name="Gold", order=2)
        Sponsor.objects.create(conference=wsc, name="Silver", order=1)
        Sponsor.objects.create(conference=wsc, name="Bronze", order=1)

        response = self.client.get(api("sponsors/"))

        assert response.status_code == 200
        assert [row["name"] for row in response.json()] == [
            "Silver",
            "Bronze",
            "Gold",
        ]

    def test_equal_orders_fall_back_to_id(self, wsc):
        first = Sponsor.objects.create(conference=wsc, name="First", order=5)
        second = Sponsor.objects.create(conference=wsc, name="Second", order=5)

        response = self.client.get(api("sponsors/"))

        assert response.status_code == 200
        assert [row["id"] for row in response.json()] == [first.pk, second.pk]

    def test_unknown_slug_404s_on_get(self, wsc):
        response = self.client.get(api("sponsors/", slug="zz-no-such-conference"))

        assert response.status_code == 404


@pytest.mark.django_db
class TestSponsorAdmin:
    def setup_method(self):
        self.user = make_superuser()
        self.client = bearer_client(self.user)

    def test_post_without_auth_401(self, wsc):
        anonymous = APIClient()

        response = anonymous.post(api("admin/sponsors/"), {"name": "X"}, format="json")

        assert response.status_code == 401
        assert not Sponsor.objects.exists()

    def test_post_creates_sponsor_attached_to_url_conference(self, wsc, other):
        response = self.client.post(
            api("admin/sponsors/", slug=other.slug),
            {"name": "ACME", "url": "https://acme.example.com", "order": 3},
            format="json",
        )

        assert response.status_code == 201
        sponsor = Sponsor.objects.get(name="ACME")
        assert sponsor.conference == other
        assert sponsor.url == "https://acme.example.com"
        assert sponsor.order == 3
        assert not Sponsor.objects.filter(conference=wsc).exists()

    def test_post_accepts_multipart(self, wsc):
        response = self.client.post(
            api("admin/sponsors/"),
            {"name": "Multipart Co", "order": 2},
            format="multipart",
        )

        assert response.status_code == 201
        assert Sponsor.objects.filter(name="Multipart Co", conference=wsc).exists()

    @staticmethod
    def _png_upload(name="logo.png"):
        buffer = BytesIO()
        Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")

    @staticmethod
    def _svg_upload(name="logo.svg", body=None):
        body = body or (
            b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            b'<rect width="10" height="10"/></svg>'
        )
        return SimpleUploadedFile(name, body, content_type="image/svg+xml")

    def test_post_stores_logo_under_sponsors_dir(self, wsc, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path

        response = self.client.post(
            api("admin/sponsors/"),
            {"name": "Logo Co", "order": 1, "logo": self._png_upload()},
            format="multipart",
        )

        assert response.status_code == 201
        sponsor = Sponsor.objects.get(name="Logo Co")
        assert sponsor.logo.name is not None
        assert sponsor.logo.name.startswith("sponsors/")
        assert (tmp_path / sponsor.logo.name).exists()

    def test_patch_without_logo_preserves_existing(self, wsc, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        sponsor = Sponsor.objects.create(
            conference=wsc, name="Old", logo=self._png_upload("old.png")
        )
        original = sponsor.logo.name

        response = self.client.patch(
            api(f"admin/sponsors/{sponsor.pk}/"),
            {"name": "New"},
            format="json",
        )

        assert response.status_code == 200
        sponsor.refresh_from_db()
        assert sponsor.logo.name == original

    def test_patch_with_logo_replaces_existing(self, wsc, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        sponsor = Sponsor.objects.create(
            conference=wsc, name="Old", logo=self._png_upload("old.png")
        )
        original = sponsor.logo.name

        response = self.client.patch(
            api(f"admin/sponsors/{sponsor.pk}/"),
            {"logo": self._png_upload("new.png")},
            format="multipart",
        )

        assert response.status_code == 200
        sponsor.refresh_from_db()
        assert sponsor.logo.name is not None
        assert sponsor.logo.name != original
        assert sponsor.logo.name.startswith("sponsors/")
        assert (tmp_path / sponsor.logo.name).exists()

    def test_post_stores_svg_logo(self, wsc, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path

        response = self.client.post(
            api("admin/sponsors/"),
            {"name": "Vector Co", "logo": self._svg_upload()},
            format="multipart",
        )

        assert response.status_code == 201
        sponsor = Sponsor.objects.get(name="Vector Co")
        assert sponsor.logo.name is not None
        assert sponsor.logo.name.startswith("sponsors/")
        assert sponsor.logo.name.endswith(".svg")
        assert (tmp_path / sponsor.logo.name).exists()

    def test_rejects_svg_with_script(self, wsc):
        bad_svg = (
            b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        )

        response = self.client.post(
            api("admin/sponsors/"),
            {"name": "Bad Vector", "logo": self._svg_upload(body=bad_svg)},
            format="multipart",
        )

        assert response.status_code == 400
        assert "logo" in response.json()
        assert not Sponsor.objects.filter(name="Bad Vector").exists()

    def test_rejects_svg_with_external_href(self, wsc):
        bad_svg = (
            b'<svg xmlns="http://www.w3.org/2000/svg">'
            b'<image href="https://example.com/logo.png"/></svg>'
        )

        response = self.client.post(
            api("admin/sponsors/"),
            {"name": "Remote Vector", "logo": self._svg_upload(body=bad_svg)},
            format="multipart",
        )

        assert response.status_code == 400
        assert "logo" in response.json()

    def test_rejects_non_image_upload(self, wsc):
        upload = SimpleUploadedFile(
            "logo.txt", b"not an image", content_type="text/plain"
        )

        response = self.client.post(
            api("admin/sponsors/"),
            {"name": "Text Co", "logo": upload},
            format="multipart",
        )

        assert response.status_code == 400
        assert "logo" in response.json()

    def test_rejects_whitespace_only_name(self, wsc):
        response = self.client.post(
            api("admin/sponsors/"), {"name": "   "}, format="json"
        )

        assert response.status_code == 400
        assert "name" in response.json()

    def test_accepts_blank_url(self, wsc):
        response = self.client.post(
            api("admin/sponsors/"), {"name": "No Site", "url": ""}, format="json"
        )

        assert response.status_code == 201
        assert Sponsor.objects.get(name="No Site").url == ""

    def test_non_manager_and_anonymous_cannot_delete(self, wsc):
        sponsor = Sponsor.objects.create(conference=wsc, name="Guarded")
        outsider = User.objects.create_user(username="sponsor-outsider", password="pw")

        anonymous = APIClient().delete(api(f"admin/sponsors/{sponsor.pk}/"))
        forbidden = bearer_client(outsider).delete(api(f"admin/sponsors/{sponsor.pk}/"))

        assert anonymous.status_code == 401
        assert forbidden.status_code == 403
        assert Sponsor.objects.filter(pk=sponsor.pk).exists()

    def test_cookie_auth_without_csrf_is_forbidden(self, wsc):
        sponsor = Sponsor.objects.create(conference=wsc, name="CSRF")
        client = APIClient(enforce_csrf_checks=True)
        client.cookies["conference-jwt-access"] = str(AccessToken.for_user(self.user))

        response = client.patch(
            api(f"admin/sponsors/{sponsor.pk}/"),
            {"name": "Hijack"},
            format="json",
        )

        assert response.status_code == 403
        sponsor.refresh_from_db()
        assert sponsor.name == "CSRF"

    def test_post_requires_name(self, wsc):
        response = self.client.post(api("admin/sponsors/"), {"order": 1}, format="json")

        assert response.status_code == 400
        assert "name" in response.json()

    def test_patch_updates_name_url_order(self, wsc):
        sponsor = Sponsor.objects.create(conference=wsc, name="Old", order=1)

        response = self.client.patch(
            api(f"admin/sponsors/{sponsor.pk}/"),
            {"name": "New", "url": "https://new.example.com", "order": 7},
            format="json",
        )

        assert response.status_code == 200
        sponsor.refresh_from_db()
        assert sponsor.name == "New"
        assert sponsor.url == "https://new.example.com"
        assert sponsor.order == 7

    def test_delete_removes_only_targeted_row(self, wsc, other):
        keep = Sponsor.objects.create(conference=wsc, name="Keep")
        drop = Sponsor.objects.create(conference=wsc, name="Drop")
        foreign = Sponsor.objects.create(conference=other, name="Foreign")

        response = self.client.delete(api(f"admin/sponsors/{drop.pk}/"))

        assert response.status_code == 204
        assert not Sponsor.objects.filter(pk=drop.pk).exists()
        assert Sponsor.objects.filter(pk=keep.pk).exists()
        assert Sponsor.objects.filter(pk=foreign.pk).exists()

    def test_cross_conference_pk_404s_for_patch_and_delete(self, wsc, other):
        sponsor = Sponsor.objects.create(conference=other, name="Other Sponsor")

        response = self.client.patch(
            api(f"admin/sponsors/{sponsor.pk}/", slug=wsc.slug),
            {"name": "Hijack"},
            format="json",
        )
        assert response.status_code == 404

        response = self.client.delete(
            api(f"admin/sponsors/{sponsor.pk}/", slug=wsc.slug)
        )
        assert response.status_code == 404

        sponsor.refresh_from_db()
        assert sponsor.name == "Other Sponsor"
        assert Sponsor.objects.filter(pk=sponsor.pk).exists()

    def test_unknown_slug_404s_on_post(self, wsc):
        response = self.client.post(
            api("admin/sponsors/", slug="zz-no-such-conference"),
            {"name": "X"},
            format="json",
        )

        assert response.status_code == 404
        assert not Sponsor.objects.exists()
