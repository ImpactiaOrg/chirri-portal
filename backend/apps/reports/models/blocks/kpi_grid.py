"""KpiGridBlock + KpiTile — grid de tiles con label + valor."""
from django.db import models

from .base_block import ReportBlock


class KpiGridBlock(ReportBlock):
    title = models.CharField(max_length=200, blank=True)

    class Meta:
        app_label = "reports"
        verbose_name = "KPI Grid Block"
        verbose_name_plural = "KPI Grid Blocks"


class KpiTile(models.Model):
    kpi_grid_block = models.ForeignKey(
        KpiGridBlock, on_delete=models.CASCADE, related_name="tiles",
    )
    label = models.CharField(max_length=120)
    value = models.DecimalField(max_digits=16, decimal_places=4)
    unit = models.CharField(
        max_length=10, blank=True,
        help_text="Unidad mostrada al lado del valor (ej. '%', 'm'). Opcional.",
    )
    period_comparison = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True,
        help_text="Delta % vs periodo anterior. Opcional.",
    )
    period_comparison_label = models.CharField(
        max_length=30, blank=True,
        help_text="Etiqueta del período de comparación (ej. 'vs feb'). Opcional.",
    )
    order = models.PositiveIntegerField()

    class Meta:
        app_label = "reports"
        ordering = ["kpi_grid_block", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["kpi_grid_block", "order"],
                name="uniq_tile_order_per_kpi_grid",
            ),
        ]
