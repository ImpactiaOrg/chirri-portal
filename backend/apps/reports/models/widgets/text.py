"""TextWidget — bloque de texto puro (markdown)."""
from django.db import models

from .base_widget import Widget


class TextWidget(Widget):
    body = models.TextField(blank=True)

    class Meta:
        app_label = "reports"
        verbose_name = "Text Widget"
        verbose_name_plural = "Text Widgets"
