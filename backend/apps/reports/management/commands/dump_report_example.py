"""Exporta un Report existente al xlsx del importer (fixture / few-shot).

Usage:
    python manage.py dump_report_example                  # usa "Reporte general · Abril"
    python manage.py dump_report_example --report 42
    python manage.py dump_report_example --out /tmp/x.xlsx

DEV-83 · Etapa 1. El default busca el report kitchen-sink del seed
(_seed_all_blocks_layout en seed_demo) que cubre los 8 block types —
sirve como ejemplo canónico para humanos y LLMs.
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.reports.importers.excel_exporter import export
from apps.reports.importers.schema import SHEETS_IN_ORDER
from apps.reports.models import Report


DEFAULT_EXAMPLE_TITLE = "Reporte general · Abril"


class Command(BaseCommand):
    help = "Exporta un Report existente al xlsx del importer (ejemplo canónico)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--report", type=int, default=None,
            help=(
                "ID del Report a exportar. Si se omite, busca por título "
                f'"{DEFAULT_EXAMPLE_TITLE}" (del seed_demo).'
            ),
        )
        parser.add_argument(
            "--out", type=Path, default=None,
            help="Path de salida. Default: reporte-<id>-ejemplo.xlsx en cwd.",
        )

    def handle(self, *args, **options):
        report = self._resolve_report(options["report"])
        out: Path = options["out"] or Path(f"reporte-{report.pk}-ejemplo.xlsx")

        buf = export(report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(buf.getvalue())
        self.stdout.write(self.style.SUCCESS(
            f"Ejemplo escrito en {out} ({len(SHEETS_IN_ORDER)} hojas, "
            f"report='{report.title or report.display_title}', "
            f"{report.blocks.count()} blocks)"
        ))

    def _resolve_report(self, report_id: int | None) -> Report:
        if report_id is not None:
            try:
                return Report.objects.get(pk=report_id)
            except Report.DoesNotExist as e:
                raise CommandError(f"Report id={report_id} no existe") from e

        report = Report.objects.filter(title=DEFAULT_EXAMPLE_TITLE).first()
        if report is None:
            raise CommandError(
                f'No encontré el report "{DEFAULT_EXAMPLE_TITLE}" del seed. '
                "Corré `python manage.py seed_demo` antes, o pasá --report <id>."
            )
        return report
