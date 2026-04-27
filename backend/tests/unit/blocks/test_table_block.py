"""Tests del TableBlock genérico."""
import pytest

from apps.reports.models import Report, TableBlock, TableRow
from apps.reports.tests.factories import make_report


@pytest.mark.django_db
def test_table_block_can_be_created_with_pill_and_show_total():
    report = make_report()
    block = TableBlock.objects.create(
        report=report, order=1,
        title="Instagram", show_total=False,
    )
    assert block.report_id == report.id
    assert block.title == "Instagram"
    assert block.show_total is False


@pytest.mark.django_db
def test_table_rows_persist_cells_as_string_list():
    report = make_report()
    block = TableBlock.objects.create(report=report, order=1, title="IG")
    TableRow.objects.create(
        table_block=block, order=1, is_header=True,
        cells=["Métrica", "Valor", "Δ"],
    )
    TableRow.objects.create(
        table_block=block, order=2, is_header=False,
        cells=["ORGANIC · reach", "312000", "+9.9%"],
    )
    rows = list(block.rows.order_by("order"))
    assert len(rows) == 2
    assert rows[0].is_header is True
    assert rows[0].cells == ["Métrica", "Valor", "Δ"]
    assert rows[1].cells == ["ORGANIC · reach", "312000", "+9.9%"]


@pytest.mark.django_db
def test_table_row_order_is_unique_per_block():
    from django.db import IntegrityError, transaction
    report = make_report()
    block = TableBlock.objects.create(report=report, order=1)
    TableRow.objects.create(table_block=block, order=1, cells=["a"])
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            TableRow.objects.create(table_block=block, order=1, cells=["b"])


@pytest.mark.django_db
def test_table_block_polymorphic_returns_subtype():
    """Asegurar que django-polymorphic devuelve la instancia subtipo."""
    from apps.reports.models import ReportBlock
    report = make_report()
    TableBlock.objects.create(report=report, order=1, title="X")
    fetched = ReportBlock.objects.filter(report=report).first()
    assert isinstance(fetched, TableBlock)


@pytest.mark.django_db
def test_table_block_serializes_with_polymorphic_dispatcher():
    from apps.reports.serializers import ReportBlockSerializer
    report = make_report()
    block = TableBlock.objects.create(
        report=report, order=1, title="IG", show_total=True,
    )
    TableRow.objects.create(
        table_block=block, order=1, is_header=True,
        cells=["Métrica", "Valor", "Δ"],
    )
    TableRow.objects.create(
        table_block=block, order=2,
        cells=["ORGANIC · reach", "312000", "+9.9%"],
    )
    data = ReportBlockSerializer(block).data
    assert data["type"] == "TableBlock"
    assert data["title"] == "IG"
    assert data["show_total"] is True
    assert len(data["rows"]) == 2
    assert data["rows"][0] == {
        "order": 1, "is_header": True,
        "cells": ["Métrica", "Valor", "Δ"],
    }
    assert data["rows"][1] == {
        "order": 2, "is_header": False,
        "cells": ["ORGANIC · reach", "312000", "+9.9%"],
    }
