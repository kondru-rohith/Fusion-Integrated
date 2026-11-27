from __future__ import annotations

from django.apps import AppConfig
from django.db import DatabaseError, OperationalError


def readiness() -> list[str]:
    """Verify the module's critical operational dependencies (Finding R2-15)."""
    unmet: list[str] = []
    try:
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except (OperationalError, DatabaseError) as exc:
        unmet.append(f"Database connection error: {exc}")

    try:
        from modules.spacs.models import CatalogueEntry

        # Verify tables are migrated and queryable
        CatalogueEntry.objects.exists()
    except (OperationalError, DatabaseError) as exc:
        unmet.append(f"SPACS database tables not ready: {exc}")

    return unmet


class SpacsConfig(AppConfig):
    name = "modules.spacs"
    label = "spacs"
    verbose_name = "SPACS - Awards and Scholarships"

    def readiness(self) -> list[str]:
        return readiness()
