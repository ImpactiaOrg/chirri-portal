"""Tests para verificar el FK de TopContent post-DEV-116.

Antes: TopContent.block FK apuntaba a ReportBlock (base genérica) y tenía
además TopContent.report FK como denormalización.
Ahora: TopContent.block FK apunta a TopContentBlock específicamente; el
report FK se elimina (derivable via block.report).
"""
import pytest


@pytest.mark.django_db
def test_top_content_block_fk_is_top_content_block(report_factory):
    from apps.reports.models import TopContent, TopContentBlock
    report = report_factory()
    block = TopContentBlock.objects.create(report=report, order=1, kind="POST")
    tc = TopContent.objects.create(
        block=block, kind="POST", network="INSTAGRAM",
        source_type="ORGANIC", rank=1,
    )
    assert tc.block_id == block.id
    # FK target class is TopContentBlock (subtype), not the base ReportBlock
    assert isinstance(tc.block, TopContentBlock)


@pytest.mark.django_db
def test_top_content_report_fk_removed():
    """El FK `report` de TopContent se eliminó — es derivable via block.report."""
    from apps.reports.models import TopContent
    fields = {f.name for f in TopContent._meta.get_fields()}
    assert "report" not in fields
