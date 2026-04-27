"""TopContentsWidget + TopContentItem — posts/contenidos destacados."""
from django.db import models

from apps.reports.choices import Network, SourceType
from apps.reports.validators import validate_image_mimetype, validate_image_size

from .base_widget import Widget


class TopContentsWidget(Widget):
    network = models.CharField(
        max_length=16, choices=Network.choices,
        null=True, blank=True,
        help_text="Red social de los contenidos destacados.",
    )
    period_label = models.CharField(
        max_length=60, blank=True,
        help_text="Etiqueta de período mostrada en la cabecera, ej. 'febrero'.",
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Top Contenidos Widget"
        verbose_name_plural = "Top Contenidos Widgets"


class TopContentItem(models.Model):
    """Top content item linked to TopContentsWidget."""

    widget = models.ForeignKey(
        TopContentsWidget, on_delete=models.CASCADE, related_name="items",
    )
    order = models.PositiveIntegerField()
    thumbnail = models.ImageField(
        upload_to="top_content/%Y/%m/",
        blank=True,
        validators=[validate_image_size, validate_image_mimetype],
    )
    caption = models.TextField(blank=True)
    post_url = models.URLField(blank=True)
    source_type = models.CharField(
        max_length=16, choices=SourceType.choices, default=SourceType.ORGANIC,
    )
    views = models.PositiveIntegerField(null=True, blank=True)
    likes = models.PositiveIntegerField(null=True, blank=True)
    comments = models.PositiveIntegerField(null=True, blank=True)
    shares = models.PositiveIntegerField(null=True, blank=True)
    saves = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        app_label = "reports"
        ordering = ["widget", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["widget", "order"],
                name="uniq_item_order_per_top_contents_widget",
            ),
        ]
