"""Automated functional requirement tests for SPACS module (FR_DESIGN).

Generated strictly according to FR_DESIGN.json test cases: TC_SPACS_001 to TC_SPACS_052.
"""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.spacs.models import ScholarshipApplication
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
        permissions = (P_APPLICATION_REVIEW,)
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
# Test Cases TC_SPACS_001 to TC_SPACS_052
# ---------------------------------------------------------------------------


def test_tc_spacs_001_afr_spacs_001():
    """
    test_id: TC_SPACS_001
    source_id: AFR-SPACS-001
    purpose: Verify authenticated users can browse published catalogue entries and unpublished
        entries are hidden.
    """
    pytest.skip(
        "NOT_AUTOMATED: Catalogue browsing interface and models are not implemented in A8_BASE."
    )


def test_tc_spacs_002_afr_spacs_002():
    """
    test_id: TC_SPACS_002
    source_id: AFR-SPACS-002
    purpose: Verify system displays all required details for a published catalogue entry.
    """
    pytest.skip(
        "NOT_AUTOMATED: Catalogue entry detail interface and models are not "
        "implemented in A8_BASE."
    )


def test_tc_spacs_003_afr_spacs_003():
    """
    test_id: TC_SPACS_003
    source_id: AFR-SPACS-003
    purpose: Verify SPACS Convener can create a new draft catalogue entry.
    """
    pytest.skip(
        "NOT_AUTOMATED: Catalogue entry creation interface and models are not "
        "implemented in A8_BASE."
    )


def test_tc_spacs_004_afr_spacs_004():
    """
    test_id: TC_SPACS_004
    source_id: AFR-SPACS-004
    purpose: Verify Convener can modify a draft without altering historical versions used by
        existing applications.
    """
    pytest.skip(
        "NOT_AUTOMATED: Catalogue versioning and modification interface is not "
        "implemented in A8_BASE."
    )


def test_tc_spacs_005_afr_spacs_005():
    """
    test_id: TC_SPACS_005
    source_id: AFR-SPACS-005
    purpose: Verify system blocks publication of a catalogue version if policy-approval
        reference or effective dates are missing.
    """
    pytest.skip(
        "NOT_AUTOMATED: Catalogue publication validation interface is not implemented in A8_BASE."
    )


def test_tc_spacs_006_afr_spacs_006():
    """
    test_id: TC_SPACS_006
    source_id: AFR-SPACS-006
    purpose: Verify Convener can retire a catalogue entry prospectively while preserving
        historical applications.
    """
    pytest.skip("NOT_AUTOMATED: Catalogue retirement interface is not implemented in A8_BASE.")


def test_tc_spacs_007_afr_spacs_007():
    """
    test_id: TC_SPACS_007
    source_id: AFR-SPACS-007
    purpose: Verify system preserves an auditable version history of catalogue criteria and
        publication status.
    """
    pytest.skip(
        "NOT_AUTOMATED: Catalogue version history interface is not implemented in "
        "A8_BASE."
    )


def test_tc_spacs_008_afr_spacs_008():
    """
    test_id: TC_SPACS_008
    source_id: AFR-SPACS-008
    purpose: Verify system blocks a student from starting an application if the scheme's
        application window is closed.
    """
    pytest.skip(
        "NOT_AUTOMATED: Scholarship scheme application window checking is not "
        "implemented in A8_BASE."
    )


def test_tc_spacs_009_afr_spacs_009():
    """
    test_id: TC_SPACS_009
    source_id: AFR-SPACS-009
    purpose: Verify system blocks submission if machine-checkable eligibility criteria are not
        satisfied.
    """
    pytest.skip(
        "NOT_AUTOMATED: Machine-checkable eligibility verification on submission is "
        "not implemented in A8_BASE."
    )


def test_tc_spacs_010_afr_spacs_010():
    """
    test_id: TC_SPACS_010
    source_id: AFR-SPACS-010
    purpose: Verify system prevents duplicate active/submitted applications for the same
        student, scholarship, and cycle.
    """
    pytest.skip(
        "NOT_AUTOMATED: Duplicate application validation across academic cycles is "
        "not implemented in A8_BASE."
    )


def test_tc_spacs_011_afr_spacs_011(stub_iam):
    """
    test_id: TC_SPACS_011
    source_id: AFR-SPACS-011
    purpose: Verify student can enter all application data required by the selected
        scholarship version.
    """
    client = _make_student_client(stub_iam, user_id=1001)
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_MERIT_2026",
        student_id=1001,
        status=ScholarshipApplication.STATUS_DRAFT,
        documents_list=[],
    )
    payload = {
        "scheme_id": "SCHEME_MERIT_2026",
        "documents_list": ["doc_income_cert", "doc_marksheet"],
    }
    response = client.patch(
        f"/api/v1/spacs/applications/{app.application_id}/",
        payload,
        format="json",
    )
    assert response.status_code == 200
    app.refresh_from_db()
    assert app.documents_list == ["doc_income_cert", "doc_marksheet"]
    assert response.json()["documents_list"] == ["doc_income_cert", "doc_marksheet"]


def test_tc_spacs_012_afr_spacs_012(stub_iam):
    """
    test_id: TC_SPACS_012
    source_id: AFR-SPACS-012
    purpose: Verify student can upload supporting documents required by the scholarship.
    """
    client = _make_student_client(stub_iam, user_id=1001)
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_MERIT_2026",
        student_id=1001,
        status=ScholarshipApplication.STATUS_DRAFT,
        documents_list=[],
    )
    doc_payload = {
        "document_type": "income_certificate",
        "file_url": "https://storage.example.com/docs/income_1001.pdf",
        "is_reusable": True,
    }
    doc_resp = client.post("/api/v1/spacs/documents/", doc_payload, format="json")
    assert doc_resp.status_code == 201
    doc_id = doc_resp.json()["document_id"]

    patch_resp = client.patch(
        f"/api/v1/spacs/applications/{app.application_id}/",
        {"documents_list": [doc_id]},
        format="json",
    )
    assert patch_resp.status_code == 200
    app.refresh_from_db()
    assert doc_id in app.documents_list


def test_tc_spacs_013_afr_spacs_013():
    """
    test_id: TC_SPACS_013
    source_id: AFR-SPACS-013
    purpose: Verify system offers previously uploaded documents for reuse only when they are
        still valid and satisfy requirements.
    """
    pytest.skip(
        "NOT_AUTOMATED: Document reuse eligibility filtering endpoint is not "
        "implemented in A8_BASE."
    )


def test_tc_spacs_014_afr_spacs_014(stub_iam):
    """
    test_id: TC_SPACS_014
    source_id: AFR-SPACS-014
    purpose: Verify system allows explicit draft saving and preserves input on recoverable
        timeout/error.
    """
    client = _make_student_client(stub_iam, user_id=1001)
    create_payload = {
        "scheme_id": "SCHEME_DRAFT_2026",
        "documents_list": ["doc_draft_01"],
    }
    resp = client.post("/api/v1/spacs/applications/", create_payload, format="json")
    assert resp.status_code == 201
    app_id = resp.json()["application_id"]

    # Simulating resume after recoverable interruption: re-fetch saved draft
    client_resumed = _make_student_client(stub_iam, user_id=1001)
    get_resp = client_resumed.get(f"/api/v1/spacs/applications/{app_id}/")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["scheme_id"] == "SCHEME_DRAFT_2026"
    assert data["documents_list"] == ["doc_draft_01"]
    assert data["status"] == ScholarshipApplication.STATUS_DRAFT


def test_tc_spacs_015_afr_spacs_015():
    """
    test_id: TC_SPACS_015
    source_id: AFR-SPACS-015
    purpose: Verify system blocks submission if mandatory fields or required documents are missing.
    """
    pytest.skip(
        "NOT_AUTOMATED: Mandatory field and required document submission validation "
        "is not implemented in A8_BASE."
    )


def test_tc_spacs_016_afr_spacs_016():
    """
    test_id: TC_SPACS_016
    source_id: AFR-SPACS-016
    purpose: Verify system assigns unique ID, timestamp, and policy version on successful
        submission.
    """
    pytest.skip(
        "NOT_AUTOMATED: Policy version binding on application submission is not "
        "implemented in A8_BASE."
    )


def test_tc_spacs_017_afr_spacs_017():
    """
    test_id: TC_SPACS_017
    source_id: AFR-SPACS-017
    purpose: Verify system changes state to Submitted and routes verification task to SPACS
        Assistant on submission.
    """
    pytest.skip(
        "NOT_AUTOMATED: Verification task creation and routing to SPACS Assistant "
        "is not implemented in A8_BASE."
    )


def test_tc_spacs_018_afr_spacs_018():
    """
    test_id: TC_SPACS_018
    source_id: AFR-SPACS-018
    purpose: Verify system notifies student and SPACS Assistant upon successful submission.
    """
    pytest.skip(
        "NOT_AUTOMATED: Submission notifications to student and SPACS Assistant are "
        "not implemented in A8_BASE."
    )


def test_tc_spacs_019_afr_spacs_019(stub_iam):
    """
    test_id: TC_SPACS_019
    source_id: AFR-SPACS-019
    purpose: Verify authorized SPACS Assistant can access assigned applications and evidence.
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_MERIT_2026",
        student_id=1001,
        status=ScholarshipApplication.STATUS_SUBMITTED,
        assigned_assistant_user_id=2001,
        documents_list=["doc_evidence_verified_01"],
    )
    client = _make_assistant_client(stub_iam, user_id=2001)
    resp = client.get(f"/api/v1/spacs/applications/{app.application_id}/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["application_id"] == str(app.application_id)
    assert data["documents_list"] == ["doc_evidence_verified_01"]
    assert data["assigned_assistant_user_id"] == 2001


def test_tc_spacs_020_afr_spacs_020(stub_iam):
    """
    test_id: TC_SPACS_020
    source_id: AFR-SPACS-020
    purpose: Verify SPACS Assistant can record verification findings without granting final
        sanction authority.
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_MERIT_2026",
        student_id=1001,
        status=ScholarshipApplication.STATUS_SUBMITTED,
        assigned_assistant_user_id=2001,
        documents_list=["doc_evidence_01"],
    )
    client = _make_assistant_client(stub_iam, user_id=2001)
    verify_payload = {
        "verification_status": ScholarshipApplication.VERIFICATION_VERIFIED,
        "verification_findings": {
            "completeness": "all documents present",
            "eligibility": "cpi criteria met",
        },
    }
    verify_resp = client.post(
        f"/api/v1/spacs/applications/{app.application_id}/verify/",
        verify_payload,
        format="json",
    )
    assert verify_resp.status_code == 200
    app.refresh_from_db()
    assert app.verification_status == ScholarshipApplication.VERIFICATION_VERIFIED
    assert app.verification_findings == verify_payload["verification_findings"]
    assert app.verified_by_user_id == 2001

    # Assistant does not have final sanction authority (approve/reject blocked)
    approve_resp = client.post(
        f"/api/v1/spacs/applications/{app.application_id}/approve/",
        {"decision_note": "Approved by assistant"},
        format="json",
    )
    assert approve_resp.status_code == 403

    reject_resp = client.post(
        f"/api/v1/spacs/applications/{app.application_id}/reject/",
        {"decision_note": "Rejected by assistant"},
        format="json",
    )
    assert reject_resp.status_code == 403


def test_tc_spacs_021_afr_spacs_021():
    """
    test_id: TC_SPACS_021
    source_id: AFR-SPACS-021
    purpose: Verify SPACS Assistant can return an application to the student for correction
        with a recorded reason.
    """
    pytest.skip(
        "NOT_AUTOMATED: Returning application for correction by SPACS Assistant and "
        "notification are not implemented in A8_BASE."
    )


def test_tc_spacs_022_afr_spacs_022(stub_iam):
    """
    test_id: TC_SPACS_022
    source_id: AFR-SPACS-022
    purpose: Verify student can modify and resubmit an application in Correction Required state.
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_MERIT_2026",
        student_id=1001,
        status=ScholarshipApplication.STATUS_CORRECTION_REQUIRED,
        documents_list=["doc_old"],
    )
    client = _make_student_client(stub_iam, user_id=1001)
    update_payload = {
        "documents_list": ["doc_corrected_01"],
        "status": ScholarshipApplication.STATUS_SUBMITTED,
    }
    resp = client.patch(
        f"/api/v1/spacs/applications/{app.application_id}/",
        update_payload,
        format="json",
    )
    assert resp.status_code == 200
    app.refresh_from_db()
    assert app.documents_list == ["doc_corrected_01"]
    assert app.status == ScholarshipApplication.STATUS_SUBMITTED


def test_tc_spacs_023_afr_spacs_023():
    """
    test_id: TC_SPACS_023
    source_id: AFR-SPACS-023
    purpose: Verify system revalidates a corrected resubmission and invalidates prior
        verification if applicable.
    """
    pytest.skip(
        "NOT_AUTOMATED: Automatic revalidation and verification invalidation on "
        "resubmission is not implemented in A8_BASE."
    )


def test_tc_spacs_024_afr_spacs_024(stub_iam):
    """
    test_id: TC_SPACS_024
    source_id: AFR-SPACS-024
    purpose: Verify SPACS Assistant can mark an application Verified and route it to the SPACS
        Convener.
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_MERIT_2026",
        student_id=1001,
        status=ScholarshipApplication.STATUS_SUBMITTED,
        assigned_assistant_user_id=2001,
    )
    asst_client = _make_assistant_client(stub_iam, user_id=2001)
    verify_resp = asst_client.post(
        f"/api/v1/spacs/applications/{app.application_id}/verify/",
        {
            "verification_status": ScholarshipApplication.VERIFICATION_VERIFIED,
            "verification_findings": {"all_verified": True},
        },
        format="json",
    )
    assert verify_resp.status_code == 200
    app.refresh_from_db()
    assert app.verification_status == ScholarshipApplication.VERIFICATION_VERIFIED
    assert app.status == ScholarshipApplication.STATUS_UNDER_VERIFICATION

    # Accessible to Convener for decision
    convener_client = _make_convener_client(stub_iam, user_id=3001)
    conv_get = convener_client.get(f"/api/v1/spacs/applications/{app.application_id}/")
    assert conv_get.status_code == 200
    assert conv_get.json()["verification_status"] == ScholarshipApplication.VERIFICATION_VERIFIED


def test_tc_spacs_025_afr_spacs_025(stub_iam):
    """
    test_id: TC_SPACS_025
    source_id: AFR-SPACS-025
    purpose: Verify SPACS Assistant can record an unresolved verification concern and route it
        appropriately.
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_MERIT_2026",
        student_id=1001,
        status=ScholarshipApplication.STATUS_SUBMITTED,
        assigned_assistant_user_id=2001,
    )
    asst_client = _make_assistant_client(stub_iam, user_id=2001)
    concern_findings = {"concern": "Income certificate validity unclear; suspected ineligibility"}
    verify_resp = asst_client.post(
        f"/api/v1/spacs/applications/{app.application_id}/verify/",
        {
            "verification_status": ScholarshipApplication.VERIFICATION_ISSUES_FOUND,
            "verification_findings": concern_findings,
        },
        format="json",
    )
    assert verify_resp.status_code == 200
    app.refresh_from_db()
    assert app.verification_status == ScholarshipApplication.VERIFICATION_ISSUES_FOUND
    assert app.verification_findings == concern_findings

    convener_client = _make_convener_client(stub_iam, user_id=3001)
    conv_get = convener_client.get(f"/api/v1/spacs/applications/{app.application_id}/")
    assert conv_get.status_code == 200
    assert conv_get.json()["verification_findings"] == concern_findings


def test_tc_spacs_026_afr_spacs_026():
    """
    test_id: TC_SPACS_026
    source_id: AFR-SPACS-026
    purpose: Verify system issues reminders/escalations when verification or decision tasks
        exceed SLA thresholds.
    """
    pytest.skip(
        "NOT_AUTOMATED: SLA monitoring job and threshold escalation are not "
        "implemented in A8_BASE."
    )


def test_tc_spacs_027_afr_spacs_027():
    """
    test_id: TC_SPACS_027
    source_id: AFR-SPACS-027
    purpose: Verify SPACS Convener can review applications routed for decision with
        verification and policy context.
    """
    pytest.skip(
        "NOT_AUTOMATED: Policy context display for Convener review is not implemented in A8_BASE."
    )


def test_tc_spacs_028_afr_spacs_028(stub_iam):
    """
    test_id: TC_SPACS_028
    source_id: AFR-SPACS-028
    purpose: Verify SPACS Convener can approve, reject, or return a scholarship application
        for correction.
    """
    convener_client = _make_convener_client(stub_iam, user_id=3001)

    # 1. Approve
    app_to_approve = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_MERIT_2026",
        student_id=1001,
        status=ScholarshipApplication.STATUS_UNDER_VERIFICATION,
        verification_status=ScholarshipApplication.VERIFICATION_VERIFIED,
    )
    resp_approve = convener_client.post(
        f"/api/v1/spacs/applications/{app_to_approve.application_id}/approve/",
        {"decision_note": "Meets all criteria; approved."},
        format="json",
    )
    assert resp_approve.status_code == 200
    app_to_approve.refresh_from_db()
    assert app_to_approve.status == ScholarshipApplication.STATUS_APPROVED
    assert app_to_approve.decided_by_user_id == 3001
    assert app_to_approve.decision_note == "Meets all criteria; approved."

    # 2. Reject
    app_to_reject = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_MERIT_2026",
        student_id=1002,
        status=ScholarshipApplication.STATUS_UNDER_VERIFICATION,
        verification_status=ScholarshipApplication.VERIFICATION_ISSUES_FOUND,
    )
    resp_reject = convener_client.post(
        f"/api/v1/spacs/applications/{app_to_reject.application_id}/reject/",
        {"decision_note": "Ineligible based on criteria."},
        format="json",
    )
    assert resp_reject.status_code == 200
    app_to_reject.refresh_from_db()
    assert app_to_reject.status == ScholarshipApplication.STATUS_REJECTED
    assert app_to_reject.decided_by_user_id == 3001

    # 3. Return for correction
    app_to_correct = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_MERIT_2026",
        student_id=1003,
        status=ScholarshipApplication.STATUS_UNDER_VERIFICATION,
    )
    resp_correct = convener_client.post(
        f"/api/v1/spacs/applications/{app_to_correct.application_id}/return_for_correction/",
        {"decision_note": "Please submit renewed income certificate."},
        format="json",
    )
    assert resp_correct.status_code == 200
    app_to_correct.refresh_from_db()
    assert app_to_correct.status == ScholarshipApplication.STATUS_CORRECTION_REQUIRED
    assert app_to_correct.decided_by_user_id == 3001


def test_tc_spacs_029_afr_spacs_029():
    """
    test_id: TC_SPACS_029
    source_id: AFR-SPACS-029
    purpose: Verify system records decision outcome, actor, timestamp, policy version, and reason.
    """
    pytest.skip(
        "NOT_AUTOMATED: Applicable policy version persistence on application "
        "decision is not implemented in A8_BASE."
    )


def test_tc_spacs_030_afr_spacs_030():
    """
    test_id: TC_SPACS_030
    source_id: AFR-SPACS-030
    purpose: Verify system updates application state and notifies student of the decision outcome.
    """
    pytest.skip(
        "NOT_AUTOMATED: Student decision outcome notification is not implemented in A8_BASE."
    )


def test_tc_spacs_031_afr_spacs_031(stub_iam):
    """
    test_id: TC_SPACS_031
    source_id: AFR-SPACS-031
    purpose: Verify system blocks student from modifying an application in a non-editable
        lifecycle state.
    """
    client = _make_student_client(stub_iam, user_id=1001)

    # Approved state
    app_approved = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_MERIT_2026",
        student_id=1001,
        status=ScholarshipApplication.STATUS_APPROVED,
        documents_list=["doc1"],
    )
    resp_appr = client.patch(
        f"/api/v1/spacs/applications/{app_approved.application_id}/",
        {"documents_list": ["doc1", "doc2"]},
        format="json",
    )
    assert resp_appr.status_code == 403

    # Rejected state
    app_rejected = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_MERIT_2026",
        student_id=1001,
        status=ScholarshipApplication.STATUS_REJECTED,
        documents_list=["doc1"],
    )
    resp_rej = client.patch(
        f"/api/v1/spacs/applications/{app_rejected.application_id}/",
        {"documents_list": ["doc1", "doc2"]},
        format="json",
    )
    assert resp_rej.status_code == 403


def test_tc_spacs_032_afr_spacs_032():
    """
    test_id: TC_SPACS_032
    source_id: AFR-SPACS-032
    purpose: Verify system revalidates and reroutes/reverifies an application after a
        permitted modification that invalidates prior processing.
    """
    pytest.skip(
        "NOT_AUTOMATED: Revalidation and rerouting workflow after application "
        "modification is not implemented in A8_BASE."
    )


def test_tc_spacs_033_afr_spacs_033(stub_iam):
    """
    test_id: TC_SPACS_033
    source_id: AFR-SPACS-033
    purpose: Verify system blocks student from withdrawing an application after a final
        decision is made.
    """
    client = _make_student_client(stub_iam, user_id=1001)
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_MERIT_2026",
        student_id=1001,
        status=ScholarshipApplication.STATUS_APPROVED,
    )
    # Attempt via DELETE
    resp_del = client.delete(f"/api/v1/spacs/applications/{app.application_id}/")
    assert resp_del.status_code == 403

    # Attempt via PATCH status withdrawn
    resp_patch = client.patch(
        f"/api/v1/spacs/applications/{app.application_id}/",
        {"status": ScholarshipApplication.STATUS_WITHDRAWN},
        format="json",
    )
    assert resp_patch.status_code == 403
    app.refresh_from_db()
    assert app.status == ScholarshipApplication.STATUS_APPROVED


def test_tc_spacs_034_afr_spacs_034():
    """
    test_id: TC_SPACS_034
    source_id: AFR-SPACS-034
    purpose: Verify system records withdrawal, closes tasks, sets state to Withdrawn, retains
        audit history, and notifies parties.
    """
    pytest.skip(
        "NOT_AUTOMATED: Task closing, audit logging, and party notification upon "
        "withdrawal are not implemented in A8_BASE."
    )


def test_tc_spacs_035_afr_spacs_035(stub_iam):
    """
    test_id: TC_SPACS_035
    source_id: AFR-SPACS-035
    purpose: Verify student can view current state and relevant status history of their own
        applications.
    """
    client = _make_student_client(stub_iam, user_id=1001)
    app1 = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_A",
        student_id=1001,
        status=ScholarshipApplication.STATUS_DRAFT,
    )
    app2 = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_B",
        student_id=1001,
        status=ScholarshipApplication.STATUS_SUBMITTED,
    )
    ScholarshipApplication.objects.create(
        scheme_id="SCHEME_C",
        student_id=1002,
        status=ScholarshipApplication.STATUS_SUBMITTED,
    )
    resp = client.get("/api/v1/spacs/applications/")
    assert resp.status_code == 200
    data = resp.json()
    results = data["results"] if isinstance(data, dict) and "results" in data else data
    app_ids = [r["application_id"] for r in results]
    assert str(app1.application_id) in app_ids
    assert str(app2.application_id) in app_ids
    assert len(results) == 2
    for item in results:
        assert item["student_id"] == 1001
        assert "status" in item
        assert "created_at" in item


def test_tc_spacs_036_afr_spacs_036():
    """
    test_id: TC_SPACS_036
    source_id: AFR-SPACS-036
    purpose: Verify staff export is restricted to authorized roles and denied for unauthorized
        staff.
    """
    pytest.skip("NOT_AUTOMATED: Staff application export endpoint is not implemented in A8_BASE.")


def test_tc_spacs_037_afr_spacs_037():
    """
    test_id: TC_SPACS_037
    source_id: AFR-SPACS-037
    purpose: Verify system identifies an awarded scholarship as renewal-eligible only when
        policy and window permit.
    """
    pytest.skip(
        "NOT_AUTOMATED: Scholarship renewal eligibility evaluation is not implemented in A8_BASE."
    )


def test_tc_spacs_038_afr_spacs_038():
    """
    test_id: TC_SPACS_038
    source_id: AFR-SPACS-038
    purpose: Verify student can start a renewal application with prefilled reusable data and
        identified refreshed evidence.
    """
    pytest.skip(
        "NOT_AUTOMATED: Renewal application prefilling workflow is not implemented in A8_BASE."
    )


def test_tc_spacs_039_afr_spacs_039():
    """
    test_id: TC_SPACS_039
    source_id: AFR-SPACS-039
    purpose: Verify system validates renewal-specific eligibility and updated evidence
        according to active policy.
    """
    pytest.skip(
        "NOT_AUTOMATED: Renewal-specific eligibility and evidence validation is not "
        "implemented in A8_BASE."
    )


def test_tc_spacs_040_afr_spacs_040():
    """
    test_id: TC_SPACS_040
    source_id: AFR-SPACS-040
    purpose: Verify system routes a submitted renewal through verification and fresh decision
        rather than auto-approving.
    """
    pytest.skip(
        "NOT_AUTOMATED: Renewal submission and routing workflow is not implemented in A8_BASE."
    )


def test_tc_spacs_041_afr_spacs_041():
    """
    test_id: TC_SPACS_041
    source_id: AFR-SPACS-041
    purpose: Verify system sends configured renewal reminders to eligible students before the
        deadline.
    """
    pytest.skip("NOT_AUTOMATED: Renewal reminder notification job is not implemented in A8_BASE.")


def test_tc_spacs_042_afr_spacs_042():
    """
    test_id: TC_SPACS_042
    source_id: AFR-SPACS-042
    purpose: Verify system supports the configured candidate-source method for an activated
        award scheme.
    """
    pytest.skip(
        "NOT_AUTOMATED: Award cycle candidate-source mechanism is not implemented in A8_BASE."
    )


def test_tc_spacs_043_afr_spacs_043():
    """
    test_id: TC_SPACS_043
    source_id: AFR-SPACS-043
    purpose: Verify SPACS Convener can prepare and finalize the candidate pool using policy
        and authoritative data.
    """
    pytest.skip(
        "NOT_AUTOMATED: Award candidate pool finalization interface is not implemented in A8_BASE."
    )


def test_tc_spacs_044_afr_spacs_044():
    """
    test_id: TC_SPACS_044
    source_id: AFR-SPACS-044
    purpose: Verify authorized Award Evaluation Committee members can access candidate info
        and record evaluations.
    """
    pytest.skip(
        "NOT_AUTOMATED: Award evaluation committee interface and evaluation "
        "recording are not implemented in A8_BASE."
    )


def test_tc_spacs_045_afr_spacs_045():
    """
    test_id: TC_SPACS_045
    source_id: AFR-SPACS-045
    purpose: Verify system records final award approval/decision outcome and approving
        authority/reference.
    """
    pytest.skip(
        "NOT_AUTOMATED: Final award approval recording interface is not implemented in A8_BASE."
    )


def test_tc_spacs_046_afr_spacs_046():
    """
    test_id: TC_SPACS_046
    source_id: AFR-SPACS-046
    purpose: Verify system blocks publication of award results before the required final
        approval is recorded.
    """
    pytest.skip(
        "NOT_AUTOMATED: Award results publication interface is not implemented in "
        "A8_BASE."
    )


def test_tc_spacs_047_afr_spacs_047():
    """
    test_id: TC_SPACS_047
    source_id: AFR-SPACS-047
    purpose: Verify system preserves candidate list, evaluation records, recommendations, and
        publication history.
    """
    pytest.skip(
        "NOT_AUTOMATED: Preserved award cycle history interface is not implemented in A8_BASE."
    )


def test_tc_spacs_048_afr_spacs_048():
    """
    test_id: TC_SPACS_048
    source_id: AFR-SPACS-048
    purpose: Verify system sends configured email and in-dashboard notifications for
        significant lifecycle events.
    """
    pytest.skip(
        "NOT_AUTOMATED: Email and in-dashboard notifications for lifecycle events "
        "are not implemented in A8_BASE."
    )


def test_tc_spacs_049_afr_spacs_049():
    """
    test_id: TC_SPACS_049
    source_id: AFR-SPACS-049
    purpose: Verify system creates time-stamped audit records for significant SPACS actions.
    """
    pytest.skip(
        "NOT_AUTOMATED: Time-stamped audit record logging for SPACS actions is not "
        "implemented in A8_BASE."
    )


def test_tc_spacs_050_afr_spacs_050():
    """
    test_id: TC_SPACS_050
    source_id: AFR-SPACS-050
    purpose: Verify system protects audit records from ordinary modification and restricts
        access to authorized personnel.
    """
    pytest.skip(
        "NOT_AUTOMATED: Audit log protection and access control interface is not "
        "implemented in A8_BASE."
    )


def test_tc_spacs_051_afr_spacs_051(stub_iam):
    """
    test_id: TC_SPACS_051
    source_id: AFR-SPACS-051
    purpose: Verify system enforces role- and ownership-based access to protected functions.
    """
    # 1. Assistant attempting to verify an application assigned to another assistant
    app_asst2 = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_MERIT_2026",
        student_id=1001,
        status=ScholarshipApplication.STATUS_SUBMITTED,
        assigned_assistant_user_id=2002,
    )
    asst1_client = _make_assistant_client(stub_iam, user_id=2001)
    resp_unassigned = asst1_client.post(
        f"/api/v1/spacs/applications/{app_asst2.application_id}/verify/",
        {
            "verification_status": ScholarshipApplication.VERIFICATION_VERIFIED,
            "verification_findings": {"test": "ok"},
        },
        format="json",
    )
    assert resp_unassigned.status_code in (403, 404)

    # 2. Student attempting to verify an application
    student_client = _make_student_client(stub_iam, user_id=1001)
    resp_student_verify = student_client.post(
        f"/api/v1/spacs/applications/{app_asst2.application_id}/verify/",
        {"verification_status": "verified", "verification_findings": {}},
        format="json",
    )
    assert resp_student_verify.status_code == 403

    # 3. Assistant attempting to approve an application (Convener function)
    resp_asst_approve = asst1_client.post(
        f"/api/v1/spacs/applications/{app_asst2.application_id}/approve/",
        {"decision_note": "attempt"},
        format="json",
    )
    assert resp_asst_approve.status_code == 403


def test_tc_spacs_052_afr_spacs_052():
    """
    test_id: TC_SPACS_052
    source_id: AFR-SPACS-052
    purpose: Verify system routes uncompleted tasks to the new role holder on reassignment
        while preserving historical actor identity.
    """
    pytest.skip(
        "NOT_AUTOMATED: Role reassignment and task routing workflow is not implemented in A8_BASE."
    )
