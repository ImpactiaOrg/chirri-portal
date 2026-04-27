"""Report serializers - post-DEV-116.

ReportBlockSerializer es polimórfico: despacha a un sub-serializer por
subtipo. Los campos agregados cross-report (yoy, q1_rollup, follower_snapshots)
se eliminaron porque dependían de ReportMetric, que ya no existe.
"""
from rest_framework import serializers

from .models import (
    Report, ReportAttachment,
    TextImageBlock, ImageBlock, KpiGridBlock, KpiTile,
    TableBlock, TableRow,
    TopContentsBlock, TopContentItem,
    TopCreatorsBlock, TopCreatorItem,
    ChartBlock, ChartDataPoint,
)


# ---------- Child row serializers ----------

class KpiTileSerializer(serializers.ModelSerializer):
    class Meta:
        model = KpiTile
        fields = (
            "label", "value", "unit",
            "period_comparison", "period_comparison_label", "order",
        )


class ChartDataPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChartDataPoint
        fields = ("label", "value", "order")


class TopContentItemSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = TopContentItem
        fields = (
            "order", "thumbnail_url", "caption", "post_url", "source_type",
            "views", "likes", "comments", "shares", "saves",
        )

    def get_thumbnail_url(self, obj) -> str | None:
        return obj.thumbnail.url if obj.thumbnail else None


class TopCreatorItemSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = TopCreatorItem
        fields = (
            "order", "thumbnail_url", "handle", "post_url",
            "views", "likes", "comments", "shares",
        )

    def get_thumbnail_url(self, obj) -> str | None:
        return obj.thumbnail.url if obj.thumbnail else None


class TableRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = TableRow
        fields = ("order", "is_header", "cells")


# ---------- Subtype block serializers ----------

BASE_BLOCK_FIELDS = ("id", "order", "instructions")


class TextImageBlockSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = TextImageBlock
        fields = BASE_BLOCK_FIELDS + (
            "type", "title", "body", "columns", "image_position", "image_alt",
            "image_url",
        )

    def get_type(self, obj) -> str:
        return "TextImageBlock"

    def get_image_url(self, obj) -> str | None:
        return obj.image.url if obj.image else None


class ImageBlockSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ImageBlock
        fields = BASE_BLOCK_FIELDS + (
            "type", "image_url", "image_alt", "title", "caption",
        )

    def get_type(self, obj) -> str:
        return "ImageBlock"

    def get_image_url(self, obj) -> str | None:
        return obj.image.url if obj.image else None


class KpiGridBlockSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    tiles = KpiTileSerializer(many=True, read_only=True)

    class Meta:
        model = KpiGridBlock
        fields = BASE_BLOCK_FIELDS + ("type", "title", "tiles")

    def get_type(self, obj) -> str:
        return "KpiGridBlock"


class TableBlockSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    rows = TableRowSerializer(many=True, read_only=True)

    class Meta:
        model = TableBlock
        fields = BASE_BLOCK_FIELDS + ("type", "title", "show_total", "rows")

    def get_type(self, obj) -> str:
        return "TableBlock"


class TopContentsBlockSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    items = TopContentItemSerializer(many=True, read_only=True)

    class Meta:
        model = TopContentsBlock
        fields = BASE_BLOCK_FIELDS + (
            "type", "title", "network", "period_label", "limit", "items",
        )

    def get_type(self, obj) -> str:
        return "TopContentsBlock"


class TopCreatorsBlockSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    items = TopCreatorItemSerializer(many=True, read_only=True)

    class Meta:
        model = TopCreatorsBlock
        fields = BASE_BLOCK_FIELDS + (
            "type", "title", "network", "period_label", "limit", "items",
        )

    def get_type(self, obj) -> str:
        return "TopCreatorsBlock"


class ChartBlockSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    data_points = ChartDataPointSerializer(many=True, read_only=True)

    class Meta:
        model = ChartBlock
        fields = BASE_BLOCK_FIELDS + (
            "type", "title", "description", "network", "chart_type", "data_points",
        )

    def get_type(self, obj) -> str:
        return "ChartBlock"


# ---------- Polymorphic dispatcher (manual, sin dep externa) ----------

_BLOCK_SERIALIZERS = {
    TextImageBlock: TextImageBlockSerializer,
    ImageBlock: ImageBlockSerializer,
    KpiGridBlock: KpiGridBlockSerializer,
    TableBlock: TableBlockSerializer,
    TopContentsBlock: TopContentsBlockSerializer,
    TopCreatorsBlock: TopCreatorsBlockSerializer,
    ChartBlock: ChartBlockSerializer,
}


class ReportBlockSerializer(serializers.Serializer):
    """Polymorphic dispatcher. Acepta un ReportBlock (base o subtipo) y lo
    serializa con el serializer correspondiente al subtipo real.

    django-polymorphic devuelve la instancia del subtipo automáticamente
    cuando hacés ReportBlock.objects.filter(...). Así que `obj` ya es el
    subtipo concreto (TextImageBlock, KpiGridBlock, etc.) - no la base.
    """

    def to_representation(self, obj):
        serializer_class = _BLOCK_SERIALIZERS.get(type(obj))
        if serializer_class is None:
            # Fallback defensivo: no debería pasar en prod.
            return {"id": obj.id, "order": obj.order, "type": type(obj).__name__}
        return serializer_class(obj, context=self.context).data


# ---------- Top-level Report serializer ----------

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
    blocks = ReportBlockSerializer(many=True, read_only=True)
    attachments = ReportAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = (
            "id", "kind", "period_start", "period_end",
            "title", "display_title", "status", "published_at",
            "intro_text", "conclusions_text",
            "stage_id", "stage_name",
            "campaign_id", "campaign_name", "brand_name",
            "blocks", "attachments",
        )
