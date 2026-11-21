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
    actor_kind = getattr(actor, "kind", None)
    if actor_kind == "student" or not (
        scoping.is_convener(actor)
        or getattr(actor, "has_permission", lambda p: False)("spacs.application.approve")
    ):
        raise PermissionDeniedError("Only the SPACS Convener can record scholarship decisions.")

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
                    f"Cannot approve application: required documents are pending or unverified "
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

    event = event_map[decision]
    if app.is_renewal:
        next_state = state_machine.resolve_renewal_transition(
            app.status, event, state_machine.SPACS_CONVENER
        )
    else:
        # If still in verified/concern, advance through open_review first
        if app.status in (state_machine.VERIFIED, state_machine.VERIFICATION_CONCERN):
            app.status = state_machine.resolve_application_transition(
                app.status, "open_review", state_machine.SPACS_CONVENER
            )
        next_state = state_machine.resolve_application_transition(
            app.status, event, state_machine.SPACS_CONVENER
        )

    old_state = app.status
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

    if decision == "returned_for_correction":
        topic = "application.correction_required"
    elif app.is_renewal:
        topic = f"renewal.{decision}"
    else:
        topic = f"application.{decision}"

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
    return record
