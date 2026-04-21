from django.core.exceptions import ValidationError

from .schemas import (
    validate_text_image_config,
    validate_kpi_grid_config,
    validate_metrics_table_config,
    validate_top_content_config,
    validate_attribution_table_config,
    validate_chart_config,
)

BLOCK_VALIDATORS = {
    "TEXT_IMAGE": validate_text_image_config,
    "KPI_GRID": validate_kpi_grid_config,
    "METRICS_TABLE": validate_metrics_table_config,
    "TOP_CONTENT": validate_top_content_config,
    "ATTRIBUTION_TABLE": validate_attribution_table_config,
    "CHART": validate_chart_config,
}


def validate_config(block_type: str, config: dict) -> None:
    validator = BLOCK_VALIDATORS.get(block_type)
    if validator is None:
        raise ValidationError({"type": [f"Tipo de bloque desconocido: {block_type}"]})
    validator(config)
