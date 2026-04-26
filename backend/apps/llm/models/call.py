from django.db import models
from django.db.models import Sum

from .job import LLMJob
from .prompt import PromptVersion


class LLMCall(models.Model):
    """1 row = 1 API call. N calls grouped under one LLMJob."""

    job = models.ForeignKey(
        LLMJob, related_name="calls", on_delete=models.CASCADE,
    )
    prompt_version = models.ForeignKey(
        PromptVersion, on_delete=models.PROTECT,
    )

    provider = models.CharField(max_length=20, default="fireworks")
    model = models.CharField(max_length=100)

    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(
        max_digits=10, decimal_places=6, default=0,
    )

    success = models.BooleanField(default=True)
    error_type = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)

    # Only filled on errors (saves storage on the happy path).
    request_payload = models.JSONField(null=True, blank=True)
    response_payload = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["job", "-created_at"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["model", "-created_at"]),
        ]

    def __str__(self):
        return f"LLMCall#{self.pk} job={self.job_id} ok={self.success}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update denormalized totals on the parent job.
        agg = self.job.calls.aggregate(
            inp=Sum("input_tokens"),
            outp=Sum("output_tokens"),
            cost=Sum("cost_usd"),
        )
        LLMJob.objects.filter(pk=self.job_id).update(
            total_input_tokens=agg["inp"] or 0,
            total_output_tokens=agg["outp"] or 0,
            total_cost_usd=agg["cost"] or 0,
        )
