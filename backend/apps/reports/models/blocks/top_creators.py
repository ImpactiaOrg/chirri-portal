"""TopCreatorsBlock + TopCreatorItem — creators destacados (DEV-129)."""
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.reports.choices import Network
from apps.reports.validators import validate_image_mimetype, validate_image_size

from .base_block import ReportBlock


class TopCreatorsBlock(ReportBlock):
    title = models.CharField(max_length=200, blank=True, default="Top creadores")
    network = models.CharField(
        max_length=16, choices=Network.choices,
        null=True, blank=True,
        help_text="Red social de los creadores destacados.",
    )
    period_label = models.CharField(
        max_length=60, blank=True,
        help_text="Etiqueta de período mostrada en la cabecera, ej. 'enero'.",
    )
    limit = models.PositiveSmallIntegerField(
        default=6,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Top Creadores Block"
        verbose_name_plural = "Top Creadores Blocks"


class TopCreatorItem(models.Model):
    block = models.ForeignKey(
        TopCreatorsBlock, on_delete=models.CASCADE, related_name="items",
    )
    order = models.PositiveIntegerField()
    thumbnail = models.ImageField(
        upload_to="top_creators/%Y/%m/",
        blank=True,
        validators=[validate_image_size, validate_image_mimetype],
    )
    handle = models.CharField(
        max_length=120,
        help_text="Handle del creator (ej. '@antoroncatti'). Obligatorio.",
    )
    post_url = models.URLField(blank=True)
    views = models.PositiveIntegerField(null=True, blank=True)
    likes = models.PositiveIntegerField(null=True, blank=True)
    comments = models.PositiveIntegerField(null=True, blank=True)
    shares = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        app_label = "reports"
        ordering = ["block", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["block", "order"],
                name="uniq_item_order_per_top_creators",
            ),
        ]

    def __str__(self):
        return f"{self.block_id} · creator {self.handle}"
