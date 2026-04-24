"""Tests de TopCreatorsBlock + TopCreatorItem (DEV-129)."""
import pytest


@pytest.mark.django_db
def test_top_creators_block_creates_with_items(report_factory):
    from apps.reports.models import TopCreatorsBlock, TopCreatorItem
    report = report_factory()
    block = TopCreatorsBlock.objects.create(
        report=report, order=1, title="Top creadores",
    )
    TopCreatorItem.objects.create(
        block=block, order=1, handle="@foo",
        views=1000, likes=50, comments=5, shares=2,
    )
    assert block.items.count() == 1
    item = block.items.first()
    assert item.handle == "@foo"


@pytest.mark.django_db
def test_top_creator_item_requires_handle(report_factory):
    from django.core.exceptions import ValidationError
    from apps.reports.models import TopCreatorsBlock, TopCreatorItem
    report = report_factory()
    block = TopCreatorsBlock.objects.create(report=report, order=1)
    item = TopCreatorItem(block=block, order=1)  # handle missing
    with pytest.raises(ValidationError):
        item.full_clean()


@pytest.mark.django_db
def test_top_creator_item_has_no_saves_field(report_factory):
    """Regresión: saves es sólo de TopContentItem (DEV-129)."""
    from apps.reports.models import TopCreatorItem
    fields = {f.name for f in TopCreatorItem._meta.get_fields()}
    assert "saves" not in fields
    assert "handle" in fields


@pytest.mark.django_db
def test_top_creators_block_serialized_shape(report_factory):
    from apps.reports.models import TopCreatorsBlock, TopCreatorItem
    from apps.reports.serializers import TopCreatorsBlockSerializer
    report = report_factory()
    block = TopCreatorsBlock.objects.create(
        report=report, order=1, title="Top creadores",
    )
    TopCreatorItem.objects.create(
        block=block, order=1, handle="@antoroncatti",
        views=8849, likes=None, comments=15, shares=2,
    )
    data = TopCreatorsBlockSerializer(block).data
    assert data["type"] == "TopCreatorsBlock"
    item = data["items"][0]
    assert item["handle"] == "@antoroncatti"
    assert item["likes"] is None
    assert "saves" not in item
