"""API Views for SPACS module."""

from __future__ import annotations

from decimal import Decimal

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.client import IamUnavailable, get_client
from fusion_auth.permissions import HasPermission
from modules.directory import contracts as directory
from modules.spacs.api import serializers as s
from modules.spacs.api.permissions import (
    MODULE,
    P_APP_APPROVE,
    P_APP_CREATE,
    P_APP_DELETE,
    P_APP_REVIEW,
    P_APP_UPDATE,
    P_APP_VIEW_SELF,
    P_AUDIT_VIEW,
    P_AWARD_CANDIDATE_REVIEW,
    P_AWARD_CYCLE_MANAGE,
    P_CATALOGUE_MANAGE,
    P_CATALOGUE_VIEW,
)
from modules.spacs.selectors import (
    applications as app_selectors,
)
from modules.spacs.selectors import (
    awards as award_selectors,
)
from modules.spacs.selectors import (
    scoping,
)
from modules.spacs.services import (
    applications as app_services,
)
from modules.spacs.services import (
    awards as award_services,
)
from modules.spacs.services import (
    catalogue as cat_services,
)
from modules.spacs.services import (
    decisions as decision_services,
)
from modules.spacs.services import (
    documents as doc_services,
)
from modules.spacs.services import (
    renewals as renewal_services,
)
from modules.spacs.services import (
    verification as verify_services,
)


# -- Catalogue Views ------------------------------------------------------------
class CatalogueListView(APIView):
    permission_classes = [MODULE, HasPermission(P_CATALOGUE_VIEW)]

    @extend_schema(responses=s.CatalogueVersionSerializer(many=True))
    def get(self, request):
        manage = (
            request.query_params.get("manage") == "true"
            or request.query_params.get("all") == "true"
        )
        is_staff_user = (
            scoping.is_convener(request.principal)
            or scoping.is_assistant(request.principal)
            or getattr(request.principal, "has_permission", lambda p: False)(P_CATALOGUE_MANAGE)
        )
        if manage and is_staff_user:
            versions = scoping.visible_catalogue_versions(request.principal)
        else:
            versions = scoping.published_scholarship_opportunities(request.principal)

        kind = request.query_params.get("kind")
        if kind:
            versions = versions.filter(entry__kind=kind)
        return Response(s.CatalogueVersionSerializer(versions, many=True).data)


class CatalogueEntryCreateView(APIView):
    permission_classes = [MODULE, HasPermission(P_CATALOGUE_MANAGE)]

    @extend_schema(responses=s.CatalogueEntrySerializer(many=True))
    def get(self, request):
        entries = scoping.visible_catalogue_entries(request.principal)
        return Response(s.CatalogueEntrySerializer(entries, many=True).data)

    @extend_schema(request=s.CatalogueEntrySerializer, responses=s.CatalogueEntrySerializer)
    def post(self, request):
        ser = s.CatalogueEntrySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        entry = cat_services.create_entry(
            code=ser.validated_data["code"],
            title=ser.validated_data["title"],
            kind=ser.validated_data["kind"],
            description=ser.validated_data.get("description", ""),
            allow_multiple_applications=ser.validated_data.get(
                "allow_multiple_applications", False
            ),
            actor=request.principal,
        )
        return Response(s.CatalogueEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class CatalogueVersionCreateView(APIView):
    permission_classes = [MODULE, HasPermission(P_CATALOGUE_MANAGE)]

    @extend_schema(request=s.CatalogueVersionSerializer, responses=s.CatalogueVersionSerializer)
    def post(self, request, pk: int):
        ser = s.CatalogueVersionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = cat_services.create_version(
            entry_id=pk,
            academic_year=ser.validated_data["academic_year"],
            valid_from=ser.validated_data.get("valid_from"),
            valid_to=ser.validated_data.get("valid_to"),
            candidate_source=ser.validated_data.get("candidate_source", "student_application"),
            policy_reference=ser.validated_data.get("policy_reference", ""),
            application_window_start=ser.validated_data.get("application_window_start"),
            application_window_end=ser.validated_data.get("application_window_end"),
            renewal_window_start=ser.validated_data.get("renewal_window_start"),
            renewal_window_end=ser.validated_data.get("renewal_window_end"),
            is_renewable=ser.validated_data.get("is_renewable", False),
            eligibility_criteria=ser.validated_data.get("eligibility_criteria", {}),
            required_documents=ser.validated_data.get("required_documents", []),
            renewal_criteria=ser.validated_data.get("renewal_criteria", {}),
            committee_config=ser.validated_data.get("committee_config", {}),
            sla_threshold_days=ser.validated_data.get("sla_threshold_days", 7),
            actor=request.principal,
        )
        return Response(s.CatalogueVersionSerializer(v).data, status=status.HTTP_201_CREATED)


@extend_schema(request=None, responses=s.CatalogueVersionSerializer)
class CatalogueVersionPublishView(APIView):
    permission_classes = [MODULE, HasPermission(P_CATALOGUE_MANAGE)]

    def post(self, request, pk: int):
        policy_ref = request.data.get("policy_reference", "")
        valid_from = request.data.get("valid_from")
        valid_to = request.data.get("valid_to")
        v = cat_services.publish_version(
            version_id=pk,
            policy_reference=policy_ref,
            valid_from=valid_from,
            valid_to=valid_to,
            actor=request.principal,
        )
        return Response(s.CatalogueVersionSerializer(v).data)


@extend_schema(request=None, responses=s.CatalogueEntrySerializer)
class CatalogueEntryRetireView(APIView):
    permission_classes = [MODULE, HasPermission(P_CATALOGUE_MANAGE)]

    def post(self, request, pk: int):
        entry = cat_services.retire_entry(pk, request.principal)
        return Response(s.CatalogueEntrySerializer(entry).data)


# -- Application Views ----------------------------------------------------------
class MyApplicationsListView(APIView):
    permission_classes = [MODULE, HasPermission(P_APP_VIEW_SELF)]

    @extend_schema(responses=s.ApplicationListSerializer(many=True))
    def get(self, request):
        apps = app_selectors.get_student_applications(request.principal)
        return Response(s.ApplicationListSerializer(apps, many=True).data)


@extend_schema(
    request=s.ScholarshipApplicationSerializer, responses=s.ScholarshipApplicationSerializer
)
class ApplicationDraftCreateView(APIView):
    permission_classes = [MODULE, HasPermission(P_APP_CREATE)]

    def post(self, request):
        actor_kind = getattr(request.principal, "kind", None)
        if actor_kind and actor_kind != "student":
            from core.api.exceptions import PermissionDeniedError

            raise PermissionDeniedError("Only students can apply for scholarships (BR-SPACS-007).")

        version_id = request.data.get("catalogue_version_id")
        cycle = request.data.get("cycle")
        submission_data = request.data.get("submission_data", {})
        income = request.data.get("annual_income_declared")
        if not version_id or not cycle:
            raise BadRequestError("catalogue_version_id and cycle are required.")

        app = app_services.create_draft(
            catalogue_version_id=int(version_id),
            cycle=str(cycle),
            actor=request.principal,
            submission_data=submission_data,
            annual_income=Decimal(str(income)) if income is not None else None,
        )
        return Response(
            s.ScholarshipApplicationSerializer(app).data, status=status.HTTP_201_CREATED
        )


class ApplicationDetailView(APIView):
    permission_classes = [MODULE]

    @extend_schema(responses=s.ScholarshipApplicationSerializer)
    def get(self, request, pk: int):
        app = app_selectors.get_application_or_404(pk, request.principal)
        return Response(s.ScholarshipApplicationSerializer(app).data)

    @extend_schema(
        request=s.ScholarshipApplicationSerializer, responses=s.ScholarshipApplicationSerializer
    )
    def put(self, request, pk: int):
        sub_data = request.data.get("submission_data", {})
        income = request.data.get("annual_income_declared")
        app = app_services.update_application(
            application_id=pk,
            submission_data=sub_data,
            annual_income=Decimal(str(income)) if income is not None else None,
            actor=request.principal,
        )
        return Response(s.ScholarshipApplicationSerializer(app).data)


@extend_schema(request=None, responses=s.ScholarshipApplicationSerializer)
class ApplicationSubmitView(APIView):
    permission_classes = [MODULE, HasPermission(P_APP_CREATE)]

    def post(self, request, pk: int):
        uid = scoping.own_user_id(request.principal)
        user_dto = directory.get_users([uid]).get(uid)

        # Fetch CPI from IAM academic standings (ADR-0008: never self-declared).
        # IamUnavailable → 503 so a downstream outage is never silently collapsed
        # into an eligibility failure (which would freeze a wrong verdict into the
        # application snapshot).
        try:
            standings = get_client().get_academic_standings([uid])
            academic_data = standings.get(uid, {})
        except IamUnavailable as exc:
            return Response(
                {
                    "error": {
                        "code": "identity_service_unavailable",
                        "message": (
                            "Academic records are temporarily unavailable. "
                            "Please try again in a few minutes."
                        ),
                        "details": [str(exc)],
                        "request_id": "",
                    }
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except (RuntimeError, ValueError, KeyError, TypeError):
            # Non-availability errors (bad payload shape etc.) — treat as no standing.
            academic_data = {}

        student_profile = {
            "cpi": academic_data.get("cpi"),
            "programme": user_dto.programme if user_dto else "",
            "discipline": user_dto.discipline if user_dto else "",
            "batch_year": user_dto.batch_year if user_dto else None,
            "category": academic_data.get("category", "GEN"),
            "active_backlogs": academic_data.get("active_backlogs", 0),
        }
        app = app_services.submit_application(
            application_id=pk,
            actor=request.principal,
            student_profile=student_profile,
        )
        return Response(s.ScholarshipApplicationSerializer(app).data)


@extend_schema(request=None, responses=s.ScholarshipApplicationSerializer)
class ApplicationResubmitView(APIView):
    permission_classes = [MODULE, HasPermission(P_APP_UPDATE)]

    def post(self, request, pk: int):
        app = app_services.resubmit_application(application_id=pk, actor=request.principal)
        return Response(s.ScholarshipApplicationSerializer(app).data)


@extend_schema(request=None, responses=s.ScholarshipApplicationSerializer)
class ApplicationWithdrawView(APIView):
    permission_classes = [MODULE, HasPermission(P_APP_DELETE)]

    def post(self, request, pk: int):
        actor_kind = getattr(request.principal, "kind", None)
        uid = scoping.own_user_id(request.principal)
        if actor_kind != "student" or uid is None:
            from core.api.exceptions import PermissionDeniedError

            raise PermissionDeniedError(
                "Only the owning student can withdraw their application (BR-SPACS-010)."
            )

        reason = request.data.get("reason", "")
        app = app_services.withdraw_application(
            application_id=pk, actor=request.principal, reason=reason
        )
        return Response(s.ScholarshipApplicationSerializer(app).data)


@extend_schema(responses=s.ApplicationTransitionSerializer(many=True))
class ApplicationHistoryView(APIView):
    permission_classes = [MODULE]

    def get(self, request, pk: int):
        app = app_selectors.get_application_or_404(pk, request.principal)
        transitions = app.transitions.order_by("at")

        is_staff = scoping.is_convener(request.principal) or scoping.is_assistant(request.principal)
        results = []
        for t in transitions:
            entry = {
                "id": t.id,
                "from_status": t.from_status,
                "to_status": t.to_status,
                "actor_label": t.actor_label,
                "at": t.at.isoformat(),
            }
            if is_staff:
                entry["actor_user_id"] = t.actor_user_id
                entry["reason"] = t.reason
            results.append(entry)

        return Response(
            {
                "application_id": app.pk,
                "redacted": not is_staff,
                "results": results,
            }
        )


@extend_schema(request=None, responses=s.ScholarshipApplicationSerializer)
class ApplyRenewalView(APIView):
    permission_classes = [MODULE, HasPermission(P_APP_CREATE)]

    def post(self, request):
        parent_id = request.data.get("parent_application_id")
        cycle = request.data.get("cycle")
        submission_data = request.data.get("submission_data", {})
        income = request.data.get("annual_income_declared")
        if not parent_id or not cycle:
            raise BadRequestError("parent_application_id and cycle are required.")

        app = renewal_services.apply_renewal(
            parent_application_id=int(parent_id),
            cycle=str(cycle),
            submission_data=submission_data,
            annual_income=Decimal(str(income)) if income is not None else None,
            actor=request.principal,
        )
        return Response(
            s.ScholarshipApplicationSerializer(app).data, status=status.HTTP_201_CREATED
        )


# -- Verification & Review Views ------------------------------------------------
class VerificationQueueView(APIView):
    permission_classes = [MODULE, HasPermission(P_APP_REVIEW)]

    @extend_schema(responses=s.ApplicationListSerializer(many=True))
    def get(self, request):
        queue = app_selectors.get_verification_queue(request.principal)
        return Response(s.ApplicationListSerializer(queue, many=True).data)


@extend_schema(request=s.VerificationFindingSerializer, responses=s.VerificationFindingSerializer)
class VerificationFindingCreateView(APIView):
    permission_classes = [MODULE, HasPermission(P_APP_REVIEW)]

    def post(self, request, pk: int):
        action = request.data.get("action")
        comments = request.data.get("comments", "")
        fields = request.data.get("correction_fields", [])
        finding = verify_services.record_finding(
            application_id=pk,
            action=action,
            comments=comments,
            correction_fields=fields,
            actor=request.principal,
        )
        return Response(s.VerificationFindingSerializer(finding).data)


# -- Decision Views -------------------------------------------------------------
class DecisionQueueView(APIView):
    permission_classes = [MODULE, HasPermission(P_APP_APPROVE)]

    @extend_schema(responses=s.ApplicationListSerializer(many=True))
    def get(self, request):
        queue = app_selectors.get_decision_queue(request.principal)
        return Response(s.ApplicationListSerializer(queue, many=True).data)


@extend_schema(request=s.ScholarshipDecisionSerializer, responses=s.ScholarshipDecisionSerializer)
class DecisionOutcomeCreateView(APIView):
    permission_classes = [MODULE, HasPermission(P_APP_APPROVE)]

    def post(self, request, pk: int):
        decision = request.data.get("decision")
        order_ref = request.data.get("sanction_order_ref", "")
        rationale = request.data.get("rationale", "")
        rec = decision_services.make_decision(
            application_id=pk,
            decision=decision,
            sanction_order_ref=order_ref,
            rationale=rationale,
            actor=request.principal,
        )
        return Response(s.ScholarshipDecisionSerializer(rec).data)


# -- Documents Views ------------------------------------------------------------
class ReusableDocumentsView(APIView):
    permission_classes = [MODULE, HasPermission(P_APP_CREATE)]

    @extend_schema(responses=s.ApplicationDocumentSerializer(many=True))
    def get(self, request):
        doc_type = request.query_params.get("doc_type")
        if not doc_type:
            raise BadRequestError("doc_type query param required.")
        uid = scoping.own_user_id(request.principal)
        docs = doc_services.get_reusable_documents(uid, doc_type)
        return Response(s.ApplicationDocumentSerializer(docs, many=True).data)


class AttachDocumentView(APIView):
    permission_classes = [MODULE, HasPermission(P_APP_CREATE)]

    @extend_schema(request=s.AttachDocumentSerializer, responses=s.ApplicationDocumentSerializer)
    def post(self, request):
        ser = s.AttachDocumentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        uid = scoping.own_user_id(request.principal)
        doc = doc_services.attach_drive_link(
            user_id=uid,
            doc_type=ser.validated_data["doc_type"],
            url=ser.validated_data["url"],
            title=ser.validated_data.get("title", ""),
            application_id=ser.validated_data.get("application_id"),
            valid_until=ser.validated_data.get("valid_until"),
            is_reusable=ser.validated_data.get("is_reusable", True),
        )
        return Response(s.ApplicationDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


@extend_schema(request=None, responses=s.ApplicationDocumentSerializer)
class DeactivateDocumentView(APIView):
    permission_classes = [MODULE]

    def post(self, request, pk: int):
        doc_services.deactivate_document(pk, request.principal)
        return Response({"status": "deactivated"})


# -- Awards Views ---------------------------------------------------------------
class AwardCycleListCreateView(APIView):
    permission_classes = [MODULE, HasPermission(P_AWARD_CANDIDATE_REVIEW)]

    @extend_schema(responses=s.AwardCycleSerializer(many=True))
    def get(self, request):
        cycles = scoping.visible_award_cycles(request.principal)
        return Response(s.AwardCycleSerializer(cycles, many=True).data)

    @extend_schema(request=s.AwardCycleSerializer, responses=s.AwardCycleSerializer)
    def post(self, request):
        if not scoping.is_convener(request.principal):
            raise BadRequestError("Convener authorization required.")
        v_id = request.data.get("catalogue_version_id")
        year = request.data.get("convocation_year")
        if not v_id or not year:
            raise BadRequestError("catalogue_version_id and convocation_year required.")
        cycle = award_services.open_cycle(
            catalogue_version_id=int(v_id),
            convocation_year=int(year),
            actor=request.principal,
        )
        return Response(s.AwardCycleSerializer(cycle).data, status=status.HTTP_201_CREATED)


class AwardCycleDetailView(APIView):
    permission_classes = [MODULE, HasPermission(P_AWARD_CANDIDATE_REVIEW)]

    @extend_schema(responses=s.AwardCycleSerializer)
    def get(self, request, pk: int):
        cycle = award_selectors.get_award_cycle_or_404(pk, request.principal)
        return Response(s.AwardCycleSerializer(cycle).data)


@extend_schema(request=None, responses=s.AwardCycleSerializer)
class AwardPreparePoolView(APIView):
    permission_classes = [MODULE, HasPermission(P_AWARD_CYCLE_MANAGE)]

    def post(self, request, pk: int):
        candidates = request.data.get("candidates", [])
        cycle = award_services.prepare_candidate_pool(
            cycle_id=pk,
            candidates_data=candidates,
            actor=request.principal,
        )
        return Response(s.AwardCycleSerializer(cycle).data)


@extend_schema(request=s.AwardCandidateSerializer, responses=s.AwardCandidateSerializer)
class AwardCandidateEvaluateView(APIView):
    permission_classes = [MODULE, HasPermission(P_AWARD_CANDIDATE_REVIEW)]

    def post(self, request, pk: int):
        score = request.data.get("score")
        remarks = request.data.get("remarks", "")
        status_val = request.data.get("shortlist_status", "shortlisted")
        if score is None:
            raise BadRequestError("Evaluation score is required.")
        cand = award_services.record_committee_evaluation(
            candidate_id=pk,
            score=Decimal(str(score)),
            remarks=remarks,
            shortlist_status=status_val,
            actor=request.principal,
        )
        return Response(s.AwardCandidateSerializer(cand).data)


@extend_schema(request=None, responses=s.AwardCycleSerializer)
class AwardRecordOutcomeView(APIView):
    permission_classes = [MODULE, HasPermission(P_AWARD_CYCLE_MANAGE)]

    def post(self, request, pk: int):
        outcomes = request.data.get("candidate_outcomes", [])
        ref = request.data.get("approval_ref", "")
        cycle = award_services.record_final_award_outcome(
            cycle_id=pk,
            candidate_outcomes=outcomes,
            approval_ref=ref,
            actor=request.principal,
        )
        return Response(s.AwardCycleSerializer(cycle).data)


@extend_schema(request=None, responses=s.AwardCycleSerializer)
class AwardRecordApprovalView(APIView):
    permission_classes = [MODULE, HasPermission(P_AWARD_CYCLE_MANAGE)]

    def post(self, request, pk: int):
        ref = request.data.get("approval_ref", "")
        cycle = award_services.record_institutional_approval(
            cycle_id=pk,
            approval_ref=ref,
            actor=request.principal,
        )
        return Response(s.AwardCycleSerializer(cycle).data)


@extend_schema(request=None, responses=s.AwardCycleSerializer)
class AwardPublishView(APIView):
    permission_classes = [MODULE, HasPermission(P_AWARD_CYCLE_MANAGE)]

    def post(self, request, pk: int):
        cycle = award_services.publish_award_results(cycle_id=pk, actor=request.principal)
        return Response(s.AwardCycleSerializer(cycle).data)


# -- Audit Trail Views ----------------------------------------------------------
class AuditLogListView(APIView):
    permission_classes = [MODULE, HasPermission(P_AUDIT_VIEW)]

    @extend_schema(responses=s.SpacsAuditLogSerializer(many=True))
    def get(self, request):
        logs = scoping.visible_audit_logs(request.principal)
        target_type = request.query_params.get("target_type")
        if target_type:
            logs = logs.filter(target_type=target_type)
        return Response(s.SpacsAuditLogSerializer(logs[:100], many=True).data)
