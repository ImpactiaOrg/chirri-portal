"""Tests de TopContentsBlock + TopContentItem (DEV-129).

Sustituye test_top_content_block.py del modelo viejo con `kind`.
"""
import pytest


@pytest.mark.django_db
def test_top_contents_block_creates_with_items(report_factory):
    from apps.reports.models import TopContentsBlock, TopContentItem
    report = report_factory()
    block = TopContentsBlock.objects.create(
        report=report, order=1, title="Top contenidos",
    )
    TopContentItem.objects.create(
        block=block, order=1, caption="Post genial",
        views=1000, likes=50, comments=5, shares=2, saves=3,
    )
    assert block.items.count() == 1
    item = block.items.first()
    assert item.caption == "Post genial"
    assert item.saves == 3


@pytest.mark.django_db
def test_top_content_item_unique_order_per_block(report_factory):
    from django.db import IntegrityError
    from apps.reports.models import TopContentsBlock, TopContentItem
    report = report_factory()
    block = TopContentsBlock.objects.create(report=report, order=1)
    TopContentItem.objects.create(block=block, order=1, views=100)
    with pytest.raises(IntegrityError):
        TopContentItem.objects.create(block=block, order=1, views=200)


@pytest.mark.django_db
def test_top_content_item_cascade_on_block_delete(report_factory):
    from apps.reports.models import TopContentsBlock, TopContentItem
    report = report_factory()
    block = TopContentsBlock.objects.create(report=report, order=1)
    TopContentItem.objects.create(block=block, order=1, views=100)
    block.delete()
    assert TopContentItem.objects.count() == 0


@pytest.mark.django_db
def test_top_contents_block_limit_default_and_validation(report_factory):
    from django.core.exceptions import ValidationError
    from apps.reports.models import TopContentsBlock
    report = report_factory()
    block = TopContentsBlock.objects.create(report=report, order=1)
    assert block.limit == 6
    block.limit = 100
    with pytest.raises(ValidationError):
        block.full_clean()


@pytest.mark.django_db
def test_top_contents_block_serialized_shape(report_factory):
    """Serializer expone `saves` como campo real (no dentro de un JSON)."""
    from apps.reports.models import TopContentsBlock, TopContentItem
    from apps.reports.serializers import TopContentsBlockSerializer
    report = report_factory()
    block = TopContentsBlock.objects.create(
        report=report, order=1, title="Top contenidos",
    )
    TopContentItem.objects.create(
        block=block, order=1, caption="x", views=1, likes=2,
        comments=3, shares=4, saves=5,
    )
    data = TopContentsBlockSerializer(block).data
    assert data["type"] == "TopContentsBlock"
    item = data["items"][0]
    assert item["saves"] == 5
    assert item["caption"] == "x"
