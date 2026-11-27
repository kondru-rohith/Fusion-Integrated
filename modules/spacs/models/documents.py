from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.spacs.models.applications import ScholarshipApplication


class ApplicationDocument(TimeStampedModel, UserScopedModel):
    """Document evidence linked to applications with reuse support (BR-SPACS-003, AFR-012, 013)."""

    VERIFICATION_STATUS = [
        ("pending", "Pending"),
        ("valid", "Valid"),
        ("invalid", "Invalid"),
        ("resubmission_needed", "Resubmission Needed"),
    ]

    application = models.ForeignKey(
        ScholarshipApplication,
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )
    doc_type = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=160)
    original_filename = models.CharField(max_length=255)
    drive_url = models.URLField(max_length=500)
    drive_file_id = models.CharField(max_length=200)

    issued_date = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_reusable = models.BooleanField(default=True)

    verification_status = models.CharField(
        max_length=24, choices=VERIFICATION_STATUS, default="pending"
    )
    verification_notes = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "spacs_application_document"
        indexes = [
            models.Index(fields=["user_id", "doc_type", "is_active"], name="spacs_doc_reuse_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.doc_type}) - u{self.user_id}"
