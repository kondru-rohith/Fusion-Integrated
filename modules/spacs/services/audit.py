from __future__ import annotations

from modules.spacs.models import ApplicationTransition, ScholarshipApplication, SpacsAuditLog
from modules.spacs.selectors import scoping


def record_transition(
    application: ScholarshipApplication,
    from_status: str,
    to_status: str,
    actor,
    reason: str = "",
) -> ApplicationTransition:
    """Record an append-only application transition (BR-SPACS-021)."""
    uid = scoping.own_user_id(actor)
    actor_label = getattr(actor, "kind", "user")
    if getattr(actor, "is_system", False) or uid is None:
        actor_label = "system"

    return ApplicationTransition.objects.create(
        application=application,
        from_status=from_status,
        to_status=to_status,
        actor_user_id=uid,
        actor_label=actor_label,
        reason=(reason or "").strip()[:500],
    )


def log_audit_event(
    action: str,
    actor,
    target_type: str,
    target_id: str | int,
    details: dict | None = None,
) -> SpacsAuditLog:
    """Record an administrative or policy audit event (BR-SPACS-021)."""
    uid = scoping.own_user_id(actor) or 0
    role = getattr(actor, "kind", "system")
    return SpacsAuditLog.objects.create(
        action=action,
        actor_id=uid,
        actor_role=role,
        target_type=target_type,
        target_id=str(target_id),
        details=details or {},
    )
