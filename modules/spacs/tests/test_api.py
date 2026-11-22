"""API tests for SPACS endpoints, role authorization, and state machines."""

from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.spacs.models import (
    ApplicationDocument,
    AwardCycle,
    CatalogueEntry,
    CatalogueVersion,
    ScholarshipApplication,
    SpacsAuditLog,
)
from modules.spacs.registry import ROLE_GRANTS

pytestmark = pytest.mark.django_db


def _client(stub_iam, permissions=(), uid=1001, kind="student", roles=("student",)):
    stub_iam(
        make_session(
            user_id=uid,
            kind=kind,
            modules=("spacs",),
            permissions=permissions,
            roles=roles,
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


@pytest.fixture
def published_scholarship():
    today = timezone.now().date()
    entry = CatalogueEntry.objects.create(
        code="mcm-scholarship",
        title="Merit-cum-Means Scholarship",
        kind="scholarship",
        status="active",
    )
    return CatalogueVersion.objects.create(
        entry=entry,
        version_number=1,
        academic_year="2026-27",
        policy_reference="REF/2026/MCM/01",
        valid_from=today,
        valid_to=today + timezone.timedelta(days=365),
        application_window_start=timezone.now() - timezone.timedelta(days=5),
        application_window_end=timezone.now() + timezone.timedelta(days=25),
        eligibility_criteria={
            "min_cpi": 7.0,
            "income_ceiling": 600000,
            "allowed_programmes": ["B.Tech"],
            "max_backlogs": 0,
        },
        required_documents=["income_certificate"],
        status="published",
    )


def test_catalogue_list_accessible_to_students(stub_iam, published_scholarship):
    """Students can list published catalogue schemes (UC-SPACS-001)."""
    c = _client(stub_iam, permissions=("spacs.catalogue.view",))
    res = c.get("/api/v1/spacs/catalogue/")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["entry_title"] == "Merit-cum-Means Scholarship"


def test_student_draft_lifecycle(stub_iam, published_scholarship):
    """Student can create draft, update it, and view own application (UC-SPACS-002, 003)."""
    c = _client(
        stub_iam,
        permissions=("spacs.application.create", "spacs.application.view_self"),
        uid=1001,
    )

    # 1. Create draft
    create_res = c.post(
        "/api/v1/spacs/applications/",
        {
            "catalogue_version_id": published_scholarship.pk,
            "cycle": "2026-27",
            "submission_data": {"bank_account": "12345678"},
        },
        format="json",
    )
    assert create_res.status_code == 201
    app_id = create_res.json()["id"]

    # 2. Update draft
    update_res = c.put(
        f"/api/v1/spacs/applications/{app_id}/",
        {
            "submission_data": {"bank_account": "12345678", "ifsc": "SBIN001"},
            "annual_income_declared": 450000,
        },
        format="json",
    )
    assert update_res.status_code == 200
    assert update_res.json()["annual_income_declared"] == "450000.00"

    # 3. View detail
    get_res = c.get(f"/api/v1/spacs/applications/{app_id}/")
    assert get_res.status_code == 200
    assert get_res.json()["application_number"] is not None


def test_scoping_isolation_returns_404(stub_iam, published_scholarship):
    """An unauthorized student attempting to view another student's application gets 404 (BR-SPACS-008)."""
    app = ScholarshipApplication.objects.create(
        user_id=2002,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-2026-99999",
        status="submitted",
    )

    # Student 1001 requests student 2002's application
    c = _client(stub_iam, permissions=("spacs.application.view_self",), uid=1001)
    res = c.get(f"/api/v1/spacs/applications/{app.pk}/")
    assert res.status_code == 404


def test_submit_application_with_eligibility_and_documents(stub_iam, published_scholarship):
    """Submitting an application checks completeness and eligibility (BR-SPACS-001, 004)."""
    app = ScholarshipApplication.objects.create(
        user_id=1001,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-2026-00010",
        annual_income_declared=Decimal("500000"),
        status="draft",
    )
    ApplicationDocument.objects.create(
        user_id=1001,
        application=app,
        doc_type="income_certificate",
        title="Income Certificate",
        drive_url="https://drive.google.com/file/d/1234567890abcdef/view",
        drive_file_id="1234567890abcdef",
        is_active=True,
    )

    user = UserRef(
        user_id=1001,
        username="u1001",
        display_name="Asha",
        kind="student",
        programme="B.Tech",
    )
    fake = stub_iam(
        make_session(
            user_id=1001,
            modules=("spacs",),
            permissions=("spacs.application.create", "spacs.application.view_self"),
        ),
        users={1001: user},
    )
    fake.standings = {1001: {"cpi": 8.5, "active_backlogs": 0, "category": "GEN"}}

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    submit_res = c.post(f"/api/v1/spacs/applications/{app.pk}/submit/")
    assert submit_res.status_code == 200
    assert submit_res.json()["status"] == "submitted"


def test_assistant_verification_flow(stub_iam, published_scholarship):
    """Assistant can review submitted applications and record findings (UC-SPACS-008, 009)."""
    app = ScholarshipApplication.objects.create(
        user_id=1001,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-2026-00011",
        status="submitted",
    )

    # Assistant verifies application
    c = _client(
        stub_iam,
        permissions=ROLE_GRANTS["spacs_assistant"],
        uid=9,
        kind="staff",
        roles=("spacs_assistant",),
    )

    # 1. Fetch queue
    queue_res = c.get("/api/v1/spacs/verification/queue/")
    assert queue_res.status_code == 200
    assert any(q["id"] == app.pk for q in queue_res.json())

    # 2. Record verification finding
    finding_res = c.post(
        f"/api/v1/spacs/verification/{app.pk}/finding/",
        {
            "action": "verified",
            "comments": "Income certificate verified from district portal.",
        },
        format="json",
    )
    assert finding_res.status_code == 200
    app.refresh_from_db()
    assert app.status == "verified"


def test_convener_sanction_flow(stub_iam, published_scholarship):
    """Convener can record final sanction on verified applications (UC-SPACS-012, 013)."""
    app = ScholarshipApplication.objects.create(
        user_id=1001,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-2026-00012",
        status="verified",
    )
    ApplicationDocument.objects.create(
        user_id=1001,
        application=app,
        doc_type="income_certificate",
        title="Income Certificate",
        verification_status="valid",
    )

    c = _client(
        stub_iam,
        permissions=ROLE_GRANTS["spacs_convener"],
        uid=1,
        kind="staff",
        roles=("spacs_convener",),
    )

    # 1. Decision queue
    queue_res = c.get("/api/v1/spacs/decisions/queue/")
    assert queue_res.status_code == 200
    assert any(q["id"] == app.pk for q in queue_res.json())

    # 2. Make decision
    dec_res = c.post(
        f"/api/v1/spacs/decisions/{app.pk}/outcome/",
        {
            "decision": "approved",
            "sanction_order_ref": "SPACS/2026/MCM/001",
            "rationale": "Eligible and within quota limit.",
        },
        format="json",
    )
    assert dec_res.status_code == 200
    app.refresh_from_db()
    assert app.status == "approved"


def test_award_cycle_and_evaluation_flow(stub_iam):
    """Convener and committee flow for convocation awards (UC-SPACS-017..020)."""
    today = timezone.now().date()
    entry = CatalogueEntry.objects.create(
        code="director-gold-medal",
        title="Director Gold Medal",
        kind="award",
        status="active",
    )
    v = CatalogueVersion.objects.create(
        entry=entry,
        version_number=1,
        academic_year="2026-27",
        policy_reference="REF/2026/DGM/01",
        valid_from=today,
        valid_to=today + timezone.timedelta(days=365),
        status="published",
    )

    convener_session = make_session(
        user_id=1,
        kind="staff",
        modules=("spacs",),
        permissions=ROLE_GRANTS["spacs_convener"],
        roles=("spacs_convener",),
    )
    committee_session = make_session(
        user_id=55,
        kind="faculty",
        modules=("spacs",),
        permissions=ROLE_GRANTS["award_committee_member"],
        roles=("award_committee_member",),
    )

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    # 1. Open cycle as convener
    stub_iam(convener_session)
    open_res = c.post(
        "/api/v1/spacs/awards/cycles/",
        {"catalogue_version_id": v.pk, "convocation_year": 2026},
        format="json",
    )
    assert open_res.status_code == 201
    cycle_id = open_res.json()["id"]

    # 2. Prepare candidate pool
    pool_res = c.post(
        f"/api/v1/spacs/awards/cycles/{cycle_id}/prepare-pool/",
        {"candidates": [{"user_id": 3001, "cpi": 9.8, "department": "CSE"}]},
        format="json",
    )
    assert pool_res.status_code == 200
    candidate = AwardCycle.objects.get(pk=cycle_id).candidates.first()

    # 3. Committee evaluation
    stub_iam(committee_session)
    eval_res = c.post(
        f"/api/v1/spacs/awards/candidates/{candidate.pk}/evaluate/",
        {"score": 95.5, "remarks": "Outstanding academic thesis and CPI."},
        format="json",
    )
    assert eval_res.status_code == 200

    # 4. Convener records outcome
    stub_iam(convener_session)
    outcome_res = c.post(
        f"/api/v1/spacs/awards/cycles/{cycle_id}/record-outcome/",
        {
            "candidate_outcomes": [{"candidate_id": candidate.pk, "outcome": "winner"}],
            "approval_ref": "SENATE/2026/AWARDS/01",
        },
        format="json",
    )
    assert outcome_res.status_code == 200

    # 5. Publish
    pub_res = c.post(f"/api/v1/spacs/awards/cycles/{cycle_id}/publish/")
    assert pub_res.status_code == 200
    assert pub_res.json()["status"] == "published"


def test_create_first_draft_version_success(stub_iam):
    """Convener can create the first draft version for an entry without versions."""
    entry = CatalogueEntry.objects.create(
        code="award-excellence",
        title="Award for Academic Excellence",
        kind="award",
        status="active",
    )
    c = _client(stub_iam, permissions=("spacs.catalogue.manage",))
    res = c.post(
        f"/api/v1/spacs/catalogue/entries/{entry.pk}/versions/",
        {
            "academic_year": "2026-27",
            "valid_from": "2026-08-01",
            "valid_to": "2027-05-31",
            "eligibility_criteria": {"min_cpi": 8.5},
            "required_documents": ["grade_sheet"],
        },
        format="json",
    )
    assert res.status_code == 201
    data = res.json()
    assert data["version_number"] == 1
    assert data["status"] == "draft"
    assert data["policy_reference"] == ""
    assert data["entry"] == entry.pk


def test_create_draft_version_defaults_valid_dates(stub_iam):
    """Creating draft version defaults valid_from and valid_to if omitted."""
    entry = CatalogueEntry.objects.create(
        code="sports-medal",
        title="Sports Medal",
        kind="award",
        status="active",
    )
    c = _client(stub_iam, permissions=("spacs.catalogue.manage",))
    res = c.post(
        f"/api/v1/spacs/catalogue/entries/{entry.pk}/versions/",
        {
            "academic_year": "2026-27",
            "eligibility_criteria": {"min_cpi": 6.0},
        },
        format="json",
    )
    assert res.status_code == 201
    data = res.json()
    assert data["version_number"] == 1
    assert data["status"] == "draft"
    assert data["valid_from"] is not None
    assert data["valid_to"] is not None


def test_opportunities_excludes_draft_and_expired_schemes(stub_iam, published_scholarship):
    """Student-facing Opportunities returns only published, active, currently valid schemes."""
    today = timezone.now().date()
    draft_entry = CatalogueEntry.objects.create(
        code="test-merit-2026",
        title="Test Merit Draft Scheme",
        kind="scholarship",
        status="active",
    )
    CatalogueVersion.objects.create(
        entry=draft_entry,
        version_number=1,
        academic_year="2026-27",
        policy_reference="",
        valid_from=today,
        valid_to=today + timezone.timedelta(days=365),
        status="draft",
    )

    # 1. Student hits Opportunities: sees only published scholarship, NOT the draft
    student_client = _client(
        stub_iam, permissions=("spacs.catalogue.view",), uid=1001, kind="student"
    )
    res_student = student_client.get("/api/v1/spacs/catalogue/")
    assert res_student.status_code == 200
    student_codes = [v["entry_code"] for v in res_student.json()]
    assert "mcm-scholarship" in student_codes
    assert "test-merit-2026" not in student_codes

    # 2. Assistant hits Opportunities: also sees only published scholarship, NOT the draft
    assistant_client = _client(
        stub_iam,
        permissions=("spacs.catalogue.view", "spacs.application.review"),
        uid=1891,
        kind="staff",
        roles=("spacs_assistant",),
    )
    res_assistant = assistant_client.get("/api/v1/spacs/catalogue/")
    assert res_assistant.status_code == 200
    assistant_codes = [v["entry_code"] for v in res_assistant.json()]
    assert "mcm-scholarship" in assistant_codes
    assert "test-merit-2026" not in assistant_codes

    # 3. Assistant hits Scheme Catalogue with manage=true: CAN see the draft
    res_manage = assistant_client.get("/api/v1/spacs/catalogue/?manage=true")
    assert res_manage.status_code == 200
    manage_codes = [v["entry_code"] for v in res_manage.json()]
    assert "test-merit-2026" in manage_codes


def test_staff_assistant_cannot_submit_student_applications(stub_iam, published_scholarship):
    """Staff/assistant roles cannot submit student applications; students cannot apply to drafts."""
    today = timezone.now().date()
    draft_entry = CatalogueEntry.objects.create(
        code="draft-scheme-only",
        title="Draft Scheme Only",
        kind="scholarship",
        status="active",
    )
    draft_ver = CatalogueVersion.objects.create(
        entry=draft_entry,
        version_number=1,
        academic_year="2026-27",
        policy_reference="",
        valid_from=today,
        valid_to=today + timezone.timedelta(days=365),
        status="draft",
    )

    # 1. Assistant tries to submit application draft: 403 Forbidden
    assistant_client = _client(
        stub_iam,
        permissions=("spacs.catalogue.view", "spacs.application.review", "spacs.application.create"),
        uid=1891,
        kind="staff",
        roles=("spacs_assistant",),
    )
    res_asst = assistant_client.post(
        "/api/v1/spacs/applications/",
        {"catalogue_version_id": published_scholarship.pk, "cycle": "2026-27"},
        format="json",
    )
    assert res_asst.status_code == 403

    # 2. Student tries to apply to a draft scheme: 404 Not Found
    student_client = _client(
        stub_iam,
        permissions=("spacs.application.create", "spacs.application.view_self"),
        uid=1001,
        kind="student",
    )
    res_draft_apply = student_client.post(
        "/api/v1/spacs/applications/",
        {"catalogue_version_id": draft_ver.pk, "cycle": "2026-27"},
        format="json",
    )
    assert res_draft_apply.status_code == 404

    # 3. Student applies to published active scheme: 201 Created
    res_valid_apply = student_client.post(
        "/api/v1/spacs/applications/",
        {"catalogue_version_id": published_scholarship.pk, "cycle": "2026-27"},
        format="json",
    )
    assert res_valid_apply.status_code == 201


# ---------------------------------------------------------------------------
# CPI eligibility regression tests (BR-SPACS-001, ADR-0008)
# ---------------------------------------------------------------------------

def _make_draft_app(published_scholarship, uid=1001):
    """Helper: create a draft ScholarshipApplication for uid."""
    return ScholarshipApplication.objects.create(
        user_id=uid,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number=f"SPACS-202627-CPI{uid}",
        annual_income_declared=Decimal("400000"),
        status="draft",
    )


def test_submit_eligible_cpi(stub_iam, published_scholarship):
    """Student with CPI >= min_cpi (8.0 >= 7.0) can submit successfully (BR-SPACS-001)."""
    app = _make_draft_app(published_scholarship)
    ApplicationDocument.objects.create(
        user_id=1001,
        application=app,
        doc_type="income_certificate",
        title="IC",
        drive_url="https://drive.google.com/file/d/aaa/view",
        drive_file_id="aaa",
        is_active=True,
    )

    user = UserRef(user_id=1001, username="u1001", display_name="Asha", kind="student",
                   programme="B.Tech")
    fake = stub_iam(
        make_session(user_id=1001, modules=("spacs",),
                     permissions=("spacs.application.create", "spacs.application.view_self")),
        users={1001: user},
    )
    # CPI well above the 7.0 floor
    fake.standings = {1001: {"cpi": 8.0, "active_backlogs": 0, "category": "GEN"}}

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    res = c.post(f"/api/v1/spacs/applications/{app.pk}/submit/")
    assert res.status_code == 200, res.json()
    assert res.json()["status"] == "submitted"
    assert res.json()["cpi_at_apply"] == "8.00"


def test_submit_ineligible_cpi(stub_iam, published_scholarship):
    """Student with CPI < min_cpi (6.5 < 7.0) receives 400 with a CPI reason (BR-SPACS-001)."""
    app = _make_draft_app(published_scholarship, uid=1002)
    ApplicationDocument.objects.create(
        user_id=1002,
        application=app,
        doc_type="income_certificate",
        title="IC",
        drive_url="https://drive.google.com/file/d/bbb/view",
        drive_file_id="bbb",
        is_active=True,
    )

    user = UserRef(user_id=1002, username="u1002", display_name="Ravi", kind="student",
                   programme="B.Tech")
    fake = stub_iam(
        make_session(user_id=1002, modules=("spacs",),
                     permissions=("spacs.application.create", "spacs.application.view_self")),
        users={1002: user},
    )
    # CPI below the 7.0 floor
    fake.standings = {1002: {"cpi": 6.5, "active_backlogs": 0, "category": "GEN"}}

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    res = c.post(f"/api/v1/spacs/applications/{app.pk}/submit/")
    assert res.status_code == 400, res.json()
    err_msg = res.json().get("error", {}).get("message", "")
    assert "CPI" in err_msg or "Eligibility" in err_msg


def test_submit_no_declared_standing(stub_iam, published_scholarship):
    """Student with no declared academic standing cannot submit a CPI-gated scheme (BR-SPACS-001).

    The IAM returns an empty mapping for the student — this means results have not
    been declared for this semester.  The eligibility engine must fail closed with
    'Academic standing or CPI has not been declared', NOT silently pass the student.
    """
    app = _make_draft_app(published_scholarship, uid=1003)
    ApplicationDocument.objects.create(
        user_id=1003,
        application=app,
        doc_type="income_certificate",
        title="IC",
        drive_url="https://drive.google.com/file/d/ccc/view",
        drive_file_id="ccc",
        is_active=True,
    )

    user = UserRef(user_id=1003, username="u1003", display_name="Meera", kind="student",
                   programme="B.Tech")
    fake = stub_iam(
        make_session(user_id=1003, modules=("spacs",),
                     permissions=("spacs.application.create", "spacs.application.view_self")),
        users={1003: user},
    )
    # Empty standings: no declared result yet
    fake.standings = {}

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    res = c.post(f"/api/v1/spacs/applications/{app.pk}/submit/")
    assert res.status_code == 400, res.json()
    err_msg = res.json().get("error", {}).get("message", "")
    assert "not been declared" in err_msg or "CPI" in err_msg


def test_submit_iam_unavailable_returns_503(stub_iam, published_scholarship):
    """IAM unavailability must return 503, never silently collapse to eligibility failure (ADR-0008)."""
    from fusion_auth.client import IamUnavailable

    app = _make_draft_app(published_scholarship, uid=1004)

    user = UserRef(user_id=1004, username="u1004", display_name="Dev", kind="student",
                   programme="B.Tech")
    fake = stub_iam(
        make_session(user_id=1004, modules=("spacs",),
                     permissions=("spacs.application.create", "spacs.application.view_self")),
        users={1004: user},
    )
    # Simulate IAM being unreachable
    fake.standings_error = IamUnavailable("connection timed out")

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    res = c.post(f"/api/v1/spacs/applications/{app.pk}/submit/")
    assert res.status_code == 503, res.json()
    err = res.json().get("error", {})
    assert err.get("code") == "identity_service_unavailable"


# ---------------------------------------------------------------------------
# Document attachment & normalization regression tests (BR-SPACS-003, 004)
# ---------------------------------------------------------------------------

def test_attached_income_certificate_satisfies_requirement_with_normalization(
    stub_iam, published_scholarship
):
    """Document attached with 'Income Certificate' normalizes and satisfies 'income_certificate'."""
    user = UserRef(user_id=1005, username="u1005", display_name="Kiran", kind="student", programme="B.Tech")
    fake = stub_iam(
        make_session(
            user_id=1005,
            modules=("spacs",),
            permissions=("spacs.application.create", "spacs.application.view_self"),
        ),
        users={1005: user},
    )
    fake.standings = {1005: {"cpi": 8.0, "active_backlogs": 0, "category": "GEN"}}

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    # 1. Attach document with human-formatted type 'Income Certificate' (as in ApplyModal / Drive modal)
    attach_res = c.post(
        "/api/v1/spacs/documents/attach-link/",
        {
            "doc_type": "Income Certificate",
            "url": "https://drive.google.com/file/d/income1234567890/view",
            "title": "Income Certificate FY25",
        },
        format="json",
    )
    assert attach_res.status_code == 201, attach_res.json()
    doc_id = attach_res.json()["id"]
    # doc_type is normalized to canonical form
    assert attach_res.json()["doc_type"] == "income_certificate"

    # 2. Create draft referencing the attached document in submission_data
    create_res = c.post(
        "/api/v1/spacs/applications/",
        {
            "catalogue_version_id": published_scholarship.pk,
            "cycle": "2026-27",
            "submission_data": {
                "bank_account": "1234567890",
                "bank_ifsc": "SBIN0001234",
                "document_ids": [doc_id],
            },
            "annual_income_declared": "400000",
        },
        format="json",
    )
    assert create_res.status_code == 201, create_res.json()
    app_id = create_res.json()["id"]

    # 3. Submit application: document satisfies the requirement and is linked to the application
    submit_res = c.post(f"/api/v1/spacs/applications/{app_id}/submit/")
    assert submit_res.status_code == 200, submit_res.json()
    assert submit_res.json()["status"] == "submitted"

    # Confirm the document is persisted against the application
    doc = ApplicationDocument.objects.get(pk=doc_id)
    assert doc.application_id == app_id


def test_genuinely_missing_document_rejected(stub_iam, published_scholarship):
    """A genuinely missing required document is rejected with a clear message (BR-SPACS-004)."""
    # Configure published scholarship to require multiple documents
    published_scholarship.required_documents = ["income_certificate", "caste_certificate"]
    published_scholarship.save(update_fields=["required_documents"])

    user = UserRef(user_id=1006, username="u1006", display_name="Pooja", kind="student", programme="B.Tech")
    fake = stub_iam(
        make_session(
            user_id=1006,
            modules=("spacs",),
            permissions=("spacs.application.create", "spacs.application.view_self"),
        ),
        users={1006: user},
    )
    fake.standings = {1006: {"cpi": 8.0, "active_backlogs": 0, "category": "GEN"}}

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    # Attach ONLY income_certificate, leaving caste_certificate missing
    attach_res = c.post(
        "/api/v1/spacs/documents/attach-link/",
        {
            "doc_type": "income_certificate",
            "url": "https://drive.google.com/file/d/incomeOnly12345/view",
            "title": "Income Certificate",
        },
        format="json",
    )
    assert attach_res.status_code == 201
    doc_id = attach_res.json()["id"]

    # Create draft
    create_res = c.post(
        "/api/v1/spacs/applications/",
        {
            "catalogue_version_id": published_scholarship.pk,
            "cycle": "2026-27",
            "submission_data": {
                "bank_account": "1234567890",
                "bank_ifsc": "SBIN0001234",
                "document_ids": [doc_id],
            },
            "annual_income_declared": "400000",
        },
        format="json",
    )
    app_id = create_res.json()["id"]

    # Submit: must fail because caste_certificate is genuinely missing
    submit_res = c.post(f"/api/v1/spacs/applications/{app_id}/submit/")
    assert submit_res.status_code == 400, submit_res.json()
    err_msg = submit_res.json().get("error", {}).get("message", "")
    assert "Missing documents: caste_certificate" in err_msg


# ---------------------------------------------------------------------------
# Application withdrawal authorization tests (BR-SPACS-010, UC-SPACS-004)
# ---------------------------------------------------------------------------

def test_student_can_withdraw_own_application(stub_iam, published_scholarship):
    """Owning student can withdraw their submitted application."""
    user = UserRef(
        user_id=1010, username="u1010", display_name="Owner Student", kind="student", programme="B.Tech"
    )
    stub_iam(
        make_session(
            user_id=1010,
            modules=("spacs",),
            permissions=(
                "spacs.application.create",
                "spacs.application.view_self",
                "spacs.application.delete",
            ),
        ),
        users={1010: user},
    )

    app = ScholarshipApplication.objects.create(
        user_id=1010,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-202627-W001",
        annual_income_declared=Decimal("400000"),
        status="submitted",
    )

    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    res = c.post(
        f"/api/v1/spacs/applications/{app.pk}/withdraw/",
        {"reason": "Changing schemes"},
        format="json",
    )
    assert res.status_code == 200, res.json()
    assert res.json()["status"] == "withdrawn"
    assert res.json()["withdrawn_reason"] == "Changing schemes"

    app.refresh_from_db()
    assert app.status == "withdrawn"


def test_staff_and_other_students_cannot_withdraw_application(stub_iam, published_scholarship):
    """Staff roles (Assistant, Convener) and other students cannot withdraw someone else's application."""
    app = ScholarshipApplication.objects.create(
        user_id=1010,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-202627-W002",
        annual_income_declared=Decimal("400000"),
        status="submitted",
    )

    # 1. SPACS Assistant attempts withdrawal -> 403 Forbidden
    assistant_client = _client(
        stub_iam,
        permissions=("spacs.application.review", "spacs.catalogue.view"),
        uid=1891,
        kind="staff",
        roles=("spacs_assistant",),
    )
    res_asst = assistant_client.post(
        f"/api/v1/spacs/applications/{app.pk}/withdraw/",
        {"reason": "Assistant attempting cancel"},
        format="json",
    )
    assert res_asst.status_code == 403

    # 2. SPACS Convener attempts withdrawal -> 403 Forbidden
    convener_client = _client(
        stub_iam,
        permissions=("spacs.application.approve", "spacs.catalogue.manage", "spacs.catalogue.view"),
        uid=1000,
        kind="staff",
        roles=("spacs_convener",),
    )
    res_conv = convener_client.post(
        f"/api/v1/spacs/applications/{app.pk}/withdraw/",
        {"reason": "Convener attempting cancel"},
        format="json",
    )
    assert res_conv.status_code == 403

    # 3. Different student attempts withdrawal -> 403 Forbidden
    other_student_client = _client(
        stub_iam,
        permissions=(
            "spacs.application.create",
            "spacs.application.view_self",
            "spacs.application.delete",
        ),
        uid=1099,
        kind="student",
    )
    res_other = other_student_client.post(
        f"/api/v1/spacs/applications/{app.pk}/withdraw/",
        {"reason": "Rival student attempting cancel"},
        format="json",
    )
    assert res_other.status_code == 403

    # Confirm application status was untouched
    app.refresh_from_db()
    assert app.status == "submitted"


def test_verified_finding_updates_documents_to_valid(stub_iam, published_scholarship):
    """Verified finding updates all active application documents to valid and logs audit."""
    app = ScholarshipApplication.objects.create(
        user_id=1001,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-2026-00091",
        status="submitted",
    )
    doc = ApplicationDocument.objects.create(
        user_id=1001,
        application=app,
        doc_type="income_certificate",
        title="Income Certificate",
        verification_status="pending",
        is_active=True,
    )

    c = _client(
        stub_iam,
        permissions=ROLE_GRANTS["spacs_assistant"],
        uid=42,
        kind="staff",
        roles=("spacs_assistant",),
    )
    finding_res = c.post(
        f"/api/v1/spacs/verification/{app.pk}/finding/",
        {
            "action": "verified",
            "comments": "All documents verified against official records.",
        },
        format="json",
    )
    assert finding_res.status_code == 200
    app.refresh_from_db()
    assert app.status == "verified"

    doc.refresh_from_db()
    assert doc.verification_status == "valid"
    assert "Verified by u42" in doc.verification_notes

    audit_entry = SpacsAuditLog.objects.filter(
        target_type="application_document",
        target_id=str(doc.pk),
        action="document_verified",
    ).first()
    assert audit_entry is not None
    assert audit_entry.actor_id == 42


def test_correction_required_finding_leaves_documents_pending(stub_iam, published_scholarship):
    """Correction required does not mark documents as valid/verified."""
    app = ScholarshipApplication.objects.create(
        user_id=1001,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-2026-00092",
        status="submitted",
    )
    doc = ApplicationDocument.objects.create(
        user_id=1001,
        application=app,
        doc_type="income_certificate",
        title="Income Certificate",
        verification_status="pending",
        is_active=True,
    )

    c = _client(
        stub_iam,
        permissions=ROLE_GRANTS["spacs_assistant"],
        uid=42,
        kind="staff",
        roles=("spacs_assistant",),
    )
    finding_res = c.post(
        f"/api/v1/spacs/verification/{app.pk}/finding/",
        {
            "action": "correction_required",
            "comments": "Income certificate is blurry. Please re-upload.",
            "correction_fields": ["income_certificate"],
        },
        format="json",
    )
    assert finding_res.status_code == 200
    app.refresh_from_db()
    assert app.status == "correction_required"

    doc.refresh_from_db()
    assert doc.verification_status == "pending"


def test_concern_raised_finding_leaves_documents_pending(stub_iam, published_scholarship):
    """Concern raised does not mark documents as valid/verified."""
    app = ScholarshipApplication.objects.create(
        user_id=1001,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-2026-00093",
        status="submitted",
    )
    doc = ApplicationDocument.objects.create(
        user_id=1001,
        application=app,
        doc_type="income_certificate",
        title="Income Certificate",
        verification_status="pending",
        is_active=True,
    )

    c = _client(
        stub_iam,
        permissions=ROLE_GRANTS["spacs_assistant"],
        uid=42,
        kind="staff",
        roles=("spacs_assistant",),
    )
    finding_res = c.post(
        f"/api/v1/spacs/verification/{app.pk}/finding/",
        {
            "action": "concern_raised",
            "comments": "Income threshold discrepancy requires committee review.",
        },
        format="json",
    )
    assert finding_res.status_code == 200
    app.refresh_from_db()
    assert app.status == "verification_concern"

    doc.refresh_from_db()
    assert doc.verification_status == "pending"


def test_approval_rejected_when_required_documents_pending_or_invalid(
    stub_iam, published_scholarship
):
    """Convener cannot approve an application if required documents are pending, invalid, or missing."""
    convener_client = _client(
        stub_iam,
        permissions=ROLE_GRANTS["spacs_convener"],
        uid=1,
        kind="staff",
        roles=("spacs_convener",),
    )

    # Case 1: Required document is pending
    app1 = ScholarshipApplication.objects.create(
        user_id=1001,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-2026-00094",
        status="verified",
    )
    doc1 = ApplicationDocument.objects.create(
        user_id=1001,
        application=app1,
        doc_type="income_certificate",
        title="Income Certificate",
        verification_status="pending",
        is_active=True,
    )
    res1 = convener_client.post(
        f"/api/v1/spacs/decisions/{app1.pk}/outcome/",
        {"decision": "approved", "sanction_order_ref": "ORD-1", "rationale": "Approve"},
        format="json",
    )
    assert res1.status_code == 400
    assert "required documents are pending or unverified" in res1.json()["error"]["message"]

    # Case 2: Required document is invalid (rejected)
    doc1.verification_status = "invalid"
    doc1.save(update_fields=["verification_status"])
    res2 = convener_client.post(
        f"/api/v1/spacs/decisions/{app1.pk}/outcome/",
        {"decision": "approved", "sanction_order_ref": "ORD-2", "rationale": "Approve"},
        format="json",
    )
    assert res2.status_code == 400

    # Case 3: Required document is completely missing (different user to avoid unique constraint)
    app2 = ScholarshipApplication.objects.create(
        user_id=1002,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-2026-00095",
        status="verified",
    )
    res3 = convener_client.post(
        f"/api/v1/spacs/decisions/{app2.pk}/outcome/",
        {"decision": "approved", "sanction_order_ref": "ORD-3", "rationale": "Approve"},
        format="json",
    )
    assert res3.status_code == 400
    assert "required documents are pending or unverified" in res3.json()["error"]["message"]


def test_approval_succeeds_when_all_required_documents_valid(
    stub_iam, published_scholarship
):
    """Convener approval succeeds when all required documents are verified and valid."""
    convener_client = _client(
        stub_iam,
        permissions=ROLE_GRANTS["spacs_convener"],
        uid=1,
        kind="staff",
        roles=("spacs_convener",),
    )

    app = ScholarshipApplication.objects.create(
        user_id=1001,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-2026-00096",
        status="verified",
    )
    ApplicationDocument.objects.create(
        user_id=1001,
        application=app,
        doc_type="income_certificate",
        title="Income Certificate",
        verification_status="valid",
        is_active=True,
    )

    res = convener_client.post(
        f"/api/v1/spacs/decisions/{app.pk}/outcome/",
        {
            "decision": "approved",
            "sanction_order_ref": "ORD-VALID-001",
            "rationale": "All criteria met and documents verified.",
        },
        format="json",
    )
    assert res.status_code == 200
    app.refresh_from_db()
    assert app.status == "approved"


def test_correction_required_editing_and_resubmission(stub_iam, published_scholarship):
    """Owning student can edit, replace documents, and resubmit a correction-required application."""
    owner_client = _client(
        stub_iam,
        permissions=ROLE_GRANTS["student"],
        uid=1001,
        kind="student",
    )
    app = ScholarshipApplication.objects.create(
        user_id=1001,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-2026-00301",
        status="correction_required",
        cpi_at_apply="8.20",
        annual_income_declared=Decimal("350000.00"),
        submission_data={
            "bank_account": "11223344",
            "bank_ifsc": "SBIN0001",
            "bank_name": "SBI",
            "statement_of_purpose": "Old motivation",
        },
    )
    old_doc = ApplicationDocument.objects.create(
        user_id=1001,
        application=app,
        doc_type="income_certificate",
        title="Old Income Certificate",
        verification_status="invalid",
        is_active=True,
    )

    # 1. GET application details - prefilled values available
    detail_res = owner_client.get(f"/api/v1/spacs/applications/{app.pk}/")
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["annual_income_declared"] == "350000.00"
    assert data["submission_data"]["bank_account"] == "11223344"
    assert data["submission_data"]["bank_ifsc"] == "SBIN0001"
    assert data["submission_data"]["statement_of_purpose"] == "Old motivation"
    assert len(data["documents"]) == 1

    # 2. Attach replacement document
    new_doc = ApplicationDocument.objects.create(
        user_id=1001,
        application=None,
        doc_type="income_certificate",
        title="Corrected Income Certificate",
        verification_status="pending",
        is_active=True,
    )

    # 3. Update existing application with modified fields and replaced document
    put_res = owner_client.put(
        f"/api/v1/spacs/applications/{app.pk}/",
        {
            "annual_income_declared": 380000,
            "submission_data": {
                "bank_account": "99887766",
                "bank_ifsc": "HDFC0001",
                "bank_name": "HDFC Bank",
                "statement_of_purpose": "Updated justification",
                "document_ids": [new_doc.pk],
            },
        },
        format="json",
    )
    assert put_res.status_code == 200
    app.refresh_from_db()
    assert app.annual_income_declared == Decimal("380000.00")
    assert app.submission_data["bank_account"] == "99887766"
    assert app.application_number == "SPACS-2026-00301"  # Preserved original number

    # Check replacement: old_doc deactivated, new_doc attached
    old_doc.refresh_from_db()
    assert not old_doc.is_active
    new_doc.refresh_from_db()
    assert new_doc.application == app
    assert new_doc.is_active

    # 4. Resubmit the application
    resubmit_res = owner_client.post(f"/api/v1/spacs/applications/{app.pk}/resubmit/")
    assert resubmit_res.status_code == 200
    app.refresh_from_db()
    assert app.status == "resubmitted"
    assert app.resubmitted_at is not None
    assert app.application_number == "SPACS-2026-00301"

    # 5. Application returns to assistant's verification queue
    assistant_client = _client(
        stub_iam,
        permissions=ROLE_GRANTS["spacs_assistant"],
        uid=42,
        kind="staff",
        roles=("spacs_assistant",),
    )
    queue_res = assistant_client.get("/api/v1/spacs/verification/queue/")
    assert queue_res.status_code == 200
    assert any(q["id"] == app.pk for q in queue_res.json())


def test_correction_editing_ownership_and_status_authorization(
    stub_iam, published_scholarship
):
    """Non-owners and unauthorized roles cannot edit or resubmit; non-correction states reject edits."""
    app = ScholarshipApplication.objects.create(
        user_id=1001,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-2026-00302",
        status="correction_required",
    )

    # 1. Other student attempts to edit -> 403
    other_student = _client(
        stub_iam,
        permissions=ROLE_GRANTS["student"],
        uid=1099,
        kind="student",
    )
    edit_res = other_student.put(
        f"/api/v1/spacs/applications/{app.pk}/",
        {"submission_data": {"bank_account": "hack"}},
        format="json",
    )
    assert edit_res.status_code == 403

    # 2. Other student attempts to resubmit -> 403
    resubmit_res = other_student.post(f"/api/v1/spacs/applications/{app.pk}/resubmit/")
    assert resubmit_res.status_code == 403

    # 3. Assistant attempts to edit -> 403
    assistant_client = _client(
        stub_iam,
        permissions=ROLE_GRANTS["spacs_assistant"],
        uid=42,
        kind="staff",
        roles=("spacs_assistant",),
    )
    assert assistant_client.put(
        f"/api/v1/spacs/applications/{app.pk}/",
        {"submission_data": {"bank_account": "hack"}},
        format="json",
    ).status_code == 403

    # 4. Owning student cannot edit when application is in submitted or verified status
    owner_client = _client(
        stub_iam,
        permissions=ROLE_GRANTS["student"],
        uid=1001,
        kind="student",
    )
    app.status = "submitted"
    app.save(update_fields=["status"])
    assert owner_client.put(
        f"/api/v1/spacs/applications/{app.pk}/",
        {"submission_data": {"bank_account": "123"}},
        format="json",
    ).status_code == 409
    assert owner_client.post(
        f"/api/v1/spacs/applications/{app.pk}/resubmit/"
    ).status_code == 409


def test_cpi_not_manually_editable_in_correction(stub_iam, published_scholarship):
    """Manual CPI editing is ignored/prevented during application correction."""
    owner_client = _client(
        stub_iam,
        permissions=ROLE_GRANTS["student"],
        uid=1001,
        kind="student",
    )
    app = ScholarshipApplication.objects.create(
        user_id=1001,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-2026-00303",
        status="correction_required",
        cpi_at_apply="7.50",
    )

    res = owner_client.put(
        f"/api/v1/spacs/applications/{app.pk}/",
        {
            "cpi_at_apply": 10.0,
            "cpi": 10.0,
            "submission_data": {"bank_account": "12345"},
        },
        format="json",
    )
    assert res.status_code == 200
    app.refresh_from_db()
    assert str(app.cpi_at_apply) == "7.50"


def test_verification_concern_details_visible_to_convener(stub_iam, published_scholarship):
    """Convener can inspect assistant's concern findings, comments, actor and timestamp."""
    convener_client = _client(
        stub_iam,
        permissions=ROLE_GRANTS["spacs_convener"],
        uid=1,
        kind="staff",
        roles=("spacs_convener",),
    )
    app = ScholarshipApplication.objects.create(
        user_id=1001,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-2026-00401",
        status="verification_concern",
    )
    from modules.spacs.models import VerificationFinding

    VerificationFinding.objects.create(
        application=app,
        reviewer_id=1891,
        action="concern_raised",
        comments="Discrepancy in revenue stamp on income certificate.",
    )

    res = convener_client.get(f"/api/v1/spacs/applications/{app.pk}/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "verification_concern"
    assert len(data["verification_findings"]) == 1
    vf = data["verification_findings"][0]
    assert vf["reviewer_id"] == 1891
    assert vf["action"] == "concern_raised"
    assert vf["comments"] == "Discrepancy in revenue stamp on income certificate."
    assert vf["created_at"] is not None


def test_concerned_application_cannot_bypass_document_verification(stub_iam, published_scholarship):
    """Convener cannot sanction a concerned application while required documents remain pending or invalid."""
    convener_client = _client(
        stub_iam,
        permissions=ROLE_GRANTS["spacs_convener"],
        uid=1,
        kind="staff",
        roles=("spacs_convener",),
    )
    app = ScholarshipApplication.objects.create(
        user_id=1001,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-2026-00402",
        status="verification_concern",
    )
    ApplicationDocument.objects.create(
        user_id=1001,
        application=app,
        doc_type="income_certificate",
        title="Income Certificate",
        verification_status="pending",
        is_active=True,
    )

    # Attempt sanction without valid document -> 400
    res = convener_client.post(
        f"/api/v1/spacs/decisions/{app.pk}/outcome/",
        {
            "decision": "approved",
            "sanction_order_ref": "ORD-001",
            "rationale": "Overriding concern without valid doc",
        },
        format="json",
    )
    assert res.status_code == 400
    assert "required documents are pending or unverified" in res.json()["error"]["message"]


def test_concerned_application_returned_for_correction_recorded_in_audit(
    stub_iam, published_scholarship
):
    """Convener can return concerned application for correction, advancing to CORRECTION_REQUIRED with audit entry."""
    convener_client = _client(
        stub_iam,
        permissions=ROLE_GRANTS["spacs_convener"],
        uid=1,
        kind="staff",
        roles=("spacs_convener",),
    )
    app = ScholarshipApplication.objects.create(
        user_id=1001,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-2026-00403",
        status="verification_concern",
    )

    res = convener_client.post(
        f"/api/v1/spacs/decisions/{app.pk}/outcome/",
        {
            "decision": "returned_for_correction",
            "rationale": "Please provide an attested copy of income proof.",
        },
        format="json",
    )
    assert res.status_code == 200
    app.refresh_from_db()
    assert app.status == "correction_required"

    # Verify audit transition was recorded
    last_transition = app.transitions.order_by("-at").first()
    assert last_transition is not None
    assert last_transition.to_status == "correction_required"
    assert "returned_for_correction" in last_transition.reason


def test_unauthorized_users_cannot_make_decisions_or_resolve_concerns(
    stub_iam, published_scholarship
):
    """Students and assistants cannot record sanction decisions or resolve concerns."""
    app = ScholarshipApplication.objects.create(
        user_id=1001,
        catalogue_entry=published_scholarship.entry,
        catalogue_version=published_scholarship,
        cycle="2026-27",
        application_number="SPACS-2026-00404",
        status="verification_concern",
    )

    # 1. Student attempting decision -> 403
    student_client = _client(
        stub_iam,
        permissions=ROLE_GRANTS["student"],
        uid=1001,
        kind="student",
    )
    res_stu = student_client.post(
        f"/api/v1/spacs/decisions/{app.pk}/outcome/",
        {"decision": "approved", "rationale": "Self-approving"},
        format="json",
    )
    assert res_stu.status_code == 403

    # 2. Assistant attempting decision -> 403
    assistant_client = _client(
        stub_iam,
        permissions=ROLE_GRANTS["spacs_assistant"],
        uid=42,
        kind="staff",
        roles=("spacs_assistant",),
    )
    res_asst = assistant_client.post(
        f"/api/v1/spacs/decisions/{app.pk}/outcome/",
        {"decision": "approved", "rationale": "Assistant approving"},
        format="json",
    )
    assert res_asst.status_code == 403

    # 3. Direct service call rejects unauthorized actor
    from core.api.exceptions import PermissionDeniedError
    from modules.spacs.services import decisions as decision_services

    fake_student = type("Actor", (), {"kind": "student", "user_id": 1001})()
    with pytest.raises(PermissionDeniedError):
        decision_services.make_decision(
            application_id=app.pk,
            decision="approved",
            rationale="bypass attempt",
            actor=fake_student,
        )
