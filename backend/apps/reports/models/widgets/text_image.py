"""TextImageWidget — combo integrado de texto + imagen con layout interno."""
from django.db import models

from apps.reports.validators import validate_image_mimetype, validate_image_size

from .base_widget import Widget


IMAGE_POSITIONS = [
    ("left", "Izquierda"),
    ("right", "Derecha"),
    ("top", "Arriba"),
]

COLUMNS_CHOICES = [(1, "1 columna"), (2, "2 columnas"), (3, "3 columnas")]


class TextImageWidget(Widget):
    body = models.TextField(blank=True)
    columns = models.PositiveSmallIntegerField(
        choices=COLUMNS_CHOICES, default=1,
    )
    image_position = models.CharField(
        max_length=10, choices=IMAGE_POSITIONS, default="top",
    )
    image_alt = models.CharField(max_length=300, blank=True)
    image = models.ImageField(
        upload_to="text_image_widgets/%Y/%m/",
        blank=True, null=True,
        validators=[validate_image_size, validate_image_mimetype],
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Text + Image Widget"
        verbose_name_plural = "Text + Image Widgets"
