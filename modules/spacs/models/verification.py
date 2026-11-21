from django.db import models

from core.db.mixins import TimeStampedModel
from modules.spacs.models.applications import ScholarshipApplication


class VerificationFinding(TimeStampedModel):
    """Findings and review actions by SPACS Assistant (CFR-SPACS-006, BR-SPACS-006, 016)."""

    ACTIONS = [
        ("verified", "Marked Verified"),
        ("correction_required", "Correction Requested"),
        ("concern_raised", "Verification Concern Recorded"),
    ]

    application = models.ForeignKey(
        ScholarshipApplication,
        on_delete=models.CASCADE,
        related_name="verification_findings",
    )
    reviewer_id = models.IntegerField(db_index=True)
    action = models.CharField(max_length=24, choices=ACTIONS)
    comments = models.TextField()
    correction_fields = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "spacs_verification_finding"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"app#{self.application_id} {self.action} by u{self.reviewer_id}"
