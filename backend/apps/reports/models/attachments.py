"""ReportAttachment — 0..N archivos descargables por reporte (DEV-108).

Generaliza el `Report.original_pdf` que introdujo DEV-105: un reporte puede
exponer múltiples archivos heterogéneos (PDF oficial, Excel con data cruda,
anexo de auditoría, decks, etc.).

`mime_type` y `size_bytes` se cachean en `save()` para que el frontend
pueda mostrar icono + tamaño sin tocar el storage.
"""
from __future__ import annotations

import mimetypes

from django.db import models

from apps.reports.validators import validate_pdf_size  # reuse size cap for now


class ReportAttachment(models.Model):
    class Kind(models.TextChoices):
        PDF_REPORT = "PDF_REPORT", "PDF del reporte"
        DATA_EXPORT = "DATA_EXPORT", "Export de datos"
        ANNEX = "ANNEX", "Anexo"
        OTHER = "OTHER", "Otro"

    report = models.ForeignKey(
        "reports.Report",
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    order = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=200)
    alt_text = models.CharField(
        max_length=255, blank=True,
        help_text="Texto alternativo para accessibility (aria-label). "
                  "Por defecto se usa el nombre del archivo.",
    )
    file = models.FileField(
        upload_to="reports/attachments/%Y/%m/",
        validators=[validate_pdf_size],
        help_text="Cualquier archivo descargable (PDF, XLSX, ZIP, ...).",
    )
    mime_type = models.CharField(max_length=100, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.OTHER,
        help_text="Agrupación liviana para icono/orden en el viewer.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["report", "order", "id"]
        indexes = [models.Index(fields=["report", "order"])]

    def __str__(self):
        return f"{self.report_id} · {self.title}"

    def save(self, *args, **kwargs):
        # Cachear mime_type + size_bytes cada vez que el archivo cambia o al
        # primer save. `content_type` existe sólo en UploadedFile recién
        # subido; al leer del storage fallback a mimetypes.guess_type(name).
        if self.file:
            detected = getattr(self.file, "content_type", None)
            if not detected:
                detected, _ = mimetypes.guess_type(self.file.name)
            self.mime_type = detected or "application/octet-stream"
            try:
                self.size_bytes = self.file.size
            except (FileNotFoundError, ValueError):
                # Si el archivo aún no está persistido (caso raro en tests),
                # dejamos size_bytes en 0 y se actualiza en el próximo save.
                self.size_bytes = 0
        super().save(*args, **kwargs)
