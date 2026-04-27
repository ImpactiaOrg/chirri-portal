"""Builder: ParsedReport + image_bytes → Report persistido (DEV-83 · Etapa 2).

Corre en `transaction.atomic()`. Si cualquier cosa falla, rollback total
y las imágenes no quedan persistidas. Los ImageField se llenan con
`ContentFile` dentro de la transacción — Django los persiste al llamar
`block.save()`.
"""
from __future__ import annotations

from django.core.files.base import ContentFile
from django.db import transaction

from apps.reports.models import (
    ChartBlock,
    ChartDataPoint,
    ImageBlock,
    KpiGridBlock,
    KpiTile,
    Report,
    TableBlock,
    TableRow,
    TextImageBlock,
    TopContentItem,
    TopContentsBlock,
    TopCreatorItem,
    TopCreatorsBlock,
)

from .parsed import ParsedBlock, ParsedReport


@transaction.atomic
def build_report(
    parsed: ParsedReport, image_bytes: dict[str, bytes], *, stage_id: int,
) -> Report:
    """Crea Report + blocks + items + persiste imágenes. Raises si algo falla."""
    report = Report.objects.create(
        stage_id=stage_id,
        kind=parsed.kind,
        period_start=parsed.period_start,
        period_end=parsed.period_end,
        title=parsed.title,
        intro_text=parsed.intro_text,
        conclusions_text=parsed.conclusions_text,
        status=Report.Status.DRAFT,
    )

    for order, nombre in parsed.layout:
        pb = parsed.blocks[nombre]
        _BUILDERS[pb.type_name](report, order, pb, image_bytes)

    return report


# ---------------------------------------------------------------------------
# Per-type builders
# ---------------------------------------------------------------------------
def _build_textimage(report, order, pb: ParsedBlock, images):
    block = TextImageBlock(
        report=report, order=order,
        title=pb.fields["title"],
        body=pb.fields["body"],
        image_alt=pb.fields["image_alt"],
        image_position=pb.fields["image_position"],
        columns=pb.fields["columns"],
    )
    _attach_image(block, "image", pb.fields.get("imagen"), images)
    block.save()


def _build_imagen(report, order, pb: ParsedBlock, images):
    block = ImageBlock(
        report=report, order=order,
        title=pb.fields["title"],
        caption=pb.fields["caption"],
        image_alt=pb.fields["image_alt"],
    )
    _attach_image(block, "image", pb.fields["imagen"], images)
    block.save()


def _build_kpis(report, order, pb: ParsedBlock, images):
    block = KpiGridBlock.objects.create(
        report=report, order=order, title=pb.fields["block_title"],
    )
    KpiTile.objects.bulk_create([
        KpiTile(
            kpi_grid_block=block,
            order=item.get("item_orden") or (idx + 1),
            label=item["label"],
            value=item["value"],
            period_comparison=item.get("period_comparison"),
        )
        for idx, item in enumerate(pb.items)
    ])


def _build_tables(report, order, pb: ParsedBlock, images):
    block = TableBlock.objects.create(
        report=report, order=order,
        title=pb.fields["block_title"],
        show_total=pb.fields.get("block_show_total", False),
    )
    TableRow.objects.bulk_create([
        TableRow(
            table_block=block,
            order=item["row_orden"],
            is_header=item.get("is_header", False),
            cells=item["cells"],
        )
        for item in pb.items
    ])


def _build_topcontents(report, order, pb: ParsedBlock, images):
    block = TopContentsBlock.objects.create(
        report=report, order=order,
        title=pb.fields["block_title"],
        network=pb.fields.get("block_network"),
        period_label=pb.fields.get("block_period_label", ""),
        limit=_coerce_int_or_default(pb.fields.get("block_limit"), 6),
    )
    for idx, item in enumerate(pb.items):
        child = TopContentItem(
            block=block,
            order=item.get("item_orden") or (idx + 1),
            caption=item.get("caption") or "",
            post_url=item.get("post_url") or "",
            source_type=item.get("source_type") or "ORGANIC",
            views=item.get("views"),
            likes=item.get("likes"),
            comments=item.get("comments"),
            shares=item.get("shares"),
            saves=item.get("saves"),
        )
        _attach_image(child, "thumbnail", item.get("imagen"), images)
        child.save()


def _build_topcreators(report, order, pb: ParsedBlock, images):
    block = TopCreatorsBlock.objects.create(
        report=report, order=order,
        title=pb.fields["block_title"],
        network=pb.fields.get("block_network"),
        period_label=pb.fields.get("block_period_label", ""),
        limit=_coerce_int_or_default(pb.fields.get("block_limit"), 6),
    )
    for idx, item in enumerate(pb.items):
        child = TopCreatorItem(
            block=block,
            order=item.get("item_orden") or (idx + 1),
            handle=item["handle"],
            post_url=item.get("post_url") or "",
            views=item.get("views"),
            likes=item.get("likes"),
            comments=item.get("comments"),
            shares=item.get("shares"),
        )
        _attach_image(child, "thumbnail", item.get("imagen"), images)
        child.save()


def _build_chart(report, order, pb: ParsedBlock, images):
    block = ChartBlock.objects.create(
        report=report, order=order,
        title=pb.fields["block_title"],
        network=pb.fields.get("block_network"),
        chart_type=pb.fields["chart_type"],
    )
    ChartDataPoint.objects.bulk_create([
        ChartDataPoint(
            chart_block=block,
            order=item.get("point_orden") or (idx + 1),
            label=item["point_label"],
            value=item["point_value"],
        )
        for idx, item in enumerate(pb.items)
    ])


_BUILDERS = {
    "TextImageBlock": _build_textimage,
    "ImageBlock": _build_imagen,
    "KpiGridBlock": _build_kpis,
    "TableBlock": _build_tables,
    "TopContentsBlock": _build_topcontents,
    "TopCreatorsBlock": _build_topcreators,
    "ChartBlock": _build_chart,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _attach_image(instance, field_name: str, filename: str | None, images: dict[str, bytes]):
    if not filename:
        return
    data = images.get(filename)
    if data is None:
        # El parser debió detectar esto — si llegó acá es un bug, pero
        # preferimos error explícito a silencio.
        raise ValueError(f"Imagen '{filename}' no está en el bundle.")
    field = getattr(instance, field_name)
    field.save(filename, ContentFile(data), save=False)


def _coerce_int_or_default(value, default: int) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
