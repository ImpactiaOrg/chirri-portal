"""ImageWidget — imagen sola con alt + caption opcional."""
from django.db import models

from apps.reports.validators import validate_image_mimetype, validate_image_size

from .base_widget import Widget


class ImageWidget(Widget):
    image = models.ImageField(
        upload_to="image_widgets/%Y/%m/",
        validators=[validate_image_size, validate_image_mimetype],
    )
    image_alt = models.CharField(max_length=200, blank=True)
    caption = models.TextField(
        blank=True,
        help_text="Se renderea debajo de la imagen, separado por una línea. "
                  "Si está vacío, esa sección se oculta.",
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Image Widget"
        verbose_name_plural = "Image Widgets"
