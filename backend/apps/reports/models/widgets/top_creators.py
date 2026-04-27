"""TopCreatorsWidget + TopCreatorItem — creadores destacados."""
from django.db import models

from apps.reports.choices import Network
from apps.reports.validators import validate_image_mimetype, validate_image_size

from .base_widget import Widget


class TopCreatorsWidget(Widget):
    network = models.CharField(
        max_length=16, choices=Network.choices,
        null=True, blank=True,
        help_text="Red social de los creadores destacados.",
    )
    period_label = models.CharField(
        max_length=60, blank=True,
        help_text="Etiqueta de período mostrada en la cabecera, ej. 'enero'.",
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Top Creadores Widget"
        verbose_name_plural = "Top Creadores Widgets"


class TopCreatorItemWidget(models.Model):
    """Top creator item linked to TopCreatorsWidget. Imported as TopCreatorItem in models/__init__.py."""

    widget = models.ForeignKey(
        TopCreatorsWidget, on_delete=models.CASCADE, related_name="items",
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
        ordering = ["widget", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["widget", "order"],
                name="uniq_item_order_per_top_creators_widget",
            ),
        ]
