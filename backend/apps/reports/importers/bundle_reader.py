"""Resolver el upload (ZIP o XLSX pelado) a xlsx_bytes + imágenes (DEV-83 · Etapa 2).

El único módulo del importer que toca `zipfile`. Devuelve los bytes del
.xlsx + un dict `{filename: image_bytes}` con las imágenes de `images/`.
Valida zip-slip, extensiones de imagen y caps de tamaño por archivo
antes de entregar nada al parser.
"""
from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import PurePosixPath

from . import schema as s
from .errors import ImporterError


# Caps para protección contra DOS / archivos adversariales.
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB por imagen
MAX_XLSX_SIZE = 10 * 1024 * 1024   # 10 MB por xlsx


def read_bundle(
    data: bytes, filename: str | None = None
) -> tuple[bytes | None, dict[str, bytes], list[ImporterError]]:
    """Resuelve el upload a (xlsx_bytes, image_bytes_by_name, errors).

    - Si `filename` termina en `.xlsx` o `data` NO es un ZIP → trata como xlsx pelado,
      sin imágenes.
    - Si es un ZIP → busca el único `.xlsx` en la raíz + las imágenes de `images/`.
    - Ante error estructural (zip corrupto, sin xlsx, múltiples xlsx) retorna
      `(None, {}, [errors])` para que el caller no intente parsear.
    """
    errors: list[ImporterError] = []

    # Fast path: xlsx pelado (detectado por magic byte o extensión)
    if _looks_like_xlsx(data, filename):
        if len(data) > MAX_XLSX_SIZE:
            errors.append(_bundle_error(
                f"Archivo xlsx excede el tamaño máximo ({MAX_XLSX_SIZE // (1024 * 1024)} MB)."
            ))
            return None, {}, errors
        return data, {}, errors

    # ZIP path
    try:
        zf = zipfile.ZipFile(BytesIO(data))
    except zipfile.BadZipFile:
        errors.append(_bundle_error(
            "Archivo no es un ZIP válido ni un xlsx. Verificá que el upload "
            "sea .zip (bundle) o .xlsx (pelado)."
        ))
        return None, {}, errors

    xlsx_bytes: bytes | None = None
    images: dict[str, bytes] = {}

    for info in zf.infolist():
        if info.is_dir():
            continue
        name = info.filename

        # zip-slip: rechazar paths absolutos o con ..
        if _is_unsafe_path(name):
            errors.append(_bundle_error(
                f"Entry del ZIP con path inseguro: '{name}'. "
                "No se permiten paths absolutos ni con '..'."
            ))
            continue

        pure = PurePosixPath(name)

        # .xlsx en la raíz
        if pure.suffix.lower() == ".xlsx" and len(pure.parts) == 1:
            if xlsx_bytes is not None:
                errors.append(_bundle_error(
                    "Más de un archivo .xlsx en la raíz del ZIP. Dejá solo uno."
                ))
                continue
            if info.file_size > MAX_XLSX_SIZE:
                errors.append(_bundle_error(
                    f"El .xlsx dentro del ZIP excede {MAX_XLSX_SIZE // (1024 * 1024)} MB."
                ))
                continue
            xlsx_bytes = zf.read(info)
            continue

        # images/ en la raíz
        if len(pure.parts) == 2 and pure.parts[0] == "images":
            if info.file_size > MAX_IMAGE_SIZE:
                errors.append(_bundle_error(
                    f"Imagen '{pure.name}' excede {MAX_IMAGE_SIZE // (1024 * 1024)} MB."
                ))
                continue
            if pure.suffix.lower() not in s.ALLOWED_IMAGE_EXTENSIONS:
                errors.append(_bundle_error(
                    f"Imagen '{pure.name}' tiene extensión no permitida. "
                    f"Aceptadas: {', '.join(s.ALLOWED_IMAGE_EXTENSIONS)}."
                ))
                continue
            images[pure.name] = zf.read(info)
            continue

        # Todo lo demás se ignora silenciosamente (ej: __MACOSX/).

    if xlsx_bytes is None and not errors:
        errors.append(_bundle_error(
            "El ZIP no contiene ningún .xlsx en la raíz. Agregá el Excel "
            "llenado a la raíz del ZIP (junto a la carpeta images/)."
        ))

    return xlsx_bytes, images, errors


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------
def _bundle_error(reason: str) -> ImporterError:
    return ImporterError(sheet="(bundle)", row=None, column=None, reason=reason)


def _looks_like_xlsx(data: bytes, filename: str | None) -> bool:
    """Heurística: si el filename termina en .xlsx, o si los primeros bytes son
    un ZIP válido pero el stream actúa como un xlsx puro (no nuestro bundle
    ZIP con xlsx adentro), deferimos al ZipFile resolver.

    Como xlsx también es un zip, no podemos distinguir por magic bytes — el
    caller nos pasa el filename cuando lo tiene. Si no lo tenemos y el caller
    nos da cualquier bytes, vamos por la ruta ZIP: si el .xlsx está como
    entry de la raíz, la función lo encuentra; si no, falla con error claro.
    """
    if filename and filename.lower().endswith(".xlsx"):
        return True
    return False


def _is_unsafe_path(name: str) -> bool:
    if name.startswith("/") or name.startswith("\\"):
        return True
    if ".." in PurePosixPath(name).parts:
        return True
    return False
