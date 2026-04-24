"""bundle_reader: resuelve ZIP/XLSX → (xlsx_bytes, images, errors) (DEV-83 · Etapa 2)."""
import zipfile
from io import BytesIO

from apps.reports.importers.bundle_reader import (
    MAX_IMAGE_SIZE,
    read_bundle,
)
from apps.reports.importers.excel_writer import build_template


def _make_zip(entries: dict[str, bytes]) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_read_bundle_xlsx_alone():
    xlsx = build_template().getvalue()
    out, images, errors = read_bundle(xlsx, filename="reporte.xlsx")
    assert errors == []
    assert out == xlsx
    assert images == {}


def test_read_bundle_zip_with_images():
    xlsx = build_template().getvalue()
    zip_bytes = _make_zip({
        "reporte.xlsx": xlsx,
        "images/hero.jpg": b"fake-jpg-bytes",
        "images/post_1.png": b"fake-png-bytes",
    })
    out, images, errors = read_bundle(zip_bytes, filename="reporte.zip")
    assert errors == []
    assert out == xlsx
    assert set(images.keys()) == {"hero.jpg", "post_1.png"}
    assert images["hero.jpg"] == b"fake-jpg-bytes"


def test_read_bundle_zip_without_xlsx_errors():
    zip_bytes = _make_zip({"images/hero.jpg": b"x"})
    out, images, errors = read_bundle(zip_bytes, filename="reporte.zip")
    assert out is None
    assert len(errors) == 1
    assert "no contiene ningún .xlsx" in errors[0].reason.lower()


def test_read_bundle_rejects_zip_slip():
    # Workaround Windows/posix separators; openpyxl tolera ambos.
    zip_bytes = _make_zip({
        "reporte.xlsx": build_template().getvalue(),
        "images/../../../etc/evil.jpg": b"x",
    })
    out, _images, errors = read_bundle(zip_bytes, filename="reporte.zip")
    assert any("path inseguro" in e.reason.lower() for e in errors)


def test_read_bundle_rejects_image_with_bad_extension():
    zip_bytes = _make_zip({
        "reporte.xlsx": build_template().getvalue(),
        "images/sketchy.exe": b"x",
    })
    out, images, errors = read_bundle(zip_bytes, filename="reporte.zip")
    assert images == {}
    assert any("extensión no permitida" in e.reason.lower() for e in errors)


def test_read_bundle_rejects_multiple_xlsx():
    zip_bytes = _make_zip({
        "reporte.xlsx": build_template().getvalue(),
        "otro.xlsx": build_template().getvalue(),
    })
    out, _images, errors = read_bundle(zip_bytes, filename="reporte.zip")
    assert any("más de un archivo .xlsx" in e.reason.lower() for e in errors)


def test_read_bundle_bad_zip():
    out, _images, errors = read_bundle(b"not-a-zip", filename="reporte.zip")
    assert out is None
    assert any("no es un zip válido" in e.reason.lower() for e in errors)
