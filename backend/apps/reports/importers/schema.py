"""Schema centralizado del importer/exporter xlsx (DEV-83).

Mapea columnas del xlsx a fields de los typed blocks. Compartido por
`excel_writer` (template vacío), `excel_exporter` (dump de un report
existente) y — en Etapa 2 — `excel_parser`. Si hay que renombrar una
columna o cambiar un enum, se toca solo acá.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Sheet names — orden fijo (el writer siempre las genera así).
# ---------------------------------------------------------------------------
SHEET_INSTRUCCIONES = "Instrucciones"
SHEET_REPORTE = "Reporte"
SHEET_TEXTIMAGE = "TextImage"
SHEET_IMAGENES = "Imagenes"
SHEET_KPIS = "Kpis"
SHEET_TABLES = "Tables"
SHEET_TOPCONTENTS = "TopContents"
SHEET_TOPCREATORS = "TopCreators"
SHEET_CHARTS = "Charts"

SHEETS_IN_ORDER = [
    SHEET_INSTRUCCIONES,
    SHEET_REPORTE,
    SHEET_TEXTIMAGE,
    SHEET_IMAGENES,
    SHEET_KPIS,
    SHEET_TABLES,
    SHEET_TOPCONTENTS,
    SHEET_TOPCREATORS,
    SHEET_CHARTS,
]

# ---------------------------------------------------------------------------
# Choice label maps — enum value (python) ↔ label en español (xlsx).
# ---------------------------------------------------------------------------
KIND_LABELS = {
    "INFLUENCER": "Influencer",
    "GENERAL": "General",
    "QUINCENAL": "Quincenal",
    "MENSUAL": "Mensual",
    "CIERRE_ETAPA": "Cierre de etapa",
}
KIND_FROM_LABEL = {v: k for k, v in KIND_LABELS.items()}

NETWORK_LABELS = {
    "INSTAGRAM": "Instagram",
    "TIKTOK": "TikTok",
    "X": "X",
}
NETWORK_FROM_LABEL = {v: k for k, v in NETWORK_LABELS.items()}

SOURCE_TYPE_LABELS = {
    "ORGANIC": "Orgánico",
    "INFLUENCER": "Influencer",
    "PAID": "Pauta",
}
SOURCE_TYPE_FROM_LABEL = {v: k for k, v in SOURCE_TYPE_LABELS.items()}

IMAGE_POSITION_VALUES = ["left", "right", "top"]
CHART_TYPE_VALUES = ["bar", "line"]
COLUMNS_VALUES = ["1", "2", "3"]
BOOL_VALUES = ["TRUE", "FALSE"]

# ---------------------------------------------------------------------------
# Headers por hoja — orden matters, el writer los emite en este orden.
# ---------------------------------------------------------------------------
REPORTE_KV_ROWS = [
    ("tipo", "enum", True, "Mensual"),
    ("fecha_inicio", "date", True, "01/04/2026"),
    ("fecha_fin", "date", True, "30/04/2026"),
    ("titulo", "text", False, "Reporte general · Abril"),
    ("intro", "text", False, "Abril fue el mes…"),
    ("conclusiones", "text", False, "El ratio click→download…"),
]

REPORTE_LAYOUT_HEADERS = ["orden", "nombre"]

TEXTIMAGE_HEADERS = [
    "nombre", "title", "body", "imagen", "image_alt",
    "image_position", "columns",
]

IMAGENES_HEADERS = [
    "nombre", "title", "caption", "imagen", "image_alt",
]

KPIS_HEADERS = [
    "nombre", "block_title", "item_orden", "label", "value", "period_comparison",
]

TABLES_HEADERS = [
    "nombre", "block_title", "block_show_total",
    "row_orden", "is_header",
    "cell_1", "cell_2", "cell_3", "cell_4",
    "cell_5", "cell_6", "cell_7", "cell_8",
]

TABLE_CELL_COLS = [f"cell_{i}" for i in range(1, 9)]

TOPCONTENTS_HEADERS = [
    "nombre", "block_title", "block_network", "block_period_label", "block_limit",
    "item_orden", "imagen", "caption", "post_url", "source_type",
    "views", "likes", "comments", "shares", "saves",
]

TOPCREATORS_HEADERS = [
    "nombre", "block_title", "block_network", "block_period_label", "block_limit",
    "item_orden", "imagen", "handle", "post_url",
    "views", "likes", "comments", "shares",
]

CHARTS_HEADERS = [
    "nombre", "block_title", "block_network", "chart_type",
    "point_orden", "point_label", "point_value",
]

SHEET_HEADERS = {
    SHEET_TEXTIMAGE: TEXTIMAGE_HEADERS,
    SHEET_IMAGENES: IMAGENES_HEADERS,
    SHEET_KPIS: KPIS_HEADERS,
    SHEET_TABLES: TABLES_HEADERS,
    SHEET_TOPCONTENTS: TOPCONTENTS_HEADERS,
    SHEET_TOPCREATORS: TOPCREATORS_HEADERS,
    SHEET_CHARTS: CHARTS_HEADERS,
}

# ---------------------------------------------------------------------------
# Dropdowns — (sheet, column_header) → list of valid values.
# El writer inserta DataValidation en el template para estas combinaciones.
# ---------------------------------------------------------------------------
_NETWORK_BLANK = [""] + list(NETWORK_LABELS.values())
_SOURCE_BLANK = [""] + list(SOURCE_TYPE_LABELS.values())

DROPDOWNS = {
    (SHEET_REPORTE, "tipo"): list(KIND_LABELS.values()),
    (SHEET_TEXTIMAGE, "image_position"): IMAGE_POSITION_VALUES,
    (SHEET_TEXTIMAGE, "columns"): COLUMNS_VALUES,
    (SHEET_TABLES, "block_show_total"): BOOL_VALUES,
    (SHEET_TABLES, "is_header"): BOOL_VALUES,
    (SHEET_TOPCONTENTS, "block_network"): _NETWORK_BLANK,
    (SHEET_TOPCONTENTS, "source_type"): _SOURCE_BLANK,
    (SHEET_TOPCREATORS, "block_network"): _NETWORK_BLANK,
    (SHEET_CHARTS, "block_network"): _NETWORK_BLANK,
    (SHEET_CHARTS, "chart_type"): CHART_TYPE_VALUES,
}

# ---------------------------------------------------------------------------
# `nombre` constraint — usado por parser (Etapa 2) y documentado en writer.
# ---------------------------------------------------------------------------
NOMBRE_PATTERN = r"^[a-z0-9_-]{1,60}$"
NOMBRE_MAX_LEN = 60

# ---------------------------------------------------------------------------
# Prefijos por block type — el exporter los usa para generar `nombre`
# legibles (ej. "textimage_1") cuando dump_report_example escupe un report.
# ---------------------------------------------------------------------------
TYPE_PREFIX = {
    "TextImageBlock": "textimage",
    "ImageBlock": "imagen",
    "KpiGridBlock": "kpi",
    "TableBlock": "table",
    "TopContentsBlock": "topcontents",
    "TopCreatorsBlock": "topcreators",
    "ChartBlock": "chart",
}

# ---------------------------------------------------------------------------
# Image upload extensions aceptadas en el ZIP (validación del bundle_reader
# en Etapa 2; el writer las documenta en Instrucciones).
# ---------------------------------------------------------------------------
ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
