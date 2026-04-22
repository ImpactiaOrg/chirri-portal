from adminsortable2.admin import SortableAdminBase, SortableInlineAdminMixin
from django.contrib import admin

from .models import (
    Report, ReportMetric, ReportBlock,
    TopContent, BrandFollowerSnapshot, OneLinkAttribution,
)


class ReportMetricInline(admin.TabularInline):
    model = ReportMetric
    extra = 0


class TopContentInline(admin.StackedInline):
    """Nested under a TOP_CONTENT ReportBlock. Admin hides it for other block types."""
    model = TopContent
    extra = 0
    fields = ("kind", "network", "source_type", "rank", "handle", "caption", "thumbnail", "post_url", "metrics")


class OneLinkAttributionInline(admin.TabularInline):
    model = OneLinkAttribution
    extra = 0


class ReportBlockInline(SortableInlineAdminMixin, admin.StackedInline):
    model = ReportBlock
    extra = 0
    fields = ("type", "config", "image")
    show_change_link = True  # click-through to ReportBlockAdmin (with TopContent inline)
    # order es gestionado por SortableInlineAdminMixin automáticamente


@admin.register(Report)
class ReportAdmin(SortableAdminBase, admin.ModelAdmin):
    list_display = ("display_title", "stage", "kind", "period_start", "period_end", "status", "published_at")
    list_filter = ("status", "kind", "stage__campaign__brand")
    search_fields = ("title", "stage__name", "stage__campaign__name")
    inlines = [
        ReportMetricInline,
        OneLinkAttributionInline,
        ReportBlockInline,
    ]
    fieldsets = (
        (None, {
            "fields": (
                "stage", "kind", "period_start", "period_end",
                "title", "status", "published_at",
                "intro_text", "conclusions_text",
                "original_pdf",
            ),
        }),
    )
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


@admin.register(ReportBlock)
class ReportBlockAdmin(admin.ModelAdmin):
    list_display = ("report", "order", "type")
    list_filter = ("type",)
    search_fields = ("report__title",)
    fields = ("report", "type", "order", "config", "image")

    def get_inline_instances(self, request, obj=None):
        # TopContent solo tiene sentido bajo un TOP_CONTENT block.
        if obj is not None and obj.type == ReportBlock.Type.TOP_CONTENT:
            return [TopContentInline(self.model, self.admin_site)]
        return []


@admin.register(TopContent)
class TopContentAdmin(admin.ModelAdmin):
    list_display = ("block", "report", "kind", "network", "rank", "handle")
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
