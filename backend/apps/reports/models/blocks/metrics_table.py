"""MetricsTableBlock + MetricsTableRow — tabla de métricas (snapshot)."""
from django.db import models

from apps.reports.choices import Network, SourceType

from .base_block import ReportBlock


class MetricsTableBlock(ReportBlock):
    title = models.CharField(max_length=200, blank=True)
    network = models.CharField(
        max_length=16, choices=Network.choices,
        null=True, blank=True,
        help_text=(
            "Metadata hint: red de social para la cual se arma la tabla. "
            "Null = cross-network (ej. 'Mes a mes'). Consumida por el "
            "fetcher AI de Metricool para saber qué data traer."
        ),
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Metrics Table Block"
        verbose_name_plural = "Metrics Table Blocks"


class MetricsTableRow(models.Model):
    metrics_table_block = models.ForeignKey(
        MetricsTableBlock, on_delete=models.CASCADE, related_name="rows",
    )
    metric_name = models.CharField(max_length=100)
    value = models.DecimalField(max_digits=16, decimal_places=4)
    source_type = models.CharField(
        max_length=16, choices=SourceType.choices,
        null=True, blank=True,
    )
    period_comparison = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True,
    )
    order = models.PositiveIntegerField()

    class Meta:
        app_label = "reports"
        ordering = ["metrics_table_block", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["metrics_table_block", "order"],
                name="uniq_row_order_per_metrics_table",
            ),
        ]
