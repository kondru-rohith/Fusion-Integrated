"""State machine for SPACS application, renewal, and award lifecycles (CW-SPACS-01..03)."""

from __future__ import annotations

from dataclasses import dataclass

# Actor constants
STUDENT = "student"
SPACS_ASSISTANT = "spacs_assistant"
SPACS_CONVENER = "spacs_convener"
AWARD_COMMITTEE = "award_committee_member"
SYSTEM = "system"

# Application states (CW-SPACS-01)
DRAFT = "draft"
SUBMITTED = "submitted"
UNDER_VERIFICATION = "under_verification"
CORRECTION_REQUIRED = "correction_required"
RESUBMITTED = "resubmitted"
VERIFIED = "verified"
VERIFICATION_CONCERN = "verification_concern"
UNDER_CONVENER_REVIEW = "under_convener_review"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"

# Renewal states (CW-SPACS-02)
RENEWAL_SUBMITTED = "renewal_submitted"
RENEWAL_UNDER_VERIFICATION = "renewal_under_verification"
RENEWAL_RESUBMITTED = "renewal_resubmitted"
RENEWAL_VERIFIED = "renewal_verified"
RENEWAL_UNDER_DECISION = "renewal_under_decision"
RENEWED = "renewed"
RENEWAL_REJECTED = "renewal_rejected"

# Convocation Award Cycle states (CW-SPACS-03)
AWARD_CYCLE_OPEN = "cycle_open"
CANDIDATE_POOL_PREPARED = "candidate_pool_prepared"
UNDER_COMMITTEE_EVALUATION = "under_committee_evaluation"
COMMITTEE_RESULT_RECORDED = "committee_result_recorded"
AWAITING_INSTITUTIONAL_APPROVAL = "awaiting_institutional_approval"
READY_FOR_PUBLICATION = "ready_for_publication"
PUBLISHED = "published"

# Terminal states
TERMINAL_APPLICATION_STATES = frozenset({APPROVED, REJECTED, WITHDRAWN, RENEWED, RENEWAL_REJECTED})
WITHDRAWABLE_STATES = frozenset({SUBMITTED, UNDER_VERIFICATION, CORRECTION_REQUIRED, VERIFIED})
EDITABLE_STATES = frozenset({DRAFT, CORRECTION_REQUIRED})


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str, event: str = ""):
        super().__init__(
            f"Cannot transition application from {frm!r} to {to!r} on event {event!r}."
        )
        self.frm = frm
        self.to = to
        self.event = event


class ActorNotAllowed(Exception):
    def __init__(self, actor: str, frm: str, to: str):
        super().__init__(
            f"Actor {actor!r} is not allowed to transition application from {frm!r} to {to!r}."
        )
        self.actor = actor
        self.frm = frm
        self.to = to


class GuardFailed(Exception):
    def __init__(self, guard: str, message: str = ""):
        super().__init__(message or f"Guard {guard!r} failed.")
        self.guard = guard


@dataclass(frozen=True)
class TransitionEdge:
    from_state: str
    event: str
    actor: str
    to_state: str
    guard_name: str | None = None


# Authoritative State-Transition Table for Scholarship Applications (CW-SPACS-01)
APPLICATION_TRANSITION_TABLE: list[TransitionEdge] = [
    # 1. Draft -> Submitted (UC-SPACS-001)
    TransitionEdge(DRAFT, "submit", STUDENT, SUBMITTED),
    # 2. Submitted -> Under Verification (UC-SPACS-002)
    TransitionEdge(SUBMITTED, "open_verification", SPACS_ASSISTANT, UNDER_VERIFICATION),
    # 3. Under Verification -> Correction Required (UC-SPACS-002)
    TransitionEdge(UNDER_VERIFICATION, "request_correction", SPACS_ASSISTANT, CORRECTION_REQUIRED),
    # 4. Correction Required -> Resubmitted (UC-SPACS-003)
    TransitionEdge(CORRECTION_REQUIRED, "resubmit", STUDENT, RESUBMITTED),
    # 5. Resubmitted -> Verified (UC-SPACS-002)
    TransitionEdge(RESUBMITTED, "verify_satisfied", SPACS_ASSISTANT, VERIFIED),
    # 5b. Resubmitted -> Under Verification (re-open)
    TransitionEdge(RESUBMITTED, "open_verification", SPACS_ASSISTANT, UNDER_VERIFICATION),
    # 6. Under Verification -> Verified (UC-SPACS-002)
    TransitionEdge(UNDER_VERIFICATION, "verify_satisfied", SPACS_ASSISTANT, VERIFIED),
    # 7. Under Verification -> Verification Concern (UC-SPACS-002)
    TransitionEdge(UNDER_VERIFICATION, "raise_concern", SPACS_ASSISTANT, VERIFICATION_CONCERN),
    # 8. Verified -> Under Convener Review (UC-SPACS-006)
    TransitionEdge(VERIFIED, "open_review", SPACS_CONVENER, UNDER_CONVENER_REVIEW),
    # 9. Verification Concern -> Under Convener Review (UC-SPACS-006)
    TransitionEdge(VERIFICATION_CONCERN, "open_review", SPACS_CONVENER, UNDER_CONVENER_REVIEW),
    # 10. Under Convener Review -> Approved (UC-SPACS-006)
    TransitionEdge(UNDER_CONVENER_REVIEW, "approve", SPACS_CONVENER, APPROVED),
    # 11. Under Convener Review -> Rejected (UC-SPACS-006)
    TransitionEdge(UNDER_CONVENER_REVIEW, "reject", SPACS_CONVENER, REJECTED),
    # 12. Under Convener Review -> Correction Required (UC-SPACS-006 return for correction)
    TransitionEdge(
        UNDER_CONVENER_REVIEW, "return_for_correction", SPACS_CONVENER, CORRECTION_REQUIRED
    ),
    # 13-16. Withdrawals by Student (BW-SPACS-05)
    TransitionEdge(SUBMITTED, "withdraw", STUDENT, WITHDRAWN),
    TransitionEdge(UNDER_VERIFICATION, "withdraw", STUDENT, WITHDRAWN),
    TransitionEdge(CORRECTION_REQUIRED, "withdraw", STUDENT, WITHDRAWN),
    TransitionEdge(
        VERIFIED, "withdraw", STUDENT, WITHDRAWN, guard_name="convener_review_not_begun"
    ),
]

# Authoritative State-Transition Table for Scholarship Renewals (CW-SPACS-02)
RENEWAL_TRANSITION_TABLE: list[TransitionEdge] = [
    # 1. Approved -> Renewal Submitted (UC-SPACS-015)
    TransitionEdge(APPROVED, "apply_renewal", STUDENT, RENEWAL_SUBMITTED),
    # 2. Renewal Submitted -> Renewal Under Verification (UC-SPACS-002)
    TransitionEdge(
        RENEWAL_SUBMITTED, "open_verification", SPACS_ASSISTANT, RENEWAL_UNDER_VERIFICATION
    ),
    # 3. Renewal Under Verification -> Correction Required (UC-SPACS-002)
    TransitionEdge(
        RENEWAL_UNDER_VERIFICATION, "request_correction", SPACS_ASSISTANT, CORRECTION_REQUIRED
    ),
    # 4. Correction Required -> Renewal Resubmitted (UC-SPACS-003)
    TransitionEdge(CORRECTION_REQUIRED, "resubmit_renewal", STUDENT, RENEWAL_RESUBMITTED),
    # 5. Renewal Resubmitted -> Renewal Verified (UC-SPACS-002)
    TransitionEdge(RENEWAL_RESUBMITTED, "verify_satisfied", SPACS_ASSISTANT, RENEWAL_VERIFIED),
    # 5b. Renewal Resubmitted -> Renewal Under Verification (re-open)
    TransitionEdge(
        RENEWAL_RESUBMITTED, "open_verification", SPACS_ASSISTANT, RENEWAL_UNDER_VERIFICATION
    ),
    # 6. Renewal Under Verification -> Renewal Verified (UC-SPACS-002)
    TransitionEdge(
        RENEWAL_UNDER_VERIFICATION, "verify_satisfied", SPACS_ASSISTANT, RENEWAL_VERIFIED
    ),
    # 7. Renewal Verified -> Renewal Under Decision (UC-SPACS-006)
    TransitionEdge(RENEWAL_VERIFIED, "open_decision", SPACS_CONVENER, RENEWAL_UNDER_DECISION),
    # 8. Renewal Under Decision -> Renewed / Approved (UC-SPACS-006)
    TransitionEdge(RENEWAL_UNDER_DECISION, "approve", SPACS_CONVENER, RENEWED),
    # 9. Renewal Under Decision -> Renewal Rejected (UC-SPACS-006)
    TransitionEdge(RENEWAL_UNDER_DECISION, "reject", SPACS_CONVENER, RENEWAL_REJECTED),
]

# Authoritative State-Transition Table for Convocation Awards (CW-SPACS-03)
AWARD_TRANSITION_TABLE: list[TransitionEdge] = [
    # 1. Award Cycle Open -> Candidate Pool Prepared (UC-SPACS-017)
    TransitionEdge(AWARD_CYCLE_OPEN, "prepare_pool", SPACS_CONVENER, CANDIDATE_POOL_PREPARED),
    # 2. Candidate Pool Prepared -> Under Committee Evaluation (UC-SPACS-018)
    TransitionEdge(
        CANDIDATE_POOL_PREPARED, "begin_evaluation", AWARD_COMMITTEE, UNDER_COMMITTEE_EVALUATION
    ),
    # 3. Under Committee Evaluation -> Committee Result Recorded (UC-SPACS-018)
    TransitionEdge(
        UNDER_COMMITTEE_EVALUATION, "record_result", AWARD_COMMITTEE, COMMITTEE_RESULT_RECORDED
    ),
    # 4. Committee Result Recorded -> Ready for Publication (Approval) (UC-SPACS-019, BW-SPACS-09)
    TransitionEdge(
        COMMITTEE_RESULT_RECORDED, "finalize_approved", SPACS_CONVENER, READY_FOR_PUBLICATION
    ),
    # 5. Committee Result Recorded -> Awaiting Institutional Approval (UC-SPACS-019, BW-SPACS-11)
    TransitionEdge(
        COMMITTEE_RESULT_RECORDED, "await_approval", SPACS_CONVENER, AWAITING_INSTITUTIONAL_APPROVAL
    ),
    # 6. Awaiting Institutional Approval -> Ready for Publication (UC-SPACS-019, BW-SPACS-11)
    TransitionEdge(
        AWAITING_INSTITUTIONAL_APPROVAL, "record_approval", SPACS_CONVENER, READY_FOR_PUBLICATION
    ),
    # 7. Ready for Publication -> Published (UC-SPACS-020)
    TransitionEdge(READY_FOR_PUBLICATION, "publish", SPACS_CONVENER, PUBLISHED),
]


def resolve_application_transition(from_state: str, event: str, actor: str) -> str:
    """Resolve the next state for an application transition or raise an exception."""
    candidates = [
        edge
        for edge in APPLICATION_TRANSITION_TABLE
        if edge.from_state == from_state and edge.event == event
    ]
    if not candidates:
        raise InvalidTransition(from_state, "<unknown>", event=event)

    matching_actor = [edge for edge in candidates if edge.actor == actor]
    if not matching_actor:
        raise ActorNotAllowed(actor, from_state, candidates[0].to_state)

    edge = matching_actor[0]
    return edge.to_state


def resolve_renewal_transition(from_state: str, event: str, actor: str) -> str:
    """Resolve the next state for a renewal transition or raise an exception."""
    candidates = [
        edge
        for edge in RENEWAL_TRANSITION_TABLE
        if edge.from_state == from_state and edge.event == event
    ]
    if not candidates:
        raise InvalidTransition(from_state, "<unknown>", event=event)

    matching_actor = [edge for edge in candidates if edge.actor == actor]
    if not matching_actor:
        raise ActorNotAllowed(actor, from_state, candidates[0].to_state)

    return matching_actor[0].to_state


def resolve_award_transition(from_state: str, event: str, actor: str) -> str:
    """Resolve the next state for an award cycle transition or raise an exception."""
    candidates = [
        edge
        for edge in AWARD_TRANSITION_TABLE
        if edge.from_state == from_state and edge.event == event
    ]
    if not candidates:
        raise InvalidTransition(from_state, "<unknown>", event=event)

    matching_actor = [edge for edge in candidates if edge.actor == actor]
    if not matching_actor:
        raise ActorNotAllowed(actor, from_state, candidates[0].to_state)

    return matching_actor[0].to_state


def is_terminal_state(state: str) -> bool:
    return state in TERMINAL_APPLICATION_STATES or state == PUBLISHED


def can_withdraw(state: str) -> bool:
    return state in WITHDRAWABLE_STATES


def is_editable(state: str) -> bool:
    return state in EDITABLE_STATES
