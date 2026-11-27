"""Scholarship decision service executed by SPACS Convener (CFR-SPACS-008, BR-SPACS-018)."""

from __future__ import annotations

from django.db import transaction

from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from modules.spacs.domain import rules, state_machine
from modules.spacs.models import ApplicationDocument, ScholarshipApplication, ScholarshipDecision
from modules.spacs.selectors import scoping
from modules.spacs.services import audit, notifications


@transaction.atomic
def open_review(application_id: int, actor) -> ScholarshipApplication:
    """Convener opens an application for decision review."""
    actor_kind = getattr(actor, "kind", None)
    if actor_kind == "student" or not (
        scoping.is_convener(actor)
        or getattr(actor, "has_permission", lambda p: False)("spacs.application.approve")
    ):
        raise PermissionDeniedError("Only the SPACS Convener can open applications for review.")

    app = scoping.visible_applications(actor).select_for_update().filter(pk=application_id).first()
    if app is None:
        raise NotFoundError("Application not found.")

    if app.status in (state_machine.VERIFIED, state_machine.VERIFICATION_CONCERN):
        next_state = state_machine.resolve_application_transition(
            app.status, "open_review", state_machine.SPACS_CONVENER
        )
        old_state = app.status
        app.status = next_state
        app.save(update_fields=["status", "updated_at"])
        audit.record_transition(app, old_state, next_state, actor, "Convener opened review")

    return app


def _validate_decision_actor(actor) -> None:
    actor_kind = getattr(actor, "kind", None)
    if actor_kind == "student" or not (
        scoping.is_convener(actor)
        or getattr(actor, "has_permission", lambda p: False)("spacs.application.approve")
    ):
        raise PermissionDeniedError("Only the SPACS Convener can record scholarship decisions.")


def _validate_approval_documents(app) -> None:
    version = app.catalogue_version
    if version and version.required_documents:
        valid_doc_types = {
            rules.normalize_doc_type(d.doc_type)
            for d in ApplicationDocument.objects.filter(
                application=app, is_active=True, verification_status="valid"
            )
        }
        unverified_docs = [
            req_doc
            for req_doc in version.required_documents
            if rules.normalize_doc_type(req_doc) not in valid_doc_types
        ]
        if unverified_docs:
            doc_list = ", ".join(unverified_docs)
            raise BadRequestError(
                "Cannot approve application: required documents are pending or unverified "
                f"({doc_list})."
            )

    invalid_docs = list(
        ApplicationDocument.objects.filter(
            application=app, is_active=True, verification_status="invalid"
        )
    )
    if invalid_docs:
        inv_types = [d.doc_type for d in invalid_docs]
        raise BadRequestError(
            f"Cannot approve application: documents were rejected ({', '.join(inv_types)})."
        )


def _resolve_decision_state(app, event: str) -> tuple[str, str]:
    if app.is_renewal:
        next_state = state_machine.resolve_renewal_transition(
            app.status, event, state_machine.SPACS_CONVENER
        )
    else:
        if app.status in (state_machine.VERIFIED, state_machine.VERIFICATION_CONCERN):
            app.status = state_machine.resolve_application_transition(
                app.status, "open_review", state_machine.SPACS_CONVENER
            )
        next_state = state_machine.resolve_application_transition(
            app.status, event, state_machine.SPACS_CONVENER
        )
    old_state = app.status
    return old_state, next_state


def _notify_decision(app, record, decision: str, rationale: str, sanction_order_ref: str) -> None:
    topic = "application.correction_required" if decision == "returned_for_correction" else (
        f"renewal.{decision}" if app.is_renewal else f"application.{decision}"
    )
    notifications.enqueue(
        topic=topic if topic in notifications.TOPICS else "application.approved",
        dedupe_key=f"application.decision:{app.pk}:{record.pk}",
        subject=(
            f"Scholarship Decision: {app.catalogue_entry.title} - "
            f"{decision.replace('_', ' ').title()}"
        ),
        body=(
            f"Your application {app.application_number} decision has been recorded: "
            f"{decision.title()}.\n{rationale}"
        ),
        recipient_user_id=app.user_id,
        payload={"decision": decision, "sanction_order_ref": sanction_order_ref},
    )


@transaction.atomic
def make_decision(
    *,
    application_id: int,
    decision: str,  # approved, rejected, returned_for_correction
    sanction_order_ref: str = "",
    rationale: str = "",
    actor,
) -> ScholarshipDecision:
    """Record final sanction or rejection outcome (BR-SPACS-018)."""
    _validate_decision_actor(actor)

    app = scoping.visible_applications(actor).select_for_update().filter(pk=application_id).first()
    if app is None:
        raise NotFoundError("Application not found.")

    event_map = {
        "approved": "approve",
        "rejected": "reject",
        "returned_for_correction": "return_for_correction",
    }
    if decision not in event_map:
        raise BadRequestError(f"Invalid decision {decision!r}.")

    if decision == "approved":
        _validate_approval_documents(app)

    event = event_map[decision]
    old_state, next_state = _resolve_decision_state(app, event)
    app.status = next_state
    app.save(update_fields=["status", "updated_at"])

    record = ScholarshipDecision.objects.create(
        application=app,
        decider_id=scoping.own_user_id(actor) or 0,
        decision=decision,
        sanction_order_ref=sanction_order_ref.strip(),
        rationale=rationale.strip(),
    )

    audit.record_transition(
        app, old_state, next_state, actor, f"Convener Decision: {decision} ({sanction_order_ref})"
    )
    _notify_decision(app, record, decision, rationale, sanction_order_ref)
    return record
