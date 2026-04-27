"""Builder: ParsedReport → Report+Section+Widgets persistidos."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.core.files.base import ContentFile
from django.db import transaction

from apps.reports.models import (
    ChartDataPointWidget,
    ChartWidget,
    ImageWidget,
    KpiGridWidget,
    KpiTileWidget,
    Report,
    Section,
    TableRowWidget,
    TableWidget,
    TextImageWidget,
    TextWidget,
    TopContentItemWidget,
    TopContentsWidget,
    TopCreatorItemWidget,
    TopCreatorsWidget,
)

from .parsed import ParsedReport, ParsedWidget


@transaction.atomic
def build_report(parsed: ParsedReport, image_bytes: dict[str, bytes], *, stage_id: int) -> Report:
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

    for ps in parsed.sections:
        section = Section.objects.create(
            report=report,
            order=ps.order,
            title=ps.title,
            layout=ps.layout,
            instructions=ps.instructions,
        )
        widgets = parsed.widgets_by_section.get(ps.nombre, [])
        for w in sorted(widgets, key=lambda x: x.widget_orden):
            _BUILDERS[w.type_name](section, w, image_bytes)

    return report


def _build_text(section, w, images):
    TextWidget.objects.create(
        section=section, order=w.widget_orden,
        title=w.widget_title,
        body=w.fields.get("body", ""),
    )


def _build_image(section, w, images):
    iw = ImageWidget(
        section=section, order=w.widget_orden,
        title=w.widget_title,
        image_alt=w.fields.get("image_alt", ""),
        caption=w.fields.get("caption", ""),
    )
    _attach_image(iw, "image", w.fields.get("imagen"), images)
    iw.save()


def _build_textimage(section, w, images):
    iw = TextImageWidget(
        section=section, order=w.widget_orden,
        title=w.widget_title,
        body=w.fields.get("body", ""),
        image_alt=w.fields.get("image_alt", ""),
        image_position=w.fields.get("image_position", "top"),
        columns=int(w.fields.get("columns") or 1),
    )
    _attach_image(iw, "image", w.fields.get("imagen"), images)
    iw.save()


def _build_kpigrid(section, w, images):
    kw = KpiGridWidget.objects.create(
        section=section, order=w.widget_orden, title=w.widget_title,
    )
    KpiTileWidget.objects.bulk_create([
        KpiTileWidget(
            widget=kw,
            order=item.get("tile_orden") or (idx + 1),
            label=str(item.get("label", "")),
            value=_dec(item.get("value"), Decimal("0")),
            unit=str(item.get("unit") or ""),
            period_comparison=_dec(item.get("period_comparison"), None),
            period_comparison_label=str(item.get("period_comparison_label") or ""),
        )
        for idx, item in enumerate(w.items)
    ])


def _build_table(section, w, images):
    tw = TableWidget.objects.create(
        section=section, order=w.widget_orden, title=w.widget_title,
        show_total=bool(w.fields.get("widget_show_total")),
    )
    for idx, item in enumerate(w.items):
        TableRowWidget.objects.create(
            widget=tw,
            order=item.get("row_orden") or (idx + 1),
            is_header=item.get("is_header", False),
            cells=item.get("cells", []),
        )


def _build_chart(section, w, images):
    cw = ChartWidget.objects.create(
        section=section, order=w.widget_orden, title=w.widget_title,
        network=w.fields.get("widget_network"),
        chart_type=w.fields.get("chart_type", "bar"),
    )
    ChartDataPointWidget.objects.bulk_create([
        ChartDataPointWidget(
            widget=cw,
            order=item.get("point_orden") or (idx + 1),
            label=str(item.get("point_label", "")),
            value=_dec(item.get("point_value"), Decimal("0")),
        )
        for idx, item in enumerate(w.items)
    ])


def _build_topcontents(section, w, images):
    tcw = TopContentsWidget.objects.create(
        section=section, order=w.widget_orden, title=w.widget_title,
        network=w.fields.get("widget_network"),
        period_label=w.fields.get("widget_period_label", ""),
    )
    for idx, item in enumerate(w.items):
        child = TopContentItemWidget(
            widget=tcw,
            order=item.get("item_orden") or (idx + 1),
            caption=str(item.get("caption") or ""),
            post_url=str(item.get("post_url") or ""),
            source_type=str(item.get("source_type") or "ORGANIC"),
            views=_int_or_none(item.get("views")),
            likes=_int_or_none(item.get("likes")),
            comments=_int_or_none(item.get("comments")),
            shares=_int_or_none(item.get("shares")),
            saves=_int_or_none(item.get("saves")),
        )
        _attach_image(child, "thumbnail", item.get("imagen"), images)
        child.save()


def _build_topcreators(section, w, images):
    tcw = TopCreatorsWidget.objects.create(
        section=section, order=w.widget_orden, title=w.widget_title,
        network=w.fields.get("widget_network"),
        period_label=w.fields.get("widget_period_label", ""),
    )
    for idx, item in enumerate(w.items):
        child = TopCreatorItemWidget(
            widget=tcw,
            order=item.get("item_orden") or (idx + 1),
            handle=str(item.get("handle", "")),
            post_url=str(item.get("post_url") or ""),
            views=_int_or_none(item.get("views")),
            likes=_int_or_none(item.get("likes")),
            comments=_int_or_none(item.get("comments")),
            shares=_int_or_none(item.get("shares")),
        )
        _attach_image(child, "thumbnail", item.get("imagen"), images)
        child.save()


_BUILDERS = {
    "TextWidget": _build_text,
    "ImageWidget": _build_image,
    "TextImageWidget": _build_textimage,
    "KpiGridWidget": _build_kpigrid,
    "TableWidget": _build_table,
    "ChartWidget": _build_chart,
    "TopContentsWidget": _build_topcontents,
    "TopCreatorsWidget": _build_topcreators,
}


def _attach_image(instance, field_name, filename, images):
    if not filename:
        return
    data = images.get(filename)
    if data is None:
        raise ValueError(f"Imagen '{filename}' no está en el bundle.")
    field = getattr(instance, field_name)
    field.save(filename, ContentFile(data), save=False)


def _dec(value, default):
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def _int_or_none(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None
