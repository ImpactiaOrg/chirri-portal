"""Widget polymorphic base."""
from django.db import models
from polymorphic.models import PolymorphicModel


class Widget(PolymorphicModel):
    section = models.ForeignKey(
        "reports.Section", on_delete=models.CASCADE, related_name="widgets",
    )
    order = models.PositiveIntegerField(db_index=True)
    title = models.CharField(
        max_length=200, blank=True,
        help_text="Subtítulo opcional dentro del widget (no es el pill — el "
                  "pill vive en la Section). Renderizado depende del widget.",
    )
    instructions = models.TextField(
        blank=True,
        help_text="Texto libre para guiar al AI o al operador. No se rendea.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "reports"
        ordering = ["section", "order"]
        indexes = [models.Index(fields=["section", "order"])]
        constraints = [
            models.UniqueConstraint(
                fields=["section", "order"],
                name="uniq_widget_order_per_section",
            ),
        ]

    def __str__(self):
        return f"{self.section_id} · {type(self).__name__} #{self.order}"
