from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Report
from .serializers import ReportDetailSerializer


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
