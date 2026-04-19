from rest_framework import serializers

from .models import Report, ReportMetric


class ReportMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportMetric
        fields = ("network", "source_type", "metric_name", "value", "period_comparison")


class ReportDetailSerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(source="stage.name", read_only=True)
    stage_id = serializers.IntegerField(source="stage.id", read_only=True)
    campaign_name = serializers.CharField(source="stage.campaign.name", read_only=True)
    campaign_id = serializers.IntegerField(source="stage.campaign.id", read_only=True)
    metrics = ReportMetricSerializer(many=True, read_only=True)
    display_title = serializers.CharField(read_only=True)

    class Meta:
        model = Report
        fields = (
            "id", "kind", "period_start", "period_end",
            "title", "display_title", "status", "published_at", "conclusions_text",
            "stage_id", "stage_name",
            "campaign_id", "campaign_name",
            "metrics",
        )
