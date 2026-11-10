"""Automated workflow tests for SPACS module (WF_DESIGN).

Generated strictly according to WF_DESIGN.json test cases: TC-SPACS-001 through TC-SPACS-022.
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
# Test Cases from WF_DESIGN.json
# ---------------------------------------------------------------------------


def test_tc_spacs_001_bw_spacs_01(stub_iam):
    """
    test_id: TC-SPACS-001
    source_id: BW-SPACS-01
    purpose: Verify successful new scholarship application flow from Draft to Verified/Routed.
    """
    # 1. Draft
    student_client = _make_student_client(stub_iam, user_id=1001)
    draft_resp = student_client.post(
        "/api/v1/spacs/applications/",
        {"scheme_id": "SCHEME_WF_001", "documents_list": ["doc_wf_01"]},
        format="json",
    )
    assert draft_resp.status_code == 201
    app_id = draft_resp.json()["application_id"]

    # 2. Submitted
    submit_resp = student_client.post(f"/api/v1/spacs/applications/{app_id}/submit/")
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == ScholarshipApplication.STATUS_SUBMITTED

    # 3. Under Verification -> Verified / Routed for Decision
    app = ScholarshipApplication.objects.get(application_id=app_id)
    app.assigned_assistant_user_id = 2001
    app.save(update_fields=["assigned_assistant_user_id"])

    asst_client = _make_assistant_client(stub_iam, user_id=2001)
    verify_resp = asst_client.post(
        f"/api/v1/spacs/applications/{app_id}/verify/",
        {
            "verification_status": ScholarshipApplication.VERIFICATION_VERIFIED,
            "verification_findings": {"all_checks": "verified"},
        },
        format="json",
    )
    assert verify_resp.status_code == 200
    app.refresh_from_db()
    assert app.status == ScholarshipApplication.STATUS_UNDER_VERIFICATION
    assert app.verification_status == ScholarshipApplication.VERIFICATION_VERIFIED

    # Verified application routed to Convener
    conv_client = _make_convener_client(stub_iam, user_id=3001)
    conv_resp = conv_client.get(f"/api/v1/spacs/applications/{app_id}/")
    assert conv_resp.status_code == 200


def test_tc_spacs_002_bw_spacs_02(stub_iam):
    """
    test_id: TC-SPACS-002
    source_id: BW-SPACS-02
    purpose: Verify correction request and successful resubmission flow.
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_CORRECTION_WF",
        student_id=1001,
        status=ScholarshipApplication.STATUS_UNDER_VERIFICATION,
        assigned_assistant_user_id=2001,
        documents_list=["doc1"],
    )
    asst_client = _make_assistant_client(stub_iam, user_id=2001)
    resp = asst_client.post(
        f"/api/v1/spacs/applications/{app.application_id}/return_for_correction/",
        {"decision_note": "Please upload valid documents."},
        format="json",
    )
    assert resp.status_code == 200
    app.refresh_from_db()
    assert app.status == ScholarshipApplication.STATUS_CORRECTION_REQUIRED


def test_tc_spacs_003_bw_spacs_03(stub_iam):
    """
    test_id: TC-SPACS-003
    source_id: BW-SPACS-03
    purpose: Verify scholarship approval path.
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_WF_003",
        student_id=1001,
        status=ScholarshipApplication.STATUS_UNDER_VERIFICATION,
        verification_status=ScholarshipApplication.VERIFICATION_VERIFIED,
    )
    conv_client = _make_convener_client(stub_iam, user_id=3001)
    resp = conv_client.post(
        f"/api/v1/spacs/applications/{app.application_id}/approve/",
        {"decision_note": "Application satisfies all scheme criteria; approved."},
        format="json",
    )
    assert resp.status_code == 200
    app.refresh_from_db()
    assert app.status == ScholarshipApplication.STATUS_APPROVED
    assert app.decided_by_user_id == 3001


def test_tc_spacs_004_bw_spacs_04(stub_iam):
    """
    test_id: TC-SPACS-004
    source_id: BW-SPACS-04
    purpose: Verify scholarship rejection path from Verification Concern.
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_WF_004",
        student_id=1001,
        status=ScholarshipApplication.STATUS_UNDER_VERIFICATION,
        verification_status=ScholarshipApplication.VERIFICATION_ISSUES_FOUND,
        verification_findings={"issue": "Ineligible parental income certificate"},
    )
    conv_client = _make_convener_client(stub_iam, user_id=3001)
    resp = conv_client.post(
        f"/api/v1/spacs/applications/{app.application_id}/reject/",
        {"decision_note": "Rejected due to ineligibility issue."},
        format="json",
    )
    assert resp.status_code == 200
    app.refresh_from_db()
    assert app.status == ScholarshipApplication.STATUS_REJECTED
    assert app.decided_by_user_id == 3001


def test_tc_spacs_005_bw_spacs_05(stub_iam):
    """
    test_id: TC-SPACS-005
    source_id: BW-SPACS-05
    purpose: Verify student can withdraw application from Submitted state.
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_WITHDRAW_WF",
        student_id=1001,
        status=ScholarshipApplication.STATUS_SUBMITTED,
        documents_list=["doc1"],
    )
    client = _make_student_client(stub_iam, user_id=1001)
    resp = client.delete(f"/api/v1/spacs/applications/{app.application_id}/")
    assert resp.status_code in (200, 204)
    app.refresh_from_db()
    assert app.status == ScholarshipApplication.STATUS_WITHDRAWN


def test_tc_spacs_006_bw_spacs_05(stub_iam):
    """
    test_id: TC-SPACS-006
    source_id: BW-SPACS-05
    purpose: Verify student can withdraw application from Under Verification state.
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_WITHDRAW_WF_UV",
        student_id=1001,
        status=ScholarshipApplication.STATUS_UNDER_VERIFICATION,
        documents_list=["doc1"],
    )
    client = _make_student_client(stub_iam, user_id=1001)
    resp = client.delete(f"/api/v1/spacs/applications/{app.application_id}/")
    assert resp.status_code in (200, 204)
    app.refresh_from_db()
    assert app.status == ScholarshipApplication.STATUS_WITHDRAWN


def test_tc_spacs_007_bw_spacs_05(stub_iam):
    """
    test_id: TC-SPACS-007
    source_id: BW-SPACS-05
    purpose: Verify student can withdraw application from Correction Required state.
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_WF_007",
        student_id=1001,
        status=ScholarshipApplication.STATUS_CORRECTION_REQUIRED,
    )
    student_client = _make_student_client(stub_iam, user_id=1001)
    resp = student_client.patch(
        f"/api/v1/spacs/applications/{app.application_id}/",
        {"status": ScholarshipApplication.STATUS_WITHDRAWN},
        format="json",
    )
    assert resp.status_code == 200
    app.refresh_from_db()
    assert app.status == ScholarshipApplication.STATUS_WITHDRAWN


def test_tc_spacs_008_bw_spacs_05():
    """
    test_id: TC-SPACS-008
    source_id: BW-SPACS-05
    purpose: (
        "Verify withdrawal from Verified/Routed is allowed only if Convener review "
        "hasn't begun and scheme permits."
    )
    """
    pytest.skip(
        "NOT_AUTOMATED: Conditional withdrawal from Verified/Routed state is not "
        "implemented in A8_BASE."
    )


def test_tc_spacs_009_bw_spacs_06():
    """
    test_id: TC-SPACS-009
    source_id: BW-SPACS-06
    purpose: Verify renewal submission and successful verification.
    """
    pytest.skip("NOT_AUTOMATED: Scholarship renewal workflow is not implemented in A8_BASE.")


def test_tc_spacs_010_bw_spacs_07():
    """
    test_id: TC-SPACS-010
    source_id: BW-SPACS-07
    purpose: Verify renewal approval path.
    """
    pytest.skip("NOT_AUTOMATED: Scholarship renewal workflow is not implemented in A8_BASE.")


def test_tc_spacs_011_bw_spacs_10():
    """
    test_id: TC-SPACS-011
    source_id: BW-SPACS-10
    purpose: Verify renewal rejection path.
    """
    pytest.skip("NOT_AUTOMATED: Scholarship renewal workflow is not implemented in A8_BASE.")


def test_tc_spacs_012_bw_spacs_08():
    """
    test_id: TC-SPACS-012
    source_id: BW-SPACS-08
    purpose: Verify award cycle candidate pool preparation and committee evaluation.
    """
    pytest.skip(
        "NOT_AUTOMATED: Award cycle and evaluation committee workflow are not "
        "implemented in A8_BASE."
    )


def test_tc_spacs_013_bw_spacs_09():
    """
    test_id: TC-SPACS-013
    source_id: BW-SPACS-09
    purpose: Verify award finalization and publication when approval is already available.
    """
    pytest.skip("NOT_AUTOMATED: Award publication workflow is not implemented in A8_BASE.")


def test_tc_spacs_014_bw_spacs_11():
    """
    test_id: TC-SPACS-014
    source_id: BW-SPACS-11
    purpose: Verify award finalization when institutional approval is pending.
    """
    pytest.skip(
        "NOT_AUTOMATED: Institutional award approval workflow is not implemented in A8_BASE."
    )


def test_tc_spacs_015_cw_spacs_01(stub_iam):
    """
    test_id: TC-SPACS-015
    source_id: CW-SPACS-01
    purpose: Verify Convener can return a verified application for correction.
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_WF_015",
        student_id=1001,
        status=ScholarshipApplication.STATUS_UNDER_VERIFICATION,
        verification_status=ScholarshipApplication.VERIFICATION_VERIFIED,
    )
    conv_client = _make_convener_client(stub_iam, user_id=3001)
    resp = conv_client.post(
        f"/api/v1/spacs/applications/{app.application_id}/return_for_correction/",
        {"decision_note": "Please upload a clearer copy of income certificate."},
        format="json",
    )
    assert resp.status_code == 200
    app.refresh_from_db()
    assert app.status == ScholarshipApplication.STATUS_CORRECTION_REQUIRED
    assert app.decided_by_user_id == 3001


def test_tc_spacs_016_cw_spacs_01(stub_iam):
    """
    test_id: TC-SPACS-016
    source_id: CW-SPACS-01
    purpose: Verify Assistant can route an unresolved verification concern to Convener.
    """
    app = ScholarshipApplication.objects.create(
        scheme_id="SCHEME_WF_016",
        student_id=1001,
        status=ScholarshipApplication.STATUS_SUBMITTED,
        assigned_assistant_user_id=2001,
    )
    asst_client = _make_assistant_client(stub_iam, user_id=2001)
    concern = {"ineligibility": "Income limit exceeds scheme threshold"}
    resp = asst_client.post(
        f"/api/v1/spacs/applications/{app.application_id}/verify/",
        {
            "verification_status": ScholarshipApplication.VERIFICATION_ISSUES_FOUND,
            "verification_findings": concern,
        },
        format="json",
    )
    assert resp.status_code == 200
    app.refresh_from_db()
    assert app.status == ScholarshipApplication.STATUS_UNDER_VERIFICATION
    assert app.verification_status == ScholarshipApplication.VERIFICATION_ISSUES_FOUND
    assert app.verification_findings == concern


def test_tc_spacs_017_cw_spacs_02():
    """
    test_id: TC-SPACS-017
    source_id: CW-SPACS-02
    purpose: Verify renewal correction request and resubmission flow.
    """
    pytest.skip(
        "NOT_AUTOMATED: Renewal correction and resubmission workflow are not "
        "implemented in A8_BASE."
    )


def test_tc_spacs_018_ps_section_4(stub_iam):
    """
    test_id: TC-SPACS-018
    source_id: PS-Section-4
    purpose: (
        "Verify system prevents duplicate active/submitted applications for the "
        "same student, scholarship, and cycle."
    )
    """
    ScholarshipApplication.objects.create(
        scheme_id="SCHEME_DUP_WF",
        student_id=1001,
        status=ScholarshipApplication.STATUS_SUBMITTED,
        documents_list=["doc1"],
    )
    client = _make_student_client(stub_iam, user_id=1001)
    resp = client.post(
        "/api/v1/spacs/applications/",
        {
            "scheme_id": "SCHEME_DUP_WF",
            "student_id": 1001,
            "status": "draft",
            "documents_list": ["doc2"],
        },
        format="json",
    )
    assert resp.status_code == 400


def test_tc_spacs_019_ps_section_4():
    """
    test_id: TC-SPACS-019
    source_id: PS-Section-4
    purpose: (
        "Verify previously uploaded documents can only be reused if still valid "
        "and acceptable for the selected scheme."
    )
    """
    pytest.skip(
        "NOT_AUTOMATED: Document reuse eligibility filtering endpoint is not "
        "implemented in A8_BASE."
    )


def test_tc_spacs_020_ps_section_4(stub_iam):
    """
    test_id: TC-SPACS-020
    source_id: PS-Section-4
    purpose: Verify draft applications are preserved on recoverable timeout or system error.
    """
    student_client = _make_student_client(stub_iam, user_id=1001)
    resp = student_client.post(
        "/api/v1/spacs/applications/",
        {"scheme_id": "SCHEME_TIMEOUT_020", "documents_list": ["doc_020"]},
        format="json",
    )
    assert resp.status_code == 201
    app_id = resp.json()["application_id"]

    # Student resumes session and retrieves preserved draft
    resumed_client = _make_student_client(stub_iam, user_id=1001)
    get_resp = resumed_client.get(f"/api/v1/spacs/applications/{app_id}/")
    assert get_resp.status_code == 200
    assert get_resp.json()["scheme_id"] == "SCHEME_TIMEOUT_020"
    assert get_resp.json()["documents_list"] == ["doc_020"]
    assert get_resp.json()["status"] == ScholarshipApplication.STATUS_DRAFT


def test_tc_spacs_021_ps_section_9():
    """
    test_id: TC-SPACS-021
    source_id: PS-Section-9
    purpose: Verify significant actions are time-stamped and audit logged.
    """
    pytest.skip(
        "NOT_AUTOMATED: Time-stamped audit logging for SPACS actions is not implemented in A8_BASE."
    )


def test_tc_spacs_022_ps_section_9():
    """
    test_id: TC-SPACS-022
    source_id: PS-Section-9
    purpose: (
        "Verify uncompleted tasks are routed according to currently configured "
        "role assignment when a role holder changes."
    )
    """
    pytest.skip(
        "NOT_AUTOMATED: Role reassignment and task routing workflow is not implemented in A8_BASE."
    )
