"""Escribe `reporte-template.xlsx` vacío para que Julián lo baje y llene.

Usage:
    python manage.py dump_report_template
    python manage.py dump_report_template --out /tmp/reporte.xlsx

DEV-83 · Etapa 1. Comparte `excel_writer.build_template()` con la vista
admin (Etapa 2), garantizando que CLI y UI emiten el mismo archivo.
"""
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.reports.importers.excel_writer import build_template
from apps.reports.importers.schema import SHEETS_IN_ORDER


class Command(BaseCommand):
    help = "Genera el template xlsx vacío del importer de reports (10 hojas)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--out", type=Path, default=Path("reporte-template.xlsx"),
            help="Path de salida (default: reporte-template.xlsx en cwd).",
        )

    def handle(self, *args, **options):
        out: Path = options["out"]
        buf = build_template()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(buf.getvalue())
        self.stdout.write(self.style.SUCCESS(
            f"Template escrito en {out} ({len(SHEETS_IN_ORDER)} hojas)"
        ))
