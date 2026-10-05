import pytest

from .models import Conference


@pytest.fixture
def wsc(db):
    return Conference.objects.create(slug="wsc2026-test")


@pytest.fixture
def other(db):
    return Conference.objects.create(slug="wsc2027-test")


def api(path, slug="wsc2026-test"):
    return f"/api/{slug}/{path}"
