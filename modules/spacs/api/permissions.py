"""Permissions for the SPACS module."""

from __future__ import annotations

from fusion_auth.permissions import HasModuleGrant

MODULE = HasModuleGrant("spacs")

# Shortcut permission checks
P_CATALOGUE_VIEW = "spacs.catalogue.view"
P_CATALOGUE_MANAGE = "spacs.catalogue.manage"
P_APP_VIEW_SELF = "spacs.application.view_self"
P_APP_CREATE = "spacs.application.create"
P_APP_UPDATE = "spacs.application.update"
P_APP_DELETE = "spacs.application.delete"
P_APP_EXPORT = "spacs.application.export"
P_APP_REVIEW = "spacs.application.review"
P_APP_APPROVE = "spacs.application.approve"
P_AWARD_CYCLE_MANAGE = "spacs.award_cycle.manage"
P_AWARD_CANDIDATE_REVIEW = "spacs.award_candidate.review"
P_AUDIT_VIEW = "spacs.audit.view"
