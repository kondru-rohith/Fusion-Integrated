"""Catalogue administration and policy versioning service (CFR-SPACS-002, BR-SPACS-014, 015)."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.spacs.models import CatalogueEntry, CatalogueVersion
from modules.spacs.selectors import scoping
from modules.spacs.services import audit


@transaction.atomic
def create_entry(
    *,
    code: str,
    title: str,
    kind: str,
    description: str = "",
    allow_multiple_applications: bool = False,
    actor,
) -> CatalogueEntry:
    clean_code = (code or "").strip().upper()
    if not clean_code or not title.strip():
        raise BadRequestError("Scheme code and title are required.")

    if CatalogueEntry.objects.filter(code=clean_code).exists():
        raise ConflictError(f"Catalogue entry {clean_code!r} already exists.")

    entry = CatalogueEntry.objects.create(
        code=clean_code,
        title=title.strip(),
        kind=kind,
        description=description.strip(),
        status="draft",
        allow_multiple_applications=allow_multiple_applications,
    )
    audit.log_audit_event(
        "catalogue.entry_created", actor, "CatalogueEntry", entry.pk, {"code": clean_code}
    )
    return entry


def _compute_version_dates(
    valid_from: datetime.date | None, valid_to: datetime.date | None
) -> tuple[datetime.date, datetime.date]:
    today = timezone.now().date()
    effective_from = valid_from or today
    effective_to = valid_to or (effective_from + datetime.timedelta(days=365))
    return effective_from, effective_to


def _persist_version_record(
    entry: CatalogueEntry, academic_year: str, policy_reference: str, kwargs: dict
) -> CatalogueVersion:
    latest = entry.versions.order_by("-version_number").first()
    next_num = (latest.version_number + 1) if latest else 1
    return CatalogueVersion.objects.create(
        entry=entry,
        version_number=next_num,
        academic_year=academic_year.strip(),
        policy_reference=(policy_reference or "").strip(),
        **kwargs,
    )


@transaction.atomic
def create_version(
    *,
    entry_id: int,
    academic_year: str,
    valid_from: datetime.date | None = None,
    valid_to: datetime.date | None = None,
    candidate_source: str = "student_application",
    policy_reference: str = "",
    application_window_start: datetime.datetime | None = None,
    application_window_end: datetime.datetime | None = None,
    renewal_window_start: datetime.datetime | None = None,
    renewal_window_end: datetime.datetime | None = None,
    is_renewable: bool = False,
    eligibility_criteria: dict | None = None,
    required_documents: list[str] | None = None,
    renewal_criteria: dict | None = None,
    committee_config: dict | None = None,
    sla_threshold_days: int = 7,
    actor,
) -> CatalogueVersion:
    entry = CatalogueEntry.objects.filter(pk=entry_id).first()
    if entry is None:
        raise NotFoundError("Catalogue entry not found.")

    effective_from, effective_to = _compute_version_dates(valid_from, valid_to)
    kwargs = {
        "candidate_source": candidate_source,
        "valid_from": effective_from,
        "valid_to": effective_to,
        "application_window_start": application_window_start,
        "application_window_end": application_window_end,
        "renewal_window_start": renewal_window_start,
        "renewal_window_end": renewal_window_end,
        "is_renewable": is_renewable,
        "eligibility_criteria": eligibility_criteria or {},
        "required_documents": required_documents or [],
        "renewal_criteria": renewal_criteria or {},
        "committee_config": committee_config or {},
        "sla_threshold_days": sla_threshold_days,
        "status": "draft",
    }
    version = _persist_version_record(entry, academic_year, policy_reference, kwargs)
    audit.log_audit_event(
        "catalogue.version_created",
        actor,
        "CatalogueVersion",
        version.pk,
        {"version": version.version_number, "entry": entry.code},
    )
    return version


@transaction.atomic
def publish_version(
    *,
    version_id: int,
    policy_reference: str,
    valid_from: datetime.date | None = None,
    valid_to: datetime.date | None = None,
    actor,
) -> CatalogueVersion:
    """Publish a policy version, ensuring approved policy reference exists (BR-SPACS-015)."""
    version = CatalogueVersion.objects.select_for_update().filter(pk=version_id).first()
    if version is None:
        raise NotFoundError("Catalogue version not found.")

    clean_ref = (policy_reference or version.policy_reference or "").strip()
    if not clean_ref:
        raise BadRequestError(
            "Approved policy reference is mandatory to publish a catalogue version (BR-SPACS-015)."
        )

    version.policy_reference = clean_ref
    if valid_from:
        version.valid_from = valid_from
    if valid_to:
        version.valid_to = valid_to

    version.status = "published"
    version.published_at = timezone.now()
    version.published_by = scoping.own_user_id(actor)
    version.save()

    # Activate parent entry if draft
    if version.entry.status == "draft":
        version.entry.status = "active"
        version.entry.save(update_fields=["status", "updated_at"])

    audit.log_audit_event(
        "catalogue.version_published",
        actor,
        "CatalogueVersion",
        version.pk,
        {"policy_reference": clean_ref, "version": version.version_number},
    )
    return version


@transaction.atomic
def retire_entry(entry_id: int, actor) -> CatalogueEntry:
    entry = CatalogueEntry.objects.select_for_update().filter(pk=entry_id).first()
    if entry is None:
        raise NotFoundError("Catalogue entry not found.")

    entry.status = "retired"
    entry.save(update_fields=["status", "updated_at"])

    # Retire current active versions prospectively
    entry.versions.filter(status="published").update(status="retired")

    audit.log_audit_event(
        "catalogue.entry_retired", actor, "CatalogueEntry", entry.pk, {"code": entry.code}
    )
    return entry
