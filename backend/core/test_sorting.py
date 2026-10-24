from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .conftest import api
from .models import Participant, ParticipantSubmission

User = get_user_model()


@pytest.mark.django_db
def test_participant_list_orders_by_surname(client, wsc):
    for name in [
        "Zdeněk Zeman",
        "Robert van der Sar",
        "Lucie Šimková",
        "Klára Sýkorová",
        "Jana Novotná",
    ]:
        Participant.objects.create(conference=wsc, name=name)

    response = client.get(api("participants/"))

    assert response.status_code == 200
    assert [row["name"] for row in response.data] == [
        "Jana Novotná",
        "Robert van der Sar",
        "Lucie Šimková",
        "Klára Sýkorová",
        "Zdeněk Zeman",
    ]


@pytest.mark.django_db
def test_admin_submission_list_orders_by_surname(wsc):
    for name in ["Zdeněk Zeman", "Lucie Šimková", "Klára Sýkorová", "Jana Novotná"]:
        ParticipantSubmission.objects.create(
            conference=wsc,
            name=name,
            email=f"{name.split()[1].lower()}@example.com",
            affiliation="CTU",
            arrival_date=date(2026, 9, 10),
            departure_date=date(2026, 9, 12),
        )

    admin = User.objects.create_user(
        username="sort-admin", password="pw", is_staff=True, is_superuser=True
    )
    token = RefreshToken.for_user(admin)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    response = client.get(api("admin/submissions/"))

    assert response.status_code == 200
    assert [row["name"] for row in response.data] == [
        "Jana Novotná",
        "Lucie Šimková",
        "Klára Sýkorová",
        "Zdeněk Zeman",
    ]


@pytest.mark.django_db
def test_rename_recomputes_sort_key_with_update_fields(wsc):
    participant = Participant.objects.create(conference=wsc, name="Jan Novák")
    assert participant.sort_key == "novak jan"

    participant.name = "Jan Zeman"
    participant.save(update_fields=["name"])
    participant.refresh_from_db()

    assert participant.sort_key == "zeman jan"


@pytest.mark.django_db
def test_save_without_name_update_keeps_persisted_sort_key(wsc):
    participant = Participant.objects.create(conference=wsc, name="Adam Malý")
    assert participant.sort_key == "maly adam"

    participant.name = "Eva Krátá"
    participant.save(update_fields=["affiliation"])
    participant.refresh_from_db()

    assert participant.name == "Adam Malý"
    assert participant.sort_key == "maly adam"


@pytest.mark.django_db
def test_raw_save_populates_empty_sort_key(wsc):
    participant = Participant(conference=wsc, name="Robert van der Sar")
    participant.save_base(raw=True)
    participant.refresh_from_db()

    assert participant.sort_key == "sar robert"


@pytest.mark.django_db
def test_raw_save_keeps_an_explicit_sort_key(wsc):
    participant = Participant(conference=wsc, name="Jan Novák", sort_key="explicit")
    participant.save_base(raw=True)
    participant.refresh_from_db()

    assert participant.sort_key == "explicit"


@pytest.mark.django_db
def test_equal_sort_keys_are_tie_broken_by_name(client, wsc):
    Participant.objects.create(conference=wsc, name="Ján Novák")
    Participant.objects.create(conference=wsc, name="Jan Novák")

    response = client.get(api("participants/"))

    assert [row["name"] for row in response.data] == ["Jan Novák", "Ján Novák"]
