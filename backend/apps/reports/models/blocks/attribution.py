"""AttributionTableBlock — tabla de OneLink attributions."""
from django.db import models

from .base_block import ReportBlock


class AttributionTableBlock(ReportBlock):
    title = models.CharField(max_length=200, blank=True)
    show_total = models.BooleanField(default=True)

    class Meta:
        app_label = "reports"
        verbose_name = "Attribution Table Block"
        verbose_name_plural = "Attribution Table Blocks"
