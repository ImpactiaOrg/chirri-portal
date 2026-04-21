import pytest
from django.core.exceptions import ValidationError

from apps.reports.blocks.registry import validate_config


# TEXT_IMAGE
def test_text_image_valid():
    validate_config("TEXT_IMAGE", {"title": "t", "text": "x", "columns": 2, "image_position": "left"})


@pytest.mark.parametrize("cols", [0, 4, -1, "two"])
def test_text_image_rejects_bad_columns(cols):
    with pytest.raises(ValidationError):
        validate_config("TEXT_IMAGE", {"columns": cols, "image_position": "left"})


def test_text_image_rejects_bad_image_position():
    with pytest.raises(ValidationError):
        validate_config("TEXT_IMAGE", {"columns": 1, "image_position": "bottom"})


# KPI_GRID
def test_kpi_grid_valid():
    validate_config("KPI_GRID", {"tiles": [{"label": "Reach", "source": "reach_total"}]})


def test_kpi_grid_rejects_empty_tiles():
    with pytest.raises(ValidationError):
        validate_config("KPI_GRID", {"tiles": []})


def test_kpi_grid_rejects_tile_without_source():
    with pytest.raises(ValidationError):
        validate_config("KPI_GRID", {"tiles": [{"label": "Reach"}]})


def test_kpi_grid_rejects_unknown_source():
    with pytest.raises(ValidationError):
        validate_config("KPI_GRID", {"tiles": [{"label": "X", "source": "foo"}]})


# METRICS_TABLE
def test_metrics_table_valid_metrics_source():
    validate_config("METRICS_TABLE", {
        "source": "metrics",
        "filter": {"network": "INSTAGRAM", "source_type": None, "has_comparison": None},
    })


def test_metrics_table_valid_yoy_source():
    validate_config("METRICS_TABLE", {"source": "yoy", "filter": {}})


def test_metrics_table_rejects_unknown_source():
    with pytest.raises(ValidationError):
        validate_config("METRICS_TABLE", {"source": "foo", "filter": {}})


def test_metrics_table_rejects_unknown_network_filter():
    with pytest.raises(ValidationError):
        validate_config("METRICS_TABLE", {"source": "metrics", "filter": {"network": "FACEBOOK"}})


# TOP_CONTENT
def test_top_content_valid_post():
    validate_config("TOP_CONTENT", {"kind": "POST", "limit": 6})


def test_top_content_valid_creator():
    validate_config("TOP_CONTENT", {"kind": "CREATOR"})


def test_top_content_rejects_bad_kind():
    with pytest.raises(ValidationError):
        validate_config("TOP_CONTENT", {"kind": "VIDEO"})


@pytest.mark.parametrize("lim", [0, -1, 21])
def test_top_content_rejects_bad_limit(lim):
    with pytest.raises(ValidationError):
        validate_config("TOP_CONTENT", {"kind": "POST", "limit": lim})


# ATTRIBUTION_TABLE
def test_attribution_table_valid():
    validate_config("ATTRIBUTION_TABLE", {"show_total": True})


def test_attribution_table_valid_defaults():
    validate_config("ATTRIBUTION_TABLE", {})


# CHART
def test_chart_valid_follower_snapshots():
    validate_config("CHART", {
        "source": "follower_snapshots", "group_by": "network", "chart_type": "bar",
    })


def test_chart_rejects_unsupported_source():
    with pytest.raises(ValidationError):
        validate_config("CHART", {"source": "engagement", "group_by": "network", "chart_type": "bar"})


def test_unknown_block_type_raises():
    with pytest.raises(ValidationError):
        validate_config("UNKNOWN", {})
