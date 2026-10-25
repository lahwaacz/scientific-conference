from django.apps import AppConfig
from django.db.backends.signals import connection_created
from django.dispatch import receiver


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        import core.signals  # noqa: F401


@receiver(connection_created)
def _enable_sqlite_wal(sender, connection, **kwargs):
    """Let gunicorn and the Celery worker read/write the same SQLite file.

    WAL is persisted in the database file itself, so every container that
    opens it inherits the mode. Non-SQLite vendors are ignored.
    """
    if connection.vendor != "sqlite":
        return
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA journal_mode=WAL;")
