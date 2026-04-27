"""ChartWidget + ChartDataPoint — gráfico bar/line con sus puntos."""
from django.db import models

from apps.reports.choices import Network

from .base_widget import Widget


CHART_TYPES = [("bar", "Bar"), ("line", "Line")]


class ChartWidget(Widget):
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
        verbose_name = "Chart Widget"
        verbose_name_plural = "Chart Widgets"


class ChartDataPointWidget(models.Model):
    """Chart data point linked to ChartWidget. Imported as ChartDataPoint in models/__init__.py."""

    widget = models.ForeignKey(
        ChartWidget, on_delete=models.CASCADE, related_name="data_points",
    )
    label = models.CharField(max_length=60)
    value = models.DecimalField(max_digits=16, decimal_places=4)
    order = models.PositiveIntegerField()

    class Meta:
        app_label = "reports"
        ordering = ["widget", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["widget", "order"],
                name="uniq_point_order_per_chart_widget",
            ),
        ]
