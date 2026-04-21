"""Tests for ReportBlock config validation enforcement.

Covers:
- DEV-105 reviewer gap: `clean()` must be enforced on `save()` (Django
  does NOT auto-call `clean()`; only ModelForm/admin does). Without this,
  `ReportBlock.objects.create(...)` silently writes invalid configs.
- `has_comparison` boolean filter on METRICS_TABLE must be whitelisted so
  typos like `has_comparasion` don't pass silently.
"""
import pytest
from django.core.exceptions import ValidationError

from apps.reports.blocks.registry import validate_config
from apps.reports.models import ReportBlock

pytestmark = pytest.mark.django_db


def test_save_rejects_invalid_config(balanz_published_report):
    """Regression: DEV-105 shipped clean() but never wired it to save().

    `ReportBlock.objects.create(...)` bypasses full_clean by default in
    Django, so an invalid config (here: empty KPI_GRID tiles list, rejected
    by validate_kpi_grid_config) was silently persisted. save() must call
    full_clean() so create() fails loudly.
    """
    with pytest.raises(ValidationError):
        ReportBlock.objects.create(
            report=balanz_published_report,
            type=ReportBlock.Type.KPI_GRID,
            order=1,
            config={"tiles": []},
        )


def test_metrics_table_accepts_has_comparison_bool():
    """METRICS_TABLE filter must accept `has_comparison: True` — used by
    seed_demo and the MetricsTableBlock frontend. Previously slipped through
    only because the schema did not enforce known filter keys.
    """
    validate_config("METRICS_TABLE", {
        "source": "metrics",
        "filter": {"has_comparison": True},
    })


def test_metrics_table_rejects_has_comparison_non_bool():
    """`has_comparison` must be a bool when present — prevents typos like
    `has_comparison: "yes"` from silently being truthy in the frontend."""
    with pytest.raises(ValidationError):
        validate_config("METRICS_TABLE", {
            "source": "metrics",
            "filter": {"has_comparison": "yes"},
        })


def test_text_image_accepts_image_alt_string():
    """TEXT_IMAGE must whitelist an optional `image_alt` string so editorial
    images can carry accessible alt text instead of the empty-alt decorative
    contract. Flagged in PR review for DEV-105."""
    validate_config("TEXT_IMAGE", {
        "columns": 1,
        "image_position": "top",
        "image_alt": "A screenshot of the dashboard",
    })


def test_text_image_rejects_non_string_image_alt():
    """`image_alt` must be a string when present — reject ints, dicts, etc."""
    with pytest.raises(ValidationError):
        validate_config("TEXT_IMAGE", {
            "columns": 1,
            "image_position": "top",
            "image_alt": 42,
        })
