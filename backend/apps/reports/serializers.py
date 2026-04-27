"""Report serializers — post Sections+Widgets refactor.

Estructura: Report → Section[] → Widget[] (polimórfico).
Block legacy serializers se borran en Task 8.
"""
from rest_framework import serializers

from .models import (
    Report, ReportAttachment, Section, Widget,
    TextWidget, ImageWidget, TextImageWidget,
    KpiGridWidget, KpiTileWidget,
    TableWidget, TableRowWidget,
    ChartWidget, ChartDataPointWidget,
    TopContentsWidget, TopContentItemWidget,
    TopCreatorsWidget, TopCreatorItemWidget,
)


# ---------- Child item / row serializers ----------

class KpiTileSerializer(serializers.ModelSerializer):
    class Meta:
        model = KpiTileWidget
        fields = (
            "label", "value", "unit",
            "period_comparison", "period_comparison_label", "order",
        )


class TableRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = TableRowWidget
        fields = ("order", "is_header", "cells")


class ChartDataPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChartDataPointWidget
        fields = ("label", "value", "order")


class TopContentItemSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = TopContentItemWidget
        fields = (
            "order", "thumbnail_url", "caption", "post_url", "source_type",
            "views", "likes", "comments", "shares", "saves",
        )

    def get_thumbnail_url(self, obj) -> str | None:
        return obj.thumbnail.url if obj.thumbnail else None


class TopCreatorItemSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = TopCreatorItemWidget
        fields = (
            "order", "thumbnail_url", "handle", "post_url",
            "views", "likes", "comments", "shares",
        )

    def get_thumbnail_url(self, obj) -> str | None:
        return obj.thumbnail.url if obj.thumbnail else None


# ---------- Widget subtype serializers ----------

BASE_WIDGET_FIELDS = ("id", "order", "title", "instructions")


class TextWidgetSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()

    class Meta:
        model = TextWidget
        fields = BASE_WIDGET_FIELDS + ("type", "body")

    def get_type(self, obj) -> str:
        return "TextWidget"


class ImageWidgetSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ImageWidget
        fields = BASE_WIDGET_FIELDS + ("type", "image_url", "image_alt", "caption")

    def get_type(self, obj) -> str:
        return "ImageWidget"

    def get_image_url(self, obj) -> str | None:
        return obj.image.url if obj.image else None


class TextImageWidgetSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = TextImageWidget
        fields = BASE_WIDGET_FIELDS + (
            "type", "body", "columns", "image_position", "image_alt", "image_url",
        )

    def get_type(self, obj) -> str:
        return "TextImageWidget"

    def get_image_url(self, obj) -> str | None:
        return obj.image.url if obj.image else None


class KpiGridWidgetSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    tiles = KpiTileSerializer(many=True, read_only=True)

    class Meta:
        model = KpiGridWidget
        fields = BASE_WIDGET_FIELDS + ("type", "tiles")

    def get_type(self, obj) -> str:
        return "KpiGridWidget"


class TableWidgetSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    rows = TableRowSerializer(many=True, read_only=True)

    class Meta:
        model = TableWidget
        fields = BASE_WIDGET_FIELDS + ("type", "show_total", "rows")

    def get_type(self, obj) -> str:
        return "TableWidget"


class ChartWidgetSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    data_points = ChartDataPointSerializer(many=True, read_only=True)

    class Meta:
        model = ChartWidget
        fields = BASE_WIDGET_FIELDS + ("type", "network", "chart_type", "data_points")

    def get_type(self, obj) -> str:
        return "ChartWidget"


class TopContentsWidgetSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    items = TopContentItemSerializer(many=True, read_only=True)

    class Meta:
        model = TopContentsWidget
        fields = BASE_WIDGET_FIELDS + ("type", "network", "period_label", "items")

    def get_type(self, obj) -> str:
        return "TopContentsWidget"


class TopCreatorsWidgetSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    items = TopCreatorItemSerializer(many=True, read_only=True)

    class Meta:
        model = TopCreatorsWidget
        fields = BASE_WIDGET_FIELDS + ("type", "network", "period_label", "items")

    def get_type(self, obj) -> str:
        return "TopCreatorsWidget"


# ---------- Polymorphic dispatcher ----------

_WIDGET_SERIALIZERS = {
    TextWidget: TextWidgetSerializer,
    ImageWidget: ImageWidgetSerializer,
    TextImageWidget: TextImageWidgetSerializer,
    KpiGridWidget: KpiGridWidgetSerializer,
    TableWidget: TableWidgetSerializer,
    ChartWidget: ChartWidgetSerializer,
    TopContentsWidget: TopContentsWidgetSerializer,
    TopCreatorsWidget: TopCreatorsWidgetSerializer,
}


class WidgetSerializer(serializers.Serializer):
    """Polymorphic dispatcher. django-polymorphic devuelve la instancia subtipo."""

    def to_representation(self, obj):
        serializer_class = _WIDGET_SERIALIZERS.get(type(obj))
        if serializer_class is None:
            return {"id": obj.id, "order": obj.order, "type": type(obj).__name__}
        return serializer_class(obj, context=self.context).data


# ---------- Section ----------

class SectionSerializer(serializers.ModelSerializer):
    widgets = WidgetSerializer(many=True, read_only=True)

    class Meta:
        model = Section
        fields = ("id", "order", "title", "layout", "instructions", "widgets")


# ---------- Top-level Report ----------

class ReportAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ReportAttachment
        fields = ("id", "title", "url", "mime_type", "size_bytes", "kind", "order")

    def get_url(self, obj) -> str | None:
        return obj.file.url if obj.file else None


class ReportDetailSerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(source="stage.name", read_only=True)
    stage_id = serializers.IntegerField(source="stage.id", read_only=True)
    campaign_name = serializers.CharField(source="stage.campaign.name", read_only=True)
    campaign_id = serializers.IntegerField(source="stage.campaign.id", read_only=True)
    brand_name = serializers.CharField(source="stage.campaign.brand.name", read_only=True)
    display_title = serializers.CharField(read_only=True)
    sections = SectionSerializer(many=True, read_only=True)
    attachments = ReportAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = (
            "id", "kind", "period_start", "period_end",
            "title", "display_title", "status", "published_at",
            "intro_text", "conclusions_text",
            "stage_id", "stage_name",
            "campaign_id", "campaign_name", "brand_name",
            "sections", "attachments",
        )
