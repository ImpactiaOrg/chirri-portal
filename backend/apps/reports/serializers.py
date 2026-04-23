from rest_framework import serializers

from .models import (
    Report, ReportBlock,
    TopContent, OneLinkAttribution,
)


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
    # DEV-116 Task 2.5: ReportBlock polymorphic — legacy type/config/image
    # fields gone. Typed-block serializers (TextImageBlock, etc.) are wired up
    # in later tasks. For now we expose only base fields + TopContent items.
    items = TopContentSerializer(many=True, read_only=True)
    type = serializers.SerializerMethodField()

    class Meta:
        model = ReportBlock
        fields = ("id", "type", "order", "items")

    def get_type(self, obj) -> str:
        # Derivar legacy-compatible 'type' string desde el polymorphic ctype.
        # Mapa explícito para no arrastrar nombres de clase como type strings.
        model = obj.get_real_instance_class().__name__
        mapping = {
            "TextImageBlock": "TEXT_IMAGE",
            "KpiGridBlock": "KPI_GRID",
            "MetricsTableBlock": "METRICS_TABLE",
            "TopContentBlock": "TOP_CONTENT",
            "AttributionTableBlock": "ATTRIBUTION",
            "ChartBlock": "CHART",
        }
        return mapping.get(model, model)


class ReportDetailSerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(source="stage.name", read_only=True)
    stage_id = serializers.IntegerField(source="stage.id", read_only=True)
    campaign_name = serializers.CharField(source="stage.campaign.name", read_only=True)
    campaign_id = serializers.IntegerField(source="stage.campaign.id", read_only=True)
    brand_name = serializers.CharField(source="stage.campaign.brand.name", read_only=True)
    display_title = serializers.CharField(read_only=True)
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
            "blocks", "original_pdf_url",
        )

    def get_original_pdf_url(self, obj) -> str | None:
        return obj.original_pdf.url if obj.original_pdf else None
