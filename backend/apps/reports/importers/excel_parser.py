"""Parser del xlsx a `ParsedReport` (DEV-83 · Etapa 2).

Pure function: no toca Django ni modelos. Recibe los bytes del xlsx + el
set de filenames disponibles en el ZIP, valida el contenido y devuelve
(ParsedReport | None, List[ImporterError]). Si hay errores, retorna
ParsedReport=None — el caller no debe intentar commitear.

Estrategia: acumular errores en vez de fail-fast. Así Julián ve todo
junto y corrige en una pasada.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Callable

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from . import schema as s
from .errors import ImporterError
from .parsed import ParsedBlock, ParsedReport


_NOMBRE_RE = re.compile(s.NOMBRE_PATTERN)


def parse(
    xlsx_bytes: bytes,
    available_images: set[str] | frozenset[str] = frozenset(),
) -> tuple[ParsedReport | None, list[ImporterError]]:
    """Parsea el xlsx. Si `errors != []`, `ParsedReport` es None."""
    errors: list[ImporterError] = []

    try:
        wb = load_workbook(BytesIO(xlsx_bytes), data_only=True)
    except Exception:  # noqa: BLE001 — queremos cualquier corrupción
        return None, [ImporterError(
            sheet="(workbook)", row=None, column=None,
            reason="xlsx corrupto o ilegible",
        )]

    # Estructural: todas las hojas deben existir.
    missing = [n for n in s.SHEETS_IN_ORDER if n not in wb.sheetnames]
    if missing:
        for name in missing:
            errors.append(ImporterError(
                sheet=name, row=None, column=None, reason="hoja faltante",
            ))
        return None, errors

    report_scalars, layout, errors_reporte = _parse_reporte(wb[s.SHEET_REPORTE])
    errors.extend(errors_reporte)

    blocks: dict[str, ParsedBlock] = {}
    nombre_to_sheet: dict[str, str] = {}

    for sheet_name, parser_fn in _BLOCK_PARSERS.items():
        parsed_blocks, sheet_errors = parser_fn(wb[sheet_name])
        errors.extend(sheet_errors)
        for pb in parsed_blocks:
            if pb.nombre in nombre_to_sheet:
                errors.append(ImporterError(
                    sheet=sheet_name, row=None, column="nombre",
                    reason=(
                        f"'{pb.nombre}' duplicado — ya existe en hoja "
                        f"{nombre_to_sheet[pb.nombre]}. 'nombre' debe ser "
                        "único en todo el archivo."
                    ),
                ))
                continue
            nombre_to_sheet[pb.nombre] = sheet_name
            blocks[pb.nombre] = pb

    # Cross-reference Layout ↔ hojas de blocks.
    layout_nombres = {n for _, n in layout}
    for orden, nombre in layout:
        if nombre not in blocks:
            errors.append(ImporterError(
                sheet=s.SHEET_REPORTE, row=None, column="nombre",
                reason=(
                    f"'{nombre}' en Layout (orden {orden}) no existe en "
                    "ninguna hoja de blocks."
                ),
            ))

    # Bloques definidos pero no listados en Layout → warning no-bloqueante:
    # acumulamos pero no impedimos el import. El builder solo crea los que
    # están en Layout para no inventar orders ajenos.
    # (decisión: por ahora ni siquiera warning — silencioso. Si se vuelve
    # problema, subir el flag.)

    # Validar image refs contra bundle.
    image_refs: set[str] = set()
    for pb in blocks.values():
        for filename in _collect_image_refs(pb):
            image_refs.add(filename)
    for filename in sorted(image_refs):
        if filename not in available_images:
            errors.append(ImporterError(
                sheet="(images)", row=None, column="imagen",
                reason=(
                    f"imagen '{filename}' referenciada en el Excel pero "
                    "no presente en images/ del ZIP."
                ),
            ))

    if errors:
        return None, errors

    assert report_scalars is not None  # si no hubiera report_scalars, habría errores
    return ParsedReport(
        stage_id=None,
        layout=layout,
        blocks=blocks,
        image_refs=image_refs,
        **report_scalars,
    ), errors


# ---------------------------------------------------------------------------
# Reporte (KV + Layout)
# ---------------------------------------------------------------------------
def _parse_reporte(ws: Worksheet) -> tuple[dict | None, list[tuple[int, str]], list[ImporterError]]:
    errors: list[ImporterError] = []

    # Parsear KV rows. Labels viven en columna A con posible '*', values en B.
    raw_kv: dict[str, object] = {}
    layout_header_row: int | None = None

    for row_idx in range(1, ws.max_row + 1):
        key_cell = ws.cell(row=row_idx, column=1).value
        if not isinstance(key_cell, str):
            continue
        key = key_cell.strip()
        if key.startswith("# Layout"):
            # El header de tabla `orden | nombre` está en la fila siguiente.
            layout_header_row = row_idx + 1
            break
        if key.startswith("#") or key == "":
            continue
        normalized = key.rstrip("*").strip()
        raw_kv[normalized] = ws.cell(row=row_idx, column=2).value

    # Validar y normalizar KV.
    scalars: dict[str, object] = {}
    required_by_key = {key: req for key, _t, req, _ex in s.REPORTE_KV_ROWS}
    type_by_key = {key: t for key, t, _r, _ex in s.REPORTE_KV_ROWS}

    for key, type_hint in type_by_key.items():
        value = raw_kv.get(key)
        required = required_by_key[key]

        if _is_blank(value):
            if required:
                errors.append(ImporterError(
                    sheet=s.SHEET_REPORTE, row=None, column=key,
                    reason="obligatorio",
                ))
            # Defaults para opcionales vacíos
            if type_hint == "text":
                scalars[_kv_dataclass_name(key)] = ""
            continue

        if type_hint == "enum":  # `tipo`
            label = str(value).strip()
            if label not in s.KIND_FROM_LABEL:
                errors.append(ImporterError(
                    sheet=s.SHEET_REPORTE, row=None, column=key,
                    reason=(
                        f"valor '{label}' inválido. Esperado: "
                        + ", ".join(s.KIND_FROM_LABEL)
                    ),
                ))
                continue
            scalars[_kv_dataclass_name(key)] = s.KIND_FROM_LABEL[label]
        elif type_hint == "date":
            d = _parse_date(value)
            if d is None:
                errors.append(ImporterError(
                    sheet=s.SHEET_REPORTE, row=None, column=key,
                    reason=(
                        f"fecha inválida: '{value}'. Formatos aceptados: "
                        "DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD."
                    ),
                ))
                continue
            scalars[_kv_dataclass_name(key)] = d
        elif type_hint == "text":
            scalars[_kv_dataclass_name(key)] = str(value)

    # Parsear Layout rows.
    layout: list[tuple[int, str]] = []
    seen_orders: set[int] = set()
    seen_nombres: set[str] = set()
    if layout_header_row is not None:
        header_cells = [
            ws.cell(row=layout_header_row, column=c).value
            for c in (1, 2)
        ]
        if header_cells != s.REPORTE_LAYOUT_HEADERS:
            errors.append(ImporterError(
                sheet=s.SHEET_REPORTE, row=layout_header_row, column="A/B",
                reason=(
                    f"headers del Layout inesperados: {header_cells}. "
                    f"Esperado: {s.REPORTE_LAYOUT_HEADERS}."
                ),
            ))
        for row_idx in range(layout_header_row + 1, ws.max_row + 1):
            orden_v = ws.cell(row=row_idx, column=1).value
            nombre_v = ws.cell(row=row_idx, column=2).value
            if _is_blank(orden_v) and _is_blank(nombre_v):
                continue
            orden = _coerce_int(orden_v)
            if orden is None or orden < 1:
                errors.append(ImporterError(
                    sheet=s.SHEET_REPORTE, row=row_idx, column="orden",
                    reason=f"entero ≥ 1 esperado, recibí '{orden_v}'",
                ))
                continue
            if orden in seen_orders:
                errors.append(ImporterError(
                    sheet=s.SHEET_REPORTE, row=row_idx, column="orden",
                    reason=f"orden {orden} duplicado en Layout",
                ))
                continue
            seen_orders.add(orden)

            nombre = str(nombre_v or "").strip()
            if not _NOMBRE_RE.match(nombre):
                errors.append(ImporterError(
                    sheet=s.SHEET_REPORTE, row=row_idx, column="nombre",
                    reason=(
                        f"'{nombre}' no cumple el patrón {s.NOMBRE_PATTERN} "
                        f"(max {s.NOMBRE_MAX_LEN} chars, a-z 0-9 _ -)."
                    ),
                ))
                continue
            if nombre in seen_nombres:
                errors.append(ImporterError(
                    sheet=s.SHEET_REPORTE, row=row_idx, column="nombre",
                    reason=f"'{nombre}' duplicado en Layout",
                ))
                continue
            seen_nombres.add(nombre)
            layout.append((orden, nombre))

    layout.sort()
    return (scalars if scalars else None), layout, errors


# ---------------------------------------------------------------------------
# Per-block-type parsers
# ---------------------------------------------------------------------------
def _parse_textimage(ws: Worksheet) -> tuple[list[ParsedBlock], list[ImporterError]]:
    blocks: list[ParsedBlock] = []
    errors: list[ImporterError] = []
    for row_idx, row in _iter_data_rows(ws, s.TEXTIMAGE_HEADERS):
        nombre = _valid_nombre(row, s.SHEET_TEXTIMAGE, row_idx, errors)
        if nombre is None:
            continue
        columns = _coerce_int(row.get("columns"))
        if columns not in (None, 1, 2, 3):
            errors.append(ImporterError(
                sheet=s.SHEET_TEXTIMAGE, row=row_idx, column="columns",
                reason=f"valor '{row.get('columns')}' inválido. Esperado: 1, 2 o 3.",
            ))
        image_position = (row.get("image_position") or "top")
        if image_position not in s.IMAGE_POSITION_VALUES:
            errors.append(ImporterError(
                sheet=s.SHEET_TEXTIMAGE, row=row_idx, column="image_position",
                reason=(
                    f"valor '{image_position}' inválido. Esperado: "
                    + ", ".join(s.IMAGE_POSITION_VALUES)
                ),
            ))
            image_position = "top"
        blocks.append(ParsedBlock(
            type_name="TextImageBlock",
            nombre=nombre,
            fields={
                "title": _str(row.get("title")),
                "body": _str(row.get("body")),
                "imagen": _str(row.get("imagen")),
                "image_alt": _str(row.get("image_alt")),
                "image_position": image_position,
                "columns": columns or 1,
            },
        ))
    return blocks, errors


def _parse_imagenes(ws: Worksheet) -> tuple[list[ParsedBlock], list[ImporterError]]:
    blocks: list[ParsedBlock] = []
    errors: list[ImporterError] = []
    for row_idx, row in _iter_data_rows(ws, s.IMAGENES_HEADERS):
        nombre = _valid_nombre(row, s.SHEET_IMAGENES, row_idx, errors)
        if nombre is None:
            continue
        imagen = _str(row.get("imagen"))
        if not imagen:
            errors.append(ImporterError(
                sheet=s.SHEET_IMAGENES, row=row_idx, column="imagen",
                reason="obligatorio (ImageBlock requiere imagen)",
            ))
            continue
        blocks.append(ParsedBlock(
            type_name="ImageBlock",
            nombre=nombre,
            fields={
                "title": _str(row.get("title")),
                "caption": _str(row.get("caption")),
                "imagen": imagen,
                "image_alt": _str(row.get("image_alt")),
            },
        ))
    return blocks, errors


def _parse_kpis(ws: Worksheet) -> tuple[list[ParsedBlock], list[ImporterError]]:
    return _parse_denormalized(
        ws, s.SHEET_KPIS, s.KPIS_HEADERS,
        type_name="KpiGridBlock",
        block_field_cols=("block_title",),
        item_field_cols=("item_orden", "label", "value", "period_comparison"),
        numeric_item_cols={"value", "period_comparison"},
        required_item_cols=("label", "value"),
    )


def _parse_metricstables(ws: Worksheet) -> tuple[list[ParsedBlock], list[ImporterError]]:
    return _parse_denormalized(
        ws, s.SHEET_METRICSTABLES, s.METRICSTABLES_HEADERS,
        type_name="MetricsTableBlock",
        block_field_cols=("block_title", "block_network"),
        item_field_cols=(
            "item_orden", "metric_name", "value", "source_type", "period_comparison",
        ),
        numeric_item_cols={"value", "period_comparison"},
        enum_item_cols={
            "source_type": (s.SOURCE_TYPE_FROM_LABEL, True),  # (label_map, blank_ok)
        },
        enum_block_cols={
            "block_network": (s.NETWORK_FROM_LABEL, True),
        },
        required_item_cols=("metric_name", "value"),
    )


def _parse_topcontents(ws: Worksheet) -> tuple[list[ParsedBlock], list[ImporterError]]:
    return _parse_denormalized(
        ws, s.SHEET_TOPCONTENTS, s.TOPCONTENTS_HEADERS,
        type_name="TopContentsBlock",
        block_field_cols=(
            "block_title", "block_network", "block_period_label", "block_limit",
        ),
        item_field_cols=(
            "item_orden", "imagen", "caption", "post_url", "source_type",
            "views", "likes", "comments", "shares", "saves",
        ),
        numeric_item_cols={"views", "likes", "comments", "shares", "saves"},
        enum_item_cols={
            "source_type": (s.SOURCE_TYPE_FROM_LABEL, True),
        },
        enum_block_cols={
            "block_network": (s.NETWORK_FROM_LABEL, True),
        },
        required_item_cols=(),
    )


def _parse_topcreators(ws: Worksheet) -> tuple[list[ParsedBlock], list[ImporterError]]:
    return _parse_denormalized(
        ws, s.SHEET_TOPCREATORS, s.TOPCREATORS_HEADERS,
        type_name="TopCreatorsBlock",
        block_field_cols=(
            "block_title", "block_network", "block_period_label", "block_limit",
        ),
        item_field_cols=(
            "item_orden", "imagen", "handle", "post_url",
            "views", "likes", "comments", "shares",
        ),
        numeric_item_cols={"views", "likes", "comments", "shares"},
        enum_block_cols={
            "block_network": (s.NETWORK_FROM_LABEL, True),
        },
        required_item_cols=("handle",),
    )


def _parse_attribution(ws: Worksheet) -> tuple[list[ParsedBlock], list[ImporterError]]:
    blocks, errors = _parse_denormalized(
        ws, s.SHEET_ATTRIBUTION, s.ATTRIBUTION_HEADERS,
        type_name="AttributionTableBlock",
        block_field_cols=("block_title", "block_show_total"),
        item_field_cols=("item_orden", "handle", "clicks", "app_downloads"),
        numeric_item_cols={"clicks", "app_downloads"},
        required_item_cols=(),
    )
    # `block_show_total` es boolean — normalizar TRUE/FALSE a python bool.
    for pb in blocks:
        raw = pb.fields.get("block_show_total")
        pb.fields["block_show_total"] = _coerce_bool(raw)
    # Si un block no tiene items (solo block-level row), eso es válido — admite
    # Attribution vacío (marca sin app). Filtramos el item "placeholder" si solo
    # tenía block fields. El exporter escribe una row con item_orden vacío
    # cuando no hay items; la reconocemos acá.
    for pb in blocks:
        pb.items = [it for it in pb.items if not _is_blank(it.get("handle"))]
    return blocks, errors


def _parse_charts(ws: Worksheet) -> tuple[list[ParsedBlock], list[ImporterError]]:
    blocks, errors = _parse_denormalized(
        ws, s.SHEET_CHARTS, s.CHARTS_HEADERS,
        type_name="ChartBlock",
        block_field_cols=("block_title", "block_network", "chart_type"),
        item_field_cols=("point_orden", "point_label", "point_value"),
        numeric_item_cols={"point_value"},
        enum_block_cols={
            "block_network": (s.NETWORK_FROM_LABEL, True),
        },
        required_item_cols=("point_label", "point_value"),
    )
    # Validar chart_type
    for pb in blocks:
        ct = pb.fields.get("chart_type")
        if ct not in s.CHART_TYPE_VALUES:
            errors.append(ImporterError(
                sheet=s.SHEET_CHARTS, row=None, column="chart_type",
                reason=(
                    f"chart '{pb.nombre}': chart_type '{ct}' inválido. "
                    f"Esperado: {', '.join(s.CHART_TYPE_VALUES)}."
                ),
            ))
    return blocks, errors


_BLOCK_PARSERS: dict[str, Callable[[Worksheet], tuple[list[ParsedBlock], list[ImporterError]]]] = {
    s.SHEET_TEXTIMAGE: _parse_textimage,
    s.SHEET_IMAGENES: _parse_imagenes,
    s.SHEET_KPIS: _parse_kpis,
    s.SHEET_METRICSTABLES: _parse_metricstables,
    s.SHEET_TOPCONTENTS: _parse_topcontents,
    s.SHEET_TOPCREATORS: _parse_topcreators,
    s.SHEET_ATTRIBUTION: _parse_attribution,
    s.SHEET_CHARTS: _parse_charts,
}


# ---------------------------------------------------------------------------
# Generic denormalized sheet parser
# ---------------------------------------------------------------------------
def _parse_denormalized(
    ws: Worksheet,
    sheet_name: str,
    headers: list[str],
    *,
    type_name: str,
    block_field_cols: tuple[str, ...],
    item_field_cols: tuple[str, ...],
    numeric_item_cols: set[str],
    enum_item_cols: dict[str, tuple[dict, bool]] | None = None,
    enum_block_cols: dict[str, tuple[dict, bool]] | None = None,
    required_item_cols: tuple[str, ...] = (),
) -> tuple[list[ParsedBlock], list[ImporterError]]:
    """Parser genérico para hojas denormalizadas (block fields repetidos en cada row).

    - `block_field_cols` + `item_field_cols` deben cubrir todas las cols relevantes.
    - Los rows se agrupan por `nombre`. Para cada grupo:
        · Los block_field_cols deben ser consistentes en todas las rows.
        · Los item_field_cols construyen la lista de items.
    """
    enum_item_cols = enum_item_cols or {}
    enum_block_cols = enum_block_cols or {}
    errors: list[ImporterError] = []
    # nombre → {fields: dict, items: list, first_row: int}
    groups: dict[str, dict] = {}

    for row_idx, row in _iter_data_rows(ws, headers):
        nombre = _valid_nombre(row, sheet_name, row_idx, errors)
        if nombre is None:
            continue

        block_fields = {}
        for col in block_field_cols:
            raw = row.get(col)
            if col in enum_block_cols:
                label_map, blank_ok = enum_block_cols[col]
                val = _parse_enum(raw, label_map, blank_ok, sheet_name, row_idx, col, errors)
            else:
                val = _str(raw) if raw is not None else ""
            block_fields[col] = val

        item = {}
        item_errors_this_row = 0
        for col in item_field_cols:
            raw = row.get(col)
            if col in enum_item_cols:
                label_map, blank_ok = enum_item_cols[col]
                val = _parse_enum(raw, label_map, blank_ok, sheet_name, row_idx, col, errors)
            elif col in numeric_item_cols:
                val = _parse_number(raw, sheet_name, row_idx, col, errors, required=col in required_item_cols)
                if val is None and col in required_item_cols and not _is_blank(raw):
                    item_errors_this_row += 1
            elif col == "item_orden" or col == "point_orden":
                val = _coerce_int(raw) if not _is_blank(raw) else None
            else:
                val = _str(raw) if raw is not None else ""
            item[col] = val

        # Required item fields
        for req_col in required_item_cols:
            if _is_blank(item.get(req_col)):
                errors.append(ImporterError(
                    sheet=sheet_name, row=row_idx, column=req_col,
                    reason="obligatorio",
                ))
                item_errors_this_row += 1

        if nombre not in groups:
            groups[nombre] = {
                "fields": block_fields,
                "items": [],
                "first_row": row_idx,
            }
        else:
            # Block field consistency check
            for col in block_field_cols:
                existing = groups[nombre]["fields"][col]
                new_val = block_fields[col]
                if existing != new_val:
                    errors.append(ImporterError(
                        sheet=sheet_name, row=row_idx, column=col,
                        reason=(
                            f"valor '{new_val}' difiere del usado antes para "
                            f"'{nombre}' ('{existing}'). Los block_* fields "
                            "deben ser idénticos en todos los rows del mismo bloque."
                        ),
                    ))

        if item_errors_this_row == 0:
            groups[nombre]["items"].append(item)

    result = [
        ParsedBlock(
            type_name=type_name,
            nombre=nombre,
            fields=data["fields"],
            items=data["items"],
        )
        for nombre, data in groups.items()
    ]
    return result, errors


# ---------------------------------------------------------------------------
# Image ref collector
# ---------------------------------------------------------------------------
def _collect_image_refs(pb: ParsedBlock):
    """Yields every non-empty filename referenced by the block."""
    # Block-level image (TextImage, Imagenes)
    img = pb.fields.get("imagen")
    if img:
        yield img
    # Item-level thumbnails (TopContents, TopCreators)
    for item in pb.items:
        if item.get("imagen"):
            yield item["imagen"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _iter_data_rows(ws: Worksheet, headers: list[str]):
    """Yields (row_idx, {header: value}) pairs skipping fully-blank rows."""
    for row_idx in range(2, ws.max_row + 1):
        values = [ws.cell(row=row_idx, column=c).value for c in range(1, len(headers) + 1)]
        if all(_is_blank(v) for v in values):
            continue
        yield row_idx, dict(zip(headers, values))


def _valid_nombre(
    row: dict, sheet: str, row_idx: int, errors: list[ImporterError]
) -> str | None:
    raw = row.get("nombre")
    nombre = str(raw or "").strip()
    if not nombre:
        errors.append(ImporterError(
            sheet=sheet, row=row_idx, column="nombre",
            reason="obligatorio",
        ))
        return None
    if not _NOMBRE_RE.match(nombre):
        errors.append(ImporterError(
            sheet=sheet, row=row_idx, column="nombre",
            reason=(
                f"'{nombre}' no cumple el patrón {s.NOMBRE_PATTERN} "
                f"(max {s.NOMBRE_MAX_LEN} chars, a-z 0-9 _ -)."
            ),
        ))
        return None
    return nombre


def _parse_enum(
    raw, label_map: dict, blank_ok: bool,
    sheet: str, row_idx: int, column: str, errors: list[ImporterError],
):
    if _is_blank(raw):
        if blank_ok:
            return None
        errors.append(ImporterError(
            sheet=sheet, row=row_idx, column=column, reason="obligatorio",
        ))
        return None
    label = str(raw).strip()
    if label not in label_map:
        errors.append(ImporterError(
            sheet=sheet, row=row_idx, column=column,
            reason=(
                f"valor '{label}' inválido. Esperado: "
                + ", ".join(label_map)
            ),
        ))
        return None
    return label_map[label]


def _parse_number(
    raw, sheet: str, row_idx: int, column: str,
    errors: list[ImporterError], *, required: bool,
):
    if _is_blank(raw):
        if required:
            errors.append(ImporterError(
                sheet=sheet, row=row_idx, column=column, reason="obligatorio",
            ))
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError):
        errors.append(ImporterError(
            sheet=sheet, row=row_idx, column=column,
            reason=f"número esperado, recibí '{raw}'",
        ))
        return None


def _parse_date(value) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, str):
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _coerce_int(value) -> int | None:
    if _is_blank(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None


def _coerce_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().upper() == "TRUE"
    return bool(value)


def _is_blank(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def _str(v) -> str:
    if v is None:
        return ""
    return str(v)


def _kv_dataclass_name(key: str) -> str:
    """Mapea la label del xlsx al field name del ParsedReport."""
    mapping = {
        "tipo": "kind",
        "fecha_inicio": "period_start",
        "fecha_fin": "period_end",
        "titulo": "title",
        "intro": "intro_text",
        "conclusiones": "conclusions_text",
    }
    return mapping[key]
