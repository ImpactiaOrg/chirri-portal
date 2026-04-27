"""Schema centralizado del importer/exporter xlsx (post sections-widgets-redesign)."""
from __future__ import annotations

# Sheet names — orden fijo
SHEET_INSTRUCCIONES = "Instrucciones"
SHEET_REPORTE = "Reporte"
SHEET_SECTIONS = "Sections"
SHEET_TEXTS = "Texts"
SHEET_IMAGES = "Images"
SHEET_TEXTIMAGES = "TextImages"
SHEET_KPIGRIDS = "KpiGrids"
SHEET_TABLES = "Tables"
SHEET_CHARTS = "Charts"
SHEET_TOPCONTENTS = "TopContents"
SHEET_TOPCREATORS = "TopCreators"

SHEETS_IN_ORDER = [
    SHEET_INSTRUCCIONES,
    SHEET_REPORTE,
    SHEET_SECTIONS,
    SHEET_TEXTS,
    SHEET_IMAGES,
    SHEET_TEXTIMAGES,
    SHEET_KPIGRIDS,
    SHEET_TABLES,
    SHEET_CHARTS,
    SHEET_TOPCONTENTS,
    SHEET_TOPCREATORS,
]

WIDGET_SHEETS = [
    SHEET_TEXTS, SHEET_IMAGES, SHEET_TEXTIMAGES, SHEET_KPIGRIDS,
    SHEET_TABLES, SHEET_CHARTS, SHEET_TOPCONTENTS, SHEET_TOPCREATORS,
]

# Layout choices
LAYOUT_VALUES = ["stack", "columns_2", "columns_3"]

# Choice label maps (igual que hoy)
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

# REPORTE KV (sin la tabla Layout — eliminada)
REPORTE_KV_ROWS = [
    ("tipo", "enum", True, "Mensual"),
    ("fecha_inicio", "date", True, "01/04/2026"),
    ("fecha_fin", "date", True, "30/04/2026"),
    ("titulo", "text", False, "Reporte general · Abril"),
    ("intro", "text", False, "Abril fue el mes…"),
    ("conclusiones", "text", False, "El ratio click→download…"),
]

SECTIONS_HEADERS = ["nombre", "title", "layout", "order", "instructions"]

TEXTS_HEADERS = ["section_nombre", "widget_orden", "widget_title", "body"]

IMAGES_HEADERS = [
    "section_nombre", "widget_orden", "widget_title",
    "imagen", "image_alt", "caption",
]

TEXTIMAGES_HEADERS = [
    "section_nombre", "widget_orden", "widget_title",
    "body", "imagen", "image_alt", "image_position", "columns",
]

KPIGRIDS_HEADERS = [
    "section_nombre", "widget_orden", "widget_title",
    "tile_orden", "label", "value", "unit",
    "period_comparison", "period_comparison_label",
]

TABLES_HEADERS = [
    "section_nombre", "widget_orden", "widget_title", "widget_show_total",
    "row_orden", "is_header",
    "cell_1", "cell_2", "cell_3", "cell_4",
    "cell_5", "cell_6", "cell_7", "cell_8",
]

TABLE_CELL_COLS = [f"cell_{i}" for i in range(1, 9)]

CHARTS_HEADERS = [
    "section_nombre", "widget_orden", "widget_title",
    "widget_network", "chart_type",
    "point_orden", "point_label", "point_value",
]

TOPCONTENTS_HEADERS = [
    "section_nombre", "widget_orden", "widget_title",
    "widget_network", "widget_period_label",
    "item_orden", "imagen", "caption", "post_url", "source_type",
    "views", "likes", "comments", "shares", "saves",
]

TOPCREATORS_HEADERS = [
    "section_nombre", "widget_orden", "widget_title",
    "widget_network", "widget_period_label",
    "item_orden", "imagen", "handle", "post_url",
    "views", "likes", "comments", "shares",
]

SHEET_HEADERS = {
    SHEET_SECTIONS: SECTIONS_HEADERS,
    SHEET_TEXTS: TEXTS_HEADERS,
    SHEET_IMAGES: IMAGES_HEADERS,
    SHEET_TEXTIMAGES: TEXTIMAGES_HEADERS,
    SHEET_KPIGRIDS: KPIGRIDS_HEADERS,
    SHEET_TABLES: TABLES_HEADERS,
    SHEET_CHARTS: CHARTS_HEADERS,
    SHEET_TOPCONTENTS: TOPCONTENTS_HEADERS,
    SHEET_TOPCREATORS: TOPCREATORS_HEADERS,
}

_NETWORK_BLANK = [""] + list(NETWORK_LABELS.values())
_SOURCE_BLANK = [""] + list(SOURCE_TYPE_LABELS.values())

DROPDOWNS = {
    (SHEET_REPORTE, "tipo"): list(KIND_LABELS.values()),
    (SHEET_SECTIONS, "layout"): LAYOUT_VALUES,
    (SHEET_TEXTIMAGES, "image_position"): IMAGE_POSITION_VALUES,
    (SHEET_TEXTIMAGES, "columns"): COLUMNS_VALUES,
    (SHEET_TABLES, "widget_show_total"): BOOL_VALUES,
    (SHEET_TABLES, "is_header"): BOOL_VALUES,
    (SHEET_CHARTS, "widget_network"): _NETWORK_BLANK,
    (SHEET_CHARTS, "chart_type"): CHART_TYPE_VALUES,
    (SHEET_TOPCONTENTS, "widget_network"): _NETWORK_BLANK,
    (SHEET_TOPCONTENTS, "source_type"): _SOURCE_BLANK,
    (SHEET_TOPCREATORS, "widget_network"): _NETWORK_BLANK,
}

NOMBRE_PATTERN = r"^[a-z0-9_-]{1,60}$"
NOMBRE_MAX_LEN = 60

TYPE_PREFIX = {
    "TextWidget": "text",
    "ImageWidget": "imagen",
    "TextImageWidget": "textimage",
    "KpiGridWidget": "kpi",
    "TableWidget": "table",
    "ChartWidget": "chart",
    "TopContentsWidget": "topcontents",
    "TopCreatorsWidget": "topcreators",
}

ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
