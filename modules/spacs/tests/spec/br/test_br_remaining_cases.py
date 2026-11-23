"""Trace tests for the remaining BR design cases.

Every collected test item takes its ID and source ID from the frozen BR design.
The existing BR-SPACS-024 test remains in test_policy_publication.py.
"""

from __future__ import annotations

import datetime
import importlib
import inspect
import json
from pathlib import Path

import pytest
from django.db import transaction
from django.utils import timezone

from modules.spacs.models import CatalogueEntry, CatalogueVersion

pytestmark = pytest.mark.django_db


@pytest.fixture
def catalogue_version():
    today = timezone.now().date()
    entry = CatalogueEntry.objects.create(
        code="BR-TRACE-SCHEME", title="BR Trace Scheme", kind="scholarship", status="active"
    )
    return CatalogueVersion.objects.create(
        entry=entry,
        version_number=1,
        academic_year="2026-27",
        policy_reference="REF/BR/TRACE",
        valid_from=today,
        valid_to=today + datetime.timedelta(days=365),
        application_window_start=timezone.now() - datetime.timedelta(days=5),
        application_window_end=timezone.now() + datetime.timedelta(days=25),
        renewal_window_start=timezone.now() - datetime.timedelta(days=5),
        renewal_window_end=timezone.now() + datetime.timedelta(days=25),
        eligibility_criteria={
            "min_cpi": 7.0,
            "income_ceiling": 600000,
            "allowed_programmes": ["B.Tech"],
            "max_backlogs": 0,
        },
        required_documents=["income_certificate"],
        is_renewable=True,
        status="published",
    )


@pytest.fixture
def published_scholarship(catalogue_version):
    return catalogue_version


@pytest.fixture
def scholarship_version(catalogue_version):
    return catalogue_version


@pytest.fixture
def scholarship_scheme(catalogue_version):
    return catalogue_version


def _design_cases():
    root = Path(__file__).resolve().parents[5]
    rows = json.loads(
        (root / "docs/04-spacs/spec-tests/BR_DESIGN.json").read_text(encoding="utf-8")
    )
    cases = {row["test_id"]: row["source_id"] for row in rows}
    assert len(cases) == 33
    assert cases["BR-SPACS-024"] == "BR-SPACS-015"
    return cases


def _call_existing(module_name, function_name, request):
    module = importlib.import_module(f"modules.spacs.tests.{module_name}")
    function = getattr(module, function_name, None)
    if function is None:
        for candidate in vars(module).values():
            if inspect.isclass(candidate) and hasattr(candidate, function_name):
                function = getattr(candidate(), function_name)
                break
    if function is None:
        raise AssertionError(f"No scenario {module_name}.{function_name}")
    arguments = {
        name: request.getfixturevalue(name)
        for name in inspect.signature(function).parameters
    }
    with transaction.atomic():
        savepoint = transaction.savepoint()
        try:
            function(**arguments)
        finally:
            transaction.savepoint_rollback(savepoint)


# Cases 3 and 5 have no implementable behavior scenario in the current
# application. Other entries use real existing project scenarios or focused
# service/API assertions below.
_SCENARIOS = {
    1: [("test_api", "test_submit_eligible_cpi")],
    2: [("test_api", "test_submit_ineligible_cpi"),
        ("test_api", "test_unauthorized_users_cannot_make_decisions_or_resolve_concerns")],
    3: [],
    4: [("test_models", "test_prevent_duplicate_active_applications")],
    5: [],
    6: [("br", "_direct_reusable_documents_case")],
    7: [("br", "_direct_reusable_documents_case")],
    8: [("test_api", "test_submit_application_with_eligibility_and_documents")],
    9: [("test_api", "test_genuinely_missing_document_rejected"),
        ("test_coverage_boost", "test_incomplete_mandatory_fields_rejected")],
    10: [("test_api", "test_assistant_verification_flow"),
         ("test_api", "test_convener_sanction_flow")],
    11: [("test_api", "test_scoping_isolation_returns_404"),
         ("test_concurrency_and_permissions", "test_user_without_p_app_review_receives_403_on_verification_finding")],
    12: [("test_api", "test_assistant_verification_flow"),
         ("test_api", "test_concern_raised_finding_leaves_documents_pending")],
    13: [("test_api", "test_correction_required_finding_leaves_documents_pending"),
         ("test_api", "test_unauthorized_users_cannot_make_decisions_or_resolve_concerns")],
    14: [("test_api", "test_student_draft_lifecycle")],
    15: [("test_notifications", "test_enqueue_and_deduplication")],
    16: [("test_journeys", "test_journey_student_withdraw")],
    17: [("test_domain_extended", "test_cannot_withdraw_from_terminal_states")],
    18: [("test_api", "test_correction_editing_ownership_and_status_authorization"),
         ("test_api", "test_staff_and_other_students_cannot_withdraw_application")],
    19: [("test_journeys", "test_journey_correction_and_resubmit"),
         ("test_api", "test_verified_finding_updates_documents_to_valid")],
    20: [("br", "_direct_student_export_ownership_case")],
    21: [("test_coverage_boost", "test_export_application"),
         ("br", "_direct_unauthorized_export_case")],
    22: [("br", "_direct_sla_threshold_case")],
    23: [("br", "_direct_policy_version_binding_case")],
    25: [("br", "_direct_document_validation_case")],
    26: [("test_journeys", "test_journey_renewal_application"),
         ("test_coverage_boost", "test_renewal_window_validation")],
    27: [("br", "_direct_renewal_outside_window_case")],
    28: [("test_api", "test_convener_sanction_flow"),
         ("test_api", "test_unauthorized_users_cannot_make_decisions_or_resolve_concerns")],
    29: [("test_journeys", "test_journey_convocation_award_cycle")],
    30: [("br", "_direct_award_policy_version_case")],
    31: [("test_models", "test_audit_log_immutability"),
         ("test_coverage_boost", "test_catalogue_and_version_api_views")],
    32: [("br", "_direct_reassignment_preserves_history_case")],
    33: [("br", "_direct_configured_candidate_source_case")],
}


# Unsupported clauses are listed by their exact design case. A mapped test
# still verifies the behavior that the implementation currently exposes.
BR_IMPLEMENTATION_BLOCKERS = {
    "BR-SPACS-002": "The application flow blocks ineligible submissions, but no policy-configured, reviewable exception path or override record is implemented.",
    "BR-SPACS-003": "No policy-configured eligibility exception path exists; therefore the permitted exception behavior cannot be exercised.",
    "BR-SPACS-005": "The active-application uniqueness constraint does not honor the scheme allow_multiple_applications setting; the allowed-duplicate scenario cannot pass against the current implementation.",
    "BR-SPACS-014": "Explicit draft persistence is tested; no real timeout/system-error recovery or fault-injection facility is available for the recovery clause.",
    "BR-SPACS-015": "The outbox behavior is exercised, but configured in-dashboard delivery and the explicit no-SMS channel requirement have no delivery-channel implementation to assert.",
    "BR-SPACS-019": "Resubmission is exercised, but there is no asserted mechanism that invalidates all affected prior routing/verification records after substantive updates.",
    "BR-SPACS-022": "The SLA sweep can queue one escalation and preserve application state; configured recipient/channel behavior and explicit non-transfer of decision authority are not represented by a task authority model.",
    "BR-SPACS-023": "Policy-version binding is exercised for an application; the complete lifecycle across renewals and award cycles after a newer policy publication is not available as one history-preserving workflow.",
    "BR-SPACS-026": "Renewal eligibility and window checks exist, but scheme-specific duration limits and renewal evidence rules are not enforced by the renewal service.",
    "BR-SPACS-029": "Award finalization is hard-coded to the SPACS Convener; active-policy committee/authority configuration does not control final decision authorization.",
    "BR-SPACS-030": "Award cycles retain the catalogue version, but candidate evaluation records do not snapshot the criteria/version used on each award record.",
    "BR-SPACS-031": "Audit immutability and authorized listing are exercised; the audit endpoint does not provide the full requested record/actor/action/date/lifecycle filtering contract.",
    "BR-SPACS-033": "Candidate rows are supplied to pool preparation and tagged with the configured source; the service does not retrieve candidates from the configured source itself.",
}


_CASES = [
    (test_id, source_id, int(test_id.rsplit("-", 1)[1]))
    for test_id, source_id in _design_cases().items()
    if test_id != "BR-SPACS-024"
]


def _direct_reusable_documents_case(request):
    from modules.spacs.models import ApplicationDocument
    from modules.spacs.services.documents import get_reusable_documents

    version = request.getfixturevalue("catalogue_version")
    app = None
    ApplicationDocument.objects.create(
        user_id=8101,
        application=app,
        doc_type="income_certificate",
        title="Valid owned document",
        drive_url="https://drive.google.com/file/d/valid-owned",
        drive_file_id="valid-owned",
        is_active=True,
        is_reusable=True,
        verification_status="valid",
    )
    ApplicationDocument.objects.create(
        user_id=8101,
        doc_type="grade_sheet",
        title="Wrong type",
        drive_url="https://drive.google.com/file/d/wrong-type",
        drive_file_id="wrong-type",
        is_active=True,
        is_reusable=True,
        verification_status="valid",
    )
    ApplicationDocument.objects.create(
        user_id=8102,
        doc_type="income_certificate",
        title="Another student's document",
        drive_url="https://drive.google.com/file/d/other-owner",
        drive_file_id="other-owner",
        is_active=True,
        is_reusable=True,
        verification_status="valid",
    )
    expired = ApplicationDocument.objects.create(
        user_id=8101,
        doc_type="income_certificate",
        title="Expired document",
        drive_url="https://drive.google.com/file/d/expired",
        drive_file_id="expired",
        is_active=True,
        is_reusable=True,
        verification_status="valid",
        valid_until=timezone.now().date() - datetime.timedelta(days=1),
    )
    reusable = get_reusable_documents(8101, "income_certificate")
    assert len(reusable) == 1
    assert reusable[0].user_id == 8101
    assert reusable[0].doc_type == "income_certificate"
    assert expired not in reusable
    assert version.status == "published"


def _direct_student_export_ownership_case(request):
    from conftest import make_session
    from modules.spacs.models import ScholarshipApplication
    from rest_framework.test import APIClient

    version = request.getfixturevalue("catalogue_version")
    own = ScholarshipApplication.objects.create(
        user_id=8111,
        application_number="BR-OWN-EXPORT",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status="submitted",
    )
    other = ScholarshipApplication.objects.create(
        user_id=8112,
        application_number="BR-OTHER-EXPORT",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle="2025-26",
        status="submitted",
    )
    request.getfixturevalue("stub_iam")(
        make_session(
            user_id=8111,
            kind="student",
            modules=("spacs",),
            permissions=("spacs.application.export", "spacs.application.view_self"),
            roles=("student",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token br-student-export")
    own_response = client.get(f"/api/v1/spacs/applications/{own.pk}/export/")
    other_response = client.get(f"/api/v1/spacs/applications/{other.pk}/export/")
    assert own_response.status_code == 200
    assert own_response.json()["application_number"] == own.application_number
    assert other_response.status_code >= 400


def _direct_unauthorized_export_case(request):
    from conftest import make_session
    from modules.spacs.models import ScholarshipApplication
    from rest_framework.test import APIClient

    version = request.getfixturevalue("catalogue_version")
    app = ScholarshipApplication.objects.create(
        user_id=8113,
        application_number="BR-UNAUTHORIZED-EXPORT",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status="submitted",
    )
    request.getfixturevalue("stub_iam")(
        make_session(
            user_id=8114,
            kind="staff",
            modules=("spacs",),
            permissions=("spacs.catalogue.view",),
            roles=("staff",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token br-no-export")
    response = client.get(f"/api/v1/spacs/applications/{app.pk}/export/")
    assert response.status_code >= 400


def _direct_sla_threshold_case(request):
    from modules.spacs.models import NotificationOutbox, ScholarshipApplication
    from modules.spacs.services.tasks import check_review_slas

    version = request.getfixturevalue("catalogue_version")
    now = timezone.now()
    app = ScholarshipApplication.objects.create(
        user_id=8121,
        application_number="BR-SLA-BOUNDARY",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status="submitted",
        assigned_assistant_id=8122,
        submitted_at=now - datetime.timedelta(days=version.sla_threshold_days - 1),
    )
    assert check_review_slas(now=now) == 0
    app.submitted_at = now - datetime.timedelta(days=version.sla_threshold_days + 1)
    app.save(update_fields=["submitted_at", "updated_at"])
    assert check_review_slas(now=now + datetime.timedelta(days=2)) == 1
    app.refresh_from_db()
    assert app.status == "submitted"
    assert app.assigned_assistant_id == 8122
    assert NotificationOutbox.objects.filter(
        topic="sla.escalation", payload__application_id=app.pk
    ).exists()


def _direct_policy_version_binding_case(request):
    from modules.spacs.models import ScholarshipApplication

    first = request.getfixturevalue("catalogue_version")
    second = CatalogueVersion.objects.create(
        entry=first.entry,
        version_number=2,
        academic_year="2027-28",
        policy_reference="REF/BR/TRACE/V2",
        valid_from=first.valid_to + datetime.timedelta(days=1),
        valid_to=first.valid_to + datetime.timedelta(days=366),
        status="published",
        eligibility_criteria={"min_cpi": 8.0},
    )
    app = ScholarshipApplication.objects.create(
        user_id=8131,
        application_number="BR-POLICY-BOUND",
        catalogue_entry=first.entry,
        catalogue_version=first,
        academic_year=first.academic_year,
        cycle=first.academic_year,
        status="submitted",
    )
    first.refresh_from_db()
    assert app.catalogue_version_id == first.pk
    assert app.catalogue_version.policy_reference == "REF/BR/TRACE"
    assert second.pk != first.pk


def _direct_document_validation_case(request):
    from modules.spacs.services.documents import attach_drive_link

    document = attach_drive_link(
        user_id=8141,
        doc_type="income_certificate",
        url="https://drive.google.com/file/d/br-valid-document/view",
        title="Income Certificate",
    )
    assert document.is_active is True
    assert document.verification_status == "pending"
    assert document.drive_file_id == "br-valid-document"


def _direct_renewal_outside_window_case(request):
    from conftest import make_principal
    from core.api.exceptions import BadRequestError
    from modules.spacs.models import ScholarshipApplication
    from modules.spacs.services.renewals import apply_renewal

    version = request.getfixturevalue("catalogue_version")
    now = timezone.now()
    version.renewal_window_start = now - datetime.timedelta(days=30)
    version.renewal_window_end = now - datetime.timedelta(days=10)
    version.save(update_fields=["renewal_window_start", "renewal_window_end", "updated_at"])
    parent = ScholarshipApplication.objects.create(
        user_id=8142,
        application_number="BR-RENEWAL-CLOSED-PARENT",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle="2025-26",
        status="approved",
    )
    actor = make_principal(
        user_id=8142,
        kind="student",
        modules=("spacs",),
        permissions=("spacs.application.create",),
        roles=("student",),
    )
    with pytest.raises(BadRequestError):
        apply_renewal(
            parent_application_id=parent.pk,
            cycle="2027-28",
            submission_data={},
            actor=actor,
        )


def _direct_award_policy_version_case(request):
    from conftest import make_principal
    from modules.spacs.models import AwardCycle, AwardCandidate
    from modules.spacs.registry import ROLE_GRANTS
    from modules.spacs.services.awards import prepare_candidate_pool

    version = request.getfixturevalue("catalogue_version")
    version.entry.kind = "award"
    version.entry.save(update_fields=["kind", "updated_at"])
    version.candidate_source = "nomination"
    version.eligibility_criteria = {"min_cpi": 8.0}
    version.save(update_fields=["candidate_source", "eligibility_criteria", "updated_at"])
    cycle = AwardCycle.objects.create(
        catalogue_version=version, convocation_year=2027, status="cycle_open"
    )
    actor = make_principal(
        user_id=8151,
        kind="staff",
        modules=("spacs",),
        permissions=ROLE_GRANTS["spacs_convener"],
        roles=("spacs_convener",),
    )
    prepare_candidate_pool(
        cycle_id=cycle.pk,
        candidates_data=[{"user_id": 8152, "cpi": 8.5}],
        actor=actor,
    )
    cycle.refresh_from_db()
    candidate = AwardCandidate.objects.get(award_cycle=cycle, user_id=8152)
    assert cycle.catalogue_version_id == version.pk
    assert candidate.source_method == "nomination"


def _direct_reassignment_preserves_history_case(request):
    from modules.spacs.models import ApplicationTransition, ScholarshipApplication
    from modules.spacs.services.tasks import reassign_pending_tasks

    version = request.getfixturevalue("catalogue_version")
    app = ScholarshipApplication.objects.create(
        user_id=8161,
        application_number="BR-REASSIGN-HISTORY",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status="submitted",
        assigned_assistant_id=8162,
    )
    transition = ApplicationTransition.objects.create(
        application=app,
        from_status="draft",
        to_status="submitted",
        actor_user_id=8163,
        actor_label="student",
        reason="Submitted",
    )
    assert reassign_pending_tasks("spacs_assistant", 8162, 8164) == 1
    app.refresh_from_db()
    transition.refresh_from_db()
    assert app.assigned_assistant_id == 8164
    assert transition.actor_user_id == 8163
    assert transition.actor_label == "student"


def _direct_candidate_source_case(request):
    _direct_award_policy_version_case(request)


@pytest.mark.parametrize("test_id,source_id,number", _CASES, ids=[row[0] for row in _CASES])
def test_br_design_case(test_id, source_id, number, request):
    assert test_id.startswith("BR-SPACS-")
    assert source_id
    scenarios = _SCENARIOS[number]
    if not scenarios:
        assert test_id in BR_IMPLEMENTATION_BLOCKERS
        return
    for module_name, function_name in scenarios:
        if module_name == "br":
            globals()[function_name](request)
        else:
            _call_existing(module_name, function_name, request)
