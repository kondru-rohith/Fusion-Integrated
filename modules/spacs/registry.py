"""What the server tells the shell about this module (ADR-0010)."""

from __future__ import annotations

MODULE = {
    "code": "spacs",
    "label": "Awards & Scholarships",
    "icon": "Award",
    "base_path": "/spacs",
    "nav_section": "Academics",
    "sort_order": 15,
    "status": "active",
}

NAV_ITEMS = [
    # -- Student self-service
    {
        "code": "spacs.catalogue",
        "label": "Opportunities",
        "icon": "ClipboardText",
        "to": "/spacs/catalogue",
        "required_permission": "spacs.catalogue.view",
        "sort_order": 10,
    },
    {
        "code": "spacs.mine",
        "label": "My Applications",
        "icon": "UserCheck",
        "to": "/spacs/mine",
        "required_permission": "spacs.application.view_self",
        "sort_order": 20,
    },
    # -- SPACS Assistant
    {
        "code": "spacs.verification",
        "label": "Verification Queue",
        "icon": "Checks",
        "to": "/spacs/verification-queue",
        "required_permission": "spacs.application.review",
        "sort_order": 30,
    },
    # -- SPACS Convener
    {
        "code": "spacs.decisions",
        "label": "Decision Approvals",
        "icon": "Signature",
        "to": "/spacs/decision-queue",
        "required_permission": "spacs.application.approve",
        "sort_order": 40,
    },
    {
        "code": "spacs.catalogue_admin",
        "label": "Scheme Catalogue",
        "icon": "Gear",
        "to": "/spacs/catalogue-admin",
        "required_permission": "spacs.catalogue.manage",
        "sort_order": 50,
    },
    # -- Award Committee & Convener
    {
        "code": "spacs.awards",
        "label": "Convocation Awards",
        "icon": "Medal",
        "to": "/spacs/awards",
        "required_permission": "spacs.award_candidate.review",
        "sort_order": 60,
    },
    # -- Audit Trail
    {
        "code": "spacs.audit",
        "label": "Audit Trail",
        "icon": "ShieldCheck",
        "to": "/spacs/audit",
        "required_permission": "spacs.audit.view",
        "sort_order": 70,
    },
]

PERMISSIONS = [
    ("spacs.catalogue.view", "Browse published scholarship and award schemes"),
    ("spacs.catalogue.manage", "Create, edit, publish and retire catalogue entries"),
    ("spacs.application.view_self", "View own scholarship applications"),
    ("spacs.application.create", "Submit a scholarship application or renewal"),
    ("spacs.application.update", "Modify an editable application draft or correction"),
    ("spacs.application.delete", "Withdraw an application"),
    ("spacs.application.export", "Export or print an application"),
    ("spacs.application.review", "Verify application evidence and request corrections"),
    ("spacs.application.approve", "Sanction or reject scholarship applications"),
    ("spacs.award_cycle.manage", "Open award cycles, prepare candidate pools, publish results"),
    ("spacs.award_candidate.review", "Evaluate and score award candidates in committee"),
    ("spacs.audit.view", "View protected SPACS audit trail"),
]

SYSTEM_PERMISSIONS = [
    "spacs.sla.escalate",
    "spacs.renewal.remind",
]

_STUDENT = [
    "spacs.catalogue.view",
    "spacs.application.view_self",
    "spacs.application.create",
    "spacs.application.update",
    "spacs.application.delete",
    "spacs.application.export",
]

_ASSISTANT = [
    "spacs.catalogue.view",
    "spacs.application.review",
    "spacs.application.export",
]

_CONVENER = [
    "spacs.catalogue.view",
    "spacs.catalogue.manage",
    "spacs.application.review",
    "spacs.application.approve",
    "spacs.application.export",
    "spacs.award_cycle.manage",
    "spacs.award_candidate.review",
    "spacs.audit.view",
]

_COMMITTEE = [
    "spacs.catalogue.view",
    "spacs.award_candidate.review",
]

_AUDITOR = [
    "spacs.catalogue.view",
    "spacs.audit.view",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "spacs_assistant": _ASSISTANT,
    "spacs_convener": _CONVENER,
    "award_committee_member": _COMMITTEE,
    "spacs_auditor": _AUDITOR,
    "Dean Academic": [*_CONVENER, *_AUDITOR],
}
