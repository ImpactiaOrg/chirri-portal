"""Valida un bundle (.zip o .xlsx) sin tocar DB (DEV-83 · Etapa 2).

Útil como feedback loop para LLMs/scripts que generan el ZIP: corren esto
antes de subir al admin y ven los errores exactamente igual que los vería
el admin.

Usage:
    python manage.py validate_import reporte.zip
    python manage.py validate_import reporte-abril.xlsx
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.reports.importers.import_flow import validate_bytes


class Command(BaseCommand):
    help = "Valida un bundle de import sin tocar DB. Muestra errores como tabla."

    def add_arguments(self, parser):
        parser.add_argument("bundle", type=Path, help="Ruta al .zip o .xlsx a validar.")

    def handle(self, *args, **options):
        path: Path = options["bundle"]
        if not path.exists():
            raise CommandError(f"Archivo no existe: {path}")

        data = path.read_bytes()
        errors = validate_bytes(data, filename=path.name)

        if not errors:
            self.stdout.write(self.style.SUCCESS(
                f"✓ {path.name} es válido. Listo para importar en el admin."
            ))
            return

        self.stdout.write(self.style.ERROR(
            f"✗ {path.name}: {len(errors)} error(es) encontrado(s)\n"
        ))
        for err in errors:
            loc = f"{err.sheet}"
            if err.row is not None:
                loc += f" fila {err.row}"
            if err.column is not None:
                loc += f" col '{err.column}'"
            self.stdout.write(f"  - {loc}: {err.reason}")
