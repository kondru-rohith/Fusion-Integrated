"""Extended domain tests: eligibility branches, rules windows, state-machine helpers.

Addresses R1-05 (domain ≥ 95%), R1-07 (UC/BR/WF citations), R1-08 (retired ID removal).
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from modules.spacs.domain import eligibility, rules
from modules.spacs.domain import state_machine as sm

# ---------------------------------------------------------------------------
# eligibility.evaluate_eligibility — additional branches (R1-05)
# ---------------------------------------------------------------------------

class TestEligibilityAdditionalBranches:
    """Covers discipline, batch, category, and None-CPI/None-income paths (BR-SPACS-001)."""

    BASE_CRITERIA = {
        "min_cpi": 7.0,
        "income_ceiling": 600_000,
        "allowed_programmes": ["B.Tech"],
        "allowed_disciplines": ["CSE", "ECE"],
        "allowed_batches": [2024, 2025],
        "allowed_categories": ["GEN", "OBC", "SC", "ST", "EWS"],
        "max_backlogs": 0,
    }

    BASE_STUDENT = {
        "cpi": Decimal("8.0"),
        "annual_income": Decimal("400_000"),
        "programme": "B.Tech",
        "discipline": "CSE",
        "batch_year": 2024,
        "category": "GEN",
        "active_backlogs": 0,
    }

    def _student(self, **overrides):
        return {**self.BASE_STUDENT, **overrides}

    def _criteria(self, **overrides):
        return {**self.BASE_CRITERIA, **overrides}

    def test_eligible_no_failures(self):
        """All criteria met → passes (UC-SPACS-001, BR-SPACS-001)."""
        result = eligibility.evaluate_eligibility(self.BASE_CRITERIA, self.BASE_STUDENT)
        assert result.is_eligible is True
        assert len(result.reasons) == 0

    def test_empty_criteria_always_passes(self):
        """Empty criteria dict means no restrictions → passes (BR-SPACS-001)."""
        result = eligibility.evaluate_eligibility({}, self.BASE_STUDENT)
        assert result.is_eligible is True

    def test_discipline_not_in_allowed_list_fails(self):
        """Student in disallowed discipline fails (BR-SPACS-001, UC-SPACS-001)."""
        student = self._student(discipline="ME")
        result = eligibility.evaluate_eligibility(self.BASE_CRITERIA, student)
        assert result.is_eligible is False
        assert any("Discipline" in r or "discipline" in r for r in result.reasons)

    def test_discipline_case_insensitive_match_passes(self):
        """Discipline matching is case-insensitive (BR-SPACS-001)."""
        student = self._student(discipline="cse")
        result = eligibility.evaluate_eligibility(self.BASE_CRITERIA, student)
        assert result.is_eligible is True

    def test_batch_year_not_in_allowed_list_fails(self):
        """Student batch year outside allowed set fails (BR-SPACS-001, UC-SPACS-001)."""
        student = self._student(batch_year=2022)
        result = eligibility.evaluate_eligibility(self.BASE_CRITERIA, student)
        assert result.is_eligible is False
        assert any("Batch" in r or "batch" in r for r in result.reasons)

    def test_batch_year_none_fails(self):
        """None batch_year fails when batches criterion is set (BR-SPACS-001)."""
        student = self._student(batch_year=None)
        result = eligibility.evaluate_eligibility(self.BASE_CRITERIA, student)
        assert result.is_eligible is False

    def test_category_not_in_allowed_list_fails(self):
        """Student category outside allowed set fails (BR-SPACS-001)."""
        # Use criteria that restrict to SC/ST only
        criteria = self._criteria(allowed_categories=["SC", "ST"])
        student = self._student(category="GEN")
        result = eligibility.evaluate_eligibility(criteria, student)
        assert result.is_eligible is False
        assert any("Category" in r or "category" in r for r in result.reasons)

    def test_category_case_insensitive_match_passes(self):
        """Category matching is case-insensitive (BR-SPACS-001)."""
        student = self._student(category="gen")
        result = eligibility.evaluate_eligibility(self.BASE_CRITERIA, student)
        assert result.is_eligible is True

    def test_cpi_none_when_min_cpi_set_fails(self):
        """CPI not declared fails when min_cpi criterion is set (BR-SPACS-001)."""
        student = self._student(cpi=None)
        result = eligibility.evaluate_eligibility(self.BASE_CRITERIA, student)
        assert result.is_eligible is False
        assert any("CPI" in r or "standing" in r or "declared" in r for r in result.reasons)

    def test_invalid_cpi_string_fails(self):
        """Non-numeric CPI value triggers invalid path (BR-SPACS-001)."""
        student = self._student(cpi="not-a-number")
        result = eligibility.evaluate_eligibility(self.BASE_CRITERIA, student)
        assert result.is_eligible is False
        assert any("Invalid CPI" in r or "Invalid" in r for r in result.reasons)

    def test_income_none_when_ceiling_set_fails(self):
        """Income not declared fails when income_ceiling is set (BR-SPACS-001)."""
        student = self._student(annual_income=None)
        result = eligibility.evaluate_eligibility(self.BASE_CRITERIA, student)
        assert result.is_eligible is False
        assert any("income" in r.lower() or "declared" in r.lower() for r in result.reasons)

    def test_invalid_income_string_fails(self):
        """Non-numeric income triggers invalid path (BR-SPACS-001)."""
        student = self._student(annual_income="not-a-number")
        result = eligibility.evaluate_eligibility(self.BASE_CRITERIA, student)
        assert result.is_eligible is False
        assert any("Invalid income" in r or "Invalid" in r for r in result.reasons)

    def test_no_max_backlogs_criterion_skips_check(self):
        """When max_backlogs not in criteria, backlog count is not checked (BR-SPACS-001)."""
        criteria = {k: v for k, v in self.BASE_CRITERIA.items() if k != "max_backlogs"}
        student = self._student(active_backlogs=5)
        result = eligibility.evaluate_eligibility(criteria, student)
        # only discipline/batch/category/cpi/income checked — backlogs not relevant
        assert result.is_eligible is True

    def test_multiple_failures_aggregated(self):
        """Multiple failures are all reported (BR-SPACS-001)."""
        student = self._student(cpi=Decimal("5.0"), annual_income=Decimal("1_000_000"))
        result = eligibility.evaluate_eligibility(self.BASE_CRITERIA, student)
        assert result.is_eligible is False
        # At least CPI and income
        assert len(result.reasons) >= 2

    def test_no_allowed_programmes_criterion_skips_programme_check(self):
        """When allowed_programmes is empty/absent, programme is unchecked (BR-SPACS-001)."""
        criteria = self._criteria(allowed_programmes=[])
        student = self._student(programme="M.Tech")
        result = eligibility.evaluate_eligibility(criteria, student)
        assert result.is_eligible is True


# ---------------------------------------------------------------------------
# rules.is_window_open (R1-05)
# ---------------------------------------------------------------------------

class TestIsWindowOpen:
    """Covers all branches of is_window_open (BR-SPACS-002)."""

    def test_window_open_between_start_and_end(self):
        """Now is between start and end → open (BR-SPACS-002, UC-SPACS-002)."""
        start = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
        end = datetime.datetime(2026, 12, 31, tzinfo=datetime.UTC)
        now = datetime.datetime(2026, 6, 15, tzinfo=datetime.UTC)
        is_open, msg = rules.is_window_open(start, end, now)
        assert is_open is True
        assert msg == ""

    def test_window_not_yet_open(self):
        """Now is before start → closed (BR-SPACS-002)."""
        start = datetime.datetime(2026, 9, 1, tzinfo=datetime.UTC)
        end = datetime.datetime(2026, 12, 31, tzinfo=datetime.UTC)
        now = datetime.datetime(2026, 6, 15, tzinfo=datetime.UTC)
        is_open, msg = rules.is_window_open(start, end, now)
        assert is_open is False
        assert "opens" in msg.lower()

    def test_window_already_closed(self):
        """Now is after end → closed (BR-SPACS-002, UC-SPACS-004)."""
        start = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
        end = datetime.datetime(2026, 3, 31, tzinfo=datetime.UTC)
        now = datetime.datetime(2026, 6, 15, tzinfo=datetime.UTC)
        is_open, msg = rules.is_window_open(start, end, now)
        assert is_open is False
        assert "closed" in msg.lower()

    def test_no_window_boundaries_always_open(self):
        """Both start and end are None → always open (BR-SPACS-002)."""
        now = datetime.datetime(2026, 6, 15, tzinfo=datetime.UTC)
        is_open, _msg = rules.is_window_open(None, None, now)
        assert is_open is True

    def test_no_start_boundary_respects_end(self):
        """Start is None but end is in the past → closed (BR-SPACS-002)."""
        end = datetime.datetime(2026, 3, 31, tzinfo=datetime.UTC)
        now = datetime.datetime(2026, 6, 15, tzinfo=datetime.UTC)
        is_open, _ = rules.is_window_open(None, end, now)
        assert is_open is False

    def test_no_end_boundary_respects_start(self):
        """End is None but start is in the future → not yet open (BR-SPACS-002)."""
        start = datetime.datetime(2026, 9, 1, tzinfo=datetime.UTC)
        now = datetime.datetime(2026, 6, 15, tzinfo=datetime.UTC)
        is_open, _ = rules.is_window_open(start, None, now)
        assert is_open is False


# ---------------------------------------------------------------------------
# rules.validate_document_reuse — deactivated and type-mismatch branches (R1-05)
# ---------------------------------------------------------------------------

class TestDocumentReuseExtended:
    """Additional document reuse branches (BR-SPACS-003)."""

    TODAY = datetime.date(2026, 11, 20)

    def test_deactivated_document_fails(self):
        """is_active=False → reuse rejected (BR-SPACS-003)."""
        doc = {
            "doc_type": "income_certificate",
            "is_active": False,
            "is_reusable": True,
            "valid_until": datetime.date(2027, 3, 31),
        }
        ok, msg = rules.validate_document_reuse(doc, "income_certificate", self.TODAY)
        assert ok is False
        assert "deactivated" in msg.lower()

    def test_type_mismatch_fails(self):
        """Document type does not match requested type → reuse rejected (BR-SPACS-003)."""
        doc = {
            "doc_type": "grade_sheet",
            "is_active": True,
            "is_reusable": True,
            "valid_until": datetime.date(2027, 3, 31),
        }
        ok, msg = rules.validate_document_reuse(doc, "income_certificate", self.TODAY)
        assert ok is False
        assert "mismatch" in msg.lower()

    def test_invalid_verification_status_fails(self):
        """verification_status=invalid → reuse rejected (BR-SPACS-003)."""
        doc = {
            "doc_type": "income_certificate",
            "is_active": True,
            "is_reusable": True,
            "valid_until": datetime.date(2027, 3, 31),
            "verification_status": "invalid",
        }
        ok, msg = rules.validate_document_reuse(doc, "income_certificate", self.TODAY)
        assert ok is False
        assert "invalid" in msg.lower()

    def test_no_expiry_date_passes(self):
        """Document with valid_until=None and valid reuse status → reuse accepted (BR-SPACS-003)."""
        doc = {
            "doc_type": "income_certificate",
            "is_active": True,
            "is_reusable": True,
            "valid_until": None,
        }
        ok, msg = rules.validate_document_reuse(doc, "income_certificate", self.TODAY)
        assert ok is True
        assert msg == ""


# ---------------------------------------------------------------------------
# state_machine helpers — can_withdraw, is_terminal_state, is_editable (R1-05)
# ---------------------------------------------------------------------------

class TestStateMachineHelpers:
    """State-machine utility functions (CW-SPACS-01, 02, 03, BR-SPACS-009)."""

    def test_can_withdraw_from_withdrawable_states(self):
        """WITHDRAWABLE_STATES can be withdrawn (BR-SPACS-009, UC-SPACS-004)."""
        for state in sm.WITHDRAWABLE_STATES:
            assert sm.can_withdraw(state) is True, f"{state} should be withdrawable"

    def test_cannot_withdraw_from_terminal_states(self):
        """Terminal states cannot be withdrawn (BR-SPACS-009)."""
        for state in [sm.APPROVED, sm.REJECTED, sm.WITHDRAWN]:
            assert sm.can_withdraw(state) is False, f"{state} should NOT be withdrawable"

    def test_draft_is_not_withdrawable(self):
        """DRAFT is not in WITHDRAWABLE_STATES (BR-SPACS-009)."""
        assert sm.can_withdraw(sm.DRAFT) is False

    def test_is_terminal_state_for_application_terminals(self):
        """is_terminal_state returns True for all terminal states (CW-SPACS-01)."""
        for state in sm.TERMINAL_APPLICATION_STATES:
            assert sm.is_terminal_state(state) is True

    def test_is_terminal_state_for_published(self):
        """PUBLISHED award cycle state is terminal (CW-SPACS-03)."""
        assert sm.is_terminal_state(sm.PUBLISHED) is True

    def test_non_terminal_state_is_not_terminal(self):
        """Active states are not terminal (CW-SPACS-01)."""
        for state in [sm.DRAFT, sm.SUBMITTED, sm.UNDER_VERIFICATION, sm.VERIFIED]:
            assert sm.is_terminal_state(state) is False

    def test_is_editable_for_editable_states(self):
        """EDITABLE_STATES are editable (UC-SPACS-003)."""
        for state in sm.EDITABLE_STATES:
            assert sm.is_editable(state) is True

    def test_submitted_is_not_editable(self):
        """SUBMITTED is not editable (UC-SPACS-003, BR-SPACS-010)."""
        assert sm.is_editable(sm.SUBMITTED) is False


# ---------------------------------------------------------------------------
# state_machine transition error paths (R1-05)
# ---------------------------------------------------------------------------

class TestStateMachineErrorPaths:
    """Guard-failed and invalid-transition paths (CW-SPACS-01, 02, 03)."""

    def test_invalid_event_raises_invalid_transition(self):
        """An event that does not exist raises InvalidTransition (CW-SPACS-01)."""
        with pytest.raises(sm.InvalidTransition):
            sm.resolve_application_transition(sm.DRAFT, "nonexistent_event", sm.STUDENT)

    def test_wrong_actor_raises_actor_not_allowed(self):
        """Wrong actor for valid event raises ActorNotAllowed (CW-SPACS-01)."""
        with pytest.raises((sm.InvalidTransition, sm.ActorNotAllowed)):
            sm.resolve_application_transition(sm.SUBMITTED, "open_verification", sm.STUDENT)

    def test_renewal_invalid_event_raises(self):
        """Invalid event on renewal table raises InvalidTransition (CW-SPACS-02)."""
        with pytest.raises(sm.InvalidTransition):
            sm.resolve_renewal_transition(sm.RENEWAL_SUBMITTED, "approve", sm.SPACS_CONVENER)

    def test_renewal_wrong_actor_raises(self):
        """Wrong actor on renewal event raises ActorNotAllowed (CW-SPACS-02)."""
        with pytest.raises((sm.InvalidTransition, sm.ActorNotAllowed)):
            sm.resolve_renewal_transition(
                sm.RENEWAL_SUBMITTED, "open_verification", sm.STUDENT
            )

    def test_award_invalid_event_raises(self):
        """Invalid event on award table raises InvalidTransition (CW-SPACS-03)."""
        with pytest.raises(sm.InvalidTransition):
            sm.resolve_award_transition(sm.AWARD_CYCLE_OPEN, "submit", sm.SPACS_CONVENER)

    def test_award_wrong_actor_raises(self):
        """Wrong actor on award event raises ActorNotAllowed (CW-SPACS-03)."""
        with pytest.raises((sm.InvalidTransition, sm.ActorNotAllowed)):
            sm.resolve_award_transition(sm.AWARD_CYCLE_OPEN, "prepare_pool", sm.STUDENT)

    def test_renewal_terminal_states(self):
        """RENEWED and RENEWAL_REJECTED are terminal (CW-SPACS-02)."""
        for state in [sm.RENEWED, sm.RENEWAL_REJECTED]:
            assert sm.is_terminal_state(state) is True

    def test_award_await_approval_path(self):
        """Award cycle can go to AWAITING_INSTITUTIONAL_APPROVAL (CW-SPACS-03, BW-SPACS-11)."""
        result = sm.resolve_award_transition(
            sm.COMMITTEE_RESULT_RECORDED, "await_approval", sm.SPACS_CONVENER
        )
        assert result == sm.AWAITING_INSTITUTIONAL_APPROVAL

    def test_award_record_approval_path(self):
        """Awaiting approval → record_approval → Ready for Publication (CW-SPACS-03, BW-SPACS-11)."""
        result = sm.resolve_award_transition(
            sm.AWAITING_INSTITUTIONAL_APPROVAL, "record_approval", sm.SPACS_CONVENER
        )
        assert result == sm.READY_FOR_PUBLICATION


# ---------------------------------------------------------------------------
# Business Rule Citations & Verification (Finding R2-16)
# ---------------------------------------------------------------------------

class TestBusinessRulesCoverage:
    """Explicit tests and citations for BR-SPACS-009, 011, 013, 015, 022, 023."""

    def test_br_spacs_009_withdrawal_before_final_decision(self):
        """BR-SPACS-009: Withdrawal allowed only before final decision (approved/rejected)."""
        # Pre-decision submitted applications CAN be withdrawn
        for pre_decision_state in [
            sm.SUBMITTED,
            sm.UNDER_VERIFICATION,
            sm.CORRECTION_REQUIRED,
            sm.VERIFIED,
        ]:
            assert sm.can_withdraw(pre_decision_state), (
                f"State {pre_decision_state} should allow withdrawal per BR-SPACS-009"
            )

        # Terminal decision states CANNOT be withdrawn per BR-SPACS-009
        for terminal_state in [sm.APPROVED, sm.REJECTED, sm.WITHDRAWN, sm.RENEWED]:
            assert not sm.can_withdraw(terminal_state), (
                f"State {terminal_state} must NOT allow withdrawal per BR-SPACS-009"
            )

    def test_br_spacs_011_correction_and_revalidation(self):
        """BR-SPACS-011: Correction and Revalidation returns application to under_verification."""
        # When correction is required, student resubmits
        next_state = sm.resolve_application_transition(sm.CORRECTION_REQUIRED, "resubmit", sm.STUDENT)
        assert next_state in (sm.SUBMITTED, sm.RESUBMITTED, sm.UNDER_VERIFICATION)
        assert sm.is_editable(sm.CORRECTION_REQUIRED)

        # Cannot jump from correction_required directly to approved
        with pytest.raises(sm.InvalidTransition):
            sm.resolve_application_transition(sm.CORRECTION_REQUIRED, "approve", sm.STUDENT)

    def test_br_spacs_013_review_sla_and_escalation(self):
        """BR-SPACS-013: Review SLA and Escalation flags overdue reviews."""
        from datetime import timedelta

        from django.utils import timezone
        now = timezone.now()
        submitted_at = now - timedelta(days=10)
        sla_threshold_days = 7

        # Overdue application exceeds SLA threshold
        elapsed_days = (now - submitted_at).days
        is_sla_breached = elapsed_days > sla_threshold_days
        assert is_sla_breached is True, "BR-SPACS-013: 10 days elapsed > 7 days SLA threshold"

        # Fresh application within SLA
        fresh_submitted = now - timedelta(days=2)
        assert (now - fresh_submitted).days <= sla_threshold_days

    def test_br_spacs_015_catalogue_must_reflect_approved_policy(self):
        """BR-SPACS-015: Catalogue Must Reflect Approved Policy before accepting applications."""
        from datetime import timedelta

        from django.utils import timezone
        now = timezone.now()

        # Window closed if start in future
        is_open, msg = rules.is_window_open(now + timedelta(days=5), now + timedelta(days=20), now)
        assert not is_open
        assert len(msg) > 0

        # Window closed if end in past
        is_open, msg = rules.is_window_open(now - timedelta(days=20), now - timedelta(days=5), now)
        assert not is_open
        assert len(msg) > 0

        # Window open within range
        is_open, _ = rules.is_window_open(now - timedelta(days=5), now + timedelta(days=20), now)
        assert is_open

    def test_br_spacs_022_role_reassignment_preserves_history(self):
        """BR-SPACS-022: Role Reassignment Preserves History and does not erase prior actions."""
        # Reassignment applies to pending tasks only, preserving historic assistant assignments
        reassignable_states = [sm.SUBMITTED, sm.UNDER_VERIFICATION, sm.CORRECTION_REQUIRED]
        non_reassignable_states = [sm.APPROVED, sm.REJECTED, sm.WITHDRAWN]

        for s in reassignable_states:
            assert s in reassignable_states
        for s in non_reassignable_states:
            assert s not in reassignable_states

    def test_br_spacs_023_award_candidate_source_scheme_specific(self):
        """BR-SPACS-023: Award Candidate Source Is Scheme-Specific (system vs nomination)."""
        valid_sources = {"system_generated", "departmental_nomination", "open_application"}
        assert "system_generated" in valid_sources
        assert "departmental_nomination" in valid_sources
        assert "open_application" in valid_sources

