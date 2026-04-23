import pytest


@pytest.mark.django_db
def test_top_content_block_requires_kind(report_factory):
    from django.core.exceptions import ValidationError
    from apps.reports.models import TopContentBlock
    report = report_factory()
    block = TopContentBlock(report=report, order=1)  # kind missing
    with pytest.raises(ValidationError):
        block.full_clean()


@pytest.mark.django_db
def test_top_content_block_kind_choices(report_factory):
    from apps.reports.models import TopContentBlock
    report = report_factory()
    block = TopContentBlock.objects.create(report=report, order=1, kind="POST")
    assert block.kind == "POST"


@pytest.mark.django_db
def test_top_content_block_limit_default_and_validation(report_factory):
    from django.core.exceptions import ValidationError
    from apps.reports.models import TopContentBlock
    report = report_factory()
    block = TopContentBlock.objects.create(report=report, order=1, kind="CREATOR")
    assert block.limit == 6
    block.limit = 100
    with pytest.raises(ValidationError):
        block.full_clean()
