"""Business rules for application completeness, document reuse, and windows.

Pure Python implementation of:
- BR-SPACS-003: Reuse of Previously Uploaded Documents
- BR-SPACS-004: Application Completeness
- BR-SPACS-009: Withdrawal Before Final Decision
- BR-SPACS-010: Owner-Only Modification/Withdrawal
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class CompletenessResult:
    is_complete: bool
    missing_fields: tuple[str, ...]
    missing_documents: tuple[str, ...]

    @classmethod
    def valid(cls) -> CompletenessResult:
        return cls(is_complete=True, missing_fields=(), missing_documents=())

    @classmethod
    def invalid(cls, missing_fields: list[str], missing_documents: list[str]) -> CompletenessResult:
        return cls(
            is_complete=False,
            missing_fields=tuple(missing_fields),
            missing_documents=tuple(missing_documents),
        )


def normalize_doc_type(doc_type: str) -> str:
    """Canonicalize document type: strip, lowercase, replace spaces/hyphens with underscores."""
    if not doc_type:
        return ""
    return str(doc_type).strip().lower().replace("-", "_").replace(" ", "_")


def validate_application_completeness(
    form_data: dict,
    mandatory_fields: list[str],
    required_document_types: list[str],
    attached_document_types: set[str],
) -> CompletenessResult:
    """Validate that all mandatory fields and required documents are provided (BR-SPACS-004)."""
    missing_fields = []
    for f in mandatory_fields:
        val = form_data.get(f)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing_fields.append(f)

    norm_attached = {normalize_doc_type(dt) for dt in attached_document_types}
    missing_docs = [
        dt for dt in required_document_types
        if normalize_doc_type(dt) not in norm_attached
    ]

    if missing_fields or missing_docs:
        return CompletenessResult.invalid(missing_fields, missing_docs)
    return CompletenessResult.valid()


def validate_document_reuse(
    document: dict,
    target_doc_type: str,
    as_of_date: datetime.date,
) -> tuple[bool, str]:
    """Validate if a prior document satisfies reuse rules (BR-SPACS-003).

    `document` dictionary representation:
      - doc_type: str
      - is_active: bool
      - is_reusable: bool
      - valid_until: datetime.date | None
      - verification_status: str ("pending", "valid", "invalid", "resubmission_needed")
    """
    if not document.get("is_active", True):
        return False, "Document has been deactivated."

    if not document.get("is_reusable", True):
        return False, "Document is marked non-reusable."

    if normalize_doc_type(document.get("doc_type", "")) != normalize_doc_type(target_doc_type):
        actual = document.get("doc_type")
        return False, f"Document type mismatch (expected {target_doc_type!r}, got {actual!r})."

    valid_until = document.get("valid_until")
    if valid_until is not None and valid_until < as_of_date:
        return False, f"Document expired on {valid_until.isoformat()}."

    if document.get("verification_status") == "invalid":
        return False, "Document was previously marked invalid by reviewers."

    return True, ""


def is_window_open(
    window_start: datetime.datetime | None,
    window_end: datetime.datetime | None,
    now: datetime.datetime,
) -> tuple[bool, str]:
    """Check if the scheme's application/renewal window is open."""
    if window_start and now < window_start:
        return False, f"Application window opens at {window_start.isoformat()}."
    if window_end and now > window_end:
        return False, f"Application window closed at {window_end.isoformat()}."
    return True, ""
