"""Role scoping for SPACS (BR-SPACS-005, 010, 012, 021).

Row-level access is decided here by narrowing querysets.
An unauthorized row yields 404 (NotFoundError), never 403, preventing ID enumeration.
"""

from __future__ import annotations

from django.db.models import QuerySet

from modules.spacs.models import (
    ApplicationDocument,
    AwardCandidate,
    AwardCycle,
    CatalogueEntry,
    CatalogueVersion,
    ScholarshipApplication,
    SpacsAuditLog,
)

# Permissions
P_CATALOGUE_VIEW = "spacs.catalogue.view"
P_CATALOGUE_MANAGE = "spacs.catalogue.manage"
P_APP_VIEW_SELF = "spacs.application.view_self"
P_APP_CREATE = "spacs.application.create"
P_APP_REVIEW = "spacs.application.review"
P_APP_APPROVE = "spacs.application.approve"
P_AWARD_CYCLE_MANAGE = "spacs.award_cycle.manage"
P_AWARD_CANDIDATE_REVIEW = "spacs.award_candidate.review"
P_AUDIT_VIEW = "spacs.audit.view"


def own_user_id(actor) -> int | None:
    if actor is None:
        return None
    uid = getattr(actor, "erp_user_id", None)
    if uid is not None:
        return int(uid)
    uid = getattr(actor, "user_id", None)
    return int(uid) if uid is not None else None


def is_convener(actor) -> bool:
    if actor is None:
        return False
    return getattr(actor, "has_permission", lambda p: False)(P_APP_APPROVE) or getattr(
        actor, "has_permission", lambda p: False
    )(P_CATALOGUE_MANAGE)


def is_assistant(actor) -> bool:
    if actor is None:
        return False
    return getattr(actor, "has_permission", lambda p: False)(P_APP_REVIEW)


def is_committee(actor) -> bool:
    if actor is None:
        return False
    return getattr(actor, "has_permission", lambda p: False)(P_AWARD_CANDIDATE_REVIEW)


def is_auditor(actor) -> bool:
    if actor is None:
        return False
    return getattr(actor, "has_permission", lambda p: False)(P_AUDIT_VIEW)


def published_scholarship_opportunities(actor=None) -> QuerySet[CatalogueVersion]:
    """Student-facing opportunities: published, active, currently valid schemes only."""
    from django.utils import timezone

    today = timezone.now().date()
    return (
        CatalogueVersion.objects.filter(
            status="published",
            entry__status="active",
            valid_from__lte=today,
            valid_to__gte=today,
        )
        .select_related("entry")
        .order_by("entry__title")
    )


def visible_catalogue_entries(actor) -> QuerySet[CatalogueEntry]:
    """Staff can see drafts and active entries; students/public only see active entries."""
    if is_convener(actor) or is_assistant(actor):
        return CatalogueEntry.objects.all()
    return CatalogueEntry.objects.filter(status="active")


def visible_catalogue_versions(actor) -> QuerySet[CatalogueVersion]:
    """Staff can see all versions; general users only see published versions."""
    if is_convener(actor) or is_assistant(actor):
        return CatalogueVersion.objects.all().select_related("entry")
    return published_scholarship_opportunities(actor)


def visible_applications(actor) -> QuerySet[ScholarshipApplication]:
    """Scoped applications queryset.

    - Convener sees all submitted/processed applications.
    - Assistant sees submitted applications in their verification queue.
    - Student sees only their own applications.
    """
    if actor is None:
        return ScholarshipApplication.objects.none()

    if is_convener(actor):
        return ScholarshipApplication.objects.all().select_related(
            "catalogue_entry", "catalogue_version"
        )

    if is_assistant(actor):
        # Assistants see anything submitted, under verification, or routed
        return ScholarshipApplication.objects.exclude(status="draft").select_related(
            "catalogue_entry", "catalogue_version"
        )

    uid = own_user_id(actor)
    if uid is not None:
        return ScholarshipApplication.objects.filter(user_id=uid).select_related(
            "catalogue_entry", "catalogue_version"
        )

    return ScholarshipApplication.objects.none()


def visible_documents(actor) -> QuerySet[ApplicationDocument]:
    """Students see their own active docs; reviewers see docs of visible applications."""
    if actor is None:
        return ApplicationDocument.objects.none()

    if is_convener(actor) or is_assistant(actor):
        return ApplicationDocument.objects.all().select_related("application")

    uid = own_user_id(actor)
    if uid is not None:
        return ApplicationDocument.objects.filter(user_id=uid, is_active=True).select_related(
            "application"
        )

    return ApplicationDocument.objects.none()


def visible_award_cycles(actor) -> QuerySet[AwardCycle]:
    """Staff & committee see all cycles; students see published cycles only."""
    if is_convener(actor) or is_committee(actor) or is_auditor(actor):
        return AwardCycle.objects.all().select_related("catalogue_version__entry")
    return AwardCycle.objects.filter(status="published").select_related("catalogue_version__entry")


def visible_award_candidates(actor, cycle_id: int | None = None) -> QuerySet[AwardCandidate]:
    """Candidate pool visible to committee and convener; published winners visible to all."""
    qs = AwardCandidate.objects.all().select_related("award_cycle__catalogue_version__entry")
    if cycle_id is not None:
        qs = qs.filter(award_cycle_id=cycle_id)

    if is_convener(actor) or is_committee(actor) or is_auditor(actor):
        return qs

    # General public / students see only finalized winners of published cycles
    return qs.filter(award_cycle__status="published", final_outcome__in=["winner", "runner_up"])


def visible_audit_logs(actor) -> QuerySet[SpacsAuditLog]:
    """Audit logs are accessible strictly to authorized personnel (BR-SPACS-021)."""
    if is_auditor(actor) or is_convener(actor):
        return SpacsAuditLog.objects.all()
    return SpacsAuditLog.objects.none()
