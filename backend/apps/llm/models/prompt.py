from django.conf import settings
from django.db import models


class Prompt(models.Model):
    """A named prompt (e.g. 'parse_pdf_report'). Has N versions; one is active."""
    key = models.SlugField(unique=True, max_length=100)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    consumer = models.CharField(
        max_length=100,
        help_text="Informational. e.g. 'reports.pdf_parser'.",
    )
    active_version = models.ForeignKey(
        "PromptVersion", on_delete=models.PROTECT,
        related_name="active_for", null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key


class PromptVersion(models.Model):
    """An immutable snapshot of a Prompt body. Auto-increments per Prompt."""
    RESPONSE_FORMAT_CHOICES = [
        ("text", "Text"),
        ("json_object", "JSON Object"),
    ]

    prompt = models.ForeignKey(
        Prompt, related_name="versions", on_delete=models.CASCADE,
    )
    version = models.PositiveIntegerField()
    body = models.TextField()
    notes = models.CharField(max_length=300, blank=True)
    model_hint = models.CharField(max_length=100, blank=True)
    response_format = models.CharField(
        max_length=20, default="text", choices=RESPONSE_FORMAT_CHOICES,
    )
    json_schema = models.JSONField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("prompt", "version")]
        ordering = ["-version"]

    def __str__(self):
        return f"{self.prompt.key}@v{self.version}"

    def save(self, *args, **kwargs):
        if not self.version:
            last = self.prompt.versions.order_by("-version").first()
            self.version = (last.version + 1) if last else 1
        super().save(*args, **kwargs)
