"""ChartBlock + ChartDataPoint — gráfico snapshot con sus puntos."""
from django.db import models

from apps.reports.choices import Network

from .base_block import ReportBlock


CHART_TYPES = [("bar", "Bar")]  # extensible a future (line, area, etc.)


class ChartBlock(ReportBlock):
    title = models.CharField(max_length=200, blank=True)
    network = models.CharField(
        max_length=16, choices=Network.choices,
        null=True, blank=True,
        help_text="Metadata hint: red social que el chart representa.",
    )
    chart_type = models.CharField(
        max_length=16, choices=CHART_TYPES, default="bar",
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Chart Block"
        verbose_name_plural = "Chart Blocks"


class ChartDataPoint(models.Model):
    chart_block = models.ForeignKey(
        ChartBlock, on_delete=models.CASCADE, related_name="data_points",
    )
    label = models.CharField(max_length=60)
    value = models.DecimalField(max_digits=16, decimal_places=4)
    order = models.PositiveIntegerField()

    class Meta:
        app_label = "reports"
        ordering = ["chart_block", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["chart_block", "order"],
                name="uniq_point_order_per_chart",
            ),
        ]
