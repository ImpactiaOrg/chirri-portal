"""KpiGridWidget + KpiTile — grilla de tiles label/valor."""
from django.db import models

from .base_widget import Widget


class KpiGridWidget(Widget):
    class Meta:
        app_label = "reports"
        verbose_name = "KPI Grid Widget"
        verbose_name_plural = "KPI Grid Widgets"


class KpiTile(models.Model):
    """KPI tile linked to KpiGridWidget."""

    widget = models.ForeignKey(
        KpiGridWidget, on_delete=models.CASCADE, related_name="tiles",
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
        ordering = ["widget", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["widget", "order"],
                name="uniq_tile_order_per_kpi_grid_widget",
            ),
        ]
