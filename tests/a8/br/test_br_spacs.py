"""Automated business rule tests for SPACS module (BR_DESIGN).

Generated strictly according to BR_DESIGN.json test cases: TC-SPACS-001A through TC-SPACS-023.
"""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.spacs.models import ScholarshipApplication, SupportingDocument
from modules.spacs.permissions import (
    ASSISTANT_ROLE,
    CONVENER_ROLE,
    P_APPLICATION_APPROVE,
    P_APPLICATION_CREATE,
    P_APPLICATION_REVIEW,
    P_APPLICATION_UPDATE,
    P_APPLICATION_VIEW,
    P_APPLICATION_VIEW_SELF,
    P_APPLICATION_WITHDRAW,
    STUDENT_ROLE,
)

pytestmark = pytest.mark.django_db


def _make_student_client(stub_iam, user_id=1001, permissions=None):
    if permissions is None:
        permissions = (
            P_APPLICATION_CREATE,
            P_APPLICATION_VIEW_SELF,
            P_APPLICATION_UPDATE,
            P_APPLICATION_WITHDRAW,
        )
    stub_iam(
        make_session(
            user_id=user_id,
            kind="student",
            roles=(STUDENT_ROLE,),
            active_role=STUDENT_ROLE,
            permissions=permissions,
            modules=("spacs",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token token-student-{user_id}")
    return client


def _make_assistant_client(stub_iam, user_id=2001, permissions=None):
    if permissions is None:
        permissions = (
            P_APPLICATION_REVIEW,
        )
    stub_iam(
        make_session(
            user_id=user_id,
            kind="staff",
            roles=(ASSISTANT_ROLE,),
            active_role=ASSISTANT_ROLE,
            permissions=permissions,
            modules=("spacs",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token token-assistant-{user_id}")
    return client


def _make_convener_client(stub_iam, user_id=3001, permissions=None):
    if permissions is None:
        permissions = (
            P_APPLICATION_VIEW,
            P_APPLICATION_APPROVE,
        )
    stub_iam(
        make_session(
            user_id=user_id,
            kind="staff",
            roles=(CONVENER_ROLE,),
            active_role=CONVENER_ROLE,
            permissions=permissions,
            modules=("spacs",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token token-convener-{user_id}")
    return client


# ---------------------------------------------------------------------------
# Test Cases from BR_DESIGN.json
# ---------------------------------------------------------------------------

def test_tc_spacs_001a_br_spacs_001_eligibility_satisfied(stub_iam):
    """
    test_id: TC-SPACS-001A
    source_id: BR-SPACS-001-eligibility-satisfied
    purpose: Verify that submission proceeds when mandatory eligibility criteria are satisfied.
    """
    client = _make_student_client(stub_iam, user_id=1001)
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_ELIGIBLE",
        student_id=1001,
        status=ScholarshipApplication.STATUS_DRAFT,
        documents_list=["doc_valid_01"],
    )
    resp = client.post(f"/api/v1/spacs/applications/{app.application_id}/submit/")
    assert resp.status_code == 200
    app.refresh_from_db()
    assert app.status == ScholarshipApplication.STATUS_SUBMITTED
    assert app.submission_date is not None


def test_tc_spacs_001b_br_spacs_001_eligibility_failed():
    """
    test_id: TC-SPACS-001B
    source_id: BR-SPACS-001-eligibility-failed
    purpose: (
        "Verify that submission is blocked when mandatory eligibility criteria "
        "are not satisfied and no exception applies."
    )
    """
    pytest.skip(
        "NOT_AUTOMATED: Machine-checkable eligibility verification on submission is "
        "not implemented in A8_BASE."
    )


def test_tc_spacs_002a_br_spacs_002_duplicate_rejected():
    """
    test_id: TC-SPACS-002A
    source_id: BR-SPACS-002-duplicate-rejected
    purpose: (
        "Verify that a duplicate active/submitted application is rejected when the "
        "scheme does not permit duplicates."
    )
    """
    pytest.skip(
        "NOT_AUTOMATED: Duplicate application validation across academic cycles is "
        "not implemented in A8_BASE."
    )


def test_tc_spacs_002b_br_spacs_002_duplicate_permitted():
    """
    test_id: TC-SPACS-002B
    source_id: BR-SPACS-002-duplicate-permitted
    purpose: Verify that a duplicate application is allowed when the scheme explicitly permits it.
    """
    pytest.skip(
        "NOT_AUTOMATED: Scheme duplicate-permission configuration is not implemented in A8_BASE."
    )


def test_tc_spacs_003a_br_spacs_003_reuse_valid_document():
    """
    test_id: TC-SPACS-003A
    source_id: BR-SPACS-003-reuse-valid-document
    purpose: Verify that a previously uploaded document can be reused when valid and matching.
    """
    pytest.skip(
        "NOT_AUTOMATED: Document reuse eligibility filtering endpoint is not "
        "implemented in A8_BASE."
    )


def test_tc_spacs_003b_br_spacs_003_reuse_invalid_document():
    """
    test_id: TC-SPACS-003B
    source_id: BR-SPACS-003-reuse-invalid-document
    purpose: Verify that an invalid or mismatched document cannot be reused.
    """
    pytest.skip(
        "NOT_AUTOMATED: Document validity verification and reuse restriction are "
        "not implemented in A8_BASE."
    )


def test_tc_spacs_004a_br_spacs_004_complete_submission(stub_iam):
    """
    test_id: TC-SPACS-004A
    source_id: BR-SPACS-004-complete-submission
    purpose: Verify that a complete application is accepted for submission.
    """
    client = _make_student_client(stub_iam, user_id=1001)
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_COMPLETE",
        student_id=1001,
        status=ScholarshipApplication.STATUS_DRAFT,
        documents_list=["doc_complete_01"],
    )
    resp = client.post(f"/api/v1/spacs/applications/{app.application_id}/submit/")
    assert resp.status_code == 200
    app.refresh_from_db()
    assert app.status == ScholarshipApplication.STATUS_SUBMITTED


def test_tc_spacs_004b_br_spacs_004_incomplete_blocked():
    """
    test_id: TC-SPACS-004B
    source_id: BR-SPACS-004-incomplete-blocked
    purpose: Verify that an incomplete application is blocked from submission.
    """
    pytest.skip(
        "NOT_AUTOMATED: Incomplete application submission validation is not implemented in A8_BASE."
    )


def test_tc_spacs_005a_br_spacs_005_authorized_review_access(stub_iam):
    """
    test_id: TC-SPACS-005A
    source_id: BR-SPACS-005-authorized-review-access
    purpose: (
        "Verify that an authorized SPACS Assistant or Convener can access "
        "applications for review."
    )
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_REVIEW_005",
        student_id=1001,
        status=ScholarshipApplication.STATUS_SUBMITTED,
        assigned_assistant_user_id=2001,
        documents_list=["doc_evidence_005"],
    )
    # Authorized Assistant
    asst_client = _make_assistant_client(stub_iam, user_id=2001)
    asst_resp = asst_client.get(f"/api/v1/spacs/applications/{app.application_id}/")
    assert asst_resp.status_code == 200
    assert asst_resp.json()["documents_list"] == ["doc_evidence_005"]

    # Authorized Convener
    conv_client = _make_convener_client(stub_iam, user_id=3001)
    conv_resp = conv_client.get(f"/api/v1/spacs/applications/{app.application_id}/")
    assert conv_resp.status_code == 200


def test_tc_spacs_005b_br_spacs_005_unauthorized_review_access(stub_iam):
    """
    test_id: TC-SPACS-005B
    source_id: BR-SPACS-005-unauthorized-review-access
    purpose: Verify that an unauthorized user is denied access to application review.
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_DENY_005",
        student_id=1001,
        status=ScholarshipApplication.STATUS_SUBMITTED,
        assigned_assistant_user_id=2002,  # assigned to 2002
    )
    # Unassigned assistant 2001 attempts review
    asst1_client = _make_assistant_client(stub_iam, user_id=2001)
    resp = asst1_client.get(f"/api/v1/spacs/applications/{app.application_id}/")
    assert resp.status_code in (403, 404)


def test_tc_spacs_006a_br_spacs_006_assistant_verification_concern(stub_iam):
    """
    test_id: TC-SPACS-006A
    source_id: BR-SPACS-006-assistant-verification-concern
    purpose: (
        "Verify that an Assistant can record a verification concern and route "
        "it to the Convener."
    )
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_CONCERN_006",
        student_id=1001,
        status=ScholarshipApplication.STATUS_SUBMITTED,
        assigned_assistant_user_id=2001,
    )
    asst_client = _make_assistant_client(stub_iam, user_id=2001)
    concern = {"evidence": "Suspected invalid income document"}
    verify_resp = asst_client.post(
        f"/api/v1/spacs/applications/{app.application_id}/verify/",
        {
            "verification_status": ScholarshipApplication.VERIFICATION_ISSUES_FOUND,
            "verification_findings": concern,
        },
        format="json",
    )
    assert verify_resp.status_code == 200
    app.refresh_from_db()
    assert app.verification_status == ScholarshipApplication.VERIFICATION_ISSUES_FOUND
    assert app.verification_findings == concern

    # Routed to Convener for final decision
    conv_client = _make_convener_client(stub_iam, user_id=3001)
    conv_resp = conv_client.get(f"/api/v1/spacs/applications/{app.application_id}/")
    assert conv_resp.status_code == 200
    assert conv_resp.json()["verification_findings"] == concern


def test_tc_spacs_006b_br_spacs_006_assistant_final_decision_denied(stub_iam):
    """
    test_id: TC-SPACS-006B
    source_id: BR-SPACS-006-assistant-final-decision-denied
    purpose: Verify that an Assistant cannot make the final scholarship approval/rejection decision.
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_DECISION_DENIED_006",
        student_id=1001,
        status=ScholarshipApplication.STATUS_UNDER_VERIFICATION,
        assigned_assistant_user_id=2001,
    )
    asst_client = _make_assistant_client(stub_iam, user_id=2001)

    appr_resp = asst_client.post(
        f"/api/v1/spacs/applications/{app.application_id}/approve/",
        {"decision_note": "Attempted approval"},
        format="json",
    )
    assert appr_resp.status_code == 403

    rej_resp = asst_client.post(
        f"/api/v1/spacs/applications/{app.application_id}/reject/",
        {"decision_note": "Attempted rejection"},
        format="json",
    )
    assert rej_resp.status_code == 403


def test_tc_spacs_007_br_spacs_007_draft_preservation_timeout(stub_iam):
    """
    test_id: TC-SPACS-007
    source_id: BR-SPACS-007-draft-preservation-timeout
    purpose: (
        "Verify that a recoverable application draft is preserved on a "
        "recoverable timeout or system error."
    )
    """
    client = _make_student_client(stub_iam, user_id=1001)
    resp = client.post(
        "/api/v1/spacs/applications/",
        {"scheme_id": "SCHEME_TIMEOUT_007", "documents_list": ["doc_007"]},
        format="json",
    )
    assert resp.status_code == 201
    app_id = resp.json()["application_id"]

    # Student resumes after simulated session interruption
    resumed_client = _make_student_client(stub_iam, user_id=1001)
    get_resp = resumed_client.get(f"/api/v1/spacs/applications/{app_id}/")
    assert get_resp.status_code == 200
    assert get_resp.json()["scheme_id"] == "SCHEME_TIMEOUT_007"
    assert get_resp.json()["documents_list"] == ["doc_007"]
    assert get_resp.json()["status"] == ScholarshipApplication.STATUS_DRAFT


def test_tc_spacs_008_br_spacs_008_notification_on_status_change():
    """
    test_id: TC-SPACS-008
    source_id: BR-SPACS-008-notification-on-status-change
    purpose: Verify that notifications are issued for significant lifecycle events.
    """
    pytest.skip(
        "NOT_AUTOMATED: Notification dispatch for lifecycle events is not implemented in A8_BASE."
    )


def test_tc_spacs_009a_br_spacs_009_withdrawal_before_decision():
    """
    test_id: TC-SPACS-009A
    source_id: BR-SPACS-009-withdrawal-before-decision
    purpose: Verify that a student can withdraw their application before a final decision.
    """
    pytest.skip(
        "NOT_AUTOMATED: Task closing, audit logging, and notification on withdrawal "
        "are not implemented in A8_BASE."
    )


def test_tc_spacs_009b_br_spacs_009_withdrawal_after_decision_denied(stub_iam):
    """
    test_id: TC-SPACS-009B
    source_id: BR-SPACS-009-withdrawal-after-decision-denied
    purpose: Verify that a student cannot withdraw their application after a final decision.
    """
    client = _make_student_client(stub_iam, user_id=1001)

    # Approved state
    app_approved = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_WITHDRAW_009",
        student_id=1001,
        status=ScholarshipApplication.STATUS_APPROVED,
    )
    resp_appr_del = client.delete(f"/api/v1/spacs/applications/{app_approved.application_id}/")
    assert resp_appr_del.status_code == 403

    resp_appr_patch = client.patch(
        f"/api/v1/spacs/applications/{app_approved.application_id}/",
        {"status": ScholarshipApplication.STATUS_WITHDRAWN},
        format="json",
    )
    assert resp_appr_patch.status_code == 403

    # Rejected state
    app_rejected = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_WITHDRAW_009",
        student_id=1001,
        status=ScholarshipApplication.STATUS_REJECTED,
    )
    resp_rej_del = client.delete(f"/api/v1/spacs/applications/{app_rejected.application_id}/")
    assert resp_rej_del.status_code == 403


def test_tc_spacs_010a_br_spacs_010_owner_modification(stub_iam):
    """
    test_id: TC-SPACS-010A
    source_id: BR-SPACS-010-owner-modification
    purpose: Verify that the owning student can modify their application.
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_MODIFY_010",
        student_id=1001,
        status=ScholarshipApplication.STATUS_DRAFT,
        documents_list=["doc_orig"],
    )
    client = _make_student_client(stub_iam, user_id=1001)
    resp = client.patch(
        f"/api/v1/spacs/applications/{app.application_id}/",
        {"documents_list": ["doc_updated"]},
        format="json",
    )
    assert resp.status_code == 200
    app.refresh_from_db()
    assert app.documents_list == ["doc_updated"]


def test_tc_spacs_010b_br_spacs_010_non_owner_modification_denied(stub_iam):
    """
    test_id: TC-SPACS-010B
    source_id: BR-SPACS-010-non-owner-modification-denied
    purpose: (
        "Verify that a non-owner is denied modification of an application via the "
        "student interface."
    )
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_MODIFY_010",
        student_id=1001,
        status=ScholarshipApplication.STATUS_DRAFT,
    )
    other_student = _make_student_client(stub_iam, user_id=2002)
    resp = other_student.patch(
        f"/api/v1/spacs/applications/{app.application_id}/",
        {"documents_list": ["doc_unauthorized"]},
        format="json",
    )
    assert resp.status_code in (403, 404)


def test_tc_spacs_011_br_spacs_011_correction_invalidates_verification():
    """
    test_id: TC-SPACS-011
    source_id: BR-SPACS-011-correction-invalidates-verification
    purpose: (
        "Verify that a correction/resubmission invalidates previous verification/routing "
        "information."
    )
    """
    pytest.skip(
        "NOT_AUTOMATED: Automatic invalidation of previous verification upon resubmission "
        "is not implemented in A8_BASE."
    )


def test_tc_spacs_012a_br_spacs_012_student_export_own():
    """
    test_id: TC-SPACS-012A
    source_id: BR-SPACS-012-student-export-own
    purpose: Verify that a student can export their own application.
    """
    pytest.skip(
        "NOT_AUTOMATED: Application export/download/print endpoint is not implemented in A8_BASE."
    )


def test_tc_spacs_012b_br_spacs_012_student_export_other_denied():
    """
    test_id: TC-SPACS-012B
    source_id: BR-SPACS-012-student-export-other-denied
    purpose: Verify that a student is denied export of another student's application.
    """
    pytest.skip(
        "NOT_AUTOMATED: Application export endpoint is not implemented in A8_BASE."
    )


def test_tc_spacs_013_br_spacs_013_sla_escalation_triggered():
    """
    test_id: TC-SPACS-013
    source_id: BR-SPACS-013-sla-escalation-triggered
    purpose: (
        "Verify that SLA reminders or escalations are triggered when task age "
        "reaches the threshold."
    )
    """
    pytest.skip(
        "NOT_AUTOMATED: SLA monitoring and escalation service is not implemented in A8_BASE."
    )


def test_tc_spacs_014_br_spacs_014_active_catalogue_version_used():
    """
    test_id: TC-SPACS-014
    source_id: BR-SPACS-014-active-catalogue-version-used
    purpose: (
        "Verify that applications use the published/active catalogue-policy version "
        "effective for the cycle."
    )
    """
    pytest.skip(
        "NOT_AUTOMATED: Catalogue-policy version binding is not implemented in A8_BASE."
    )


def test_tc_spacs_015_br_spacs_015_catalogue_publication_blocked():
    """
    test_id: TC-SPACS-015
    source_id: BR-SPACS-015-catalogue-publication-blocked
    purpose: (
        "Verify that catalogue publication is blocked without required policy "
        "approval metadata."
    )
    """
    pytest.skip(
        "NOT_AUTOMATED: Catalogue publication approval validation interface is not "
        "implemented in A8_BASE."
    )


def test_tc_spacs_016a_br_spacs_016_authenticity_recorded_by_reviewer():
    """
    test_id: TC-SPACS-016A
    source_id: BR-SPACS-016-authenticity-recorded-by-reviewer
    purpose: Verify that document authenticity is recorded by an authorized reviewer.
    """
    pytest.skip(
        "NOT_AUTOMATED: Substantive document authenticity verification recording is not "
        "implemented in A8_BASE."
    )


def test_tc_spacs_016b_br_spacs_016_upload_alone_not_authenticated(stub_iam):
    """
    test_id: TC-SPACS-016B
    source_id: BR-SPACS-016-upload-alone-not-authenticated
    purpose: Verify that document upload alone is not treated as authenticated evidence.
    """
    client = _make_student_client(stub_iam, user_id=1001)
    doc_resp = client.post(
        "/api/v1/spacs/documents/",
        {
            "document_type": "income_cert",
            "file_url": "https://storage.example.com/unverified.pdf",
            "is_reusable": True,
        },
        format="json",
    )
    assert doc_resp.status_code == 201
    doc_id = doc_resp.json()["document_id"]

    doc = SupportingDocument.objects.get(document_id=doc_id)
    # Upload alone defaults to pending validity, not valid/authenticated
    assert doc.validity_status == SupportingDocument.VALIDITY_PENDING


def test_tc_spacs_017_br_spacs_017_renewal_fresh_decision():
    """
    test_id: TC-SPACS-017
    source_id: BR-SPACS-017-renewal-fresh-decision
    purpose: Verify that a renewal undergoes fresh verification and decision.
    """
    pytest.skip(
        "NOT_AUTOMATED: Scholarship renewal workflow is not implemented in A8_BASE."
    )


def test_tc_spacs_018a_br_spacs_018_convener_final_approval(stub_iam):
    """
    test_id: TC-SPACS-018A
    source_id: BR-SPACS-018-convener-final-approval
    purpose: Verify that the SPACS Convener can make the final scholarship approval.
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_APPROVAL_018",
        student_id=1001,
        status=ScholarshipApplication.STATUS_UNDER_VERIFICATION,
        verification_status=ScholarshipApplication.VERIFICATION_VERIFIED,
    )
    conv_client = _make_convener_client(stub_iam, user_id=3001)
    resp = conv_client.post(
        f"/api/v1/spacs/applications/{app.application_id}/approve/",
        {"decision_note": "Final sanction approved."},
        format="json",
    )
    assert resp.status_code == 200
    app.refresh_from_db()
    assert app.status == ScholarshipApplication.STATUS_APPROVED
    assert app.decided_by_user_id == 3001
    assert app.decision_note == "Final sanction approved."


def test_tc_spacs_018b_br_spacs_018_assistant_final_approval_denied(stub_iam):
    """
    test_id: TC-SPACS-018B
    source_id: BR-SPACS-018-assistant-final-approval-denied
    purpose: Verify that the SPACS Assistant cannot make the final scholarship approval.
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_APPROVAL_018",
        student_id=1001,
        status=ScholarshipApplication.STATUS_UNDER_VERIFICATION,
        assigned_assistant_user_id=2001,
    )
    asst_client = _make_assistant_client(stub_iam, user_id=2001)
    resp = asst_client.post(
        f"/api/v1/spacs/applications/{app.application_id}/approve/",
        {"decision_note": "Attempt by assistant"},
        format="json",
    )
    assert resp.status_code == 403


def test_tc_spacs_019_br_spacs_019_award_evaluation_follows_policy():
    """
    test_id: TC-SPACS-019
    source_id: BR-SPACS-019-award-evaluation-follows-policy
    purpose: (
        "Verify that award evaluation and approval follow the committee/authority "
        "defined by the active award policy."
    )
    """
    pytest.skip(
        "NOT_AUTOMATED: Award evaluation committee workflow is not implemented in A8_BASE."
    )


def test_tc_spacs_020_br_spacs_020_award_criteria_versioning():
    """
    test_id: TC-SPACS-020
    source_id: BR-SPACS-020-award-criteria-versioning
    purpose: (
        "Verify that candidate generation and evaluation use the award criteria version "
        "effective for the cycle."
    )
    """
    pytest.skip(
        "NOT_AUTOMATED: Award criteria versioning interface is not implemented in A8_BASE."
    )


def test_tc_spacs_021_br_spacs_021_audit_records_protected():
    """
    test_id: TC-SPACS-021
    source_id: BR-SPACS-021-audit-records-protected
    purpose: (
        "Verify that significant actions are audit logged and protected from "
        "ordinary modification."
    )
    """
    pytest.skip(
        "NOT_AUTOMATED: SPACS audit logging and log protection are not implemented in A8_BASE."
    )


def test_tc_spacs_022_br_spacs_022_role_reassignment_preserves_history():
    """
    test_id: TC-SPACS-022
    source_id: BR-SPACS-022-role-reassignment-preserves-history
    purpose: (
        "Verify that role reassignment routes pending tasks but preserves "
        "historical actor identity."
    )
    """
    pytest.skip(
        "NOT_AUTOMATED: Role reassignment and task routing workflow is not implemented in A8_BASE."
    )


def test_tc_spacs_023_br_spacs_023_award_candidate_source_configured():
    """
    test_id: TC-SPACS-023
    source_id: BR-SPACS-023-award-candidate-source-configured
    purpose: (
        "Verify that an award cycle obtains candidates using the method configured "
        "by the active award policy."
    )
    """
    pytest.skip(
        "NOT_AUTOMATED: Award cycle candidate generation is not implemented in A8_BASE."
    )
