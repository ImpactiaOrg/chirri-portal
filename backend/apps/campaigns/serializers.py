from rest_framework import serializers

from .models import Campaign, Stage


class StageSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Stage
        fields = ("id", "order", "kind", "name")


class CampaignListSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    stage_count = serializers.IntegerField(source="_stage_count", read_only=True)
    stages = StageSummarySerializer(many=True, read_only=True)
    published_report_count = serializers.IntegerField(source="_published_count", read_only=True)
    last_published_at = serializers.DateTimeField(source="_last_published_at", read_only=True)

    class Meta:
        model = Campaign
        fields = (
            "id", "brand_name", "name", "brief", "status",
            "start_date", "end_date", "is_ongoing_operation",
            "stages", "stage_count",
            "published_report_count", "last_published_at",
        )
