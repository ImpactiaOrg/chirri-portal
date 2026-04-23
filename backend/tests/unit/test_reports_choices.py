"""Network y SourceType ahora viven en choices.py — evita coupling con
ReportMetric (que se va a eliminar en DEV-116)."""
import pytest


def test_network_choices_importable_from_choices_module():
    from apps.reports.choices import Network
    assert Network.INSTAGRAM == "INSTAGRAM"
    assert Network.TIKTOK == "TIKTOK"
    assert Network.X == "X"


def test_source_type_choices_importable_from_choices_module():
    from apps.reports.choices import SourceType
    assert SourceType.ORGANIC == "ORGANIC"
    assert SourceType.INFLUENCER == "INFLUENCER"
    assert SourceType.PAID == "PAID"


def test_network_choices_backward_compatible_via_reportmetric():
    """Mientras ReportMetric exista (fase transicional), sus choices
    siguen funcionando igual."""
    from apps.reports.models import ReportMetric
    assert ReportMetric.Network.INSTAGRAM == "INSTAGRAM"
