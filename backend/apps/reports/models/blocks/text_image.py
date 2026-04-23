"""TextImageBlock: bloque narrativo con imagen opcional."""
from django.db import models

from apps.reports.validators import validate_image_mimetype, validate_image_size

from .base_block import ReportBlock


IMAGE_POSITIONS = [
    ("left", "Izquierda"),
    ("right", "Derecha"),
    ("top", "Arriba"),
]

COLUMNS_CHOICES = [(1, "1 columna"), (2, "2 columnas"), (3, "3 columnas")]


class TextImageBlock(ReportBlock):
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    columns = models.PositiveSmallIntegerField(
        choices=COLUMNS_CHOICES, default=1,
    )
    image_position = models.CharField(
        max_length=10, choices=IMAGE_POSITIONS, default="top",
    )
    image_alt = models.CharField(max_length=300, blank=True)
    image = models.ImageField(
        upload_to="report_blocks/%Y/%m/",
        blank=True, null=True,
        validators=[validate_image_size, validate_image_mimetype],
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Text + Image Block"
        verbose_name_plural = "Text + Image Blocks"
