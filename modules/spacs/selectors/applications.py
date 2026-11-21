from __future__ import annotations

from core.api.exceptions import NotFoundError
from modules.spacs.models import ScholarshipApplication
from modules.spacs.selectors import scoping


def get_application_or_404(application_id: int, actor) -> ScholarshipApplication:
    app = scoping.visible_applications(actor).filter(pk=application_id).first()
    if app is None:
        raise NotFoundError("No such application.")
    return app


def get_student_applications(actor) -> list[ScholarshipApplication]:
    uid = scoping.own_user_id(actor)
    if uid is None:
        return []
    return list(
        ScholarshipApplication.objects.filter(user_id=uid)
        .select_related("catalogue_entry", "catalogue_version")
        .order_by("-created_at")
    )


def get_verification_queue(actor) -> list[ScholarshipApplication]:
    """Applications waiting for assistant verification."""
    return list(
        scoping.visible_applications(actor)
        .filter(
            status__in=[
                "submitted",
                "under_verification",
                "resubmitted",
                "renewal_submitted",
                "renewal_under_verification",
                "renewal_resubmitted",
            ]
        )
        .order_by("created_at")
    )


def get_decision_queue(actor) -> list[ScholarshipApplication]:
    """Applications waiting for convener sanction."""
    return list(
        scoping.visible_applications(actor)
        .filter(
            status__in=[
                "verified",
                "verification_concern",
                "under_convener_review",
                "renewal_verified",
                "renewal_under_decision",
            ]
        )
        .order_by("created_at")
    )
