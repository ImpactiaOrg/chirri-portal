from rest_framework import serializers

from apps.reports.models import Report

from .models import Campaign, Stage


def _compute_stage_reach(stage: Stage) -> int | None:
    """Reach de una etapa evitando doble-conteo con CIERRE_ETAPA.

    Si la etapa tiene un cierre, ese ya rollupea la etapa — usamos solo ese.
    Si no, sumamos los demás (mensuales, influencer, general). Espera que
    `stage.reports.all()` esté prefetcheado con `reach_total` anotado.
    """
    reports = list(stage.reports.all())
    cierres = [r for r in reports if r.kind == Report.Kind.CIERRE_ETAPA]
    pool = cierres if cierres else [r for r in reports if r.kind != Report.Kind.CIERRE_ETAPA]
    total = sum((r.reach_total or 0) for r in pool)
    return total or None


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
    reach_total = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = (
            "id", "brand_name", "name", "brief", "status",
            "start_date", "end_date", "is_ongoing_operation",
            "stages", "stage_count",
            "published_report_count", "last_published_at",
            "reach_total",
        )

    def get_reach_total(self, campaign):
        """Suma los reach_total de todas las etapas (cada una aplica la regla
        anti-doble-conteo contra CIERRE_ETAPA). Requiere que la view haya
        prefetcheado stages → reports con `reach_total` anotado."""
        total = 0
        for stage in campaign.stages.all():
            stage_total = _compute_stage_reach(stage)
            if stage_total:
                total += stage_total
        return total or None


class CampaignReportRowSerializer(serializers.ModelSerializer):
    """Minimal report payload for the per-stage list on the campaign detail page.

    Intentionally smaller than ReportDetailSerializer — we only need what the
    row renders (title, kind, period, published_at, reach_total) to avoid
    dragging metrics and top_content into a list view. `reach_total` comes
    from a Sum annotation in the campaign-detail view; it's None when the
    report has no metrics tagged `reach`.
    """

    display_title = serializers.CharField(read_only=True)
    reach_total = serializers.DecimalField(
        max_digits=16, decimal_places=0, read_only=True, allow_null=True,
    )

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
            "reach_total",
        )


class StageWithReportsSerializer(serializers.ModelSerializer):
    reports = serializers.SerializerMethodField()
    reach_total = serializers.SerializerMethodField()

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
            "reach_total",
        )

    def get_reports(self, stage):
        # Stage.reports is prefetched in the view with status=PUBLISHED filter.
        return CampaignReportRowSerializer(stage.reports.all(), many=True).data

    def get_reach_total(self, stage):
        return _compute_stage_reach(stage)


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
