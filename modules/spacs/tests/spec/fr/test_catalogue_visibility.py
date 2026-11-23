"""Specification tests for FR catalogue visibility cases."""

import datetime

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.spacs.models import CatalogueEntry, CatalogueVersion

pytestmark = pytest.mark.django_db


def _catalogue_client(stub_iam):
    stub_iam(
        make_session(
            user_id=7101,
            kind="student",
            modules=("spacs",),
            permissions=("spacs.catalogue.view",),
            roles=("student",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token spec-fr-catalogue")
    return client


def _award_version(*, code, title, entry_status, version_status):
    today = timezone.now().date()
    entry = CatalogueEntry.objects.create(
        code=code,
        title=title,
        kind="award",
        status=entry_status,
    )
    return CatalogueVersion.objects.create(
        entry=entry,
        version_number=1,
        academic_year="2026-27",
        policy_reference=f"REF/{code}",
        valid_from=today,
        valid_to=today + datetime.timedelta(days=30),
        status=version_status,
    )


def _assert_only_currently_published_are_exposed(response, published_titles):
    assert response.status_code == 200
    exposed = {item["entry_title"] for item in response.json()}
    assert exposed == set(published_titles)


def test_fr_spacs_001_authenticated_catalogue_exposes_published_entries_only(
    stub_iam, published_scholarship
):
    """test_id=FR-SPACS-001; source_id=CFR-SPACS-001."""
    _award_version(
        code="FR001-AWARD-PUB",
        title="FR001 Published Award",
        entry_status="active",
        version_status="published",
    )
    _award_version(
        code="FR001-SCH-DRAFT",
        title="FR001 Unpublished Scholarship",
        entry_status="draft",
        version_status="draft",
    )
    _award_version(
        code="FR001-AWARD-RETIRED",
        title="FR001 Retired Award",
        entry_status="retired",
        version_status="retired",
    )

    response = _catalogue_client(stub_iam).get("/api/v1/spacs/catalogue/")

    _assert_only_currently_published_are_exposed(
        response,
        {published_scholarship.entry.title, "FR001 Published Award"},
    )


def test_fr_spacs_019_authenticated_catalogue_excludes_unpublished_and_retired(
    stub_iam, published_scholarship
):
    """test_id=FR-SPACS-019; source_id=AFR-SPACS-001."""
    _award_version(
        code="FR019-AWARD-PUB",
        title="FR019 Published Award",
        entry_status="active",
        version_status="published",
    )
    _award_version(
        code="FR019-SCH-DRAFT",
        title="FR019 Draft Scholarship",
        entry_status="draft",
        version_status="draft",
    )
    _award_version(
        code="FR019-SCH-RETIRED",
        title="FR019 Retired Scholarship",
        entry_status="retired",
        version_status="retired",
    )

    response = _catalogue_client(stub_iam).get("/api/v1/spacs/catalogue/")

    _assert_only_currently_published_are_exposed(
        response,
        {published_scholarship.entry.title, "FR019 Published Award"},
    )
