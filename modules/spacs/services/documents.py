"""Document attachment, validation, and reuse service (BR-SPACS-003, BR-SPACS-016)."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from core.files import drive, validators
from modules.spacs.domain import rules
from modules.spacs.models import ApplicationDocument, ScholarshipApplication
from modules.spacs.selectors import scoping

MAX_DOCUMENTS_PER_STUDENT = 30


@transaction.atomic
def attach_drive_link(
    *,
    user_id: int,
    doc_type: str,
    url: str,
    title: str = "",
    application_id: int | None = None,
    valid_until: datetime.date | None = None,
    is_reusable: bool = True,
) -> ApplicationDocument:
    """Validate and canonicalize a Google Drive link, saving it as an application document."""
    try:
        ref = drive.parse(url)
    except drive.InvalidDriveLink as exc:
        raise ConflictError(exc.message, code=exc.code) from exc

    if (
        ApplicationDocument.objects.filter(user_id=user_id, is_active=True).count()
        >= MAX_DOCUMENTS_PER_STUDENT
    ):
        raise ConflictError(
            f"You can keep at most {MAX_DOCUMENTS_PER_STUDENT} documents. Deactivate an older one.",
            code="too_many_documents",
        )

    clean_doc_type = rules.normalize_doc_type(doc_type) or doc_type.strip()
    clean_title = (title or "").strip()[:160] or doc_type.replace("_", " ").title()
    clean_filename = validators.sanitise_filename(title or doc_type, fallback="document")

    app = None
    if application_id is not None:
        app = ScholarshipApplication.objects.filter(pk=application_id, user_id=user_id).first()
        if app is None:
            raise NotFoundError("Application not found.")

    return ApplicationDocument.objects.create(
        user_id=user_id,
        application=app,
        doc_type=clean_doc_type,
        title=clean_title,
        original_filename=clean_filename,
        drive_url=ref.url,
        drive_file_id=ref.file_id,
        issued_date=timezone.now().date(),
        valid_until=valid_until,
        is_active=True,
        is_reusable=is_reusable,
        verification_status="pending",
    )


def get_reusable_documents(user_id: int, target_doc_type: str) -> list[ApplicationDocument]:
    """Return all valid, reusable documents owned by the student (BR-SPACS-003)."""
    norm_target = rules.normalize_doc_type(target_doc_type)
    candidates = ApplicationDocument.objects.filter(
        user_id=user_id,
        is_active=True,
        is_reusable=True,
    ).order_by("-created_at")

    today = timezone.now().date()
    valid_docs = []
    for doc in candidates:
        if rules.normalize_doc_type(doc.doc_type) != norm_target:
            continue
        is_valid, _ = rules.validate_document_reuse(
            {
                "doc_type": doc.doc_type,
                "is_active": doc.is_active,
                "is_reusable": doc.is_reusable,
                "valid_until": doc.valid_until,
                "verification_status": doc.verification_status,
            },
            target_doc_type,
            today,
        )
        if is_valid:
            valid_docs.append(doc)
    return valid_docs


@transaction.atomic
def deactivate_document(document_id: int, actor) -> None:
    """Soft-deactivate a document so past verification records retain audit integrity."""
    uid = scoping.own_user_id(actor)
    doc = ApplicationDocument.objects.filter(pk=document_id, user_id=uid, is_active=True).first()
    if doc is None:
        raise NotFoundError("Document not found.")

    doc.is_active = False
    doc.save(update_fields=["is_active", "updated_at"])
