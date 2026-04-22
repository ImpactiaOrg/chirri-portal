import logging

from django.db.models import Count, Max, Prefetch, Q, Sum
from django.http import Http404
from rest_framework import permissions, viewsets
from rest_framework.exceptions import NotFound

from apps.reports.models import Report

from .models import Campaign, Stage
from .serializers import CampaignDetailSerializer, CampaignListSerializer

logger = logging.getLogger(__name__)


class CampaignViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CampaignDetailSerializer
        return CampaignListSerializer

    def get_queryset(self):
        client_id = getattr(self.request.user, "client_id", None)
        if client_id is None:
            return Campaign.objects.none()

        if self.action == "retrieve":
            published_reports = (
                Report.objects
                .filter(status=Report.Status.PUBLISHED)
                .annotate(
                    reach_total=Sum(
                        "metrics__value",
                        filter=Q(metrics__metric_name="reach"),
                    ),
                )
                .order_by("-published_at")
            )
            stages_qs = Stage.objects.prefetch_related(
                Prefetch("reports", queryset=published_reports)
            )
            return (
                Campaign.objects
                .filter(brand__client_id=client_id)
                .select_related("brand")
                .prefetch_related(Prefetch("stages", queryset=stages_qs))
            )

        published = Q(stages__reports__status=Report.Status.PUBLISHED)
        # Para el cálculo de reach_total per-campaign (serializer lo computa en
        # Python sumando stages), prefetcheamos los reportes publicados con el
        # mismo annotate que usa el detail. Sin esto sería N+1 al acceder a
        # stage.reports.all() en el serializer.
        published_reports = (
            Report.objects
            .filter(status=Report.Status.PUBLISHED)
            .annotate(
                reach_total=Sum(
                    "metrics__value",
                    filter=Q(metrics__metric_name="reach"),
                ),
            )
        )
        stages_qs = Stage.objects.prefetch_related(
            Prefetch("reports", queryset=published_reports)
        )
        return (
            Campaign.objects
            .filter(brand__client_id=client_id)
            .select_related("brand")
            .prefetch_related(Prefetch("stages", queryset=stages_qs))
            .annotate(
                _stage_count=Count("stages", distinct=True),
                _published_count=Count("stages__reports", filter=published, distinct=True),
                _last_published_at=Max("stages__reports__published_at", filter=published),
            )
        )

    def retrieve(self, request, *args, **kwargs):
        try:
            response = super().retrieve(request, *args, **kwargs)
        except (Http404, NotFound):
            logger.warning(
                "campaign_detail_access_denied",
                extra={
                    "campaign_id": kwargs.get("pk"),
                    "user_id": getattr(request.user, "id", None),
                    "client_id": getattr(request.user, "client_id", None),
                    "reason": "not_found_or_scoped_out",
                },
            )
            raise
        logger.info(
            "campaign_detail_served",
            extra={
                "campaign_id": kwargs.get("pk"),
                "client_id": getattr(request.user, "client_id", None),
                "user_id": request.user.id,
            },
        )
        return response
