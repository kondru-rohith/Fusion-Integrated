"""DRF Serializers for SPACS. Explicit field allow-lists only."""

from rest_framework import serializers

from modules.spacs.models import (
    ApplicationDocument,
    ApplicationTransition,
    AwardCandidate,
    AwardCycle,
    CatalogueEntry,
    CatalogueVersion,
    ScholarshipApplication,
    ScholarshipDecision,
    SpacsAuditLog,
    VerificationFinding,
)


class CatalogueEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogueEntry
        fields = (
            "id",
            "code",
            "title",
            "kind",
            "description",
            "status",
            "allow_multiple_applications",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class CatalogueVersionSerializer(serializers.ModelSerializer):
    entry_code = serializers.CharField(source="entry.code", read_only=True)
    entry_title = serializers.CharField(source="entry.title", read_only=True)
    entry_kind = serializers.CharField(source="entry.kind", read_only=True)
    policy_reference = serializers.CharField(required=False, allow_blank=True, default="")
    valid_from = serializers.DateField(required=False)
    valid_to = serializers.DateField(required=False)

    class Meta:
        model = CatalogueVersion
        fields = (
            "id",
            "entry",
            "entry_code",
            "entry_title",
            "entry_kind",
            "version_number",
            "academic_year",
            "policy_reference",
            "candidate_source",
            "valid_from",
            "valid_to",
            "application_window_start",
            "application_window_end",
            "renewal_window_start",
            "renewal_window_end",
            "is_renewable",
            "eligibility_criteria",
            "required_documents",
            "renewal_criteria",
            "committee_config",
            "sla_threshold_days",
            "status",
            "published_at",
            "published_by",
            "created_at",
        )
        read_only_fields = (
            "id",
            "entry",
            "version_number",
            "status",
            "published_at",
            "published_by",
            "created_at",
        )

    def validate(self, attrs):
        from django.utils import timezone

        if not attrs.get("valid_from"):
            attrs["valid_from"] = timezone.now().date()
        if not attrs.get("valid_to"):
            attrs["valid_to"] = attrs["valid_from"] + timezone.timedelta(days=365)
        return super().validate(attrs)


class ApplicationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationDocument
        fields = (
            "id",
            "application",
            "doc_type",
            "title",
            "original_filename",
            "drive_url",
            "issued_date",
            "valid_until",
            "is_active",
            "is_reusable",
            "verification_status",
            "verification_notes",
            "created_at",
        )
        read_only_fields = fields


class AttachDocumentSerializer(serializers.Serializer):
    doc_type = serializers.CharField(max_length=64)
    url = serializers.URLField(max_length=500)
    title = serializers.CharField(max_length=160, required=False, allow_blank=True)
    application_id = serializers.IntegerField(required=False, allow_null=True)
    valid_until = serializers.DateField(required=False, allow_null=True)
    is_reusable = serializers.BooleanField(required=False, default=True)


class ApplicationTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationTransition
        fields = (
            "id",
            "from_status",
            "to_status",
            "actor_user_id",
            "actor_label",
            "reason",
            "at",
        )
        read_only_fields = fields


class VerificationFindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationFinding
        fields = ("id", "reviewer_id", "action", "comments", "correction_fields", "created_at")
        read_only_fields = fields


class ScholarshipDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScholarshipDecision
        fields = ("id", "decider_id", "decision", "sanction_order_ref", "rationale", "created_at")
        read_only_fields = fields


class ScholarshipApplicationSerializer(serializers.ModelSerializer):
    scheme_code = serializers.CharField(source="catalogue_entry.code", read_only=True)
    scheme_title = serializers.CharField(source="catalogue_entry.title", read_only=True)
    scheme_kind = serializers.CharField(source="catalogue_entry.kind", read_only=True)
    required_documents = serializers.ListField(
        source="catalogue_version.required_documents",
        child=serializers.CharField(),
        read_only=True,
        default=list,
    )
    documents = ApplicationDocumentSerializer(many=True, read_only=True)
    verification_findings = VerificationFindingSerializer(many=True, read_only=True)
    decisions = ScholarshipDecisionSerializer(many=True, read_only=True)

    class Meta:
        model = ScholarshipApplication
        fields = (
            "id",
            "user_id",
            "application_number",
            "catalogue_entry",
            "scheme_code",
            "scheme_title",
            "scheme_kind",
            "catalogue_version",
            "academic_year",
            "cycle",
            "is_renewal",
            "parent_application",
            "status",
            "cpi_at_apply",
            "annual_income_declared",
            "demographic_snapshot",
            "submission_data",
            "required_documents",
            "submitted_at",
            "resubmitted_at",
            "withdrawn_at",
            "withdrawn_reason",
            "assigned_assistant_id",
            "assigned_at",
            "documents",
            "verification_findings",
            "decisions",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user_id",
            "application_number",
            "catalogue_entry",
            "catalogue_version",
            "status",
            "cpi_at_apply",
            "demographic_snapshot",
            "submitted_at",
            "resubmitted_at",
            "withdrawn_at",
            "assigned_assistant_id",
            "assigned_at",
            "created_at",
            "updated_at",
        )


class ApplicationListSerializer(serializers.ModelSerializer):
    scheme_code = serializers.CharField(source="catalogue_entry.code", read_only=True)
    scheme_title = serializers.CharField(source="catalogue_entry.title", read_only=True)

    class Meta:
        model = ScholarshipApplication
        fields = (
            "id",
            "user_id",
            "application_number",
            "scheme_code",
            "scheme_title",
            "academic_year",
            "cycle",
            "is_renewal",
            "status",
            "annual_income_declared",
            "submitted_at",
            "created_at",
        )
        read_only_fields = fields


class AwardCandidateSerializer(serializers.ModelSerializer):
    scheme_title = serializers.CharField(
        source="award_cycle.catalogue_version.entry.title", read_only=True
    )

    class Meta:
        model = AwardCandidate
        fields = (
            "id",
            "award_cycle",
            "scheme_title",
            "user_id",
            "source_method",
            "cpi_at_evaluation",
            "standing_snapshot",
            "evaluation_score",
            "committee_remarks",
            "shortlist_status",
            "final_outcome",
            "created_at",
        )
        read_only_fields = ("id", "award_cycle", "created_at")


class AwardCycleSerializer(serializers.ModelSerializer):
    scheme_code = serializers.CharField(source="catalogue_version.entry.code", read_only=True)
    scheme_title = serializers.CharField(source="catalogue_version.entry.title", read_only=True)
    candidates = AwardCandidateSerializer(many=True, read_only=True)

    class Meta:
        model = AwardCycle
        fields = (
            "id",
            "catalogue_version",
            "scheme_code",
            "scheme_title",
            "convocation_year",
            "status",
            "institutional_approval_ref",
            "published_at",
            "candidates",
            "created_at",
        )
        read_only_fields = ("id", "status", "published_at", "created_at")


class SpacsAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpacsAuditLog
        fields = (
            "id",
            "created_at",
            "actor_id",
            "actor_role",
            "action",
            "target_type",
            "target_id",
            "details",
        )
        read_only_fields = fields
