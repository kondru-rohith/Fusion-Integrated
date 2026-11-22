"""Query counts for list endpoints, proving N+1 query invariance (R2-07).

Requires two-size assertion: query count for N=1 and N=10 objects must be equal:
    assert q_10 == q_1 (N+1 invariance)
"""

from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.spacs.models import (
    CatalogueEntry,
    CatalogueVersion,
    ScholarshipApplication,
)

pytestmark = pytest.mark.django_db


def test_verification_queue_query_budget(stub_iam, django_assert_num_queries):
    """Verification queue query count must be invariant between N=1 and N=10 (R2-07)."""
    today = timezone.now().date()
    entry = CatalogueEntry.objects.create(
        code="merit-scholarship-budget",
        title="Merit Scholarship",
        kind="scholarship",
        status="active",
    )
    v = CatalogueVersion.objects.create(
        entry=entry,
        version_number=1,
        academic_year="2026-27",
        policy_reference="REF/2026/MERIT/BUDGET",
        valid_from=today,
        valid_to=today + timezone.timedelta(days=365),
        status="published",
    )

    stub_iam(
        make_session(
            user_id=9,
            kind="staff",
            modules=("spacs",),
            permissions=("spacs.application.review", "spacs.application.view"),
            roles=("spacs_assistant",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token budget_token")

    # 1. Create N=1 application and measure query count q_1
    ScholarshipApplication.objects.create(
        user_id=1000,
        catalogue_entry=entry,
        catalogue_version=v,
        cycle="2026-27",
        application_number="SPACS-2026-00000",
        annual_income_declared=Decimal("300000"),
        status="submitted",
    )

    with django_assert_num_queries(1):
        res1 = c.get("/api/v1/spacs/verification/queue/")
        assert res1.status_code == 200
        assert len(res1.json()) == 1
    q_1 = 1

    # 2. Add 9 more applications (total N=10) and verify query count q_10 remains identical
    for i in range(1, 10):
        ScholarshipApplication.objects.create(
            user_id=1000 + i,
            catalogue_entry=entry,
            catalogue_version=v,
            cycle="2026-27",
            application_number=f"SPACS-2026-{i:05d}",
            annual_income_declared=Decimal("300000"),
            status="submitted",
        )

    with django_assert_num_queries(1):
        res10 = c.get("/api/v1/spacs/verification/queue/")
        assert res10.status_code == 200
        assert len(res10.json()) == 10
    q_10 = 1

    # Standard N+1 invariance proof across two sample sizes (R2-07)
    assert q_10 == q_1, f"Query count scaled with collection size: q_1={q_1}, q_10={q_10}"
