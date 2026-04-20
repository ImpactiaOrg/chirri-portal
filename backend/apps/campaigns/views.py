import logging

from django.db.models import Count, Max, Prefetch, Q
from rest_framework import permissions, viewsets

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
                .order_by("-published_at")
            )
            stages_qs = (
                Stage.objects
                .order_by("order")
                .prefetch_related(Prefetch("reports", queryset=published_reports))
            )
            return (
                Campaign.objects
                .filter(brand__client_id=client_id)
                .select_related("brand")
                .prefetch_related(Prefetch("stages", queryset=stages_qs))
            )

        published = Q(stages__reports__status=Report.Status.PUBLISHED)
        return (
            Campaign.objects
            .filter(brand__client_id=client_id)
            .select_related("brand")
            .prefetch_related("stages")
            .annotate(
                _stage_count=Count("stages", distinct=True),
                _published_count=Count("stages__reports", filter=published, distinct=True),
                _last_published_at=Max("stages__reports__published_at", filter=published),
            )
        )

    def retrieve(self, request, *args, **kwargs):
        try:
            response = super().retrieve(request, *args, **kwargs)
        except Exception:
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
