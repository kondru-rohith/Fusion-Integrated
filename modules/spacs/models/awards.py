from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.spacs.models.catalogue import CatalogueVersion


class AwardCycle(TimeStampedModel):
    """An annual or convocation award cycle (CFR-SPACS-013, 015, CW-SPACS-03)."""

    STATUS_CHOICES = [
        ("cycle_open", "Award Cycle Open"),
        ("candidate_pool_prepared", "Candidate Pool Prepared"),
        ("under_committee_evaluation", "Under Committee Evaluation"),
        ("committee_result_recorded", "Committee Result Recorded"),
        ("awaiting_institutional_approval", "Awaiting Institutional Approval"),
        ("ready_for_publication", "Ready for Publication"),
        ("published", "Published"),
    ]

    catalogue_version = models.ForeignKey(
        CatalogueVersion, on_delete=models.PROTECT, related_name="award_cycles"
    )
    convocation_year = models.PositiveIntegerField()
    status = models.CharField(max_length=36, choices=STATUS_CHOICES, default="cycle_open")
    institutional_approval_ref = models.CharField(max_length=200, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "spacs_award_cycle"
        ordering = ["-convocation_year"]

    def __str__(self) -> str:
        return f"{self.catalogue_version.entry.title} ({self.convocation_year}) [{self.status}]"


class AwardCandidate(TimeStampedModel, UserScopedModel):
    """An eligible candidate evaluated for an award (CFR-SPACS-014, BR-SPACS-019)."""

    SHORTLIST_STATUS = [
        ("nominated", "Nominated / In Pool"),
        ("shortlisted", "Shortlisted"),
        ("recommended", "Recommended"),
        ("not_recommended", "Not Recommended"),
    ]
    FINAL_OUTCOME = [("winner", "Award Winner"), ("runner_up", "Runner Up"), ("none", "None")]

    award_cycle = models.ForeignKey(AwardCycle, on_delete=models.CASCADE, related_name="candidates")
    source_method = models.CharField(max_length=24)  # system_generated, application, nomination
    cpi_at_evaluation = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    standing_snapshot = models.JSONField(default=dict, blank=True)

    evaluation_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    committee_remarks = models.TextField(blank=True)
    shortlist_status = models.CharField(
        max_length=24, choices=SHORTLIST_STATUS, default="nominated"
    )
    final_outcome = models.CharField(max_length=16, choices=FINAL_OUTCOME, default="none")

    class Meta:
        db_table = "spacs_award_candidate"
        constraints = [
            models.UniqueConstraint(
                fields=["award_cycle", "user_id"], name="spacs_candidate_unique_per_cycle"
            ),
        ]

    def __str__(self) -> str:
        return f"Cycle #{self.award_cycle_id} Candidate u{self.user_id} ({self.shortlist_status})"
