"""ImageBlock: imagen full-width con overlay opcional (DEV-130)."""
from django.db import models

from apps.reports.validators import validate_image_mimetype, validate_image_size

from .base_block import ReportBlock


OVERLAY_POSITIONS = [
    ("top", "Arriba"),
    ("bottom", "Abajo"),
    ("center", "Centrado"),
    ("none", "Sin overlay"),
]


class ImageBlock(ReportBlock):
    image = models.ImageField(
        upload_to="image_blocks/%Y/%m/",
        validators=[validate_image_size, validate_image_mimetype],
    )
    image_alt = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=200, blank=True)
    caption = models.TextField(blank=True)
    overlay_position = models.CharField(
        max_length=10, choices=OVERLAY_POSITIONS, default="bottom",
        help_text="Dónde pintar el título+caption. 'none' deja la imagen sola.",
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Image Block"
        verbose_name_plural = "Image Blocks"
