"""ReportBlock base polimórfico — DEV-116.

Cada subtipo hereda de ReportBlock y aporta sus campos tipados. La base
define lo compartido: FK a Report, order, metadata libre (instructions)
y timestamps. `polymorphic_ctype` lo inyecta django-polymorphic.
"""
from django.db import models
from polymorphic.models import PolymorphicModel


class ReportBlock(PolymorphicModel):
    report = models.ForeignKey(
        "reports.Report", on_delete=models.CASCADE, related_name="blocks",
    )
    order = models.PositiveIntegerField(db_index=True)
    instructions = models.TextField(
        blank=True,
        help_text=(
            "Texto libre para guiar al AI (Metricool auto-fill) o al "
            "operador humano. Ej: 'mostrar solo posts con ads, ignorar "
            "los orgánicos de la campaña Q4 vieja'. No se renderiza en "
            "el viewer público."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "reports"
        db_table = "reports_reportblock"  # preservar table name del legacy
        ordering = ["report", "order"]
        indexes = [models.Index(fields=["report", "order"])]
        constraints = [
            models.UniqueConstraint(
                fields=["report", "order"],
                name="uniq_block_order_per_report",
            ),
        ]

    def __str__(self):
        return f"{self.report_id} · {type(self).__name__} #{self.order}"
