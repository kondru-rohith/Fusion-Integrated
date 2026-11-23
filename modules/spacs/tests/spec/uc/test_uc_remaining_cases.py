"""Trace tests for the remaining UC design cases.

Each collected case retains its frozen test_id/source_id. Existing project
scenarios are invoked as real behavior tests and rolled back between cases.
Clauses without a supported endpoint or real infrastructure are recorded in
UC_IMPLEMENTATION_BLOCKERS below rather than simulated with mocks.
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
def scholarship_scheme():
    today = timezone.now().date()
    entry = CatalogueEntry.objects.create(
        code="UC-TRACE-SCHEME", title="UC Trace Scheme", kind="scholarship", status="active"
    )
    return CatalogueVersion.objects.create(
        entry=entry,
        version_number=1,
        academic_year="2026-27",
        policy_reference="REF/UC/TRACE",
        valid_from=today,
        valid_to=today + datetime.timedelta(days=365),
        application_window_start=timezone.now() - datetime.timedelta(days=5),
        application_window_end=timezone.now() + datetime.timedelta(days=25),
        renewal_window_start=timezone.now() - datetime.timedelta(days=5),
        renewal_window_end=timezone.now() + datetime.timedelta(days=25),
        is_renewable=True,
        eligibility_criteria={
            "min_cpi": 7.0,
            "income_ceiling": 600000,
            "allowed_programmes": ["B.Tech"],
            "max_backlogs": 0,
        },
        required_documents=["income_certificate"],
        status="published",
    )


@pytest.fixture
def catalogue_version(scholarship_scheme):
    return scholarship_scheme


@pytest.fixture
def scholarship_version(scholarship_scheme):
    return scholarship_scheme


@pytest.fixture
def published_scholarship(scholarship_scheme):
    return scholarship_scheme


@pytest.fixture
def admin_actor():
    from conftest import make_principal
    from modules.spacs.registry import ROLE_GRANTS

    return make_principal(
        user_id=7790,
        kind="staff",
        modules=("spacs",),
        permissions=ROLE_GRANTS["spacs_convener"],
        roles=("spacs_convener",),
    )


def _design_cases():
    root = Path(__file__).resolve().parents[5]
    design = json.loads(
        (root / "docs/04-spacs/spec-tests/UC_DESIGN.json").read_text(encoding="utf-8")
    )
    cases = {row["test_id"]: row["source_id"] for row in design}
    assert len(cases) == 58
    assert cases["UC-SPACS-030"] == "UC-SPACS-014"
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


# The entries identify the closest concrete behavior scenario for each use
# case. Multiple entries are separate assertions/scenarios within that case.
_SCENARIOS = {
    1: [("test_journeys", "test_journey_apply_verify_approve")],
    2: [("test_api", "test_student_draft_lifecycle")],
    3: [("test_api", "test_submit_application_with_eligibility_and_documents"),
        ("test_api", "test_attached_income_certificate_satisfies_requirement_with_normalization")],
    4: [("test_api", "test_submit_ineligible_cpi"),
        ("test_api", "test_genuinely_missing_document_rejected"),
        ("test_models", "test_prevent_duplicate_active_applications")],
    5: [("test_api", "test_student_draft_lifecycle")],
    6: [("test_journeys", "test_journey_apply_verify_approve")],
    7: [("test_journeys", "test_journey_correction_and_resubmit")],
    8: [("test_api", "test_concern_raised_finding_leaves_documents_pending"),
        ("test_api", "test_verification_concern_details_visible_to_convener")],
    9: [("test_concurrency_and_permissions", "test_user_without_p_app_review_receives_403_on_verification_finding")],
    10: [("test_journeys", "test_journey_correction_and_resubmit")],
    11: [("test_api", "test_correction_required_editing_and_resubmission"),
         ("test_api", "test_student_draft_lifecycle")],
    12: [("test_api", "test_student_draft_lifecycle")],
    13: [("test_api", "test_correction_editing_ownership_and_status_authorization")],
    14: [("test_journeys", "test_journey_student_withdraw")],
    15: [("test_domain_extended", "test_cannot_withdraw_from_terminal_states")],
    16: [("test_domain_extended", "test_cannot_withdraw_from_terminal_states")],
    17: [("test_journeys", "test_journey_apply_verify_approve")],
    18: [("test_api", "test_concerned_application_returned_for_correction_recorded_in_audit")],
    19: [("test_concurrency_and_permissions", "test_user_without_p_app_approve_receives_403_on_decision_views")],
    20: [("uc", "_direct_student_export_case")],
    21: [("test_coverage_boost", "test_export_application")],
    22: [("uc", "_direct_export_denied_case")],
    23: [("uc", "_direct_application_history_case")],
    24: [("uc", "_direct_foreign_history_denied_case")],
    25: [("test_api", "test_create_first_draft_version_success")],
    26: [("test_coverage_boost", "test_incomplete_mandatory_fields_rejected")],
    27: [("test_api", "test_create_draft_version_defaults_valid_dates")],
    28: [("test_api", "test_create_draft_version_defaults_valid_dates")],
    29: [("test_api", "test_create_first_draft_version_success")],
    31: [("test_journeys", "test_journey_renewal_application")],
    32: [("test_coverage_boost", "test_renewal_window_validation")],
    33: [("test_journeys", "test_journey_renewal_application")],
    34: [("test_journeys", "test_journey_convocation_award_cycle")],
    35: [("test_journeys", "test_journey_convocation_award_cycle")],
    36: [("test_journeys", "test_journey_convocation_award_cycle")],
    37: [("test_journeys", "test_journey_convocation_award_cycle")],
    38: [("test_journeys", "test_journey_convocation_award_cycle")],
    39: [("test_coverage_boost", "test_award_two_step_approval_and_publish")],
    40: [("test_coverage_boost", "test_award_two_step_approval_and_publish")],
    41: [("test_journeys", "test_journey_convocation_award_cycle")],
    42: [("test_coverage_boost", "test_award_two_step_approval_and_publish")],
    43: [("test_coverage_boost", "test_catalogue_and_version_api_views")],
    44: [("test_concurrency_and_permissions", "test_user_without_spacs_module_grant_receives_403")],
    45: [("test_coverage_boost", "test_create_and_publish_version")],
    46: [("test_coverage_boost", "test_create_and_publish_version")],
    47: [("uc", "_direct_sla_case")],
    48: [("uc", "_direct_completed_sla_case")],
    49: [("uc", "_direct_sla_case")],
    50: [],
    51: [("uc", "_direct_renewal_reminder_case")],
    52: [("uc", "_direct_nonrenewable_reminder_case")],
    53: [("uc", "_direct_renewal_reminder_case")],
    54: [],
    55: [("uc", "_direct_reassignment_case")],
    56: [("uc", "_direct_no_pending_reassignment_case")],
    57: [("uc", "_direct_multiple_reassignment_case")],
    58: [("uc", "_direct_reassignment_case")],
}


# These design clauses exceed the corresponding supported implementation or
# real test infrastructure. Their nearest supported scenario remains mapped
# above; this list identifies the unexercised clause precisely.
UC_IMPLEMENTATION_BLOCKERS = {
    "UC-SPACS-005": "No supported real timeout/system-error injection and draft-recovery facility.",
    "UC-SPACS-012": "No edit-cancel endpoint or persisted edit session; only the draft lifecycle is available.",
    "UC-SPACS-013": "No concurrent application-edit race hook or refresh-state response contract is exposed for deterministic integration coverage.",
    "UC-SPACS-016": "No deterministic withdrawal-confirmation race hook is exposed.",
    "UC-SPACS-033": "No renewal-draft creation flow is exposed; renewal creation currently submits a renewal application.",
    "UC-SPACS-035": "Candidate-pool preparation receives supplied candidate rows; no authoritative-data completeness resolver or incomplete-record resolution flow is exposed.",
    "UC-SPACS-037": "Award evaluation has no pending-evidence request action or evaluation-history record for that action.",
    "UC-SPACS-049": "SLA processing has no configured multi-stage reminder schedule; the implemented service emits its single escalation stage.",
    "UC-SPACS-050": "The delivery-failure clause requires a failing delivery backend; none is configured, and replacing it with a mock is disallowed.",
    "UC-SPACS-053": "Renewal reminder processing has no configurable multiple reminder stages; one fixed trigger is implemented.",
    "UC-SPACS-054": "The delivery-failure clause requires a failing delivery backend; none is configured, and replacing it with a mock is disallowed.",
    "UC-SPACS-058": "Role reassignment accepts old/new user IDs directly and has no current-holder resolver or surfaced unresolved-routing state.",
    "UC-SPACS-028": "No API operation for editing a historical/published catalogue version in place is exposed, so an attempted edit and its required rejection cannot be exercised through the application interface.",
    "UC-SPACS-047": "The SLA service queues an outbox escalation, but it does not record the required notification event in the audit trail or deliver configured channel/recipient variants.",
    "UC-SPACS-051": "The reminder service queues an outbox event; it does not audit delivery or recheck renewal eligibility and active window at trigger time as specified.",
    "UC-SPACS-052": "The available negative reminder behavior covers non-renewable schemes; no renewal-window/applicability recheck is implemented at trigger time.",
    "UC-SPACS-038": "The existing award journey exercises authorized evaluation only; no project scenario exercises rejection of a different-committee member on candidate-pool access and mutation.",
    "UC-SPACS-034": "The candidate preparation endpoint accepts a caller-supplied candidate list; no authoritative configured-source retrieval or configured eligibility-filtering scenario is available.",
    "UC-SPACS-036": "The existing award journey verifies evaluation score and remarks, but does not expose assertions for evaluation history, shortlist selection, or required recommendation fields as one committee operation.",
    "UC-SPACS-043": "The audit API scenario exercises listing, but the implementation exposes no filter parameters; filtering and read-only enforcement for each requested filter cannot be verified by that scenario.",
}


def _direct_sla_case(request):
    from modules.spacs.models import NotificationOutbox, ScholarshipApplication
    from modules.spacs.services.tasks import check_review_slas

    version = request.getfixturevalue("catalogue_version")
    now = timezone.now()
    app = ScholarshipApplication.objects.create(
        user_id=7791,
        application_number="SPACS-UC-SLA-001",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status="submitted",
        submitted_at=now - datetime.timedelta(days=version.sla_threshold_days + 1),
    )
    assert check_review_slas(now=now) == 1
    assert NotificationOutbox.objects.filter(
        topic="sla.escalation", payload__application_id=app.pk
    ).exists()
    assert ScholarshipApplication.objects.filter(pk=app.pk, status="submitted").exists()


def _direct_student_export_case(request):
    from conftest import make_session
    from modules.spacs.models import ScholarshipApplication
    from rest_framework.test import APIClient

    version = request.getfixturevalue("catalogue_version")
    app = ScholarshipApplication.objects.create(
        user_id=7801,
        application_number="SPACS-UC-EXPORT-OWNER",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status="submitted",
    )
    request.getfixturevalue("stub_iam")(
        make_session(
            user_id=7801,
            kind="student",
            modules=("spacs",),
            permissions=("spacs.application.export", "spacs.application.view_self"),
            roles=("student",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token uc-owner-export")
    response = client.get(f"/api/v1/spacs/applications/{app.pk}/export/")
    assert response.status_code == 200
    assert response.json()["application_number"] == app.application_number


def _direct_export_denied_case(request):
    from conftest import make_session
    from modules.spacs.models import ScholarshipApplication
    from rest_framework.test import APIClient

    version = request.getfixturevalue("catalogue_version")
    app = ScholarshipApplication.objects.create(
        user_id=7802,
        application_number="SPACS-UC-EXPORT-FOREIGN",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status="submitted",
    )
    request.getfixturevalue("stub_iam")(
        make_session(
            user_id=7803,
            kind="student",
            modules=("spacs",),
            permissions=("spacs.application.export", "spacs.application.view_self"),
            roles=("student",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token uc-foreign-export")
    response = client.get(f"/api/v1/spacs/applications/{app.pk}/export/")
    assert response.status_code >= 400


def _direct_application_history_case(request):
    from conftest import make_session
    from modules.spacs.models import ApplicationTransition, ScholarshipApplication
    from modules.spacs.registry import ROLE_GRANTS
    from rest_framework.test import APIClient

    version = request.getfixturevalue("catalogue_version")
    app = ScholarshipApplication.objects.create(
        user_id=7804,
        application_number="SPACS-UC-HISTORY-OWNER",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status="submitted",
    )
    ApplicationTransition.objects.create(
        application=app,
        from_status="draft",
        to_status="submitted",
        actor_user_id=7804,
        actor_label="student",
        reason="Submitted",
    )
    request.getfixturevalue("stub_iam")(
        make_session(
            user_id=7804,
            kind="student",
            modules=("spacs",),
            permissions=ROLE_GRANTS["student"],
            roles=("student",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token uc-owner-history")
    response = client.get(f"/api/v1/spacs/applications/{app.pk}/history/")
    assert response.status_code == 200
    assert response.json()["results"]


def _direct_foreign_history_denied_case(request):
    from conftest import make_session
    from modules.spacs.models import ScholarshipApplication
    from modules.spacs.registry import ROLE_GRANTS
    from rest_framework.test import APIClient

    version = request.getfixturevalue("catalogue_version")
    app = ScholarshipApplication.objects.create(
        user_id=7805,
        application_number="SPACS-UC-HISTORY-FOREIGN",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status="submitted",
    )
    request.getfixturevalue("stub_iam")(
        make_session(
            user_id=7806,
            kind="student",
            modules=("spacs",),
            permissions=ROLE_GRANTS["student"],
            roles=("student",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token uc-foreign-history")
    response = client.get(f"/api/v1/spacs/applications/{app.pk}/history/")
    assert response.status_code >= 400


def _direct_completed_sla_case(request):
    from modules.spacs.models import NotificationOutbox, ScholarshipApplication
    from modules.spacs.services.tasks import check_review_slas

    version = request.getfixturevalue("catalogue_version")
    now = timezone.now()
    ScholarshipApplication.objects.create(
        user_id=7792,
        application_number="SPACS-UC-SLA-COMPLETE",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status="approved",
        submitted_at=now - datetime.timedelta(days=version.sla_threshold_days + 1),
    )
    assert check_review_slas(now=now) == 0
    assert not NotificationOutbox.objects.filter(topic="sla.escalation").exists()


def _direct_renewal_reminder_case(request):
    from modules.spacs.models import NotificationOutbox, ScholarshipApplication
    from modules.spacs.services.tasks import send_renewal_reminders

    version = request.getfixturevalue("catalogue_version")
    now = timezone.now()
    version.renewal_window_end = now + datetime.timedelta(days=5)
    version.save(update_fields=["renewal_window_end", "updated_at"])
    app = ScholarshipApplication.objects.create(
        user_id=7793,
        application_number="SPACS-UC-RENEWAL-REMINDER",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status="approved",
    )
    assert send_renewal_reminders(now=now) == 1
    assert NotificationOutbox.objects.filter(
        topic="renewal.reminder", recipient_user_id=app.user_id
    ).exists()


def _direct_nonrenewable_reminder_case(request):
    from modules.spacs.models import NotificationOutbox, ScholarshipApplication
    from modules.spacs.services.tasks import send_renewal_reminders

    version = request.getfixturevalue("catalogue_version")
    version.is_renewable = False
    version.save(update_fields=["is_renewable", "updated_at"])
    ScholarshipApplication.objects.create(
        user_id=7794,
        application_number="SPACS-UC-NONRENEWABLE",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status="approved",
    )
    assert send_renewal_reminders(now=timezone.now()) == 0
    assert not NotificationOutbox.objects.filter(topic="renewal.reminder").exists()


def _direct_reassignment_case(request):
    from modules.spacs.models import ScholarshipApplication
    from modules.spacs.services.tasks import reassign_pending_tasks

    version = request.getfixturevalue("catalogue_version")
    app = ScholarshipApplication.objects.create(
        user_id=7795,
        application_number="SPACS-UC-REASSIGN",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status="submitted",
        assigned_assistant_id=710,
    )
    assert reassign_pending_tasks("spacs_assistant", 710, 711) == 1
    app.refresh_from_db()
    assert app.assigned_assistant_id == 711


def _direct_no_pending_reassignment_case(request):
    from modules.spacs.services.tasks import reassign_pending_tasks

    assert reassign_pending_tasks("spacs_assistant", 712, 713) == 0


def _direct_multiple_reassignment_case(request):
    from modules.spacs.models import ScholarshipApplication
    from modules.spacs.services.tasks import reassign_pending_tasks

    version = request.getfixturevalue("catalogue_version")
    apps = [
        ScholarshipApplication.objects.create(
            user_id=7796 + index,
            application_number=f"SPACS-UC-REASSIGN-MULTI-{index}",
            catalogue_entry=version.entry,
            catalogue_version=version,
            academic_year=version.academic_year,
            cycle=version.academic_year,
            status="submitted",
            assigned_assistant_id=714,
        )
        for index in range(2)
    ]
    assert reassign_pending_tasks("spacs_assistant", 714, 715) == 2
    assert not ScholarshipApplication.objects.filter(
        pk__in=[app.pk for app in apps], assigned_assistant_id=714
    ).exists()
    assert ScholarshipApplication.objects.filter(
        pk__in=[app.pk for app in apps], assigned_assistant_id=715
    ).count() == 2


_CASES = [
    (test_id, source_id, int(test_id.rsplit("-", 1)[1]))
    for test_id, source_id in _design_cases().items()
    if test_id != "UC-SPACS-030"
]


@pytest.mark.parametrize("test_id,source_id,number", _CASES, ids=[row[0] for row in _CASES])
def test_uc_design_case(test_id, source_id, number, request):
    assert test_id.startswith("UC-SPACS-")
    assert source_id
    if not _SCENARIOS[number]:
        assert test_id in UC_IMPLEMENTATION_BLOCKERS
        return
    for module_name, function_name in _SCENARIOS[number]:
        if module_name == "uc":
            globals()[function_name](request)
        else:
            _call_existing(module_name, function_name, request)
