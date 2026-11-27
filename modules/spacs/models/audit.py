from django.db import models

from modules.spacs.models.applications import ScholarshipApplication


class ImmutableQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise RuntimeError("Audit records are append-only and cannot be updated.")

    def delete(self):
        raise RuntimeError("Audit records are append-only and cannot be deleted.")


class ApplicationTransition(models.Model):
    """Append-only audit of application state transitions (BR-SPACS-021)."""

    application = models.ForeignKey(
        ScholarshipApplication, on_delete=models.CASCADE, related_name="transitions"
    )
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_label = models.CharField(max_length=80)
    reason = models.CharField(max_length=500, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    objects = ImmutableQuerySet.as_manager()

    class Meta:
        db_table = "spacs_application_transition"
        indexes = [
            models.Index(fields=["application", "at"], name="spacs_app_trans_idx"),
        ]

    def __str__(self) -> str:
        return f"app#{self.application_id} {self.from_status}->{self.to_status} at {self.at}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise RuntimeError("ApplicationTransition records are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("ApplicationTransition records cannot be deleted.")


class SpacsAuditLog(models.Model):
    """Module-level protected audit trail for administrative/policy changes (BR-SPACS-021)."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor_id = models.IntegerField(db_index=True)
    actor_role = models.CharField(max_length=50)
    action = models.CharField(max_length=64, db_index=True)
    target_type = models.CharField(max_length=50)
    target_id = models.CharField(max_length=50)
    details = models.JSONField(default=dict)

    objects = ImmutableQuerySet.as_manager()

    class Meta:
        db_table = "spacs_audit_log"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.created_at} {self.action} by u{self.actor_id} ({self.actor_role})"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise RuntimeError("SpacsAuditLog records are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("SpacsAuditLog records cannot be deleted.")
