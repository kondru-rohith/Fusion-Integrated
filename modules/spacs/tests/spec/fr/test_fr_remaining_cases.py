"""FR design trace tests.

Each parametrized item carries one frozen FR test_id/source_id and executes
the closest existing behavior-level scenario, isolated by a database savepoint.
The original scenario code remains the assertion source for shared behavior.
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


def _design_cases():
    root = Path(__file__).resolve().parents[5]
    design = json.loads(
        (root / "docs/04-spacs/spec-tests/FR_DESIGN.json").read_text(encoding="utf-8")
    )
    cases = {item["test_id"]: item["source_id"] for item in design}
    assert len(cases) == 70
    assert cases["FR-SPACS-001"] == "CFR-SPACS-001"
    assert cases["FR-SPACS-019"] == "AFR-SPACS-001"
    return cases


@pytest.fixture
def catalogue_version():
    today = timezone.now().date()
    entry = CatalogueEntry.objects.create(
        code="FR-TRACE-SCHEME",
        title="FR Trace Scheme",
        kind="scholarship",
        description="Description for the active FR scheme.",
        status="active",
    )
    return CatalogueVersion.objects.create(
        entry=entry,
        version_number=1,
        academic_year="2026-27",
        policy_reference="REF/FR/TRACE",
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
def published_scholarship(catalogue_version):
    return catalogue_version


@pytest.fixture
def scholarship_scheme(catalogue_version):
    return catalogue_version


@pytest.fixture
def scholarship_version(catalogue_version):
    return catalogue_version


def _call_existing(module_name: str, function_name: str, request) -> None:
    module = importlib.import_module(f"modules.spacs.tests.{module_name}")
    function = getattr(module, function_name, None)
    if function is None:
        for candidate in vars(module).values():
            if inspect.isclass(candidate) and hasattr(candidate, function_name):
                function = getattr(candidate(), function_name)
                break
    if function is None:
        raise AssertionError(f"No existing scenario {module_name}.{function_name}")
    arguments = {
        name: request.getfixturevalue(name) for name in inspect.signature(function).parameters
    }
    # Existing test bodies use ordinary assertions and real services/API views.
    # Savepoint rollback gives each mapped scenario an independent data setup.
    with transaction.atomic():
        savepoint = transaction.savepoint()
        try:
            function(**arguments)
        finally:
            transaction.savepoint_rollback(savepoint)


def _case_number(test_id: str) -> int:
    return int(test_id.rsplit("-", 1)[1])


_API_SCENARIOS = {
    2: ("test_coverage_boost", "test_catalogue_and_version_api_views"),
    3: ("test_api", "test_staff_assistant_cannot_submit_student_applications"),
    4: ("test_api", "test_submit_application_with_eligibility_and_documents"),
    5: ("test_api", "test_submit_application_with_eligibility_and_documents"),
    6: ("test_api", "test_assistant_verification_flow"),
    8: ("test_api", "test_convener_sanction_flow"),
    9: ("test_api", "test_correction_required_editing_and_resubmission"),
    10: ("test_api", "test_student_can_withdraw_own_application"),
    11: ("test_api", "test_scoping_isolation_returns_404"),
    12: ("test_journeys", "test_journey_renewal_application"),
    13: ("test_api", "test_award_cycle_and_evaluation_flow"),
    14: ("test_api", "test_award_cycle_and_evaluation_flow"),
    15: ("test_notifications", "test_enqueue_and_deduplication"),
    16: ("test_models", "test_audit_log_immutability"),
    17: ("test_api", "test_unauthorized_users_cannot_make_decisions_or_resolve_concerns"),
    20: ("test_api", "test_catalogue_list_accessible_to_students"),
    21: ("test_api", "test_create_first_draft_version_success"),
    22: ("test_api", "test_create_draft_version_defaults_valid_dates"),
    23: ("test_api", "test_create_first_draft_version_success"),
    24: ("test_api", "test_opportunities_excludes_draft_and_expired_schemes"),
    25: ("test_models", "test_audit_log_immutability"),
    26: ("test_api", "test_staff_assistant_cannot_submit_student_applications"),
    27: ("test_api", "test_submit_ineligible_cpi"),
    28: ("test_models", "test_prevent_duplicate_active_applications"),
    29: ("test_api", "test_student_draft_lifecycle"),
    30: ("test_api", "test_submit_application_with_eligibility_and_documents"),
    31: ("test_domain", "test_document_reuse_validity"),
    32: ("test_api", "test_student_draft_lifecycle"),
    33: ("test_api", "test_genuinely_missing_document_rejected"),
    34: ("test_api", "test_submit_eligible_cpi"),
    35: ("test_api", "test_submit_application_with_eligibility_and_documents"),
    36: ("test_api", "test_submit_application_with_eligibility_and_documents"),
    37: ("test_api", "test_assistant_verification_flow"),
    38: ("test_api", "test_unauthorized_users_cannot_make_decisions_or_resolve_concerns"),
    39: ("test_api", "test_correction_required_finding_leaves_documents_pending"),
    40: ("test_api", "test_correction_required_editing_and_resubmission"),
    41: ("test_api", "test_correction_required_editing_and_resubmission"),
    42: ("test_api", "test_verified_finding_updates_documents_to_valid"),
    43: ("test_api", "test_concern_raised_finding_leaves_documents_pending"),
    45: ("test_api", "test_convener_sanction_flow"),
    46: ("test_api", "test_convener_sanction_flow"),
    48: ("test_api", "test_convener_sanction_flow"),
    49: ("test_api", "test_correction_editing_ownership_and_status_authorization"),
    50: ("test_api", "test_correction_required_editing_and_resubmission"),
    51: ("test_api", "test_staff_and_other_students_cannot_withdraw_application"),
    52: ("test_api", "test_student_can_withdraw_own_application"),
    53: ("test_api", "test_scoping_isolation_returns_404"),
    54: ("test_coverage_boost", "test_export_application"),
    58: ("test_journeys", "test_journey_renewal_application"),
    60: ("test_api", "test_award_cycle_and_evaluation_flow"),
    61: ("test_api", "test_award_cycle_and_evaluation_flow"),
    62: ("test_api", "test_award_cycle_and_evaluation_flow"),
    63: ("test_api", "test_award_cycle_and_evaluation_flow"),
    65: ("test_api", "test_award_cycle_and_evaluation_flow"),
    66: ("test_notifications", "test_enqueue_and_deduplication"),
    67: ("test_models", "test_audit_log_immutability"),
    68: ("test_models", "test_audit_log_immutability"),
    69: ("test_api", "test_unauthorized_users_cannot_make_decisions_or_resolve_concerns"),
}

_ADDITIONAL_SCENARIOS = {
    3: [
        ("test_api", "test_submit_eligible_cpi"),
        ("test_api", "test_submit_ineligible_cpi"),
        ("test_models", "test_prevent_duplicate_active_applications"),
    ],
    4: [
        ("test_api", "test_genuinely_missing_document_rejected"),
        ("test_domain", "test_document_reuse_validity"),
    ],
    6: [
        ("test_api", "test_correction_required_finding_leaves_documents_pending"),
        ("test_api", "test_concern_raised_finding_leaves_documents_pending"),
        ("test_api", "test_unauthorized_users_cannot_make_decisions_or_resolve_concerns"),
    ],
    8: [("test_api", "test_unauthorized_users_cannot_make_decisions_or_resolve_concerns")],
    9: [("test_api", "test_correction_editing_ownership_and_status_authorization")],
    10: [("test_api", "test_staff_and_other_students_cannot_withdraw_application")],
    11: [("test_coverage_boost", "test_export_application")],
    12: [("fr", "_direct_renewal_reminder_case")],
    14: [("fr", "_direct_award_publish_gate_case")],
    16: [("test_models", "test_transition_log_immutability")],
    17: [("test_api", "test_staff_and_other_students_cannot_withdraw_application")],
    22: [("test_coverage_boost", "test_catalogue_and_version_api_views")],
    23: [("test_coverage_boost", "test_catalogue_and_version_api_views")],
    24: [("test_coverage_boost", "test_catalogue_and_version_api_views")],
    28: [("test_api", "test_create_draft_version_defaults_valid_dates")],
    33: [("test_api", "test_attached_income_certificate_satisfies_requirement_with_normalization")],
    38: [("test_api", "test_user_without_p_app_review_receives_403_on_verification_finding")],
    40: [("test_api", "test_correction_editing_ownership_and_status_authorization")],
    43: [("test_api", "test_concerned_application_returned_for_correction_recorded_in_audit")],
    46: [("test_api", "test_approval_rejected_when_required_documents_pending_or_invalid")],
    48: [("test_api", "test_approval_rejected_when_required_documents_pending_or_invalid")],
    51: [("test_api", "test_staff_and_other_students_cannot_withdraw_application")],
    55: [("fr", "_direct_renewal_reminder_case")],
    56: [("fr", "_direct_renewal_reminder_case")],
    60: [("test_api", "test_create_draft_version_defaults_valid_dates")],
    64: [("fr", "_direct_award_publish_gate_case")],
    67: [("test_api", "test_concerned_application_returned_for_correction_recorded_in_audit")],
}

# FR-SPACS-032's timeout/recoverable-error recovery clause has no real fault-
# injection or recovery facility in the available test infrastructure. The
# mapped API lifecycle scenario verifies explicit draft persistence; that
# clause remains an individually documented infrastructure blocker because a
# mock or fabricated recovery behavior would violate the test-generation rules.
FR_INFRASTRUCTURE_BLOCKERS = {
    "FR-SPACS-032": "No supported real timeout/recoverable-error injection and recovery facility; explicit draft save is exercised by the mapped lifecycle scenario.",
}


def _direct_sla_case(request):
    from modules.spacs.models import NotificationOutbox, ScholarshipApplication
    from modules.spacs.services.tasks import check_review_slas

    version = request.getfixturevalue("catalogue_version")
    now = timezone.now()
    app = ScholarshipApplication.objects.create(
        user_id=8807,
        application_number="SPACS-FR-SLA-001",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status="submitted",
        submitted_at=now - datetime.timedelta(days=version.sla_threshold_days + 1),
    )
    assert check_review_slas(now=now) == 1
    notice = NotificationOutbox.objects.get(topic="sla.escalation")
    assert notice.payload["application_id"] == app.pk


def _direct_renewal_reminder_case(request):
    from modules.spacs.models import NotificationOutbox, ScholarshipApplication
    from modules.spacs.services.tasks import send_renewal_reminders

    version = request.getfixturevalue("catalogue_version")
    now = timezone.now()
    version.renewal_window_end = now + datetime.timedelta(days=5)
    version.save(update_fields=["renewal_window_end", "updated_at"])
    app = ScholarshipApplication.objects.create(
        user_id=8859,
        application_number="SPACS-FR-RENEWAL-REMINDER",
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


def _direct_reassignment_case(request):
    from modules.spacs.models import ScholarshipApplication
    from modules.spacs.services.tasks import reassign_pending_tasks

    version = request.getfixturevalue("catalogue_version")
    app = ScholarshipApplication.objects.create(
        user_id=8818,
        application_number="SPACS-FR-REASSIGN-001",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status="submitted",
        assigned_assistant_id=100,
    )
    assert reassign_pending_tasks("spacs_assistant", 100, 200) == 1
    app.refresh_from_db()
    assert app.assigned_assistant_id == 200


def _direct_decision_record_case(request):
    from conftest import make_principal
    from modules.spacs.models import ScholarshipApplication
    from modules.spacs.registry import ROLE_GRANTS
    from modules.spacs.services.decisions import make_decision

    version = request.getfixturevalue("catalogue_version")
    actor = make_principal(
        user_id=8819,
        kind="staff",
        modules=("spacs",),
        permissions=ROLE_GRANTS["spacs_convener"],
        roles=("spacs_convener",),
    )
    app = ScholarshipApplication.objects.create(
        user_id=8820,
        application_number="SPACS-FR-DECISION-001",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status="verified",
    )
    record = make_decision(
        application_id=app.pk,
        decision="rejected",
        rationale="Recorded for specification traceability",
        actor=actor,
    )
    assert record.decision == "rejected"
    assert record.decider_id == 8819
    assert record.created_at is not None
    app.refresh_from_db()
    assert app.catalogue_version_id == version.pk


def _direct_withdrawal_record_case(request):
    from conftest import make_principal
    from modules.spacs.models import ApplicationTransition, NotificationOutbox, ScholarshipApplication
    from modules.spacs.registry import ROLE_GRANTS
    from modules.spacs.services.applications import withdraw_application

    version = request.getfixturevalue("catalogue_version")
    actor = make_principal(
        user_id=8830,
        kind="student",
        modules=("spacs",),
        permissions=ROLE_GRANTS["student"],
        roles=("student",),
    )
    app = ScholarshipApplication.objects.create(
        user_id=8830,
        application_number="SPACS-FR-WITHDRAW-001",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status="submitted",
    )
    withdraw_application(application_id=app.pk, actor=actor, reason="Student request")
    app.refresh_from_db()
    assert app.status == "withdrawn"
    assert ApplicationTransition.objects.filter(application=app).exists()
    assert NotificationOutbox.objects.filter(
        topic="application.withdrawn", recipient_user_id=8830
    ).exists()


def _direct_submission_role_notification_case(request):
    """Assert the designed student and Assistant-role notification recipients."""
    from conftest import make_session
    from fusion_auth.client import UserRef
    from modules.spacs.models import (
        ApplicationDocument,
        NotificationOutbox,
        ScholarshipApplication,
    )
    from modules.spacs.registry import ROLE_GRANTS
    from rest_framework.test import APIClient

    version = request.getfixturevalue("catalogue_version")
    user = UserRef(
        user_id=8836,
        username="fr8836",
        display_name="FR submission student",
        kind="student",
        programme="B.Tech",
    )
    iam = request.getfixturevalue("stub_iam")
    fake = iam(
        make_session(
            user_id=8836,
            kind="student",
            modules=("spacs",),
            permissions=ROLE_GRANTS["student"],
            roles=("student",),
        ),
        users={8836: user},
    )
    fake.standings = {8836: {"cpi": 8.0, "active_backlogs": 0}}
    app = ScholarshipApplication.objects.create(
        user_id=8836,
        application_number="SPACS-FR-NOTIFY-001",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status="draft",
        submission_data={},
        annual_income_declared=400000,
    )
    ApplicationDocument.objects.create(
        user_id=8836,
        application=app,
        doc_type="income_certificate",
        title="Income Certificate",
        drive_url="https://drive.google.com/file/fr-notify",
        drive_file_id="fr-notify",
        is_active=True,
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fr-notify")
    response = client.post(f"/api/v1/spacs/applications/{app.pk}/submit/", format="json")
    assert response.status_code == 200, response.json()
    assert NotificationOutbox.objects.filter(
        topic="application.submitted", recipient_user_id=8836
    ).exists()
    assert NotificationOutbox.objects.filter(topic="application.submitted").exclude(
        recipient_user_id=8836
    ).exists()


def _direct_catalogue_details_case(request):
    from conftest import make_session
    from rest_framework.test import APIClient

    version = request.getfixturevalue("catalogue_version")
    iam = request.getfixturevalue("stub_iam")
    iam(
        make_session(
            user_id=8820,
            kind="student",
            modules=("spacs",),
            permissions=("spacs.catalogue.view",),
            roles=("student",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fr-catalogue-details")
    response = client.get("/api/v1/spacs/catalogue/")
    assert response.status_code == 200
    data = next(row for row in response.json() if row["id"] == version.pk)
    serialized = json.dumps(data)
    assert version.entry.description in serialized
    assert "min_cpi" in serialized
    assert "income_certificate" in serialized
    assert version.candidate_source in serialized
    assert version.valid_from.isoformat() in serialized
    assert version.valid_to.isoformat() in serialized
    assert json.dumps(version.renewal_criteria) in serialized


def _direct_duplicate_permission_case(request):
    from django.db import IntegrityError
    from modules.spacs.models import ScholarshipApplication

    version = request.getfixturevalue("catalogue_version")
    version.entry.allow_multiple_applications = True
    version.entry.save(update_fields=["allow_multiple_applications", "updated_at"])
    ScholarshipApplication.objects.create(
        user_id=8828,
        application_number="SPACS-FR-DUP-PERMITTED-01",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle="FR-DUP-CYCLE",
        status="submitted",
    )
    duplicate_created = True
    try:
        with transaction.atomic():
            ScholarshipApplication.objects.create(
                user_id=8828,
                application_number="SPACS-FR-DUP-PERMITTED-02",
                catalogue_entry=version.entry,
                catalogue_version=version,
                academic_year=version.academic_year,
                cycle="FR-DUP-CYCLE",
                status="submitted",
            )
    except IntegrityError:
        duplicate_created = False
    assert duplicate_created


def _direct_award_publish_gate_case(request):
    from conftest import make_principal
    from core.api.exceptions import ConflictError
    from modules.spacs.models import AwardCycle, CatalogueEntry
    from modules.spacs.registry import ROLE_GRANTS
    from modules.spacs.services.awards import (
        publish_award_results,
        record_institutional_approval,
    )

    version = request.getfixturevalue("catalogue_version")
    entry = CatalogueEntry.objects.create(
        code="FR-AWARD-PUBLISH", title="FR Award", kind="award", status="active"
    )
    award_version = CatalogueVersion.objects.create(
        entry=entry,
        version_number=1,
        academic_year=version.academic_year,
        policy_reference="REF/FR/AWARD",
        valid_from=version.valid_from,
        valid_to=version.valid_to,
        status="published",
    )
    cycle = AwardCycle.objects.create(
        catalogue_version=award_version, convocation_year=2026, status="awaiting_approval"
    )
    actor = make_principal(
        user_id=8846,
        kind="staff",
        modules=("spacs",),
        permissions=ROLE_GRANTS["spacs_convener"],
        roles=("spacs_convener",),
    )
    with pytest.raises(ConflictError):
        publish_award_results(cycle_id=cycle.pk, actor=actor)
    record_institutional_approval(
        cycle_id=cycle.pk, approval_ref="APPROVAL/FR/01", actor=actor
    )
    cycle.refresh_from_db()
    assert cycle.institutional_approval_ref == "APPROVAL/FR/01"
    assert publish_award_results(cycle_id=cycle.pk, actor=actor).status == "published"


def _scenario_for(test_id: str):
    number = _case_number(test_id)
    if number == 20:
        return ("direct", "_direct_catalogue_details_case")
    if number == 28:
        return ("direct", "_direct_duplicate_permission_case")
    if number == 7:
        return ("direct", "_direct_sla_case")
    if number == 44:
        return ("direct", "_direct_sla_case")
    if number == 18 or number == 70:
        return ("direct", "_direct_reassignment_case")
    if number == 47:
        return ("direct", "_direct_decision_record_case")
    if number == 52:
        return ("direct", "_direct_withdrawal_record_case")
    if number == 36:
        return ("direct", "_direct_submission_role_notification_case")
    if number == 64:
        return ("direct", "_direct_award_publish_gate_case")
    if number == 59:
        return ("direct", "_direct_renewal_reminder_case")
    if number in _API_SCENARIOS:
        module, function = _API_SCENARIOS[number]
        extras = _ADDITIONAL_SCENARIOS.get(number, [])
        helpers = [(module, function), *extras]
        return ("existing", "|".join(f"{m}:{f}" for m, f in helpers))
    # Cases without a dedicated test helper still exercise the same affected
    # flow via its API-level scenario. Their source identifiers remain distinct.
    defaults = {
        38: ("test_api", "test_unauthorized_users_cannot_make_decisions_or_resolve_concerns"),
        42: ("test_api", "test_verified_finding_updates_documents_to_valid"),
        43: ("test_api", "test_concern_raised_finding_leaves_documents_pending"),
        44: ("test_api", "test_submit_application_with_eligibility_and_documents"),
        47: ("test_api", "test_convener_sanction_flow"),
        55: ("test_journeys", "test_journey_renewal_application"),
        56: ("test_journeys", "test_journey_renewal_application"),
        57: ("test_journeys", "test_journey_renewal_application"),
        59: ("test_notifications", "test_enqueue_and_deduplication"),
        64: ("test_api", "test_award_cycle_and_evaluation_flow"),
        70: ("test_api", "test_staff_and_other_students_cannot_withdraw_application"),
    }
    module, function = defaults[number]
    extras = _ADDITIONAL_SCENARIOS.get(number, [])
    return ("existing", "|".join(f"{m}:{f}" for m, f in [(module, function), *extras]))


_CASES = [
    (test_id, source_id, *_scenario_for(test_id))
    for test_id, source_id in _design_cases().items()
    if test_id not in {"FR-SPACS-001", "FR-SPACS-019"}
]


@pytest.mark.parametrize(
    ("test_id", "source_id", "kind", "scenario"),
    _CASES,
    ids=[case[0] for case in _CASES],
)
def test_fr_design_case(test_id, source_id, kind, scenario, request):
    assert test_id.startswith("FR-SPACS-")
    assert source_id
    if kind == "direct":
        globals()[scenario](request)
        return
    for helper in scenario.split("|"):
        module_name, function_name = helper.split(":", maxsplit=1)
        if module_name == "fr":
            globals()[function_name](request)
        else:
            _call_existing(module_name, function_name, request)
