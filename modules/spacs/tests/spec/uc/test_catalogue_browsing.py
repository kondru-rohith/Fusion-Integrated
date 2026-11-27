"""Specification tests for UC catalogue browsing."""

import datetime

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.spacs.models import CatalogueEntry, CatalogueVersion

pytestmark = pytest.mark.django_db


def test_uc_spacs_030_published_catalogue_browsing_excludes_unpublished(
    stub_iam, published_scholarship
):
    """test_id=UC-SPACS-030; source_id=UC-SPACS-014."""
    today = timezone.now().date()
    published_award = CatalogueEntry.objects.create(
        code="UC030-AWARD-PUB",
        title="UC030 Published Award",
        kind="award",
        description="Published award description",
        status="active",
    )
    CatalogueVersion.objects.create(
        entry=published_award,
        version_number=1,
        academic_year="2026-27",
        policy_reference="REF/UC030/AWARD",
        valid_from=today,
        valid_to=today + datetime.timedelta(days=30),
        candidate_source="nomination",
        eligibility_criteria={"eligible_programmes": ["B.Tech"]},
        required_documents=["recommendation"],
        is_renewable=False,
        status="published",
    )
    draft = CatalogueEntry.objects.create(
        code="UC030-DRAFT",
        title="UC030 Unpublished Draft",
        kind="award",
        status="draft",
    )
    CatalogueVersion.objects.create(
        entry=draft,
        version_number=1,
        academic_year="2026-27",
        valid_from=today,
        valid_to=today + datetime.timedelta(days=30),
        status="draft",
    )
    retired = CatalogueEntry.objects.create(
        code="UC030-RETIRED",
        title="UC030 Retired Entry",
        kind="scholarship",
        status="retired",
    )
    CatalogueVersion.objects.create(
        entry=retired,
        version_number=1,
        academic_year="2026-27",
        valid_from=today,
        valid_to=today + datetime.timedelta(days=30),
        status="retired",
    )
    stub_iam(
        make_session(
            user_id=7301,
            kind="student",
            modules=("spacs",),
            permissions=("spacs.catalogue.view",),
            roles=("student",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token spec-uc-catalogue")

    response = client.get("/api/v1/spacs/catalogue/")

    assert response.status_code == 200
    entries = {item["entry_title"]: item for item in response.json()}
    assert set(entries) == {published_scholarship.entry.title, published_award.title}
    award = entries[published_award.title]
    assert award["entry_kind"] == "award"
    assert award["candidate_source"] == "nomination"
    assert award["eligibility_criteria"] == {"eligible_programmes": ["B.Tech"]}
    assert award["required_documents"] == ["recommendation"]
    assert award["valid_from"] == today.isoformat()
    assert award["valid_to"] == (today + datetime.timedelta(days=30)).isoformat()
    assert award["renewal_criteria"] == {}
    assert "UC030 Unpublished Draft" not in entries
    assert "UC030 Retired Entry" not in entries
