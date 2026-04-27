"""TableBlock + TableRow — tabla genérica (un reporte es un PowerPoint, no un dominio).

Reemplaza MetricsTableBlock + AttributionTableBlock. Los valores de las
celdas son strings; el frontend infiere alineación y formato (números a la
derecha con locale es-AR, deltas con coloreo verde/rojo).
"""
from django.db import models

from .base_block import ReportBlock


class TableBlock(ReportBlock):
    title = models.CharField(
        max_length=200, blank=True,
        help_text="Pill title arriba de la tabla (ej. 'Instagram', 'Atribución OneLink').",
    )
    show_total = models.BooleanField(
        default=False,
        help_text=(
            "Si está activado, el frontend agrega una fila 'Total' al final "
            "sumando las columnas numéricas de las filas no-header."
        ),
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Table Block"
        verbose_name_plural = "Table Blocks"


class TableRow(models.Model):
    table_block = models.ForeignKey(
        TableBlock, on_delete=models.CASCADE, related_name="rows",
    )
    order = models.PositiveIntegerField()
    is_header = models.BooleanField(
        default=False,
        help_text="Si está activado, la fila se renderea con estilo de header (bold + uppercase + bg).",
    )
    cells = models.JSONField(
        default=list,
        help_text="Lista de strings, una por columna. El render formatea números/deltas automáticamente.",
    )

    class Meta:
        app_label = "reports"
        ordering = ["table_block", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["table_block", "order"],
                name="uniq_row_order_per_table",
            ),
        ]

    def __str__(self):
        return f"{self.table_block_id} #{self.order}: {self.cells}"
