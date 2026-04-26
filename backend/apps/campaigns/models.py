from django.db import models

from apps.tenants.models import Brand


class Campaign(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        FINISHED = "FINISHED", "Finished"
        PAUSED = "PAUSED", "Paused"

    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="campaigns")
    name = models.CharField(max_length=200)
    mother_concept = models.TextField(blank=True)
    tagline = models.CharField(max_length=300, blank=True)
    objective = models.TextField(blank=True)
    brief = models.TextField(
        blank=True,
        help_text="Narrative short description for the portal header.",
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    is_ongoing_operation = models.BooleanField(
        default=False,
        help_text="True for implicit 'Operación continua' campaigns used by brands without structured campaigns.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-status", "-start_date"]

    def __str__(self):
        return f"{self.brand.name} · {self.name}"


class Stage(models.Model):
    class Kind(models.TextChoices):
        AWARENESS = "AWARENESS", "Awareness"
        EDUCATION = "EDUCATION", "Educación"
        VALIDATION = "VALIDATION", "Validación"
        CONVERSION = "CONVERSION", "Conversión"
        ONGOING = "ONGOING", "Ongoing"
        OTHER = "OTHER", "Other"

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="stages")
    order = models.PositiveIntegerField(default=1)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.OTHER)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["campaign", "order"]
        unique_together = [("campaign", "order")]

    def __str__(self):
        return f"{self.campaign.name} · {self.name}"
