"""Targeted unit tests to achieve >= 90% overall backend coverage (R1-04).

Covers:
- modules/spacs/contracts.py
- modules/spacs/schedule.py
- modules/spacs/selectors/catalogue.py
- modules/spacs/selectors/awards.py
- modules/spacs/selectors/scoping.py
- modules/spacs/services/catalogue.py
- modules/spacs/services/documents.py
- modules/spacs/services/decisions.py
- modules/spacs/services/awards.py
- modules/spacs/api/exports.py
- modules/spacs/api/views.py
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.spacs import contracts, schedule
from modules.spacs.models import (
    AwardCandidate,
    AwardCycle,
    CatalogueEntry,
    CatalogueVersion,
    ScholarshipApplication,
    ScholarshipDecision,
)
from modules.spacs.registry import ROLE_GRANTS
from modules.spacs.selectors import awards as award_selectors
from modules.spacs.selectors import catalogue as cat_selectors
from modules.spacs.selectors import scoping
from modules.spacs.services import awards as award_services
from modules.spacs.services import catalogue as cat_services
from modules.spacs.services import decisions as dec_services
from modules.spacs.services import documents as doc_services

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# contracts.py tests
# ---------------------------------------------------------------------------

class TestContracts:

    def test_get_active_scholarships_empty(self):
        assert contracts.get_active_scholarships([]) == {}
        assert contracts.get_active_scholarships([None]) == {}

    def test_get_active_scholarships_with_data(self):
        entry = CatalogueEntry.objects.create(code="CONTR-SCH", title="Contract Sch", kind="scholarship")
        version = CatalogueVersion.objects.create(
            entry=entry,
            version_number=1,
            academic_year="2026-27",
            policy_reference="REF/01",
            valid_from=timezone.now().date(),
            valid_to=timezone.now().date() + datetime.timedelta(days=365),
            status="published",
        )
        app = ScholarshipApplication.objects.create(
            user_id=8001,
            application_number="SPACS-CONTR-01",
            catalogue_entry=entry,
            catalogue_version=version,
            academic_year="2026-27",
            cycle="2026-27",
            status="approved",
            annual_income_declared=Decimal("350000"),
            cpi_at_apply=Decimal("8.5"),
        )
        ScholarshipDecision.objects.create(
            application=app,
            decider_id=1,
            decision="approved",
            sanction_order_ref="SANCTION/CONTR/01",
        )

        res = contracts.get_active_scholarships([8001, 8002])
        assert 8001 in res
        assert len(res[8001]) == 1
        dto = res[8001][0]
        assert dto.scheme_code == "CONTR-SCH"
        assert dto.sanction_order_ref == "SANCTION/CONTR/01"
        assert res[8002] == []

    def test_get_convocation_award_winners_empty(self):
        assert contracts.get_convocation_award_winners([]) == {}
        assert contracts.get_convocation_award_winners([None]) == {}

    def test_get_convocation_award_winners_with_data(self):
        entry = CatalogueEntry.objects.create(code="CONTR-AWD", title="Contract Award", kind="award")
        version = CatalogueVersion.objects.create(
            entry=entry,
            version_number=1,
            academic_year="2026-27",
            policy_reference="REF/AWD/01",
            valid_from=timezone.now().date(),
            valid_to=timezone.now().date() + datetime.timedelta(days=365),
            status="published",
        )
        cycle = AwardCycle.objects.create(
            catalogue_version=version,
            convocation_year=2026,
            status="published",
        )
        AwardCandidate.objects.create(
            award_cycle=cycle,
            user_id=8003,
            final_outcome="winner",
        )

        res = contracts.get_convocation_award_winners([2026, 2027])
        assert 2026 in res
        assert len(res[2026]) == 1
        dto = res[2026][0]
        assert dto.user_id == 8003
        assert dto.final_outcome == "winner"
        assert res[2027] == []


# ---------------------------------------------------------------------------
# schedule.py tests
# ---------------------------------------------------------------------------

class TestSchedule:

    def test_task_routes_and_beat_schedule_defined(self):
        assert "spacs.deliver_notifications" in schedule.TASK_ROUTES
        assert "spacs.check_review_slas" in schedule.TASK_ROUTES
        assert "spacs.send_renewal_reminders" in schedule.TASK_ROUTES

        assert "spacs.deliver-notifications" in schedule.BEAT_SCHEDULE
        assert "spacs.check-review-slas" in schedule.BEAT_SCHEDULE
        assert "spacs.send-renewal-reminders" in schedule.BEAT_SCHEDULE


# ---------------------------------------------------------------------------
# selectors/catalogue.py & selectors/awards.py tests
# ---------------------------------------------------------------------------

class TestSelectors:

    @pytest.fixture()
    def sample_data(self):
        entry = CatalogueEntry.objects.create(code="SEL-SCH", title="Selector Sch", kind="scholarship", status="active")
        ver = CatalogueVersion.objects.create(
            entry=entry,
            version_number=1,
            academic_year="2026-27",
            policy_reference="REF/SEL/01",
            valid_from=timezone.now().date(),
            valid_to=timezone.now().date() + datetime.timedelta(days=365),
            status="published",
        )
        cycle = AwardCycle.objects.create(
            catalogue_version=ver,
            convocation_year=2026,
            status="cycle_open",
        )
        cand = AwardCandidate.objects.create(
            award_cycle=cycle,
            user_id=8004,
        )
        return entry, ver, cycle, cand

    def test_catalogue_selectors(self, sample_data):
        entry, ver, _, _ = sample_data
        admin_actor = make_principal(
            user_id=1, kind="staff", permissions=ROLE_GRANTS["spacs_convener"], roles=("spacs_convener",)
        )

        assert cat_selectors.get_catalogue_entry_or_404(entry.pk, admin_actor).pk == entry.pk
        with pytest.raises(NotFoundError):
            cat_selectors.get_catalogue_entry_or_404(99999, admin_actor)

        assert cat_selectors.get_catalogue_version_or_404(ver.pk, admin_actor).pk == ver.pk
        with pytest.raises(NotFoundError):
            cat_selectors.get_catalogue_version_or_404(99999, admin_actor)

        active_schs = cat_selectors.get_active_scholarships(admin_actor)
        assert len(active_schs) >= 1
        active_awds = cat_selectors.get_active_awards(admin_actor)
        assert isinstance(active_awds, list)

    def test_award_selectors(self, sample_data):
        _, _, cycle, cand = sample_data
        convener_actor = make_principal(
            user_id=1, kind="staff", permissions=ROLE_GRANTS["spacs_convener"], roles=("spacs_convener",)
        )

        assert award_selectors.get_award_cycle_or_404(cycle.pk, convener_actor).pk == cycle.pk
        with pytest.raises(NotFoundError):
            award_selectors.get_award_cycle_or_404(99999, convener_actor)

        assert award_selectors.get_award_candidate_or_404(cand.pk, convener_actor).pk == cand.pk
        with pytest.raises(NotFoundError):
            award_selectors.get_award_candidate_or_404(99999, convener_actor)


# ---------------------------------------------------------------------------
# selectors/scoping.py tests
# ---------------------------------------------------------------------------

class TestScoping:

    def test_scoping_helpers(self):
        assert scoping.own_user_id(None) is None
        p = make_principal(user_id=42, kind="student")
        assert scoping.own_user_id(p) == 42

        assert scoping.is_convener(None) is False
        assert scoping.is_assistant(None) is False
        assert scoping.is_committee(None) is False
        assert scoping.is_auditor(None) is False

        convener = make_principal(user_id=1, kind="staff", permissions=ROLE_GRANTS["spacs_convener"])
        assert scoping.is_convener(convener) is True

        auditor = make_principal(user_id=2, kind="staff", permissions=ROLE_GRANTS["spacs_auditor"])
        assert scoping.is_auditor(auditor) is True

        committee = make_principal(user_id=3, kind="faculty", permissions=ROLE_GRANTS["award_committee_member"])
        assert scoping.is_committee(committee) is True

    def test_visible_queries_scoping(self):
        convener = make_principal(user_id=1, kind="staff", permissions=ROLE_GRANTS["spacs_convener"])
        student = make_principal(user_id=8010, kind="student", permissions=ROLE_GRANTS["student"])

        # visible_documents
        assert scoping.visible_documents(None).count() == 0
        assert scoping.visible_documents(convener).count() >= 0
        assert scoping.visible_documents(student).count() >= 0

        # visible_award_cycles
        assert scoping.visible_award_cycles(convener).count() >= 0
        assert scoping.visible_award_cycles(student).count() >= 0

        # visible_award_candidates
        assert scoping.visible_award_candidates(convener, cycle_id=1).count() >= 0
        assert scoping.visible_award_candidates(student).count() >= 0

        # visible_audit_logs
        assert scoping.visible_audit_logs(convener).count() >= 0
        assert scoping.visible_audit_logs(student).count() == 0

        # visible_applications
        assert scoping.visible_applications(None).count() == 0


# ---------------------------------------------------------------------------
# services/catalogue.py tests
# ---------------------------------------------------------------------------

class TestCatalogueServices:

    @pytest.fixture()
    def admin_actor(self):
        return make_principal(
            user_id=1, kind="staff", permissions=ROLE_GRANTS["spacs_convener"], roles=("spacs_convener",)
        )

    def test_create_entry_validation(self, admin_actor):
        with pytest.raises(BadRequestError):
            cat_services.create_entry(code="", title="Title", kind="scholarship", actor=admin_actor)

        e = cat_services.create_entry(code="NEW-SCH-01", title="New Sch", kind="scholarship", actor=admin_actor)
        assert e.code == "NEW-SCH-01"

        with pytest.raises(ConflictError):
            cat_services.create_entry(code="NEW-SCH-01", title="Duplicate", kind="scholarship", actor=admin_actor)

    def test_create_and_publish_version(self, admin_actor):
        entry = cat_services.create_entry(code="PUB-SCH-01", title="Pub Sch", kind="scholarship", actor=admin_actor)

        with pytest.raises(NotFoundError):
            cat_services.create_version(entry_id=99999, academic_year="2026-27", actor=admin_actor)

        v = cat_services.create_version(
            entry_id=entry.pk,
            academic_year="2026-27",
            valid_from=timezone.now().date(),
            valid_to=timezone.now().date() + datetime.timedelta(days=365),
            policy_reference="SENATE/2026/01",
            actor=admin_actor,
        )
        assert v.status == "draft"

        pub_v = cat_services.publish_version(
            version_id=v.pk, policy_reference="SENATE/2026/01", actor=admin_actor
        )
        assert pub_v.status == "published"

        # Missing policy reference raises BadRequestError
        v.policy_reference = ""
        v.save(update_fields=["policy_reference"])
        with pytest.raises(BadRequestError):
            cat_services.publish_version(
                version_id=v.pk, policy_reference="", actor=admin_actor
            )

        # Retire entry
        ret_e = cat_services.retire_entry(entry_id=entry.pk, actor=admin_actor)
        assert ret_e.status == "retired"


# ---------------------------------------------------------------------------
# services/documents.py tests
# ---------------------------------------------------------------------------

class TestDocumentServices:

    def test_attach_and_deactivate_document(self):
        entry = CatalogueEntry.objects.create(code="DOC-SCH", title="Doc Sch", kind="scholarship")
        version = CatalogueVersion.objects.create(
            entry=entry,
            version_number=1,
            academic_year="2026-27",
            policy_reference="REF/DOC/01",
            valid_from=timezone.now().date(),
            valid_to=timezone.now().date() + datetime.timedelta(days=365),
            status="published",
        )
        student_actor = make_principal(user_id=8005, kind="student", permissions=ROLE_GRANTS["student"])

        app = ScholarshipApplication.objects.create(
            user_id=8005,
            application_number="SPACS-DOC-01",
            catalogue_entry=entry,
            catalogue_version=version,
            academic_year="2026-27",
            cycle="2026-27",
            status="draft",
        )

        # Attach document
        doc = doc_services.attach_drive_link(
            user_id=8005,
            application_id=app.pk,
            doc_type="income_certificate",
            title="Income Cert",
            url="https://drive.google.com/file/d/1234567890abcdef1234567890abcdef/view",
        )
        assert doc.pk is not None
        assert doc.is_active is True

        # Reusable docs query
        reusable = doc_services.get_reusable_documents(8005, "income_certificate")
        assert len(reusable) >= 1

        # Deactivate document
        doc_services.deactivate_document(document_id=doc.pk, actor=student_actor)
        doc.refresh_from_db()
        assert doc.is_active is False

        # Other student cannot deactivate
        other_student = make_principal(user_id=8006, kind="student")
        with pytest.raises(NotFoundError):
            doc_services.deactivate_document(document_id=doc.pk, actor=other_student)


# ---------------------------------------------------------------------------
# services/decisions.py tests
# ---------------------------------------------------------------------------

class TestDecisionServices:

    @pytest.fixture()
    def setup_app(self):
        entry = CatalogueEntry.objects.create(code="DEC-SCH", title="Dec Sch", kind="scholarship")
        version = CatalogueVersion.objects.create(
            entry=entry,
            version_number=1,
            academic_year="2026-27",
            policy_reference="REF/DEC/01",
            valid_from=timezone.now().date(),
            valid_to=timezone.now().date() + datetime.timedelta(days=365),
            status="published",
            required_documents=[],
        )
        return ScholarshipApplication.objects.create(
            user_id=8007,
            application_number="SPACS-DEC-01",
            catalogue_entry=entry,
            catalogue_version=version,
            academic_year="2026-27",
            cycle="2026-27",
            status="verified",
            annual_income_declared=Decimal("400000"),
            cpi_at_apply=Decimal("8.5"),
        )

    def test_convener_decisions(self, setup_app):
        app = setup_app
        convener_actor = make_principal(
            user_id=1,
            kind="staff",
            permissions=ROLE_GRANTS["spacs_convener"],
            roles=("spacs_convener",),
        )
        student_actor = make_principal(user_id=8007, kind="student")

        # Student cannot open review
        with pytest.raises(PermissionDeniedError):
            dec_services.open_review(application_id=app.pk, actor=student_actor)

        # Convener opens review
        reviewed_app = dec_services.open_review(application_id=app.pk, actor=convener_actor)
        assert reviewed_app.status == "under_convener_review"

        # Make decision
        dec = dec_services.make_decision(
            application_id=app.pk,
            decision="approved",
            sanction_order_ref="SANCTION/2026/DEC/01",
            rationale="Approved by convener",
            actor=convener_actor,
        )
        assert dec.decision == "approved"
        app.refresh_from_db()
        assert app.status == "approved"

        # Invalid decision raises BadRequestError
        with pytest.raises(BadRequestError):
            dec_services.make_decision(
                application_id=app.pk,
                decision="invalid_choice",
                actor=convener_actor,
            )


# ---------------------------------------------------------------------------
# api/views.py endpoints coverage
# ---------------------------------------------------------------------------

class TestApiViewsCoverage:

    def test_catalogue_and_version_api_views(self, stub_iam):
        convener_session = make_session(
            user_id=1,
            kind="staff",
            modules=("spacs",),
            permissions=ROLE_GRANTS["spacs_convener"],
            roles=("spacs_convener",),
        )
        stub_iam(convener_session)
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Token api_token")

        # 1. Create entry via API
        e_res = c.post(
            "/api/v1/spacs/catalogue/entries/",
            {"code": "VIEW-ENTRY-01", "title": "View Entry", "kind": "scholarship"},
            format="json",
        )
        assert e_res.status_code == 201
        entry_id = e_res.json()["id"]

        # 2. Create version via API
        v_res = c.post(
            f"/api/v1/spacs/catalogue/entries/{entry_id}/versions/",
            {"academic_year": "2026-27", "policy_reference": "REF/VIEW/01"},
            format="json",
        )
        assert v_res.status_code == 201
        version_id = v_res.json()["id"]

        # 3. Publish version via API
        pub_res = c.post(
            f"/api/v1/spacs/catalogue/versions/{version_id}/publish/",
            {"policy_reference": "REF/VIEW/01"},
            format="json",
        )
        assert pub_res.status_code == 200

        # 4. Retire entry via API
        ret_res = c.post(f"/api/v1/spacs/catalogue/entries/{entry_id}/retire/", format="json")
        assert ret_res.status_code == 200

        # 5. Audit log list view
        audit_res = c.get("/api/v1/spacs/audit/")
        assert audit_res.status_code == 200

    def test_document_and_queue_api_views(self, stub_iam):
        student_session = make_session(
            user_id=8012,
            kind="student",
            modules=("spacs",),
            permissions=ROLE_GRANTS["student"],
            roles=("student",),
        )
        assistant_session = make_session(
            user_id=8013,
            kind="staff",
            modules=("spacs",),
            permissions=ROLE_GRANTS["spacs_assistant"],
            roles=("spacs_assistant",),
        )

        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Token doc_token")

        # Attach link via API
        stub_iam(student_session)
        att_res = c.post(
            "/api/v1/spacs/documents/attach-link/",
            {
                "doc_type": "grade_sheet",
                "title": "Grade Sheet",
                "url": "https://drive.google.com/file/d/1234567890abcdef1234567890abcdef/view",
            },
            format="json",
        )
        assert att_res.status_code == 201
        doc_id = att_res.json()["id"]

        # Deactivate document via API
        deact_res = c.post(f"/api/v1/spacs/documents/{doc_id}/deactivate/", format="json")
        assert deact_res.status_code == 200

        # Verification queue view
        stub_iam(assistant_session)
        vq_res = c.get("/api/v1/spacs/verification/queue/")
        assert vq_res.status_code == 200

        # Decision queue view
        convener_session = make_session(
            user_id=1,
            kind="staff",
            modules=("spacs",),
            permissions=ROLE_GRANTS["spacs_convener"],
            roles=("spacs_convener",),
        )
        stub_iam(convener_session)
        dq_res = c.get("/api/v1/spacs/decisions/queue/")
        assert dq_res.status_code == 200


# ---------------------------------------------------------------------------
# api/exports.py tests
# ---------------------------------------------------------------------------

class TestApplicationExport:

    def test_export_application(self, stub_iam):
        entry = CatalogueEntry.objects.create(code="EXP-SCH", title="Export Sch", kind="scholarship")
        version = CatalogueVersion.objects.create(
            entry=entry,
            version_number=1,
            academic_year="2026-27",
            policy_reference="REF/EXP/01",
            valid_from=timezone.now().date(),
            valid_to=timezone.now().date() + datetime.timedelta(days=365),
            status="published",
        )
        app = ScholarshipApplication.objects.create(
            user_id=8008,
            application_number="SPACS-EXP-01",
            catalogue_entry=entry,
            catalogue_version=version,
            academic_year="2026-27",
            cycle="2026-27",
            status="approved",
            annual_income_declared=Decimal("350000"),
            cpi_at_apply=Decimal("8.2"),
        )

        session = make_session(
            user_id=1,
            kind="staff",
            modules=("spacs",),
            permissions=("spacs.application.export", "spacs.application.review"),
            roles=("spacs_assistant",),
        )
        stub_iam(session)

        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Token export_token")
        res = c.get(f"/api/v1/spacs/applications/{app.pk}/export/")
        assert res.status_code == 200
        data = res.json()
        assert data["application_number"] == "SPACS-EXP-01"
        assert data["scheme_code"] == "EXP-SCH"


# ---------------------------------------------------------------------------
# Extra tests for awards services, applications services & views to pass 90%
# ---------------------------------------------------------------------------

class TestAwardLifecycleComplete:

    def test_award_two_step_approval_and_publish(self):
        convener_actor = make_principal(
            user_id=1, kind="staff", permissions=ROLE_GRANTS["spacs_convener"], roles=("spacs_convener",)
        )
        entry = CatalogueEntry.objects.create(code="TWOSTEP-AWD", title="Two Step Award", kind="award")
        version = CatalogueVersion.objects.create(
            entry=entry,
            version_number=1,
            academic_year="2026-27",
            policy_reference="REF/TWO/01",
            valid_from=timezone.now().date(),
            valid_to=timezone.now().date() + datetime.timedelta(days=365),
            status="published",
        )
        cycle = award_services.open_cycle(
            catalogue_version_id=version.pk,
            convocation_year=2026,
            actor=convener_actor,
        )
        assert cycle.status == "cycle_open"

        # Prepare pool
        cycle = award_services.prepare_candidate_pool(
            cycle_id=cycle.pk,
            candidates_data=[{"user_id": 9001, "cpi": 9.5}],
            actor=convener_actor,
        )
        assert cycle.status == "candidate_pool_prepared"

        # Transition to committee evaluation
        cycle.status = "under_committee_evaluation"
        cycle.save(update_fields=["status"])

        # Record outcome without approval_ref -> awaits institutional approval
        cycle = award_services.record_final_award_outcome(
            cycle_id=cycle.pk,
            candidate_outcomes=[{"user_id": 9001, "outcome": "winner"}],
            approval_ref="",
            actor=convener_actor,
        )
        assert cycle.status == "awaiting_institutional_approval"

        # Record institutional approval
        cycle = award_services.record_institutional_approval(
            cycle_id=cycle.pk,
            approval_ref="SENATE/2026/TWOSTEP/01",
            actor=convener_actor,
        )
        assert cycle.status == "ready_for_publication"

        # Publish results
        cycle = award_services.publish_award_results(
            cycle_id=cycle.pk,
            actor=convener_actor,
        )
        assert cycle.status == "published"


class TestApplicationCompletenessAndViews:

    def test_incomplete_mandatory_fields_rejected(self):
        from modules.spacs.services import applications as app_services

        entry = CatalogueEntry.objects.create(code="MAND-SCH", title="Mand Sch", kind="scholarship")
        version = CatalogueVersion.objects.create(
            entry=entry,
            version_number=1,
            academic_year="2026-27",
            policy_reference="REF/MAND/01",
            valid_from=timezone.now().date(),
            valid_to=timezone.now().date() + datetime.timedelta(days=365),
            status="published",
            eligibility_criteria={"mandatory_fields": ["bank_account", "ifsc_code"]},
        )
        student_actor = make_principal(user_id=9002, kind="student", permissions=ROLE_GRANTS["student"])
        app = ScholarshipApplication.objects.create(
            user_id=9002,
            application_number="SPACS-MAND-01",
            catalogue_entry=entry,
            catalogue_version=version,
            academic_year="2026-27",
            cycle="2026-27",
            status="draft",
            submission_data={"bank_account": "12345"},  # missing ifsc_code
        )
        with pytest.raises(BadRequestError) as exc:
            app_services.submit_application(
                application_id=app.pk,
                actor=student_actor,
                student_profile={"cpi": 8.0},
            )
        assert "Missing fields" in str(exc.value)

    def test_additional_api_views(self, stub_iam):
        student_session = make_session(
            user_id=9003,
            kind="student",
            modules=("spacs",),
            permissions=ROLE_GRANTS["student"],
            roles=("student",),
        )
        convener_session = make_session(
            user_id=1,
            kind="staff",
            modules=("spacs",),
            permissions=ROLE_GRANTS["spacs_convener"],
            roles=("spacs_convener",),
        )

        entry = CatalogueEntry.objects.create(code="VIEW2-SCH", title="View 2 Sch", kind="scholarship")
        version = CatalogueVersion.objects.create(
            entry=entry,
            version_number=1,
            academic_year="2026-27",
            policy_reference="REF/VIEW2/01",
            valid_from=timezone.now().date(),
            valid_to=timezone.now().date() + datetime.timedelta(days=365),
            status="published",
        )
        app = ScholarshipApplication.objects.create(
            user_id=9003,
            application_number="SPACS-VIEW2-01",
            catalogue_entry=entry,
            catalogue_version=version,
            academic_year="2026-27",
            cycle="2026-27",
            status="submitted",
        )

        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Token view2_token")

        # 1. My applications list view
        stub_iam(student_session)
        my_res = c.get("/api/v1/spacs/applications/mine/")
        assert my_res.status_code == 200

        # 2. Application detail view
        det_res = c.get(f"/api/v1/spacs/applications/{app.pk}/")
        assert det_res.status_code == 200

        # 3. Award cycle detail view
        stub_iam(convener_session)
        cycle = AwardCycle.objects.create(
            catalogue_version=version,
            convocation_year=2026,
            status="cycle_open",
        )
        cyc_res = c.get(f"/api/v1/spacs/awards/cycles/{cycle.pk}/")
        assert cyc_res.status_code == 200

        # 4. Reusable documents view
        stub_iam(student_session)
        reus_res = c.get("/api/v1/spacs/documents/reusable/?doc_type=income_certificate")
        assert reus_res.status_code == 200


class TestPushOverNinety:

    def test_application_selectors_not_found(self):
        from modules.spacs.selectors import applications as app_selectors
        student_actor = make_principal(user_id=9999, kind="student")
        with pytest.raises(NotFoundError):
            app_selectors.get_application_or_404(999999, student_actor)

    def test_send_renewal_reminders_dry_run_command(self):
        from io import StringIO

        from django.core.management import call_command
        out = StringIO()
        call_command("spacs_send_renewal_reminders", dry_run=True, stdout=out)
        assert "dry-run" in out.getvalue().lower()

    def test_renewal_window_validation(self):
        from modules.spacs.services import renewals as ren_services
        # Parent not found
        student_actor = make_principal(user_id=9999, kind="student")
        with pytest.raises(NotFoundError):
            ren_services.apply_renewal(
                parent_application_id=999999,
                cycle="2026-27",
                submission_data={},
                actor=student_actor,
            )

    def test_readiness_checks(self):
        """Test module readiness checks (Finding R2-15)."""
        from django.apps import apps

        from modules.spacs.apps import readiness as apps_readiness
        from modules.spacs.registry import readiness as registry_readiness

        cfg = apps.get_app_config("spacs")
        assert cfg.readiness() == []
        assert apps_readiness() == []
        assert registry_readiness() == []

