from __future__ import annotations

from core.api.exceptions import NotFoundError
from modules.spacs.models import AwardCandidate, AwardCycle
from modules.spacs.selectors import scoping


def get_award_cycle_or_404(cycle_id: int, actor) -> AwardCycle:
    cycle = scoping.visible_award_cycles(actor).filter(pk=cycle_id).first()
    if cycle is None:
        raise NotFoundError("No such award cycle.")
    return cycle


def get_award_candidate_or_404(candidate_id: int, actor) -> AwardCandidate:
    candidate = scoping.visible_award_candidates(actor).filter(pk=candidate_id).first()
    if candidate is None:
        raise NotFoundError("No such award candidate.")
    return candidate
