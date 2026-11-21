"""SPACS public contract for cross-module integration.

All getters take plural sequences (enforced by ops/checks/contracts_are_plural.py).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.spacs.models import AwardCandidate, ScholarshipApplication


@dataclass(frozen=True)
class StudentScholarshipDTO:
    application_id: int
    user_id: int
    scheme_code: str
    scheme_title: str
    academic_year: str
    cycle: str
    status: str
    sanction_order_ref: str = ""


@dataclass(frozen=True)
class AwardWinnerDTO:
    user_id: int
    scheme_code: str
    scheme_title: str
    convocation_year: int
    final_outcome: str


def get_active_scholarships(user_ids: Sequence[int]) -> dict[int, list[StudentScholarshipDTO]]:
    """Batched query returning active or approved scholarships for given student user IDs."""
    ids = {int(uid) for uid in user_ids if uid is not None}
    if not ids:
        return {}

    apps = (
        ScholarshipApplication.objects.filter(user_id__in=ids, status__in=["approved", "renewed"])
        .select_related("catalogue_entry", "catalogue_version")
        .prefetch_related("decisions")
    )

    out: dict[int, list[StudentScholarshipDTO]] = {uid: [] for uid in ids}
    for app in apps:
        latest_decision = app.decisions.filter(decision="approved").first()
        order_ref = latest_decision.sanction_order_ref if latest_decision else ""
        out[app.user_id].append(
            StudentScholarshipDTO(
                application_id=app.id,
                user_id=app.user_id,
                scheme_code=app.catalogue_entry.code,
                scheme_title=app.catalogue_entry.title,
                academic_year=app.academic_year,
                cycle=app.cycle,
                status=app.status,
                sanction_order_ref=order_ref,
            )
        )
    return out


def get_convocation_award_winners(
    convocation_years: Sequence[int],
) -> dict[int, list[AwardWinnerDTO]]:
    """Batched query returning award winners for given convocation years."""
    years = {int(y) for y in convocation_years if y is not None}
    if not years:
        return {}

    candidates = AwardCandidate.objects.filter(
        award_cycle__convocation_year__in=years,
        award_cycle__status="published",
        final_outcome__in=["winner", "runner_up"],
    ).select_related("award_cycle__catalogue_version__entry")

    out: dict[int, list[AwardWinnerDTO]] = {y: [] for y in years}
    for c in candidates:
        year = c.award_cycle.convocation_year
        out[year].append(
            AwardWinnerDTO(
                user_id=c.user_id,
                scheme_code=c.award_cycle.catalogue_version.entry.code,
                scheme_title=c.award_cycle.catalogue_version.entry.title,
                convocation_year=year,
                final_outcome=c.final_outcome,
            )
        )
    return out
