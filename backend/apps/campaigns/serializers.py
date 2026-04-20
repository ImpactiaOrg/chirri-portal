from rest_framework import serializers

from apps.reports.models import Report

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


class CampaignReportRowSerializer(serializers.ModelSerializer):
    """Minimal report payload for the per-stage list on the campaign detail page.

    Intentionally smaller than ReportDetailSerializer — we only need what the
    row renders (title, kind, period, published_at) to avoid dragging metrics
    and top_content into a list view.
    """

    display_title = serializers.CharField(read_only=True)

    class Meta:
        model = Report
        fields = (
            "id",
            "title",
            "display_title",
            "kind",
            "period_start",
            "period_end",
            "published_at",
        )


class StageWithReportsSerializer(serializers.ModelSerializer):
    reports = serializers.SerializerMethodField()

    class Meta:
        model = Stage
        fields = (
            "id",
            "order",
            "kind",
            "name",
            "description",
            "start_date",
            "end_date",
            "reports",
        )

    def get_reports(self, stage):
        # Stage.reports is prefetched in the view with status=PUBLISHED filter.
        return CampaignReportRowSerializer(stage.reports.all(), many=True).data


class CampaignDetailSerializer(serializers.ModelSerializer):
    """Detail payload: campaign + stages nested with their published reports.

    Does NOT inherit from CampaignListSerializer because the list serializer
    reads annotations (_stage_count, _published_count, _last_published_at)
    that are only added to the list queryset — inheriting them here would
    crash on retrieve.
    """

    brand_name = serializers.CharField(source="brand.name", read_only=True)
    stages_with_reports = StageWithReportsSerializer(
        source="stages", many=True, read_only=True
    )

    class Meta:
        model = Campaign
        fields = (
            "id",
            "brand_name",
            "name",
            "brief",
            "status",
            "start_date",
            "end_date",
            "is_ongoing_operation",
            "stages_with_reports",
        )
