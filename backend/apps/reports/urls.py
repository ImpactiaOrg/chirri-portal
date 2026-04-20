from django.urls import path

from .views import LatestPublishedReportView, ReportDetailView

urlpatterns = [
    path("latest/", LatestPublishedReportView.as_view(), name="report-latest"),
    path("<int:pk>/", ReportDetailView.as_view(), name="report-detail"),
]
