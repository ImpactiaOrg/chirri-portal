"""validate_import CLI: pasa si el bundle es válido, lista errores si no."""
from io import StringIO

import pytest
from django.core.management import call_command

from apps.reports.importers.excel_writer import build_template


def test_validate_import_empty_template_reports_errors(tmp_path):
    p = tmp_path / "vacio.xlsx"
    p.write_bytes(build_template().getvalue())
    out = StringIO()
    call_command("validate_import", str(p), stdout=out)
    text = out.getvalue()
    assert "error" in text.lower()
    assert "tipo" in text.lower()
    assert "fecha_inicio" in text.lower()


def test_validate_import_missing_file_errors(tmp_path):
    p = tmp_path / "nope.xlsx"
    with pytest.raises(Exception):  # CommandError
        call_command("validate_import", str(p))
