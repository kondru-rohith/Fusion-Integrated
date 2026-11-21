from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.spacs.models.catalogue import CatalogueEntry, CatalogueVersion


class ScholarshipApplication(TimeStampedModel, UserScopedModel):
    """A student scholarship or renewal application instance (CFR-SPACS-003, 012)."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("under_verification", "Under Verification"),
        ("correction_required", "Correction Required"),
        ("resubmitted", "Resubmitted"),
        ("verified", "Verified / Routed for Decision"),
        ("verification_concern", "Verification Concern / Routed"),
        ("under_convener_review", "Under Convener Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        # Renewal states (CW-SPACS-02)
        ("renewal_submitted", "Renewal Submitted"),
        ("renewal_under_verification", "Renewal Under Verification"),
        ("renewal_resubmitted", "Renewal Resubmitted"),
        ("renewal_verified", "Renewal Verified / Routed"),
        ("renewal_under_decision", "Renewal Under Decision"),
        ("renewed", "Renewed / Approved"),
        ("renewal_rejected", "Renewal Rejected"),
    ]

    application_number = models.CharField(max_length=32, unique=True, db_index=True)
    catalogue_entry = models.ForeignKey(
        CatalogueEntry, on_delete=models.PROTECT, related_name="applications"
    )
    catalogue_version = models.ForeignKey(
        CatalogueVersion, on_delete=models.PROTECT, related_name="applications"
    )
    academic_year = models.CharField(max_length=16)
    cycle = models.CharField(max_length=32)
    is_renewal = models.BooleanField(default=False)
    parent_application = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="renewals",
    )

    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="draft", db_index=True)

    # Snapshot frozen at submission (BR-014)
    cpi_at_apply = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    annual_income_declared = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    demographic_snapshot = models.JSONField(default=dict, blank=True)
    submission_data = models.JSONField(default=dict, blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    resubmitted_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdrawn_reason = models.CharField(max_length=300, blank=True)

    assigned_assistant_id = models.IntegerField(null=True, blank=True, db_index=True)
    assigned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "spacs_scholarship_application"
        constraints = [
            # BR-SPACS-002: Exactly one active application per student per scheme per cycle
            models.UniqueConstraint(
                fields=["user_id", "catalogue_entry", "cycle", "is_renewal"],
                condition=models.Q(
                    status__in=[
                        "submitted",
                        "under_verification",
                        "correction_required",
                        "resubmitted",
                        "verified",
                        "verification_concern",
                        "under_convener_review",
                        "approved",
                        "renewal_submitted",
                        "renewal_under_verification",
                        "renewal_resubmitted",
                        "renewal_verified",
                        "renewal_under_decision",
                        "renewed",
                    ]
                ),
                name="spacs_unique_active_application_per_cycle",
            )
        ]
        indexes = [
            models.Index(fields=["user_id", "status"], name="spacs_app_user_status_idx"),
            models.Index(fields=["status", "assigned_assistant_id"], name="spacs_app_assign_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.application_number} ({self.status}) - u{self.user_id}"
