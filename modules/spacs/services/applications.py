"""Application submission, update, resubmission and withdrawal service."""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.spacs.domain import eligibility, rules, state_machine
from modules.spacs.models import ApplicationDocument, CatalogueVersion, ScholarshipApplication
from modules.spacs.selectors import scoping
from modules.spacs.services import audit, notifications


def _generate_app_number(academic_year: str) -> str:
    short_uuid = uuid.uuid4().hex[:6].upper()
    return f"SPACS-{academic_year.replace('-', '')}-{short_uuid}"


def _validate_student_applicant(actor) -> int:
    uid = scoping.own_user_id(actor)
    if uid is None:
        raise BadRequestError("Authenticated user required.")
    actor_kind = getattr(actor, "kind", None)
    if actor_kind and actor_kind != "student":
        raise PermissionDeniedError("Only students can apply for scholarships (BR-SPACS-007).")
    return uid


def _find_active_version(catalogue_version_id: int) -> CatalogueVersion:
    today = timezone.now().date()
    version = (
        CatalogueVersion.objects.filter(
            pk=catalogue_version_id,
            status="published",
            entry__status="active",
            valid_from__lte=today,
            valid_to__gte=today,
        )
        .select_related("entry")
        .first()
    )
    if version is None:
        raise NotFoundError("Active published scholarship scheme not found.")
    return version


@transaction.atomic
def create_draft(
    *,
    catalogue_version_id: int,
    cycle: str,
    actor,
    submission_data: dict | None = None,
    annual_income: Decimal | None = None,
) -> ScholarshipApplication:
    """Create a persistent application draft (BR-SPACS-007)."""
    uid = _validate_student_applicant(actor)
    version = _find_active_version(catalogue_version_id)

    app_number = _generate_app_number(version.academic_year)
    sub_data = submission_data or {}
    income_val = annual_income or sub_data.get("annual_income")
    app = ScholarshipApplication.objects.create(
        user_id=uid,
        application_number=app_number,
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=cycle.strip(),
        is_renewal=False,
        status=state_machine.DRAFT,
        submission_data=sub_data,
        annual_income_declared=Decimal(str(income_val)) if income_val is not None else None,
    )
    doc_ids = sub_data.get("document_ids", [])
    if doc_ids:
        ApplicationDocument.objects.filter(
            pk__in=doc_ids, user_id=uid, is_active=True
        ).update(application=app)
    audit.record_transition(app, "none", state_machine.DRAFT, actor, "Created draft")
    return app


@transaction.atomic
def update_application(
    *,
    application_id: int,
    submission_data: dict,
    annual_income: Decimal | None = None,
    actor,
) -> ScholarshipApplication:
    """Save changes to an editable application draft or correction."""
    actor_kind = getattr(actor, "kind", None)
    uid = scoping.own_user_id(actor)
    if actor_kind != "student" or uid is None:
        raise PermissionDeniedError(
            "Only the owning student can edit an application (BR-SPACS-010)."
        )

    app = ScholarshipApplication.objects.select_for_update().filter(pk=application_id).first()
    if app is None:
        raise NotFoundError("Application not found.")

    if app.user_id != uid:
        raise PermissionDeniedError(
            "Only the owning student can edit their application (BR-SPACS-010)."
        )

    if not state_machine.is_editable(app.status):
        raise ConflictError(f"Application cannot be edited in state {app.status!r}.")

    if app.status == state_machine.CORRECTION_REQUIRED:
        ApplicationDocument.objects.filter(
            application=app, is_active=True, verification_status="valid"
        ).update(verification_status="pending", verification_notes="")

    app.submission_data = submission_data
    if annual_income is not None:
        app.annual_income_declared = annual_income
    app.save(update_fields=["submission_data", "annual_income_declared", "updated_at"])

    doc_ids = submission_data.get("document_ids")
    if doc_ids is not None:
        ApplicationDocument.objects.filter(
            pk__in=doc_ids, user_id=app.user_id, is_active=True
        ).update(application=app)
        ApplicationDocument.objects.filter(
            application=app, is_active=True
        ).exclude(pk__in=doc_ids).update(is_active=False)
    return app


def _check_submission_window_and_eligibility(
    version: CatalogueVersion, app: ScholarshipApplication, student_profile: dict, now
) -> dict:
    is_open, win_msg = rules.is_window_open(
        version.application_window_start, version.application_window_end, now
    )
    if not is_open:
        raise BadRequestError(win_msg)

    income = app.annual_income_declared or student_profile.get("annual_income")
    eval_student = {
        "cpi": (
            float(student_profile.get("cpi")) if student_profile.get("cpi") is not None else None
        ),
        "annual_income": str(income) if income is not None else None,
        "programme": student_profile.get("programme"),
        "discipline": student_profile.get("discipline"),
        "batch_year": student_profile.get("batch_year"),
        "category": student_profile.get("category"),
        "active_backlogs": student_profile.get("active_backlogs", 0),
    }
    elig_result = eligibility.evaluate_eligibility(version.eligibility_criteria, eval_student)
    if not elig_result.is_eligible:
        raise BadRequestError("Eligibility criteria not met: " + "; ".join(elig_result.reasons))
    return eval_student


def _auto_link_required_documents(app: ScholarshipApplication, version: CatalogueVersion) -> None:
    doc_ids = (app.submission_data or {}).get("document_ids", [])
    if doc_ids:
        ApplicationDocument.objects.filter(
            pk__in=doc_ids, user_id=app.user_id, is_active=True, application__isnull=True
        ).update(application=app)

    req_docs = list(version.required_documents or [])
    attached_docs = list(ApplicationDocument.objects.filter(application=app, is_active=True))
    attached_norm_types = {rules.normalize_doc_type(d.doc_type) for d in attached_docs}

    for req_doc in req_docs:
        norm_req = rules.normalize_doc_type(req_doc)
        if norm_req in attached_norm_types:
            continue
        candidates = (
            ApplicationDocument.objects.filter(user_id=app.user_id, is_active=True)
            .exclude(application=app)
            .order_by("-created_at")
        )
        for c in candidates:
            if rules.normalize_doc_type(c.doc_type) == norm_req:
                if c.application is None:
                    c.application = app
                    c.save(update_fields=["application"])
                    attached_norm_types.add(norm_req)
                    break
                if c.is_reusable:
                    ApplicationDocument.objects.create(
                        user_id=app.user_id,
                        application=app,
                        doc_type=c.doc_type,
                        title=c.title,
                        original_filename=c.original_filename,
                        drive_url=c.drive_url,
                        drive_file_id=c.drive_file_id,
                        issued_date=c.issued_date,
                        valid_until=c.valid_until,
                        is_active=True,
                        is_reusable=c.is_reusable,
                        verification_status="pending",
                    )
                    attached_norm_types.add(norm_req)
                    break


def _verify_submission_completeness(app: ScholarshipApplication, version: CatalogueVersion) -> None:
    req_docs = list(version.required_documents or [])
    attached_doc_types = set(
        ApplicationDocument.objects.filter(application=app, is_active=True).values_list(
            "doc_type", flat=True
        )
    )
    mandatory_fields = version.eligibility_criteria.get("mandatory_fields", [])
    comp_result = rules.validate_application_completeness(
        app.submission_data, mandatory_fields, req_docs, attached_doc_types
    )
    if not comp_result.is_complete:
        errs = []
        if comp_result.missing_fields:
            errs.append("Missing fields: " + ", ".join(comp_result.missing_fields))
        if comp_result.missing_documents:
            errs.append("Missing documents: " + ", ".join(comp_result.missing_documents))
        raise BadRequestError("Application is incomplete: " + "; ".join(errs))


@transaction.atomic
def submit_application(
    *,
    application_id: int,
    actor,
    student_profile: dict,
) -> ScholarshipApplication:
    """Validate completeness & eligibility and advance to Submitted (UC-001, BR-001, 002, 004)."""
    app = scoping.visible_applications(actor).select_for_update().filter(pk=application_id).first()
    if app is None:
        raise NotFoundError("Application not found.")
    if app.status != state_machine.DRAFT:
        raise ConflictError(f"Cannot submit application in status {app.status!r}.")

    version = app.catalogue_version
    now = timezone.now()

    eval_student = _check_submission_window_and_eligibility(version, app, student_profile, now)
    _auto_link_required_documents(app, version)
    _verify_submission_completeness(app, version)

    next_state = state_machine.resolve_application_transition(
        app.status, "submit", state_machine.STUDENT
    )
    old_state = app.status
    app.status = next_state
    app.submitted_at = now
    app.cpi_at_apply = student_profile.get("cpi")
    app.demographic_snapshot = eval_student

    try:
        app.save()
    except IntegrityError as exc:
        raise ConflictError(
            "An active application already exists for this scholarship and cycle (BR-SPACS-002)."
        ) from exc

    audit.record_transition(app, old_state, next_state, actor, "Student submitted application")
    notifications.enqueue(
        topic="application.submitted",
        dedupe_key=f"application.submitted:{app.pk}",
        subject=f"Application Submitted: {app.catalogue_entry.title}",
        body=(
            f"Your application {app.application_number} for "
            f"{app.catalogue_entry.title} has been submitted."
        ),
        recipient_user_id=app.user_id,
        payload={"application_id": app.pk, "application_number": app.application_number},
    )
    return app


def _validate_resubmitting_student(app: ScholarshipApplication | None, actor) -> None:
    actor_kind = getattr(actor, "kind", None)
    uid = scoping.own_user_id(actor)
    if actor_kind != "student" or uid is None:
        raise PermissionDeniedError(
            "Only the owning student can resubmit their application (BR-SPACS-010)."
        )
    if app is None:
        raise NotFoundError("Application not found.")
    if app.user_id != uid:
        raise PermissionDeniedError(
            "Only the owning student can resubmit their application (BR-SPACS-010)."
        )
    if app.status != state_machine.CORRECTION_REQUIRED:
        raise ConflictError(f"Cannot resubmit application in status {app.status!r}.")


@transaction.atomic
def resubmit_application(
    *,
    application_id: int,
    actor,
) -> ScholarshipApplication:
    """Resubmit corrected application (UC-003, BR-011)."""
    app = ScholarshipApplication.objects.select_for_update().filter(pk=application_id).first()
    _validate_resubmitting_student(app, actor)

    version = app.catalogue_version
    attached_doc_types = set(
        ApplicationDocument.objects.filter(application=app, is_active=True).values_list(
            "doc_type", flat=True
        )
    )
    comp_result = rules.validate_application_completeness(
        app.submission_data, [], version.required_documents or [], attached_doc_types
    )
    if not comp_result.is_complete:
        raise BadRequestError(
            "Resubmission incomplete: " + ", ".join(comp_result.missing_documents)
        )

    event = "resubmit_renewal" if app.is_renewal else "resubmit"
    next_state = (
        state_machine.resolve_renewal_transition(app.status, event, state_machine.STUDENT)
        if app.is_renewal
        else state_machine.resolve_application_transition(app.status, event, state_machine.STUDENT)
    )

    old_state = app.status
    app.status = next_state
    app.resubmitted_at = timezone.now()
    app.save(update_fields=["status", "resubmitted_at", "updated_at"])

    audit.record_transition(
        app, old_state, next_state, actor, "Student resubmitted corrected application"
    )
    notifications.enqueue(
        topic="application.resubmitted",
        dedupe_key=f"application.resubmitted:{app.pk}:{app.resubmitted_at.isoformat()}",
        subject=f"Application Resubmitted: {app.application_number}",
        body=(
            f"Your corrected application {app.application_number} "
            "has been resubmitted for verification."
        ),
        recipient_user_id=app.user_id,
    )
    return app


@transaction.atomic
def withdraw_application(
    *,
    application_id: int,
    actor,
    reason: str = "",
) -> ScholarshipApplication:
    """Withdraw an application while the lifecycle permits (UC-004, BR-009, BR-010)."""
    actor_kind = getattr(actor, "kind", None)
    uid = scoping.own_user_id(actor)
    if actor_kind != "student" or uid is None:
        raise PermissionDeniedError(
            "Only the owning student can withdraw their application (BR-SPACS-010)."
        )

    app = ScholarshipApplication.objects.select_for_update().filter(pk=application_id).first()
    if app is None:
        raise NotFoundError("Application not found.")

    if app.user_id != uid:
        raise PermissionDeniedError(
            "Only the owning student can withdraw their application (BR-SPACS-010)."
        )

    if not state_machine.can_withdraw(app.status):
        raise ConflictError(f"Application cannot be withdrawn in status {app.status!r}.")

    next_state = state_machine.resolve_application_transition(
        app.status, "withdraw", state_machine.STUDENT
    )
    old_state = app.status
    app.status = next_state
    app.withdrawn_at = timezone.now()
    app.withdrawn_reason = (reason or "").strip()[:300]
    app.save(update_fields=["status", "withdrawn_at", "withdrawn_reason", "updated_at"])

    audit.record_transition(app, old_state, next_state, actor, f"Withdrawn: {reason}")
    notifications.enqueue(
        topic="application.withdrawn",
        dedupe_key=f"application.withdrawn:{app.pk}",
        subject=f"Application Withdrawn: {app.application_number}",
        body=f"Your application {app.application_number} has been withdrawn.",
        recipient_user_id=app.user_id,
    )
    return app
