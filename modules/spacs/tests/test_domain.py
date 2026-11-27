"""Domain tests: pure Python, no database, state transitions and eligibility rules."""

import datetime
from decimal import Decimal

import pytest

from modules.spacs.domain import eligibility, rules
from modules.spacs.domain import state_machine as sm


def test_application_lifecycle_valid_transitions():
    """Verify standard happy-path transitions for scholarship application (CW-SPACS-01)."""
    # Draft -> Submitted
    assert sm.resolve_application_transition(sm.DRAFT, "submit", sm.STUDENT) == sm.SUBMITTED

    # Submitted -> Under Verification
    assert (
        sm.resolve_application_transition(sm.SUBMITTED, "open_verification", sm.SPACS_ASSISTANT)
        == sm.UNDER_VERIFICATION
    )

    # Under Verification -> Verified
    assert (
        sm.resolve_application_transition(
            sm.UNDER_VERIFICATION, "verify_satisfied", sm.SPACS_ASSISTANT
        )
        == sm.VERIFIED
    )

    # Verified -> Under Convener Review -> Approved
    assert (
        sm.resolve_application_transition(sm.VERIFIED, "open_review", sm.SPACS_CONVENER)
        == sm.UNDER_CONVENER_REVIEW
    )
    assert (
        sm.resolve_application_transition(sm.UNDER_CONVENER_REVIEW, "approve", sm.SPACS_CONVENER)
        == sm.APPROVED
    )


def test_application_lifecycle_correction_loop():
    """Verify correction loop between assistant and student (BR-SPACS-006)."""
    # Under Verification -> Correction Required
    assert (
        sm.resolve_application_transition(
            sm.UNDER_VERIFICATION, "request_correction", sm.SPACS_ASSISTANT
        )
        == sm.CORRECTION_REQUIRED
    )

    # Correction Required -> Resubmitted
    assert (
        sm.resolve_application_transition(sm.CORRECTION_REQUIRED, "resubmit", sm.STUDENT)
        == sm.RESUBMITTED
    )

    # Resubmitted -> Under Verification
    assert (
        sm.resolve_application_transition(sm.RESUBMITTED, "open_verification", sm.SPACS_ASSISTANT)
        == sm.UNDER_VERIFICATION
    )


def test_application_terminal_states():
    """Terminal states must have no valid outgoing transitions."""
    for terminal in [sm.APPROVED, sm.REJECTED, sm.WITHDRAWN]:
        for event in ["submit", "approve", "reject", "withdraw"]:
            with pytest.raises((sm.InvalidTransition, sm.ActorNotAllowed)):
                sm.resolve_application_transition(terminal, event, sm.SPACS_CONVENER)


def test_application_unauthorized_actor_rejected():
    """Students cannot approve applications, and assistants cannot reject directly."""
    with pytest.raises((sm.InvalidTransition, sm.ActorNotAllowed)):
        sm.resolve_application_transition(sm.VERIFIED, "approve", sm.STUDENT)

    with pytest.raises((sm.InvalidTransition, sm.ActorNotAllowed)):
        sm.resolve_application_transition(sm.VERIFIED, "reject", sm.SPACS_ASSISTANT)


def test_renewal_lifecycle_transitions():
    """Verify transitions for scholarship renewal (CW-SPACS-02, BR-SPACS-017)."""
    assert (
        sm.resolve_renewal_transition(sm.RENEWAL_SUBMITTED, "open_verification", sm.SPACS_ASSISTANT)
        == sm.RENEWAL_UNDER_VERIFICATION
    )
    assert (
        sm.resolve_renewal_transition(
            sm.RENEWAL_UNDER_VERIFICATION, "verify_satisfied", sm.SPACS_ASSISTANT
        )
        == sm.RENEWAL_VERIFIED
    )
    assert (
        sm.resolve_renewal_transition(sm.RENEWAL_VERIFIED, "open_decision", sm.SPACS_CONVENER)
        == sm.RENEWAL_UNDER_DECISION
    )
    assert (
        sm.resolve_renewal_transition(sm.RENEWAL_UNDER_DECISION, "approve", sm.SPACS_CONVENER)
        == sm.RENEWED
    )


def test_convocation_award_cycle_transitions():
    """Verify convocation award transitions (CW-SPACS-03)."""
    assert (
        sm.resolve_award_transition(sm.AWARD_CYCLE_OPEN, "prepare_pool", sm.SPACS_CONVENER)
        == sm.CANDIDATE_POOL_PREPARED
    )
    assert (
        sm.resolve_award_transition(
            sm.CANDIDATE_POOL_PREPARED, "begin_evaluation", sm.AWARD_COMMITTEE
        )
        == sm.UNDER_COMMITTEE_EVALUATION
    )
    assert (
        sm.resolve_award_transition(
            sm.UNDER_COMMITTEE_EVALUATION, "record_result", sm.AWARD_COMMITTEE
        )
        == sm.COMMITTEE_RESULT_RECORDED
    )
    assert (
        sm.resolve_award_transition(
            sm.COMMITTEE_RESULT_RECORDED, "finalize_approved", sm.SPACS_CONVENER
        )
        == sm.READY_FOR_PUBLICATION
    )
    assert (
        sm.resolve_award_transition(sm.READY_FOR_PUBLICATION, "publish", sm.SPACS_CONVENER)
        == sm.PUBLISHED
    )


def test_eligibility_cpi_and_income_evaluation():
    """Evaluate machine-checkable eligibility rules (BR-SPACS-001)."""
    criteria = {
        "min_cpi": 7.5,
        "income_ceiling": 500000,
        "eligible_programmes": ["B.Tech"],
        "eligible_disciplines": ["CSE", "ECE"],
        "eligible_batches": [2024, 2025],
        "max_backlogs": 0,
    }

    # Qualifying student
    student = {
        "cpi": Decimal("8.2"),
        "annual_income": Decimal("400000"),
        "programme": "B.Tech",
        "discipline": "CSE",
        "batch_year": 2024,
        "category": "GEN",
        "active_backlogs": 0,
    }
    result = eligibility.evaluate_eligibility(criteria, student)
    assert result.is_eligible is True
    assert len(result.reasons) == 0

    # Low CPI
    student["cpi"] = Decimal("7.0")
    result = eligibility.evaluate_eligibility(criteria, student)
    assert result.is_eligible is False
    assert any("CPI" in f for f in result.reasons)

    # Income exceeds ceiling
    student["cpi"] = Decimal("8.0")
    student["annual_income"] = Decimal("600000")
    result = eligibility.evaluate_eligibility(criteria, student)
    assert result.is_eligible is False
    assert any("income" in f for f in result.reasons)

    # Active backlogs
    student["annual_income"] = Decimal("400000")
    student["active_backlogs"] = 1
    result = eligibility.evaluate_eligibility(criteria, student)
    assert result.is_eligible is False
    assert any("backlog" in f for f in result.reasons)


def test_application_completeness_validation():
    """Verify application completeness rules (BR-SPACS-004)."""
    mandatory = ["bank_account", "ifsc_code"]
    required_docs = ["income_certificate", "grade_sheet"]

    # Incomplete form and docs
    res = rules.validate_application_completeness(
        form_data={"bank_account": "12345"},
        mandatory_fields=mandatory,
        required_document_types=required_docs,
        attached_document_types={"income_certificate"},
    )
    assert res.is_complete is False
    assert "ifsc_code" in res.missing_fields
    assert "grade_sheet" in res.missing_documents

    # Complete
    res = rules.validate_application_completeness(
        form_data={"bank_account": "12345", "ifsc_code": "SBIN0001"},
        mandatory_fields=mandatory,
        required_document_types=required_docs,
        attached_document_types={"income_certificate", "grade_sheet"},
    )
    assert res.is_complete is True

    # Complete with unnormalized document types (case and hyphen/space variation)
    res_normalized = rules.validate_application_completeness(
        form_data={"bank_account": "12345", "ifsc_code": "SBIN0001"},
        mandatory_fields=mandatory,
        required_document_types=required_docs,
        attached_document_types={"Income Certificate", "Grade-Sheet"},
    )
    assert res_normalized.is_complete is True


def test_document_reuse_validity():
    """Verify document reuse rules (BR-SPACS-003, AFR-012, 013)."""
    today = datetime.date(2026, 11, 20)

    # Non-reusable document
    doc = {
        "doc_type": "income_certificate",
        "is_active": True,
        "is_reusable": False,
        "valid_until": datetime.date(2027, 3, 31),
    }
    is_valid, msg = rules.validate_document_reuse(doc, "income_certificate", today)
    assert is_valid is False
    assert "non-reusable" in msg

    # Expired document
    doc["is_reusable"] = True
    doc["valid_until"] = datetime.date(2026, 10, 31)
    is_valid, msg = rules.validate_document_reuse(doc, "income_certificate", today)
    assert is_valid is False
    assert "expired" in msg

    # Valid reusable document
    doc["valid_until"] = datetime.date(2027, 3, 31)
    is_valid, msg = rules.validate_document_reuse(doc, "income_certificate", today)
    assert is_valid is True
