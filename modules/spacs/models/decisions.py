from django.db import models

from core.db.mixins import TimeStampedModel
from modules.spacs.models.applications import ScholarshipApplication


class ScholarshipDecision(TimeStampedModel):
    """Sanction or rejection outcome recorded by SPACS Convener (CFR-SPACS-008, BR-SPACS-018)."""

    DECISIONS = [
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("returned_for_correction", "Returned for Correction"),
    ]

    application = models.ForeignKey(
        ScholarshipApplication, on_delete=models.CASCADE, related_name="decisions"
    )
    decider_id = models.IntegerField(db_index=True)
    decision = models.CharField(max_length=24, choices=DECISIONS)
    sanction_order_ref = models.CharField(max_length=100, blank=True)
    rationale = models.TextField(blank=True)

    class Meta:
        db_table = "spacs_scholarship_decision"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"app#{self.application_id} {self.decision} by u{self.decider_id}"
