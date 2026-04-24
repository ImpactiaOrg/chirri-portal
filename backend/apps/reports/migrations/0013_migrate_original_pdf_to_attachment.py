"""Data migration + drop del `Report.original_pdf` (DEV-108).

Cada Report con `original_pdf` no vacío queda convertido en un
ReportAttachment kind=PDF_REPORT, order=0, title="Reporte (PDF)".
Después se dropea el FileField original.

El reverse no intenta reconstruir `original_pdf` — si hay que volver atrás,
hacerlo por mano o restaurar de backup.
"""
import mimetypes

from django.db import migrations


def forward(apps, schema_editor):
    Report = apps.get_model("reports", "Report")
    ReportAttachment = apps.get_model("reports", "ReportAttachment")

    for report in Report.objects.exclude(original_pdf="").exclude(original_pdf=None):
        file = report.original_pdf
        if not file:
            continue
        mime_type, _ = mimetypes.guess_type(file.name)
        try:
            size_bytes = file.size
        except (FileNotFoundError, ValueError):
            size_bytes = 0
        ReportAttachment.objects.create(
            report=report,
            order=0,
            title="Reporte (PDF)",
            file=file.name,
            mime_type=mime_type or "application/pdf",
            size_bytes=size_bytes,
            kind="PDF_REPORT",
        )


def reverse_noop(apps, schema_editor):
    # No reviviendo original_pdf — si necesitás el rollback, lo hacés a mano.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0012_attachments_model"),
    ]

    operations = [
        migrations.RunPython(forward, reverse_noop),
        migrations.RemoveField(
            model_name="report",
            name="original_pdf",
        ),
    ]
