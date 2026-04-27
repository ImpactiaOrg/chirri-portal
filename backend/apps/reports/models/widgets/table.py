"""TableWidget + TableRow — tabla genérica (PowerPoint)."""
from django.db import models

from .base_widget import Widget


class TableWidget(Widget):
    show_total = models.BooleanField(
        default=False,
        help_text=(
            "Si está activado, el frontend agrega una fila 'Total' al final "
            "sumando las columnas numéricas de las filas no-header."
        ),
    )

    class Meta:
        app_label = "reports"
        verbose_name = "Table Widget"
        verbose_name_plural = "Table Widgets"


class TableRowWidget(models.Model):
    """Table row linked to TableWidget. Imported as TableRow in models/__init__.py."""

    widget = models.ForeignKey(
        TableWidget, on_delete=models.CASCADE, related_name="rows",
    )
    order = models.PositiveIntegerField()
    is_header = models.BooleanField(
        default=False,
        help_text="Si está activado, la fila se renderea con estilo de header.",
    )
    cells = models.JSONField(
        default=list,
        help_text="Lista de strings, una por columna.",
    )

    class Meta:
        app_label = "reports"
        ordering = ["widget", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["widget", "order"],
                name="uniq_row_order_per_table_widget",
            ),
        ]

    def __str__(self):
        return f"{self.widget_id} #{self.order}: {self.cells}"
