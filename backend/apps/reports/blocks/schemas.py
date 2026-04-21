from django.core.exceptions import ValidationError

ALLOWED_NETWORKS = {"INSTAGRAM", "TIKTOK", "X"}
ALLOWED_SOURCE_TYPES = {"ORGANIC", "INFLUENCER", "PAID"}
ALLOWED_KPI_SOURCES = {
    "reach_total", "reach_organic", "reach_influencer",
    "reach_paid", "engagement_total",
}
ALLOWED_METRICS_SOURCES = {"metrics", "yoy", "q1_rollup"}
ALLOWED_IMAGE_POSITIONS = {"left", "right", "top"}
ALLOWED_TOP_CONTENT_KINDS = {"POST", "CREATOR"}
CHART_SUPPORTED_COMBINATIONS = {
    ("follower_snapshots", "network", "bar"),
}


def _require(config, key, typ):
    if key not in config:
        raise ValidationError({"config": [f"Falta key requerida: {key}"]})
    if not isinstance(config[key], typ):
        raise ValidationError({"config": [f"Key '{key}' debe ser {typ.__name__}"]})


def validate_text_image_config(config: dict) -> None:
    cols = config.get("columns")
    if cols not in (1, 2, 3):
        raise ValidationError({"config": ["columns debe ser 1, 2 o 3"]})
    pos = config.get("image_position")
    if pos not in ALLOWED_IMAGE_POSITIONS:
        raise ValidationError({"config": [
            f"image_position debe ser una de {sorted(ALLOWED_IMAGE_POSITIONS)}"
        ]})
    image_alt = config.get("image_alt")
    if image_alt is not None and not isinstance(image_alt, str):
        raise ValidationError({"config": ["image_alt debe ser string"]})


def validate_kpi_grid_config(config: dict) -> None:
    tiles = config.get("tiles")
    if not isinstance(tiles, list) or len(tiles) == 0:
        raise ValidationError({"config": ["tiles debe ser lista no vacía"]})
    for tile in tiles:
        if not isinstance(tile, dict):
            raise ValidationError({"config": ["cada tile debe ser objeto"]})
        if "source" not in tile:
            raise ValidationError({"config": ["tile sin source"]})
        if tile["source"] not in ALLOWED_KPI_SOURCES:
            raise ValidationError({"config": [
                f"source desconocido: {tile['source']}"
            ]})


ALLOWED_METRICS_TABLE_FILTER_KEYS = {"network", "source_type", "has_comparison"}


def validate_metrics_table_config(config: dict) -> None:
    source = config.get("source")
    if source not in ALLOWED_METRICS_SOURCES:
        raise ValidationError({"config": [
            f"source debe ser una de {sorted(ALLOWED_METRICS_SOURCES)}"
        ]})
    flt = config.get("filter", {})
    if not isinstance(flt, dict):
        raise ValidationError({"config": ["filter debe ser objeto"]})
    unknown = set(flt.keys()) - ALLOWED_METRICS_TABLE_FILTER_KEYS
    if unknown:
        raise ValidationError({"config": [
            f"filter keys desconocidas: {sorted(unknown)}"
        ]})
    network = flt.get("network")
    if network is not None and network not in ALLOWED_NETWORKS:
        raise ValidationError({"config": [f"network desconocido: {network}"]})
    stype = flt.get("source_type")
    if stype is not None and stype not in ALLOWED_SOURCE_TYPES:
        raise ValidationError({"config": [f"source_type desconocido: {stype}"]})
    has_comparison = flt.get("has_comparison")
    # Allow None (absent/null) or bool. Reject strings like "yes" that would
    # otherwise be truthy in the frontend.
    if has_comparison is not None and not isinstance(has_comparison, bool):
        raise ValidationError({"config": [
            "filter.has_comparison debe ser boolean"
        ]})


def validate_top_content_config(config: dict) -> None:
    kind = config.get("kind")
    if kind not in ALLOWED_TOP_CONTENT_KINDS:
        raise ValidationError({"config": [
            "kind debe ser POST o CREATOR"
        ]})
    lim = config.get("limit", 6)
    if not isinstance(lim, int) or lim < 1 or lim > 20:
        raise ValidationError({"config": ["limit debe ser int entre 1 y 20"]})


def validate_attribution_table_config(config: dict) -> None:
    show_total = config.get("show_total", True)
    if not isinstance(show_total, bool):
        raise ValidationError({"config": ["show_total debe ser boolean"]})


def validate_chart_config(config: dict) -> None:
    source = config.get("source")
    group_by = config.get("group_by")
    chart_type = config.get("chart_type")
    if (source, group_by, chart_type) not in CHART_SUPPORTED_COMBINATIONS:
        raise ValidationError({"config": [
            "combinación CHART no soportada en fase 1 — solo follower_snapshots + network + bar"
        ]})
