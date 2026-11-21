"""Query counts for list endpoints, so an N+1 query regression fails tests."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.spacs.models import (
    CatalogueEntry,
    CatalogueVersion,
    ScholarshipApplication,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def cohort():
    """Create 10 applications with related versions and entries."""
    from django.utils import timezone

    today = timezone.now().date()
    entry = CatalogueEntry.objects.create(
        code="merit-scholarship",
        title="Merit Scholarship",
        kind="scholarship",
        status="active",
    )
    v = CatalogueVersion.objects.create(
        entry=entry,
        version_number=1,
        academic_year="2026-27",
        policy_reference="REF/2026/MERIT/01",
        valid_from=today,
        valid_to=today + timezone.timedelta(days=365),
        status="published",
    )

    apps = []
    for i in range(10):
        app = ScholarshipApplication.objects.create(
            user_id=1000 + i,
            catalogue_entry=entry,
            catalogue_version=v,
            cycle="2026-27",
            application_number=f"SPACS-2026-{i:05d}",
            annual_income_declared=Decimal("300000"),
            status="submitted",
        )
        apps.append(app)
    return apps


def test_verification_queue_query_budget(stub_iam, cohort, django_assert_num_queries):
    """Verification queue query count must not scale with application count."""
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
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    # The list query should execute with minimal queries (select_related entry and version)
    with django_assert_num_queries(1):
        res = c.get("/api/v1/spacs/verification/queue/")
        assert res.status_code == 200
        assert len(res.json()) == 10
