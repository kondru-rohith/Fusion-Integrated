"""Specification tests for BR catalogue-policy publication rules."""

import datetime

import pytest
from django.utils import timezone

from conftest import make_principal
from core.api.exceptions import BadRequestError
from modules.spacs.models import CatalogueEntry
from modules.spacs.registry import ROLE_GRANTS
from modules.spacs.services import catalogue

pytestmark = pytest.mark.django_db


def test_br_spacs_024_policy_version_requires_approval_reference():
    """test_id=BR-SPACS-024; source_id=BR-SPACS-015."""
    actor = make_principal(
        user_id=7401,
        kind="staff",
        modules=("spacs",),
        permissions=ROLE_GRANTS["spacs_convener"],
        roles=("spacs_convener",),
    )
    entry = CatalogueEntry.objects.create(
        code="BR024-POLICY",
        title="BR024 Policy Version",
        kind="scholarship",
        status="draft",
    )
    today = timezone.now().date()
    version = catalogue.create_version(
        entry_id=entry.pk,
        academic_year="2026-27",
        valid_from=today,
        valid_to=today + datetime.timedelta(days=30),
        policy_reference="",
        actor=actor,
    )

    with pytest.raises(BadRequestError):
        catalogue.publish_version(version_id=version.pk, policy_reference="", actor=actor)

    published = catalogue.publish_version(
        version_id=version.pk,
        policy_reference="APPROVED/BR024/01",
        actor=actor,
    )

    assert published.status == "published"
    assert published.policy_reference == "APPROVED/BR024/01"
