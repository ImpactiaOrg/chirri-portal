from rest_framework import serializers

from .models import (
    Report, ReportMetric, ReportBlock,
    TopContent, OneLinkAttribution,
)
from .services.aggregations import (
    build_q1_rollup, build_yoy, build_follower_snapshots,
)


class ReportMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportMetric
        fields = ("network", "source_type", "metric_name", "value", "period_comparison")


class TopContentSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = TopContent
        fields = (
            "kind", "network", "source_type", "rank", "handle",
            "caption", "thumbnail_url", "post_url", "metrics",
        )

    def get_thumbnail_url(self, obj) -> str | None:
        return obj.thumbnail.url if obj.thumbnail else None


class OneLinkAttributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OneLinkAttribution
        fields = ("influencer_handle", "clicks", "app_downloads")


class ReportBlockSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    items = TopContentSerializer(many=True, read_only=True)

    class Meta:
        model = ReportBlock
        fields = ("id", "type", "order", "config", "image_url", "items")

    def get_image_url(self, obj) -> str | None:
        return obj.image.url if obj.image else None


class ReportDetailSerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(source="stage.name", read_only=True)
    stage_id = serializers.IntegerField(source="stage.id", read_only=True)
    campaign_name = serializers.CharField(source="stage.campaign.name", read_only=True)
    campaign_id = serializers.IntegerField(source="stage.campaign.id", read_only=True)
    brand_name = serializers.CharField(source="stage.campaign.brand.name", read_only=True)
    display_title = serializers.CharField(read_only=True)
    metrics = ReportMetricSerializer(many=True, read_only=True)
    onelink = OneLinkAttributionSerializer(many=True, read_only=True)
    follower_snapshots = serializers.SerializerMethodField()
    q1_rollup = serializers.SerializerMethodField()
    yoy = serializers.SerializerMethodField()
    blocks = ReportBlockSerializer(many=True, read_only=True)
    original_pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            "id", "kind", "period_start", "period_end",
            "title", "display_title", "status", "published_at",
            "intro_text", "conclusions_text",
            "stage_id", "stage_name",
            "campaign_id", "campaign_name", "brand_name",
            "metrics", "onelink",
            "follower_snapshots", "q1_rollup", "yoy",
            "blocks", "original_pdf_url",
        )

    def get_follower_snapshots(self, obj):
        return build_follower_snapshots(obj)

    def get_q1_rollup(self, obj):
        return build_q1_rollup(obj)

    def get_yoy(self, obj):
        return build_yoy(obj)

    def get_original_pdf_url(self, obj) -> str | None:
        return obj.original_pdf.url if obj.original_pdf else None
