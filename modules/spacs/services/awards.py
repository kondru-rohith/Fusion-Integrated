"""Convocation awards candidate pool, evaluation, and publishing.

Covers CFR-SPACS-013..016, CW-SPACS-03.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.spacs.domain import state_machine
from modules.spacs.models import AwardCandidate, AwardCycle, CatalogueVersion
from modules.spacs.services import audit, notifications


@transaction.atomic
def open_cycle(
    *,
    catalogue_version_id: int,
    convocation_year: int,
    actor,
) -> AwardCycle:
    """Open an award cycle for candidate evaluation (CFR-SPACS-013)."""
    version = CatalogueVersion.objects.filter(
        pk=catalogue_version_id, entry__kind="award", status="published"
    ).first()
    if version is None:
        raise NotFoundError("Published convocation award scheme not found.")

    cycle, _ = AwardCycle.objects.get_or_create(
        catalogue_version=version,
        convocation_year=convocation_year,
        defaults={"status": state_machine.AWARD_CYCLE_OPEN},
    )
    audit.log_audit_event(
        "award.cycle_opened", actor, "AwardCycle", cycle.pk, {"year": convocation_year}
    )
    return cycle


@transaction.atomic
def prepare_candidate_pool(
    *,
    cycle_id: int,
    candidates_data: list[dict],
    actor,
) -> AwardCycle:
    """Populate candidate pool from academic standings or nominations.

    Specification: UC-SPACS-017, BR-SPACS-023.
    """
    cycle = AwardCycle.objects.select_for_update().filter(pk=cycle_id).first()
    if cycle is None:
        raise NotFoundError("Award cycle not found.")

    next_state = state_machine.resolve_award_transition(
        cycle.status, "prepare_pool", state_machine.SPACS_CONVENER
    )
    old_state = cycle.status

    source_method = cycle.catalogue_version.candidate_source
    for cand in candidates_data:
        uid = cand.get("user_id")
        if uid is None:
            continue
        AwardCandidate.objects.update_or_create(
            award_cycle=cycle,
            user_id=int(uid),
            defaults={
                "source_method": source_method,
                "cpi_at_evaluation": Decimal(str(cand["cpi"])) if cand.get("cpi") else None,
                "standing_snapshot": cand.get("standing_snapshot", {}),
                "shortlist_status": "nominated",
            },
        )

    cycle.status = next_state
    cycle.save(update_fields=["status", "updated_at"])
    audit.log_audit_event(
        "award.pool_prepared",
        actor,
        "AwardCycle",
        cycle.pk,
        {"from": old_state, "to": next_state, "candidates_count": len(candidates_data)},
    )
    return cycle


@transaction.atomic
def record_committee_evaluation(
    *,
    candidate_id: int,
    score: Decimal,
    remarks: str,
    shortlist_status: str,
    actor,
) -> AwardCandidate:
    """Record evaluation scores and remarks by committee members (UC-SPACS-018, BR-SPACS-019)."""
    candidate = AwardCandidate.objects.select_for_update().filter(pk=candidate_id).first()
    if candidate is None:
        raise NotFoundError("Candidate not found.")

    cycle = candidate.award_cycle
    if cycle.status == state_machine.CANDIDATE_POOL_PREPARED:
        cycle.status = state_machine.resolve_award_transition(
            cycle.status, "begin_evaluation", state_machine.AWARD_COMMITTEE
        )
        cycle.save(update_fields=["status", "updated_at"])

    candidate.evaluation_score = score
    candidate.committee_remarks = (remarks or "").strip()
    candidate.shortlist_status = shortlist_status
    candidate.save(
        update_fields=["evaluation_score", "committee_remarks", "shortlist_status", "updated_at"]
    )

    audit.log_audit_event(
        "award.candidate_evaluated",
        actor,
        "AwardCandidate",
        candidate.pk,
        {"score": str(score), "shortlist_status": shortlist_status},
    )
    return candidate


@transaction.atomic
def record_final_award_outcome(
    *,
    cycle_id: int,
    candidate_outcomes: list[dict],  # [{user_id, outcome: winner|runner_up|none}]
    approval_ref: str = "",
    actor,
) -> AwardCycle:
    """Record final award winners and institutional approval reference (UC-SPACS-019)."""
    cycle = AwardCycle.objects.select_for_update().filter(pk=cycle_id).first()
    if cycle is None:
        raise NotFoundError("Award cycle not found.")

    has_approval = bool(approval_ref.strip())
    event = "finalize_approved" if has_approval else "await_approval"

    # If cycle still in committee evaluation, advance to committee result recorded first
    if cycle.status == state_machine.UNDER_COMMITTEE_EVALUATION:
        cycle.status = state_machine.resolve_award_transition(
            cycle.status, "record_result", state_machine.AWARD_COMMITTEE
        )

    next_state = state_machine.resolve_award_transition(
        cycle.status, event, state_machine.SPACS_CONVENER
    )
    old_state = cycle.status

    for item in candidate_outcomes:
        uid = item.get("user_id")
        outcome = item.get("outcome", "none")
        if uid is not None:
            AwardCandidate.objects.filter(award_cycle=cycle, user_id=int(uid)).update(
                final_outcome=outcome
            )

    cycle.status = next_state
    if has_approval:
        cycle.institutional_approval_ref = approval_ref.strip()
    cycle.save(update_fields=["status", "institutional_approval_ref", "updated_at"])

    audit.log_audit_event(
        "award.outcome_recorded",
        actor,
        "AwardCycle",
        cycle.pk,
        {"from": old_state, "to": next_state, "approval_ref": approval_ref},
    )
    return cycle


@transaction.atomic
def record_institutional_approval(
    *,
    cycle_id: int,
    approval_ref: str,
    actor,
) -> AwardCycle:
    """Record receipt of institutional approval when previously pending.

    Specification: UC-SPACS-019, BW-SPACS-11.
    """
    cycle = AwardCycle.objects.select_for_update().filter(pk=cycle_id).first()
    if cycle is None:
        raise NotFoundError("Award cycle not found.")

    if cycle.status != state_machine.AWAITING_INSTITUTIONAL_APPROVAL:
        raise ConflictError(
            f"Cycle is not awaiting institutional approval (status: {cycle.status!r})."
        )

    if not approval_ref.strip():
        raise BadRequestError("Institutional approval reference required.")

    next_state = state_machine.resolve_award_transition(
        cycle.status, "record_approval", state_machine.SPACS_CONVENER
    )
    cycle.status = next_state
    cycle.institutional_approval_ref = approval_ref.strip()
    cycle.save(update_fields=["status", "institutional_approval_ref", "updated_at"])

    audit.log_audit_event(
        "award.approval_recorded", actor, "AwardCycle", cycle.pk, {"approval_ref": approval_ref}
    )
    return cycle


@transaction.atomic
def publish_award_results(
    *,
    cycle_id: int,
    actor,
) -> AwardCycle:
    """Publish finalized award results to institute portal (UC-SPACS-020)."""
    cycle = AwardCycle.objects.select_for_update().filter(pk=cycle_id).first()
    if cycle is None:
        raise NotFoundError("Award cycle not found.")

    if cycle.status != state_machine.READY_FOR_PUBLICATION:
        raise ConflictError(
            f"Award cycle must be ready for publication (status: {cycle.status!r})."
        )

    next_state = state_machine.resolve_award_transition(
        cycle.status, "publish", state_machine.SPACS_CONVENER
    )
    old_state = cycle.status

    cycle.status = next_state
    cycle.published_at = timezone.now()
    cycle.save(update_fields=["status", "published_at", "updated_at"])

    audit.log_audit_event(
        "award.results_published",
        actor,
        "AwardCycle",
        cycle.pk,
        {"from": old_state, "to": next_state},
    )

    # Notify winners
    winners = AwardCandidate.objects.filter(award_cycle=cycle, final_outcome="winner")
    for w in winners:
        notifications.enqueue(
            topic="award.published",
            dedupe_key=f"award.winner:{cycle.pk}:{w.user_id}",
            subject=f"Award Winner Announcement: {cycle.catalogue_version.entry.title}",
            body=(
                f"Congratulations! You have been awarded "
                f"{cycle.catalogue_version.entry.title} "
                f"for Convocation {cycle.convocation_year}."
            ),
            recipient_user_id=w.user_id,
        )

    return cycle
