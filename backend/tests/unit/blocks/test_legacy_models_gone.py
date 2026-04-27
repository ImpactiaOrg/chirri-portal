"""Los modelos legacy que el spec elimina no deberían ser importables.

Regression guard — si alguien reintroduce ReportMetric, MetricsTableBlock,
AttributionTableBlock, OneLinkAttribution, o las aggregaciones eliminadas,
el test falla.
"""
import pytest


def test_report_metric_gone():
    with pytest.raises(ImportError):
        from apps.reports.models import ReportMetric  # noqa: F401


def test_metrics_table_block_gone():
    """MetricsTableBlock eliminado en DEV Task 7 — reemplazado por TableBlock."""
    with pytest.raises(ImportError):
        from apps.reports.models import MetricsTableBlock  # noqa: F401


def test_metrics_table_row_gone():
    with pytest.raises(ImportError):
        from apps.reports.models import MetricsTableRow  # noqa: F401


def test_attribution_table_block_gone():
    """AttributionTableBlock eliminado en DEV Task 7 — reemplazado por TableBlock."""
    with pytest.raises(ImportError):
        from apps.reports.models import AttributionTableBlock  # noqa: F401


def test_onelink_attribution_gone():
    """OneLinkAttribution eliminado en DEV Task 7."""
    with pytest.raises(ImportError):
        from apps.reports.models import OneLinkAttribution  # noqa: F401


def test_aggregations_module_or_functions_gone():
    """build_yoy / build_q1_rollup / build_follower_snapshots eliminados."""
    import importlib
    try:
        mod = importlib.import_module("apps.reports.services.aggregations")
    except ImportError:
        return  # module entero eliminado, OK

    # Si el module sigue ahí, ninguna de las 3 funcs debería estar.
    for func_name in ("build_yoy", "build_q1_rollup", "build_follower_snapshots"):
        assert not hasattr(mod, func_name), f"Expected {func_name} to be gone"
