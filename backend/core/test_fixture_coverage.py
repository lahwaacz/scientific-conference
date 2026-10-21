import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"
TYPES = ("talk", "poster", "attend")
ALL_COMBINATIONS = {
    combo for size in range(1, len(TYPES) + 1) for combo in combinations(TYPES, size)
}


def load(name):
    return json.loads((FIXTURES / name).read_text())


def allowed_types(conference):
    return tuple(
        contribution_type
        for contribution_type in TYPES
        if conference[f"registration_allow_{contribution_type}"]
    )


def test_demo_conferences_cover_every_allowed_type_combination():
    conferences = [row["fields"] for row in load("conferences.json")]

    assert {allowed_types(conference) for conference in conferences} == ALL_COMBINATIONS


def test_every_demo_conference_has_a_participant_for_each_allowed_type():
    conferences = load("conferences.json")
    participants = [
        row for row in load("participants.json") if row["model"] == "core.participant"
    ]
    participant_types = defaultdict(set)
    for participant in participants:
        participant_types[participant["fields"]["conference"]].add(
            participant["fields"]["contribution_type"]
        )

    for conference in conferences:
        assert participant_types[conference["pk"]] == set(
            allowed_types(conference["fields"])
        )


def test_fixture_session_talks_have_their_session_day():
    program = load("program.json")
    session_days = {
        row["pk"]: row["fields"]["day"]
        for row in program
        if row["model"] == "core.session"
    }

    for row in program:
        if row["model"] != "core.talk" or row["fields"].get("session") is None:
            continue
        session_id = row["fields"]["session"]
        assert row["fields"].get("day") == session_days[session_id]


def test_fixture_published_rows_match_each_contribution_type():
    rows = load("participants.json")
    program = load("program.json")
    participants = {
        row["pk"]: row["fields"] for row in rows if row["model"] == "core.participant"
    }
    abstracts = {
        row["fields"]["participant"] for row in rows if row["model"] == "core.abstract"
    }
    talk_types = {
        row["fields"]["participant"]: row["fields"].get("talk_type", "talk")
        for row in program
        if row["model"] == "core.talk" and row["fields"].get("participant")
    }
    talks = set(talk_types)
    submissions = {
        row["fields"]["published_participant"]: row["fields"]
        for row in rows
        if row["model"] == "core.participantsubmission"
    }

    for participant_id, fields in participants.items():
        contribution_type = fields["contribution_type"]
        submission = submissions[participant_id]

        assert submission["contribution_type"] == contribution_type
        assert submission["status"] == "approved"
        if contribution_type == "attend":
            assert participant_id not in abstracts
            assert participant_id not in talks
            assert submission["published_abstract"] is None
        else:
            assert participant_id in abstracts
            assert submission["published_abstract"] is not None
        if contribution_type == "poster":
            assert talk_types[participant_id] == "poster"
        if contribution_type == "talk":
            assert talk_types[participant_id] == "talk"
