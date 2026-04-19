from django.db.models import Count, Max, Q
from rest_framework import permissions, viewsets

from apps.reports.models import Report

from .models import Campaign
from .serializers import CampaignListSerializer


class CampaignViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CampaignListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        client_id = getattr(self.request.user, "client_id", None)
        published = Q(stages__reports__status=Report.Status.PUBLISHED)
        qs = (
            Campaign.objects
            .select_related("brand")
            .prefetch_related("stages")
            .annotate(
                _stage_count=Count("stages", distinct=True),
                _published_count=Count("stages__reports", filter=published, distinct=True),
                _last_published_at=Max("stages__reports__published_at", filter=published),
            )
        )
        if client_id is None:
            return qs.none()
        return qs.filter(brand__client_id=client_id)
