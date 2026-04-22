import logging

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Report
from .serializers import ReportDetailSerializer

logger = logging.getLogger(__name__)


class LatestPublishedReportView(APIView):
    """Most recently published report for the authenticated user's client.

    Returns 204 No Content when the user has no published reports yet — the
    frontend treats 204 as `null`. We avoid `Response(None)` because DRF's
    JSONRenderer serializes it to an empty body (not `"null"`), which breaks
    `res.json()` on the client.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        client_id = getattr(request.user, "client_id", None)
        if client_id is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        report = (
            Report.objects
            .filter(stage__campaign__brand__client_id=client_id, status=Report.Status.PUBLISHED)
            .select_related("stage", "stage__campaign")
            .order_by("-published_at")
            .first()
        )
        if report is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(ReportDetailSerializer(report).data)


class ReportDetailView(RetrieveAPIView):
    """Detail of a single published report for the authenticated user's client.

    Scoping happens in get_object (not middleware — see CLAUDE.md gotcha).
    Cross-tenant or DRAFT access returns 404, not 403, to avoid leaking existence.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReportDetailSerializer

    def get_queryset(self):
        client_id = getattr(self.request.user, "client_id", None)
        if client_id is None:
            return Report.objects.none()
        return (
            Report.objects
            .filter(
                stage__campaign__brand__client_id=client_id,
                status=Report.Status.PUBLISHED,
            )
            .select_related("stage", "stage__campaign", "stage__campaign__brand")
            .prefetch_related("metrics", "onelink", "blocks", "blocks__items")
        )

    def get_object(self):
        try:
            obj = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        except (Http404, NotFound):
            logger.warning(
                "report_access_denied",
                extra={
                    "report_id": self.kwargs.get("pk"),
                    "user_id": getattr(self.request.user, "id", None),
                    "reason": "not_found_or_scoped_out",
                },
            )
            raise
        logger.info(
            "report_served",
            extra={
                "report_id": obj.pk,
                "client_id": getattr(self.request.user, "client_id", None),
                "user_id": self.request.user.id,
            },
        )
        return obj
