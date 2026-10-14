"""People endpoint: one Person model with M2M Role lookup
("organizer" / "committee") behind /api/<slug>/people/.

Pins the public read shape (roles as a list of role-name strings, no
auth-user fields), ?role= filtering with cross-conference isolation,
the admin-only write path (JSON list and repeated multipart `roles`
values), role-set replacement on PATCH (an explicit JSON [] clears; a
multipart request without a `roles` key leaves the set unchanged), the
admin-only auth-user link with user_username, and the photo upload_to
directory.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .conftest import api
from .models import Conference, Person, Role

SLUG_A = "wsc2026-test"
SLUG_B = "wsc2027-test"


def wsc_conference():
    return Conference.objects.get_or_create(slug=SLUG_A)[0]


def other_conference():
    return Conference.objects.get_or_create(slug=SLUG_B)[0]


def staff_client(username="admin"):
    user = User.objects.create_user(username=username, password="pw", is_staff=True)
    token = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client, user


class PeopleTestCase(TestCase):
    def setUp(self):
        self.organizer_role, _ = Role.objects.get_or_create(
            name="organizer", defaults={"label": "Organiser"}
        )
        self.committee_role, _ = Role.objects.get_or_create(
            name="committee", defaults={"label": "Organising Committee"}
        )

    def make_person(self, conference, name, roles):
        person = Person.objects.create(conference=conference, name=name)
        person.roles.set(roles)
        return person


class TestPublicPeopleList(PeopleTestCase):
    def test_get_returns_roles_as_name_list(self):
        person = self.make_person(
            wsc_conference(), "Both Roles", [self.organizer_role, self.committee_role]
        )

        response = APIClient().get(api("people/"))

        self.assertEqual(response.status_code, 200)
        results = response.json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], person.pk)
        self.assertEqual(sorted(results[0]["roles"]), ["committee", "organizer"])

    def test_public_list_omits_auth_user_fields(self):
        _, user = staff_client("linked-admin")
        person = Person.objects.create(
            conference=wsc_conference(), name="Linked", user=user
        )
        person.roles.set([self.organizer_role])

        response = APIClient().get(api("people/"))

        self.assertEqual(response.status_code, 200)
        results = response.json()
        self.assertEqual(len(results), 1)
        self.assertNotIn("user", results[0])
        self.assertNotIn("user_username", results[0])

    def test_role_filter_organizer_and_committee(self):
        conference = wsc_conference()
        organizer = self.make_person(conference, "Org Only", [self.organizer_role])
        member = self.make_person(conference, "Cmt Only", [self.committee_role])
        self.make_person(conference, "No Roles", [])

        for role_name, expected in (
            ("organizer", [organizer.pk]),
            ("committee", [member.pk]),
        ):
            with self.subTest(role=role_name):
                response = APIClient().get(api("people/"), {"role": role_name})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    sorted(p["id"] for p in response.json()), sorted(expected)
                )

    def test_empty_role_filter_returns_everybody(self):
        person = self.make_person(wsc_conference(), "Org Only", [self.organizer_role])

        response = APIClient().get(api("people/"), {"role": ""})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([p["id"] for p in response.json()], [person.pk])

    def test_role_filter_is_scoped_to_own_conference(self):
        self.make_person(wsc_conference(), "Own Org", [self.organizer_role])
        foreign = self.make_person(
            other_conference(), "Foreign Org", [self.organizer_role]
        )

        response = APIClient().get(api("people/", slug=SLUG_B))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([p["id"] for p in response.json()], [foreign.pk])

        response = APIClient().get(api("people/", slug=SLUG_B), {"role": "organizer"})
        self.assertEqual([p["id"] for p in response.json()], [foreign.pk])


class TestPeopleWrites(PeopleTestCase):
    def setUp(self):
        super().setUp()
        self.conference = wsc_conference()

    def test_post_requires_admin(self):
        response = APIClient().post(api("people/"), {"name": "Anon"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_post_as_staff_creates_person_with_both_roles(self):
        client, _ = staff_client()

        response = client.post(
            api("people/"),
            {
                "name": "Ada",
                "email": "ada@example.org",
                "roles": ["organizer", "committee"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        person = Person.objects.get(name="Ada")
        self.assertEqual(
            set(person.roles.values_list("name", flat=True)),
            {"organizer", "committee"},
        )
        self.assertEqual(person.conference, wsc_conference())

    def test_post_multipart_repeated_role_values(self):
        # The SPA posts multipart with one `roles` field per selected role.
        client, _ = staff_client()

        response = client.post(
            api("people/"),
            {"name": "Multi", "roles": ["organizer", "committee"]},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(sorted(response.json()["roles"]), ["committee", "organizer"])

    def test_patch_requires_admin(self):
        person = self.make_person(wsc_conference(), "Org", [self.organizer_role])

        response = APIClient().patch(
            api(f"people/{person.pk}/"), {"name": "X"}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_patch_replaces_role_set(self):
        person = self.make_person(
            wsc_conference(),
            "Both",
            [self.organizer_role, self.committee_role],
        )
        client, _ = staff_client()

        response = client.patch(
            api(f"people/{person.pk}/"), {"roles": ["committee"]}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["roles"], ["committee"])
        person.refresh_from_db()
        self.assertEqual(
            list(person.roles.values_list("name", flat=True)), ["committee"]
        )

    def test_patch_json_empty_roles_clears(self):
        person = self.make_person(wsc_conference(), "Org", [self.organizer_role])
        client, _ = staff_client()

        response = client.patch(
            api(f"people/{person.pk}/"), {"roles": []}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["roles"], [])
        person.refresh_from_db()
        self.assertEqual(list(person.roles.all()), [])

    def test_patch_multipart_without_roles_key_keeps_roles(self):
        # Pins the DRF partial-update semantics the SPA relies on: multipart
        # FormData cannot express an empty list, so an absent `roles` key
        # means "leave unchanged" — the editor sends JSON for field saves.
        person = self.make_person(wsc_conference(), "Org", [self.organizer_role])
        client, _ = staff_client()

        response = client.patch(
            api(f"people/{person.pk}/"),
            {"name": "Renamed"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        person.refresh_from_db()
        self.assertEqual(person.name, "Renamed")
        self.assertEqual(
            list(person.roles.values_list("name", flat=True)), ["organizer"]
        )

    def test_delete_as_staff(self):
        person = self.make_person(wsc_conference(), "Org", [self.organizer_role])
        client, _ = staff_client()

        response = client.delete(api(f"people/{person.pk}/"))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Person.objects.filter(pk=person.pk).exists())

    def test_unknown_role_name_is_rejected(self):
        client, _ = staff_client()

        response = client.post(
            api("people/"), {"name": "X", "roles": ["chair"]}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("roles", response.json())

    def test_link_user_and_username(self):
        client, user = staff_client()
        person = self.make_person(wsc_conference(), "Linked", [])

        response = client.patch(
            api(f"people/{person.pk}/"), {"user": user.pk}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["user"], user.pk)
        self.assertEqual(body["user_username"], "admin")
        person.refresh_from_db()
        self.assertEqual(person.user, user)

    def test_user_username_is_none_when_unlinked(self):
        person = self.make_person(wsc_conference(), "Unlinked", [])
        client, _ = staff_client()

        response = client.get(api(f"people/{person.pk}/"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["user_username"])


class TestPersonModel(PeopleTestCase):
    def test_photo_upload_to_is_people_dir(self):
        self.assertEqual(Person._meta.get_field("photo").upload_to, "people/")
