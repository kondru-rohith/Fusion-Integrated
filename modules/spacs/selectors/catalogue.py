from __future__ import annotations

from core.api.exceptions import NotFoundError
from modules.spacs.models import CatalogueEntry, CatalogueVersion
from modules.spacs.selectors import scoping


def get_catalogue_entry_or_404(entry_id: int, actor) -> CatalogueEntry:
    entry = scoping.visible_catalogue_entries(actor).filter(pk=entry_id).first()
    if entry is None:
        raise NotFoundError("No such catalogue entry.")
    return entry


def get_catalogue_version_or_404(version_id: int, actor) -> CatalogueVersion:
    ver = scoping.visible_catalogue_versions(actor).filter(pk=version_id).first()
    if ver is None:
        raise NotFoundError("No such catalogue version.")
    return ver


def get_active_scholarships(actor) -> list[CatalogueVersion]:
    return list(
        scoping.visible_catalogue_versions(actor)
        .filter(entry__kind="scholarship", status="published")
        .order_by("entry__title")
    )


def get_active_awards(actor) -> list[CatalogueVersion]:
    return list(
        scoping.visible_catalogue_versions(actor)
        .filter(entry__kind="award", status="published")
        .order_by("entry__title")
    )
