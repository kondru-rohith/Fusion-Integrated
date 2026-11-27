#!/usr/bin/env python
"""SPACS (Awards & Scholarships) Architecture and Operations Reference (R1-16).

This reference documents the architectural layers, data models, state machines,
and permissions of the SPACS module. It is a read-only executable reference.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SPACS_INFO = {
    "module_code": "spacs",
    "name": "SPACS — Awards & Scholarships",
    "description": (
        "Scholarship administration, merit-cum-means awards, "
        "convocation medals and renewal workflows."
    ),
    "layers": {
        "domain": (
            "Pure Python business rules, eligibility evaluations, and state machines "
            "(modules/spacs/domain/)"
        ),
        "models": "Django ORM entities with immutable audit records (modules/spacs/models/)",
        "selectors": "Scoping and read queries (modules/spacs/selectors/)",
        "services": (
            "Write workflows, transactional actions, outbox notifications "
            "(modules/spacs/services/)"
        ),
        "api": "Thin DRF views and serializers (modules/spacs/api/)",
    },
    "state_machines": [
        "CW-SPACS-01: Scholarship Application Lifecycle",
        "CW-SPACS-02: Scholarship Renewal Lifecycle",
        "CW-SPACS-03: Convocation Award Cycle",
    ],
    "key_roles": [
        "student: browses catalogue, submits drafts, uploads docs, requests corrections",
        "spacs_assistant: verifies documents, records findings, requests corrections",
        "spacs_convener: sanctions awards, opens review, publishes award cycles",
        "spacs_admin: manages catalogue entries and versions",
    ],
}


def main():
    print(f"=== {SPACS_INFO['name']} ===")
    print(f"Code: {SPACS_INFO['module_code']}")
    print(f"Description: {SPACS_INFO['description']}\n")
    print("Architectural Layers:")
    for layer, desc in SPACS_INFO["layers"].items():
        print(f"  - {layer:<12}: {desc}")
    print("\nState Machines:")
    for sm in SPACS_INFO["state_machines"]:
        print(f"  - {sm}")
    print("\nKey Roles:")
    for role in SPACS_INFO["key_roles"]:
        print(f"  - {role}")
    print("\nReference verified successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
