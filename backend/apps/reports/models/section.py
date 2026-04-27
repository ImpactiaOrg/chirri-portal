"""Section — contenedor de presentación de un Report.

Una Section tiene un pill (título visual) y un layout que define cómo
acomodar sus widgets. Color rotation del pill se calcula en frontend
desde `order` (mint → pink → yellow → white).
"""
from django.db import models


class Section(models.Model):
    class Layout(models.TextChoices):
        STACK = "stack", "Stack vertical"
        COLUMNS_2 = "columns_2", "2 columnas"
        COLUMNS_3 = "columns_3", "3 columnas"

    report = models.ForeignKey(
        "reports.Report", on_delete=models.CASCADE, related_name="sections",
    )
    order = models.PositiveIntegerField(db_index=True)
    title = models.CharField(
        max_length=200, blank=True,
        help_text="Pill title arriba de la sección. Vacío = sin pill.",
    )
    layout = models.CharField(
        max_length=16, choices=Layout.choices, default=Layout.STACK,
        help_text="Cómo acomoda sus widgets. Stack = vertical full-width. "
                  "Columns_2/3 = grid responsive (collapsa a 1 col en mobile).",
    )
    instructions = models.TextField(
        blank=True,
        help_text="Texto libre para guiar al AI o al operador. No se rendea.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "reports"
        ordering = ["report", "order"]
        indexes = [models.Index(fields=["report", "order"])]
        constraints = [
            models.UniqueConstraint(
                fields=["report", "order"],
                name="uniq_section_order_per_report",
            ),
        ]

    def __str__(self):
        return f"{self.report_id} · Section #{self.order}: {self.title or '(sin título)'}"
