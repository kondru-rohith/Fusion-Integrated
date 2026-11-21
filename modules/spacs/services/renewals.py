"""Scholarship renewal service (CFR-SPACS-012, BR-SPACS-017, CW-SPACS-02)."""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.spacs.domain import rules, state_machine
from modules.spacs.models import ScholarshipApplication
from modules.spacs.selectors import scoping
from modules.spacs.services import audit, notifications


@transaction.atomic
def apply_renewal(
    *,
    parent_application_id: int,
    cycle: str,
    submission_data: dict,
    annual_income: Decimal | None = None,
    actor,
) -> ScholarshipApplication:
    """Create a fresh renewal application linked to prior award (BR-SPACS-017)."""
    uid = scoping.own_user_id(actor)
    parent = (
        ScholarshipApplication.objects.select_for_update()
        .filter(pk=parent_application_id, user_id=uid)
        .select_related("catalogue_entry", "catalogue_version")
        .first()
    )
    if parent is None:
        raise NotFoundError("Prior scholarship application not found.")

    if parent.status not in (state_machine.APPROVED, state_machine.RENEWED):
        raise ConflictError(f"Cannot renew scholarship in status {parent.status!r}.")

    version = parent.catalogue_version
    if not version.is_renewable:
        raise ConflictError("This scholarship scheme is not configured for renewal.")

    now = timezone.now()
    is_open, win_msg = rules.is_window_open(
        version.renewal_window_start, version.renewal_window_end, now
    )
    if not is_open:
        raise BadRequestError(win_msg)

    short_uuid = uuid.uuid4().hex[:6].upper()
    renewal_number = f"SPACS-REN-{version.academic_year.replace('-', '')}-{short_uuid}"

    renewal_app = ScholarshipApplication.objects.create(
        user_id=uid,
        application_number=renewal_number,
        catalogue_entry=parent.catalogue_entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=cycle.strip(),
        is_renewal=True,
        parent_application=parent,
        status=state_machine.RENEWAL_SUBMITTED,
        annual_income_declared=annual_income or parent.annual_income_declared,
        submission_data=submission_data,
        submitted_at=now,
    )

    audit.record_transition(
        renewal_app, "none", state_machine.RENEWAL_SUBMITTED, actor, "Student applied for renewal"
    )
    notifications.enqueue(
        topic="renewal.submitted",
        dedupe_key=f"renewal.submitted:{renewal_app.pk}",
        subject=f"Renewal Application Submitted: {parent.catalogue_entry.title}",
        body=(
            f"Your renewal application {renewal_app.application_number} "
            "has been submitted for fresh verification."
        ),
        recipient_user_id=uid,
    )
    return renewal_app
