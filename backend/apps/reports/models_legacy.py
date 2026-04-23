from django.db import models

from apps.campaigns.models import Stage
from .choices import Network, SourceType
from .validators import (
    validate_image_mimetype, validate_image_size,
    validate_pdf_mimetype, validate_pdf_size,
)


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
    original_pdf = models.FileField(
        upload_to="reports/pdf/%Y/%m/",
        blank=True,
        null=True,
        validators=[validate_pdf_size, validate_pdf_mimetype],
        help_text="PDF original del reporte (Google Slides export), descargable por el cliente.",
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

    # Back-compat aliases — Network y SourceType viven en choices.py ahora.
    Network = Network
    SourceType = SourceType

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


class TopContent(models.Model):
    class Kind(models.TextChoices):
        POST = "POST", "Post destacado"
        CREATOR = "CREATOR", "Creator destacado"

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="top_content")
    block = models.ForeignKey(
        "ReportBlock",
        on_delete=models.CASCADE,
        related_name="items",
        help_text="Bloque TOP_CONTENT que renderiza este ítem en el viewer.",
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    network = models.CharField(max_length=16, choices=ReportMetric.Network.choices)
    source_type = models.CharField(max_length=16, choices=ReportMetric.SourceType.choices)
    rank = models.PositiveIntegerField(help_text="1-based ordering within (kind, network).")
    handle = models.CharField(max_length=120, blank=True)
    caption = models.TextField(blank=True)
    thumbnail = models.ImageField(
        upload_to="top_content/%Y/%m/",
        blank=True,
        validators=[validate_image_size, validate_image_mimetype],
    )
    post_url = models.URLField(blank=True)
    metrics = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["report", "kind", "network", "rank"]
        indexes = [models.Index(fields=["report", "kind"])]

    def save(self, *args, **kwargs):
        # report y block.report siempre viven sincronizados. Esto permite crear
        # TopContent desde el inline del ReportBlockAdmin sin tener que elegir
        # report a mano (se deriva del block padre).
        if self.block_id:
            self.report_id = self.block.report_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.report_id} · {self.kind}/{self.network} #{self.rank}"


class BrandFollowerSnapshot(models.Model):
    brand = models.ForeignKey(
        "tenants.Brand",
        on_delete=models.CASCADE,
        related_name="follower_snapshots",
    )
    network = models.CharField(max_length=16, choices=ReportMetric.Network.choices)
    as_of = models.DateField()
    followers_count = models.PositiveIntegerField()

    class Meta:
        unique_together = [("brand", "network", "as_of")]
        ordering = ["-as_of"]

    def __str__(self):
        return f"{self.brand_id}/{self.network} @ {self.as_of}: {self.followers_count}"


class OneLinkAttribution(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="onelink")
    influencer_handle = models.CharField(max_length=120)
    clicks = models.PositiveIntegerField(default=0)
    app_downloads = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["report", "-app_downloads"]
        indexes = [models.Index(fields=["report"])]

    def __str__(self):
        return f"{self.report_id} · {self.influencer_handle}: {self.app_downloads}d/{self.clicks}c"
