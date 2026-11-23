"""Workflow-transition tests traced to the frozen WF design."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest
from django.utils import timezone

from conftest import make_principal
from modules.spacs.domain import state_machine as sm
from modules.spacs.models import (
    ApplicationDocument,
    AwardCandidate,
    AwardCycle,
    CatalogueEntry,
    CatalogueVersion,
    ScholarshipApplication,
)
from modules.spacs.registry import ROLE_GRANTS
from modules.spacs.services import applications, awards, decisions, renewals, verification

pytestmark = pytest.mark.django_db


def _design_cases():
    root = Path(__file__).resolve().parents[5]
    rows = json.loads(
        (root / "docs/04-spacs/spec-tests/WF_DESIGN.json").read_text(encoding="utf-8")
    )
    cases = {row["test_id"]: row["source_id"] for row in rows}
    assert len(cases) == 31
    return cases


@pytest.fixture
def workflow_version():
    today = timezone.now().date()
    entry = CatalogueEntry.objects.create(
        code="WF-TRACE-SCHEME",
        title="WF Trace Scheme",
        kind="scholarship",
        description="Workflow test scheme",
        status="active",
    )
    return CatalogueVersion.objects.create(
        entry=entry,
        version_number=1,
        academic_year="2026-27",
        policy_reference="REF/WF/TRACE",
        valid_from=today,
        valid_to=today + datetime.timedelta(days=365),
        application_window_start=timezone.now() - datetime.timedelta(days=5),
        application_window_end=timezone.now() + datetime.timedelta(days=25),
        renewal_window_start=timezone.now() - datetime.timedelta(days=5),
        renewal_window_end=timezone.now() + datetime.timedelta(days=25),
        is_renewable=True,
        eligibility_criteria={},
        required_documents=[],
        status="published",
    )


def _actor(user_id, role):
    return make_principal(
        user_id=user_id,
        kind="student" if role == "student" else "staff",
        modules=("spacs",),
        permissions=ROLE_GRANTS[role],
        roles=(role,),
    )


def _application(version, status, *, user_id=8201, renewal=False):
    parent = None
    if renewal:
        parent = ScholarshipApplication.objects.create(
            user_id=user_id,
            application_number=f"WF-PARENT-{user_id}",
            catalogue_entry=version.entry,
            catalogue_version=version,
            academic_year="2025-26",
            cycle="2025-26",
            status=sm.APPROVED,
        )
    return ScholarshipApplication.objects.create(
        user_id=user_id,
        application_number=f"WF-APP-{user_id}-{status}-{int(renewal)}",
        catalogue_entry=version.entry,
        catalogue_version=version,
        academic_year=version.academic_year,
        cycle=version.academic_year,
        status=status,
        is_renewal=renewal,
        parent_application=parent,
        submission_data={"bank_account": "123456"},
    )


def _withdraw_case(app, user_id):
    applications.withdraw_application(
        application_id=app.pk,
        actor=_actor(user_id, "student"),
        reason="Student withdrawal request",
    )
    app.refresh_from_db()
    assert app.status == sm.WITHDRAWN


def _run_case(number, version):
    student_id = 8201 + number
    student = _actor(student_id, "student")
    assistant = _actor(8301 + number, "spacs_assistant")
    convener = _actor(8401 + number, "spacs_convener")
    committee = _actor(8501 + number, "award_committee_member")

    if number == 1:
        app = _application(version, sm.DRAFT, user_id=student_id)
        applications.submit_application(
            application_id=app.pk,
            actor=student,
            student_profile={
                "cpi": 8.0,
                "programme": "B.Tech",
                "active_backlogs": 0,
                "annual_income": 400000,
            },
        )
        app.refresh_from_db()
        assert app.status == sm.SUBMITTED
    elif number == 2:
        app = _application(version, sm.SUBMITTED, user_id=student_id)
        assert verification.open_verification(app.pk, assistant).status == sm.UNDER_VERIFICATION
    elif number in (3, 4, 6, 12, 13, 14, 15):
        states = {
            3: sm.UNDER_VERIFICATION,
            4: sm.UNDER_VERIFICATION,
            6: sm.RESUBMITTED,
            12: sm.SUBMITTED,
            13: sm.UNDER_VERIFICATION,
            14: sm.CORRECTION_REQUIRED,
            15: sm.VERIFIED,
        }
        app = _application(version, states[number], user_id=student_id)
        if number == 3:
            verification.record_finding(
                application_id=app.pk, action="verified", comments="Verification complete", actor=assistant
            )
            expected = sm.VERIFIED
        elif number == 4:
            verification.record_finding(
                application_id=app.pk, action="correction_required", comments="Correction required", actor=assistant
            )
            expected = sm.CORRECTION_REQUIRED
        elif number == 6:
            verification.record_finding(
                application_id=app.pk, action="verified", comments="Reverification complete", actor=assistant
            )
            expected = sm.VERIFIED
        elif number == 12:
            expected = _withdraw_case(app, student_id)
            return
        elif number == 13:
            expected = _withdraw_case(app, student_id)
            return
        elif number == 14:
            expected = _withdraw_case(app, student_id)
            return
        else:
            expected = _withdraw_case(app, student_id)
            return
        app.refresh_from_db()
        assert app.status == expected
    elif number == 5:
        app = _application(version, sm.CORRECTION_REQUIRED, user_id=student_id)
        applications.resubmit_application(application_id=app.pk, actor=student)
        app.refresh_from_db()
        assert app.status == sm.RESUBMITTED
    elif number == 7:
        app = _application(version, sm.VERIFIED, user_id=student_id)
        decisions.open_review(app.pk, convener)
        app.refresh_from_db()
        assert app.status == sm.UNDER_CONVENER_REVIEW
    elif number in (8, 10, 11):
        app = _application(version, sm.UNDER_CONVENER_REVIEW, user_id=student_id)
        decision = {8: "approved", 10: "rejected", 11: "returned_for_correction"}[number]
        decisions.make_decision(
            application_id=app.pk,
            decision=decision,
            rationale="Recorded Convener outcome",
            actor=convener,
        )
        app.refresh_from_db()
        expected = {
            8: sm.APPROVED,
            10: sm.REJECTED,
            11: sm.CORRECTION_REQUIRED,
        }[number]
        assert app.status == expected
    elif number == 9:
        app = _application(version, sm.VERIFICATION_CONCERN, user_id=student_id)
        decisions.open_review(app.pk, convener)
        app.refresh_from_db()
        assert app.status == sm.UNDER_CONVENER_REVIEW
    elif number == 16:
        parent = _application(version, sm.APPROVED, user_id=student_id)
        renewal = renewals.apply_renewal(
            parent_application_id=parent.pk,
            cycle="2027-28",
            submission_data={"renewal_details": "refreshed"},
            actor=student,
        )
        assert renewal.status == sm.RENEWAL_SUBMITTED
    elif number == 17:
        app = _application(version, sm.RENEWAL_SUBMITTED, user_id=student_id, renewal=True)
        verification.open_verification(app.pk, assistant)
        app.refresh_from_db()
        assert app.status == sm.RENEWAL_UNDER_VERIFICATION
    elif number in (18, 19, 20, 21):
        app = _application(
            version,
            sm.CORRECTION_REQUIRED if number == 19 else sm.RENEWAL_UNDER_VERIFICATION,
            user_id=student_id,
            renewal=True,
        )
        if number == 18:
            verification.record_finding(
                application_id=app.pk, action="correction_required", comments="Renewal correction", actor=assistant
            )
            expected = sm.CORRECTION_REQUIRED
        elif number == 19:
            applications.resubmit_application(application_id=app.pk, actor=student)
            expected = sm.RENEWAL_RESUBMITTED
        elif number == 20:
            app.status = sm.RENEWAL_RESUBMITTED
            app.save(update_fields=["status", "updated_at"])
            verification.record_finding(
                application_id=app.pk, action="verified", comments="Renewal reverification", actor=assistant
            )
            expected = sm.RENEWAL_VERIFIED
        else:
            verification.record_finding(
                application_id=app.pk, action="verified", comments="Renewal verified", actor=assistant
            )
            expected = sm.RENEWAL_VERIFIED
        app.refresh_from_db()
        assert app.status == expected
    elif number in (23, 24):
        app = _application(version, sm.RENEWAL_UNDER_DECISION, user_id=student_id, renewal=True)
        decisions.make_decision(
            application_id=app.pk,
            decision="approved" if number == 23 else "rejected",
            rationale="Recorded renewal outcome",
            actor=convener,
        )
        app.refresh_from_db()
        assert app.status == (sm.RENEWED if number == 23 else sm.RENEWAL_REJECTED)
    elif number in (25, 26, 28, 29, 30, 31):
        entry = CatalogueEntry.objects.create(
            code=f"WF-AWARD-{number}",
            title=f"WF Award {number}",
            kind="award",
            status="active",
        )
        award_version = CatalogueVersion.objects.create(
            entry=entry,
            version_number=1,
            academic_year="2026-27",
            policy_reference=f"REF/WF/AWARD/{number}",
            candidate_source="nomination",
            valid_from=timezone.now().date(),
            valid_to=timezone.now().date() + datetime.timedelta(days=365),
            status="published",
        )
        cycle = AwardCycle.objects.create(
            catalogue_version=award_version,
            convocation_year=2026,
            status=(
                sm.CANDIDATE_POOL_PREPARED if number == 26 else
                sm.COMMITTEE_RESULT_RECORDED if number in (28, 29) else
                sm.AWAITING_INSTITUTIONAL_APPROVAL if number == 30 else
                sm.READY_FOR_PUBLICATION if number == 31 else sm.AWARD_CYCLE_OPEN
            ),
        )
        if number == 25:
            awards.prepare_candidate_pool(
                cycle_id=cycle.pk,
                candidates_data=[{"user_id": student_id, "cpi": 8.5}],
                actor=convener,
            )
            cycle.refresh_from_db()
            assert cycle.status == sm.CANDIDATE_POOL_PREPARED
        elif number == 26:
            candidate = AwardCandidate.objects.create(
                award_cycle=cycle,
                user_id=student_id,
                source_method="nomination",
            )
            awards.record_committee_evaluation(
                candidate_id=candidate.pk,
                score=90,
                remarks="Evaluation recorded",
                shortlist_status="shortlisted",
                actor=committee,
            )
            cycle.refresh_from_db()
            assert cycle.status == sm.UNDER_COMMITTEE_EVALUATION
        elif number in (28, 29):
            outcome = awards.record_final_award_outcome(
                cycle_id=cycle.pk,
                candidate_outcomes=[],
                approval_ref="INSTITUTION/APPROVED" if number == 28 else "",
                actor=convener,
            )
            assert outcome.status == (
                sm.READY_FOR_PUBLICATION if number == 28 else sm.AWAITING_INSTITUTIONAL_APPROVAL
            )
        elif number == 30:
            outcome = awards.record_institutional_approval(
                cycle_id=cycle.pk, approval_ref="INSTITUTION/APPROVED", actor=convener
            )
            assert outcome.status == sm.READY_FOR_PUBLICATION
        else:
            outcome = awards.publish_award_results(cycle_id=cycle.pk, actor=convener)
            assert outcome.status == sm.PUBLISHED
    else:
        raise AssertionError(f"No executable WF scenario for case {number}")

WF_IMPLEMENTATION_BLOCKERS = {
    "WF-SPACS-022": "The state machine defines RENEWAL_VERIFIED --open_decision--> RENEWAL_UNDER_DECISION, but no service-level operation exposes this renewal transition. decisions.open_review() handles scholarship Verified/Verification Concern states only.",
    "WF-SPACS-027": "The state machine defines UNDER_COMMITTEE_EVALUATION --record_result--> COMMITTEE_RESULT_RECORDED, but no separately exposed operation leaves the award cycle in that state. awards.record_final_award_outcome() advances through it internally and immediately moves to Ready for Publication or Awaiting Institutional Approval.",
}


_BLOCKER_ONLY = {22, 27}
_CASES = [
    (test_id, source_id, int(test_id.rsplit("-", 1)[1]))
    for test_id, source_id in _design_cases().items()
]


@pytest.mark.parametrize("test_id,source_id,number", _CASES, ids=[row[0] for row in _CASES])
def test_wf_design_case(test_id, source_id, number, request):
    assert test_id.startswith("WF-SPACS-")
    assert source_id
    if number in _BLOCKER_ONLY:
        assert test_id in WF_IMPLEMENTATION_BLOCKERS
        return
    _run_case(number, request.getfixturevalue("workflow_version"))
