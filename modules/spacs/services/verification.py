"""Application verification service executed by SPACS Assistant (BR-SPACS-006, BR-SPACS-016)."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, NotFoundError
from modules.spacs.domain import state_machine
from modules.spacs.models import ApplicationDocument, ScholarshipApplication, VerificationFinding
from modules.spacs.selectors import scoping
from modules.spacs.services import audit, notifications


@transaction.atomic
def open_verification(application_id: int, actor) -> ScholarshipApplication:
    """Assistant claims or opens an application for verification."""
    app = scoping.visible_applications(actor).select_for_update().filter(pk=application_id).first()
    if app is None:
        raise NotFoundError("Application not found.")

    if app.status in (state_machine.SUBMITTED, state_machine.RESUBMITTED):
        next_state = state_machine.resolve_application_transition(
            app.status, "open_verification", state_machine.SPACS_ASSISTANT
        )
        old_state = app.status
        app.status = next_state
        app.assigned_assistant_id = scoping.own_user_id(actor)
        app.assigned_at = timezone.now()
        app.save(update_fields=["status", "assigned_assistant_id", "assigned_at", "updated_at"])
        audit.record_transition(app, old_state, next_state, actor, "Assistant opened verification")
    elif app.status in (state_machine.RENEWAL_SUBMITTED, state_machine.RENEWAL_RESUBMITTED):
        next_state = state_machine.resolve_renewal_transition(
            app.status, "open_verification", state_machine.SPACS_ASSISTANT
        )
        old_state = app.status
        app.status = next_state
        app.assigned_assistant_id = scoping.own_user_id(actor)
        app.assigned_at = timezone.now()
        app.save(update_fields=["status", "assigned_assistant_id", "assigned_at", "updated_at"])
        audit.record_transition(app, old_state, next_state, actor, "Assistant opened verification")

    return app


def _mark_documents_verified(app, actor) -> None:
    reviewer_uid = scoping.own_user_id(actor) or 0
    now_ts = timezone.now()
    for doc in ApplicationDocument.objects.filter(application=app, is_active=True):
        doc.verification_status = "valid"
        doc.verification_notes = f"Verified by u{reviewer_uid} at {now_ts.isoformat()}"
        doc.save(update_fields=["verification_status", "verification_notes", "updated_at"])
        audit.log_audit_event(
            action="document_verified",
            actor=actor,
            target_type="application_document",
            target_id=doc.pk,
            details={"application_id": app.pk, "doc_type": doc.doc_type, "status": "valid"},
        )


def _notify_finding(
    app, finding, action: str, clean_comments: str, correction_fields: list[str] | None
) -> None:
    if action == "correction_required":
        notifications.enqueue(
            topic="application.correction_required",
            dedupe_key=f"application.correction_required:{app.pk}:{finding.pk}",
            subject=f"Correction Required: {app.application_number}",
            body=f"Your application requires corrections: {clean_comments}",
            recipient_user_id=app.user_id,
            payload={"correction_fields": correction_fields or []},
        )
    elif action == "verified":
        notifications.enqueue(
            topic="application.verified",
            dedupe_key=f"application.verified:{app.pk}",
            subject=f"Application Verified: {app.application_number}",
            body=(
                f"Your application {app.application_number} "
                "has been verified and routed for sanction."
            ),
            recipient_user_id=app.user_id,
        )


def _advance_finding_state(app, action: str) -> tuple[str, str]:
    event_map = {
        "verified": "verify_satisfied",
        "correction_required": "request_correction",
        "concern_raised": "raise_concern",
    }
    if action not in event_map:
        raise BadRequestError(f"Invalid verification action {action!r}.")

    event = event_map[action]
    next_state = (
        state_machine.resolve_renewal_transition(app.status, event, state_machine.SPACS_ASSISTANT)
        if app.is_renewal
        else state_machine.resolve_application_transition(
            app.status, event, state_machine.SPACS_ASSISTANT
        )
    )

    old_state = app.status
    app.status = next_state
    app.save(update_fields=["status", "updated_at"])
    return old_state, next_state


@transaction.atomic
def record_finding(
    *,
    application_id: int,
    action: str,  # verified, correction_required, concern_raised
    comments: str,
    correction_fields: list[str] | None = None,
    actor,
) -> VerificationFinding:
    """Record verification outcome without making the final sanction decision (BR-SPACS-006)."""
    app = scoping.visible_applications(actor).select_for_update().filter(pk=application_id).first()
    if app is None:
        raise NotFoundError("Application not found.")

    if app.status in (
        state_machine.SUBMITTED,
        state_machine.RESUBMITTED,
        state_machine.RENEWAL_SUBMITTED,
        state_machine.RENEWAL_RESUBMITTED,
    ):
        open_verification(application_id, actor)
        app.refresh_from_db()

    clean_comments = (comments or "").strip()
    if not clean_comments:
        raise BadRequestError("Verification comments are required.")

    old_state, next_state = _advance_finding_state(app, action)

    finding = VerificationFinding.objects.create(
        application=app,
        reviewer_id=scoping.own_user_id(actor) or 0,
        action=action,
        comments=clean_comments,
        correction_fields=correction_fields or [],
    )

    audit.record_transition(
        app, old_state, next_state, actor, f"Verification: {action} - {clean_comments}"
    )

    if action == "verified":
        _mark_documents_verified(app, actor)

    _notify_finding(app, finding, action, clean_comments, correction_fields)
    return finding
