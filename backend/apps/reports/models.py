from django.db import models

from apps.campaigns.models import Stage


class Report(models.Model):
    class Kind(models.TextChoices):
        INFLUENCER = "INFLUENCER", "Influencer"
        GENERAL = "GENERAL", "General"
        QUINCENAL = "QUINCENAL", "Quincenal"
        MENSUAL = "MENSUAL", "Mensual"
        CIERRE_ETAPA = "CIERRE_ETAPA", "Cierre de etapa"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"

    stage = models.ForeignKey(Stage, on_delete=models.CASCADE, related_name="reports")
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.MENSUAL)
    period_start = models.DateField()
    period_end = models.DateField()
    title = models.CharField(
        max_length=300,
        blank=True,
        help_text="Auto-generated from kind + period if left blank.",
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    conclusions_text = models.TextField(blank=True)
    intro_text = models.TextField(
        blank=True,
        help_text="Intro textual al principio del reporte (separada de conclusions_text).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_start", "-created_at"]

    def __str__(self):
        if self.title:
            return self.title
        return f"{self.get_kind_display()} · {self.period_start:%b %Y}"

    @property
    def display_title(self) -> str:
        if self.title:
            return self.title
        return f"{self.get_kind_display()} · {self.period_start:%b %Y}"


class ReportMetric(models.Model):
    """A single metric value in a Report, tagged by network and source type.
    This is the structural separation organic vs influencer vs paid that the portal
    is built around — see design addendum.
    """

    class Network(models.TextChoices):
        INSTAGRAM = "INSTAGRAM", "Instagram"
        TIKTOK = "TIKTOK", "TikTok"
        X = "X", "X/Twitter"

    class SourceType(models.TextChoices):
        ORGANIC = "ORGANIC", "Orgánico"
        INFLUENCER = "INFLUENCER", "Influencer"
        PAID = "PAID", "Pauta"

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="metrics")
    network = models.CharField(max_length=16, choices=Network.choices)
    source_type = models.CharField(max_length=16, choices=SourceType.choices)
    metric_name = models.CharField(
        max_length=100,
        help_text="e.g., reach, impressions, engagement_rate, followers_gained",
    )
    value = models.DecimalField(max_digits=16, decimal_places=4)
    period_comparison = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True,
        help_text="Delta %% vs previous period (e.g., 12.4 for +12.4%%).",
    )

    class Meta:
        indexes = [models.Index(fields=["report", "network", "source_type"])]
        ordering = ["report", "network", "source_type", "metric_name"]

    def __str__(self):
        return f"{self.report} · {self.network}/{self.source_type}/{self.metric_name}={self.value}"
