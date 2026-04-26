from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models


class LLMJob(models.Model):
    """1 row = 1 user-triggered request. Aggregates N LLMCalls."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        RUNNING = "RUNNING", "En curso"
        SUCCESS = "SUCCESS", "Éxito"
        FAILED = "FAILED", "Fallido"

    consumer = models.CharField(max_length=100, db_index=True)
    handler_path = models.CharField(max_length=200)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
        db_index=True,
    )

    input_metadata = models.JSONField(default=dict, blank=True)
    output_metadata = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    total_input_tokens = models.PositiveIntegerField(default=0)
    total_output_tokens = models.PositiveIntegerField(default=0)
    total_cost_usd = models.DecimalField(
        max_digits=10, decimal_places=6, default=0,
    )

    result_content_type = models.ForeignKey(
        "contenttypes.ContentType", on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    result_object_id = models.PositiveIntegerField(null=True, blank=True)
    result = GenericForeignKey("result_content_type", "result_object_id")

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["consumer", "-created_at"]),
        ]
        permissions = [
            ("view_costs", "Ver costos LLM"),
        ]

    def __str__(self):
        return f"LLMJob#{self.pk} {self.consumer} {self.status}"
