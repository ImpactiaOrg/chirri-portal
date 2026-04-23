"""TopContentBlock — lista de top posts o creators destacados."""
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .base_block import ReportBlock


TOP_CONTENT_KINDS = [("POST", "Post destacado"), ("CREATOR", "Creator destacado")]


class TopContentBlock(ReportBlock):
    title = models.CharField(max_length=200, blank=True)
    kind = models.CharField(max_length=16, choices=TOP_CONTENT_KINDS)
    limit = models.PositiveSmallIntegerField(
        default=6,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Top Content Block"
        verbose_name_plural = "Top Content Blocks"
