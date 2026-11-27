from django.db import models

from core.db.mixins import TimeStampedModel


class CatalogueEntry(TimeStampedModel):
    """A scholarship scheme or award category (CFR-SPACS-001, 002)."""

    SCHEME_KINDS = [("scholarship", "Scholarship"), ("award", "Convocation Award")]
    STATUS_CHOICES = [("draft", "Draft"), ("active", "Active"), ("retired", "Retired")]

    code = models.CharField(max_length=32, unique=True, db_index=True)
    title = models.CharField(max_length=200)
    kind = models.CharField(max_length=16, choices=SCHEME_KINDS)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft")
    allow_multiple_applications = models.BooleanField(default=False)

    class Meta:
        db_table = "spacs_catalogue_entry"
        ordering = ["title"]

    def __str__(self) -> str:
        return f"{self.title} ({self.code})"


class CatalogueVersion(TimeStampedModel):
    """An effective-dated, immutable policy version governing cycles (BR-SPACS-014, 015)."""

    STATUS = [("draft", "Draft"), ("published", "Published"), ("retired", "Retired")]
    CANDIDATE_SOURCES = [
        ("student_application", "Student Application"),
        ("system_generated", "System-Generated Academic Pool"),
        ("nomination", "Faculty/Department Nomination"),
    ]

    entry = models.ForeignKey(CatalogueEntry, on_delete=models.PROTECT, related_name="versions")
    version_number = models.PositiveIntegerField(default=1)
    academic_year = models.CharField(max_length=16)  # e.g., "2026-2027"
    policy_reference = models.CharField(max_length=200)  # Required to publish (BR-015)
    candidate_source = models.CharField(
        max_length=24, choices=CANDIDATE_SOURCES, default="student_application"
    )

    valid_from = models.DateField()
    valid_to = models.DateField()
    application_window_start = models.DateTimeField(null=True, blank=True)
    application_window_end = models.DateTimeField(null=True, blank=True)
    renewal_window_start = models.DateTimeField(null=True, blank=True)
    renewal_window_end = models.DateTimeField(null=True, blank=True)

    is_renewable = models.BooleanField(default=False)
    eligibility_criteria = models.JSONField(default=dict, blank=True)
    required_documents = models.JSONField(default=list, blank=True)
    renewal_criteria = models.JSONField(default=dict, blank=True)
    committee_config = models.JSONField(default=dict, blank=True)
    sla_threshold_days = models.PositiveIntegerField(default=7)

    status = models.CharField(max_length=16, choices=STATUS, default="draft")
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "spacs_catalogue_version"
        constraints = [
            models.UniqueConstraint(
                fields=["entry", "version_number"], name="spacs_version_unique_per_entry"
            ),
        ]
        ordering = ["-version_number"]

    def __str__(self) -> str:
        return f"{self.entry.code} v{self.version_number} ({self.academic_year})"
