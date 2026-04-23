"""Los modelos legacy que el spec elimina no deberían ser importables.

Regression guard — si alguien reintroduce ReportMetric o las aggregaciones
eliminadas, el test falla.
"""
import pytest


def test_report_metric_gone():
    with pytest.raises(ImportError):
        from apps.reports.models import ReportMetric  # noqa: F401


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
