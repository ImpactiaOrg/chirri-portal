"""Network y SourceType viven en choices.py (DEV-116).

Antes estaban acoplados a ReportMetric; ahora el módulo canónico es
apps.reports.choices y los typed blocks leen desde ahí.
"""


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
