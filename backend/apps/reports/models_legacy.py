from django.db import models

from apps.campaigns.models import Stage
from .choices import Network, SourceType
from .validators import validate_image_mimetype, validate_image_size


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


class TopContent(models.Model):
    class Kind(models.TextChoices):
        POST = "POST", "Post destacado"
        CREATOR = "CREATOR", "Creator destacado"

    block = models.ForeignKey(
        "TopContentBlock",
        on_delete=models.CASCADE,
        related_name="items",
        help_text="Bloque TOP_CONTENT que renderiza este ítem en el viewer.",
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    network = models.CharField(max_length=16, choices=Network.choices)
    source_type = models.CharField(max_length=16, choices=SourceType.choices)
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
        ordering = ["block", "kind", "network", "rank"]
        indexes = [models.Index(fields=["block", "kind"])]

    def __str__(self):
        return f"{self.block_id} · {self.kind}/{self.network} #{self.rank}"


class BrandFollowerSnapshot(models.Model):
    brand = models.ForeignKey(
        "tenants.Brand",
        on_delete=models.CASCADE,
        related_name="follower_snapshots",
    )
    network = models.CharField(max_length=16, choices=Network.choices)
    as_of = models.DateField()
    followers_count = models.PositiveIntegerField()

    class Meta:
        unique_together = [("brand", "network", "as_of")]
        ordering = ["-as_of"]

    def __str__(self):
        return f"{self.brand_id}/{self.network} @ {self.as_of}: {self.followers_count}"


class OneLinkAttribution(models.Model):
    attribution_block = models.ForeignKey(
        "AttributionTableBlock",
        on_delete=models.CASCADE,
        related_name="entries",
    )
    influencer_handle = models.CharField(max_length=120)
    clicks = models.PositiveIntegerField(default=0)
    app_downloads = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["attribution_block", "-app_downloads"]
        indexes = [models.Index(fields=["attribution_block"])]

    def __str__(self):
        return f"{self.attribution_block_id} · {self.influencer_handle}: {self.app_downloads}d/{self.clicks}c"
