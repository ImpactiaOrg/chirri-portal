"""ImageBlock: imagen dentro de un card, con pill-title arriba y caption debajo (DEV-130)."""
from django.db import models

from apps.reports.validators import validate_image_mimetype, validate_image_size

from .base_block import ReportBlock


class ImageBlock(ReportBlock):
    image = models.ImageField(
        upload_to="image_blocks/%Y/%m/",
        validators=[validate_image_size, validate_image_mimetype],
    )
    image_alt = models.CharField(max_length=200, blank=True)
    title = models.CharField(
        max_length=200, blank=True,
        help_text="Se renderea como pill title arriba del card.",
    )
    caption = models.TextField(
        blank=True,
        help_text="Se renderea debajo de la imagen, separado por una línea. "
                  "Si está vacío, esa sección se oculta.",
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Image Block"
        verbose_name_plural = "Image Blocks"
