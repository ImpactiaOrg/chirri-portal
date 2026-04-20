from django.contrib import admin

from .models import (
    Report, ReportMetric,
    TopContent, BrandFollowerSnapshot, OneLinkAttribution,
)


class ReportMetricInline(admin.TabularInline):
    model = ReportMetric
    extra = 0


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("display_title", "stage", "kind", "period_start", "period_end", "status", "published_at")
    list_filter = ("status", "kind", "stage__campaign__brand")
    search_fields = ("title", "stage__name", "stage__campaign__name")
    inlines = [ReportMetricInline]
    actions = ["publish_reports"]

    @admin.action(description="Publicar reportes seleccionados")
    def publish_reports(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status=Report.Status.DRAFT).update(
            status=Report.Status.PUBLISHED, published_at=timezone.now()
        )
        self.message_user(request, f"{updated} reporte(s) publicado(s).")


@admin.register(ReportMetric)
class ReportMetricAdmin(admin.ModelAdmin):
    list_display = ("report", "network", "source_type", "metric_name", "value", "period_comparison")
    list_filter = ("network", "source_type")
    search_fields = ("report__title", "metric_name")


@admin.register(TopContent)
class TopContentAdmin(admin.ModelAdmin):
    list_display = ("report", "kind", "network", "rank", "handle")
    list_filter = ("kind", "network", "source_type")
    search_fields = ("handle", "caption")


@admin.register(BrandFollowerSnapshot)
class BrandFollowerSnapshotAdmin(admin.ModelAdmin):
    list_display = ("brand", "network", "as_of", "followers_count")
    list_filter = ("brand", "network")
    date_hierarchy = "as_of"


@admin.register(OneLinkAttribution)
class OneLinkAttributionAdmin(admin.ModelAdmin):
    list_display = ("report", "influencer_handle", "clicks", "app_downloads")
    search_fields = ("influencer_handle",)
