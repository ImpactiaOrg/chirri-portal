from django.urls import path

from .views import LatestPublishedReportView

urlpatterns = [
    path("latest/", LatestPublishedReportView.as_view(), name="report-latest"),
]
