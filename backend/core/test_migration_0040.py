"""Exercise migration 0040 through Django's real migration executor.

Seeding through the executor's historical apps after rolling back avoids the
in-memory SQLite snapshot pitfall: schema changes and seeds use the same
connection-visible state, rather than current models or an external snapshot.
"""

from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class TestRegistrationConfigMigration0040(TransactionTestCase):
    migrate_from = ("core", "0039_conferencemanagers")
    migrate_to = (
        "core",
        "0040_remove_conference_registration_instructions_and_more",
    )

    def setUp(self) -> None:
        super().setUp()

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        historical_apps = executor.loader.project_state([self.migrate_from]).apps
        Conference = historical_apps.get_model("core", "Conference")
        ParticipantSubmission = historical_apps.get_model(
            "core", "ParticipantSubmission"
        )

        field_names = {field.name for field in Conference._meta.get_fields()}
        self.assertIn("registration_instructions", field_names)
        self.assertNotIn("registration_collect_dates", field_names)
        submission_field_names = {
            field.name for field in ParticipantSubmission._meta.get_fields()
        }
        self.assertNotIn("stay_dates_derived", submission_field_names)

        Conference.objects.create(
            slug="migration-0040-multi-day",
            date_start=date(2026, 5, 1),
            date_end=date(2026, 5, 3),
        )
        Conference.objects.create(
            slug="migration-0040-single-day",
            date_start=date(2026, 6, 1),
            date_end=date(2026, 6, 1),
        )
        Conference.objects.create(
            slug="migration-0040-inverted",
            date_start=date(2026, 7, 3),
            date_end=date(2026, 7, 2),
        )
        Conference.objects.create(
            slug="migration-0040-start-only",
            date_start=date(2026, 8, 1),
        )
        Conference.objects.create(
            slug="migration-0040-end-only",
            date_end=date(2026, 8, 2),
        )
        self.submission_id = ParticipantSubmission.objects.create(
            conference=Conference.objects.get(slug="migration-0040-multi-day"),
            name="Migration Tester",
            email="migration@example.com",
            affiliation="CTU",
            arrival_date=date(2026, 5, 1),
            departure_date=date(2026, 5, 3),
        ).pk

    def tearDown(self) -> None:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_forward_migration_computes_flags_and_removes_legacy_column(self) -> None:
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        migrated_apps = executor.loader.project_state([self.migrate_to]).apps
        Conference = migrated_apps.get_model("core", "Conference")
        ParticipantSubmission = migrated_apps.get_model("core", "ParticipantSubmission")
        self.assertFalse(
            ParticipantSubmission.objects.get(pk=self.submission_id).stay_dates_derived
        )

        expected = {
            "migration-0040-multi-day": True,
            "migration-0040-single-day": False,
            "migration-0040-inverted": True,
            "migration-0040-start-only": True,
            "migration-0040-end-only": True,
        }
        actual = dict(
            Conference.objects.filter(slug__in=expected).values_list(
                "slug", "registration_collect_dates"
            )
        )
        self.assertEqual(actual, expected)

        with connection.cursor() as cursor:
            conference_columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor, "core_conference"
                )
            }
            submission_columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor, "core_participantsubmission"
                )
            }

        self.assertNotIn("registration_instructions", conference_columns)
        self.assertIn("registration_collect_dates", conference_columns)
        self.assertIn("stay_dates_derived", submission_columns)
