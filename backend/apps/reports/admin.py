"""Django admin — Sections + Widgets (post sections-widgets-redesign)."""
import logging

from adminsortable2.admin import SortableAdminBase, SortableTabularInline
from django.contrib import admin, messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import path, reverse
from polymorphic.admin import (
    PolymorphicInlineSupportMixin,
    PolymorphicParentModelAdmin,
    PolymorphicChildModelAdmin,
    StackedPolymorphicInline,
)

from .importers.excel_exporter import export as export_report_xlsx
from .importers.excel_writer import build_template
from .importers.forms import ImportReportForm
from .importers.import_flow import import_bytes
from .importers.pdf_form import ImportPdfForm
from .importers.pdf_parser import submit_pdf as submit_pdf_parser

from .models import (
    Report, ReportAttachment, Section, Widget,
    TextWidget, ImageWidget, TextImageWidget,
    KpiGridWidget, KpiTile,
    TableWidget, TableRow,
    ChartWidget, ChartDataPoint,
    TopContentsWidget, TopContentItem,
    TopCreatorsWidget, TopCreatorItem,
    BrandFollowerSnapshot,
)

logger = logging.getLogger(__name__)


# ---------- Child item / row inlines ----------

class KpiTileInline(SortableTabularInline):
    model = KpiTile
    extra = 0
    fields = ("order", "label", "value", "unit", "period_comparison", "period_comparison_label")
    ordering = ("order",)


class TableRowInline(SortableTabularInline):
    model = TableRow
    extra = 0
    fields = ("order", "is_header", "cells")
    ordering = ("order",)


class ChartDataPointInline(SortableTabularInline):
    model = ChartDataPoint
    extra = 0
    fields = ("order", "label", "value")
    ordering = ("order",)


class TopContentItemInline(SortableTabularInline):
    model = TopContentItem
    extra = 0
    fields = (
        "order", "thumbnail", "caption", "source_type", "post_url",
        "views", "likes", "comments", "shares", "saves",
    )
    ordering = ("order",)


class TopCreatorItemInline(SortableTabularInline):
    model = TopCreatorItem
    extra = 0
    fields = (
        "order", "thumbnail", "handle", "post_url",
        "views", "likes", "comments", "shares",
    )
    ordering = ("order",)


class ReportAttachmentInline(SortableTabularInline):
    model = ReportAttachment
    extra = 0
    fields = ("order", "title", "file", "kind", "mime_type", "size_bytes")
    readonly_fields = ("mime_type", "size_bytes")
    ordering = ("order",)


# ---------- Polymorphic Widget inline (montado dentro de SectionAdmin) ----------

class WidgetInline(StackedPolymorphicInline):
    """Stacked polymorphic inline: el dropdown 'Add another' deja crear cualquier widget."""

    class TextWidgetInline(StackedPolymorphicInline.Child):
        model = TextWidget

    class ImageWidgetInline(StackedPolymorphicInline.Child):
        model = ImageWidget

    class TextImageWidgetInline(StackedPolymorphicInline.Child):
        model = TextImageWidget

    class KpiGridWidgetInline(StackedPolymorphicInline.Child):
        model = KpiGridWidget

    class TableWidgetInline(StackedPolymorphicInline.Child):
        model = TableWidget

    class ChartWidgetInline(StackedPolymorphicInline.Child):
        model = ChartWidget

    class TopContentsWidgetInline(StackedPolymorphicInline.Child):
        model = TopContentsWidget

    class TopCreatorsWidgetInline(StackedPolymorphicInline.Child):
        model = TopCreatorsWidget

    model = Widget
    child_inlines = (
        TextWidgetInline,
        ImageWidgetInline,
        TextImageWidgetInline,
        KpiGridWidgetInline,
        TableWidgetInline,
        ChartWidgetInline,
        TopContentsWidgetInline,
        TopCreatorsWidgetInline,
    )


# ---------- SectionAdmin ----------

@admin.register(Section)
class SectionAdmin(SortableAdminBase, PolymorphicInlineSupportMixin, admin.ModelAdmin):
    list_display = ("report", "order", "title", "layout")
    list_filter = ("layout",)
    search_fields = ("title", "report__title")
    inlines = [WidgetInline]
    fields = ("report", "order", "title", "layout", "instructions")


# ---------- Section inline para ReportAdmin ----------

class SectionInline(SortableTabularInline):
    model = Section
    extra = 0
    fields = ("order", "title", "layout")
    ordering = ("order",)
    show_change_link = True


# ---------- ReportAdmin ----------

@admin.register(Report)
class ReportAdmin(SortableAdminBase, admin.ModelAdmin):
    list_display = (
        "display_title", "client_col", "brand_col", "campaign_col", "stage",
        "kind", "period_start", "period_end", "status", "published_at",
    )
    list_filter = (
        "status", "kind",
        "stage__campaign__brand__client",
        "stage__campaign__brand",
        "stage__campaign",
    )
    list_select_related = ("stage", "stage__campaign", "stage__campaign__brand", "stage__campaign__brand__client")
    search_fields = (
        "title", "stage__name", "stage__campaign__name",
        "stage__campaign__brand__name",
        "stage__campaign__brand__client__name",
    )

    @admin.display(description="Cliente", ordering="stage__campaign__brand__client__name")
    def client_col(self, obj):
        return obj.stage.campaign.brand.client.name

    @admin.display(description="Brand", ordering="stage__campaign__brand__name")
    def brand_col(self, obj):
        return obj.stage.campaign.brand.name

    @admin.display(description="Campaña", ordering="stage__campaign__name")
    def campaign_col(self, obj):
        return obj.stage.campaign.name

    inlines = [ReportAttachmentInline, SectionInline]
    fieldsets = (
        (None, {
            "fields": (
                "stage", "kind", "period_start", "period_end",
                "title", "status", "published_at",
                "intro_text", "conclusions_text",
            ),
        }),
    )
    actions = ["publish_reports"]

    @admin.action(description="Publicar reportes seleccionados")
    def publish_reports(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status=Report.Status.DRAFT).update(
            status=Report.Status.PUBLISHED, published_at=timezone.now(),
        )
        self.message_user(request, f"{updated} reporte(s) publicado(s).")

    # ---- Importer / Exporter custom URLs ----
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "download-template/",
                self.admin_site.admin_view(self.download_template_view),
                name="reports_report_download_template",
            ),
            path(
                "download-example/<int:report_id>/",
                self.admin_site.admin_view(self.download_example_view),
                name="reports_report_download_example",
            ),
            path(
                "import/",
                self.admin_site.admin_view(self.import_view),
                name="reports_report_import",
            ),
            path(
                "import/cascade/<str:level>/",
                self.admin_site.admin_view(self.import_cascade_view),
                name="reports_report_import_cascade",
            ),
            path(
                "import-pdf/",
                self.admin_site.admin_view(self.import_pdf_view),
                name="reports_report_import_pdf",
            ),
        ]
        return custom + urls

    def import_cascade_view(self, request, level: str):
        if not request.user.has_perm("reports.add_report"):
            return JsonResponse({"results": []}, status=403)
        parent = request.GET.get("parent")
        from apps.campaigns.models import Campaign, Stage
        from apps.tenants.models import Brand
        if level == "brand":
            qs = Brand.objects.filter(client_id=parent).order_by("name")
        elif level == "campaign":
            qs = Campaign.objects.filter(brand_id=parent).order_by("name")
        elif level == "stage":
            qs = Stage.objects.filter(campaign_id=parent).order_by("order")
        else:
            return JsonResponse({"results": []}, status=400)
        return JsonResponse({
            "results": [{"id": obj.pk, "text": str(obj)} for obj in qs],
        })

    def download_template_view(self, request):
        if not request.user.has_perm("reports.add_report"):
            return HttpResponse(status=403)
        buf = build_template()
        resp = HttpResponse(
            buf.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = 'attachment; filename="reporte-template.xlsx"'
        return resp

    def download_example_view(self, request, report_id: int):
        if not request.user.has_perm("reports.view_report"):
            return HttpResponse(status=403)
        try:
            report = Report.objects.get(pk=report_id)
        except Report.DoesNotExist:
            return HttpResponse(status=404)
        buf = export_report_xlsx(report)
        resp = HttpResponse(
            buf.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = (
            f'attachment; filename="reporte-{report.pk}-export.xlsx"'
        )
        return resp

    def import_view(self, request):
        if not request.user.has_perm("reports.add_report"):
            return HttpResponse(status=403)

        import_errors = []
        if request.method == "POST":
            form = ImportReportForm(request.POST, request.FILES, admin_site=self.admin_site)
            if form.is_valid():
                stage = form.cleaned_data["stage"]
                uploaded = form.cleaned_data["file"]
                logger.info(
                    "report_import_started",
                    extra={
                        "user_id": request.user.pk,
                        "stage_id": stage.pk,
                        "filename": uploaded.name,
                        "size": uploaded.size,
                    },
                )
                data = uploaded.read()
                report, import_errors = import_bytes(
                    data, filename=uploaded.name, stage_id=stage.pk,
                )
                if not import_errors and report is not None:
                    messages.success(
                        request,
                        f"Reporte importado como DRAFT (id={report.pk}, "
                        f"{report.sections.count()} sections).",
                    )
                    return redirect(reverse(
                        "admin:reports_report_change", args=[report.pk],
                    ))
                logger.warning(
                    "report_import_validation_failed",
                    extra={
                        "user_id": request.user.pk,
                        "stage_id": stage.pk,
                        "error_count": len(import_errors),
                    },
                )
        else:
            form = ImportReportForm(admin_site=self.admin_site)

        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "import_errors": import_errors,
            "opts": self.model._meta,
        }
        return render(request, "admin/reports/report/import.html", context)

    def import_pdf_view(self, request):
        if not request.user.has_perm("reports.add_report"):
            return HttpResponse(status=403)
        if request.method == "POST":
            form = ImportPdfForm(request.POST, request.FILES)
            if form.is_valid():
                stage = form.cleaned_data["stage"]
                upload = form.cleaned_data["file"]
                logger.info(
                    "report_pdf_import_started",
                    extra={
                        "user_id": request.user.pk,
                        "stage_id": stage.pk,
                        "filename": upload.name,
                        "size": upload.size,
                    },
                )
                job = submit_pdf_parser(
                    pdf_bytes=upload.read(),
                    filename=upload.name,
                    stage_id=stage.pk,
                    user=request.user,
                )
                return redirect(reverse(
                    "admin:llm_llmjob_change", args=[job.pk],
                ))
        else:
            form = ImportPdfForm()

        return render(request, "admin/reports/report/import_pdf.html", {
            **self.admin_site.each_context(request),
            "form": form,
            "opts": self.model._meta,
        })


# ---------- Standalone polymorphic Widget admin (debug/búsqueda) ----------

@admin.register(Widget)
class WidgetParentAdmin(PolymorphicParentModelAdmin):
    base_model = Widget
    child_models = (
        TextWidget, ImageWidget, TextImageWidget,
        KpiGridWidget, TableWidget, ChartWidget,
        TopContentsWidget, TopCreatorsWidget,
    )
    list_display = ("section", "order", "title", "polymorphic_ctype")
    list_filter = ("polymorphic_ctype",)
    search_fields = ("title", "section__title", "section__report__title")


class _WidgetChildAdminBase(SortableAdminBase, PolymorphicChildModelAdmin):
    base_model = Widget


@admin.register(TextWidget)
class TextWidgetAdmin(_WidgetChildAdminBase):
    list_display = ("section", "order", "title")


@admin.register(ImageWidget)
class ImageWidgetAdmin(_WidgetChildAdminBase):
    list_display = ("section", "order", "title")


@admin.register(TextImageWidget)
class TextImageWidgetAdmin(_WidgetChildAdminBase):
    list_display = ("section", "order", "title")


@admin.register(KpiGridWidget)
class KpiGridWidgetAdmin(_WidgetChildAdminBase):
    inlines = [KpiTileInline]
    list_display = ("section", "order", "title")


@admin.register(TableWidget)
class TableWidgetAdmin(_WidgetChildAdminBase):
    inlines = [TableRowInline]
    list_display = ("section", "order", "title", "show_total")


@admin.register(ChartWidget)
class ChartWidgetAdmin(_WidgetChildAdminBase):
    inlines = [ChartDataPointInline]
    list_display = ("section", "order", "title", "network", "chart_type")
    list_filter = ("network", "chart_type")


@admin.register(TopContentsWidget)
class TopContentsWidgetAdmin(_WidgetChildAdminBase):
    inlines = [TopContentItemInline]
    list_display = ("section", "order", "title", "network")
    list_filter = ("network",)


@admin.register(TopCreatorsWidget)
class TopCreatorsWidgetAdmin(_WidgetChildAdminBase):
    inlines = [TopCreatorItemInline]
    list_display = ("section", "order", "title", "network")
    list_filter = ("network",)


# ---------- Standalone admins for debugging ----------

@admin.register(BrandFollowerSnapshot)
class BrandFollowerSnapshotAdmin(admin.ModelAdmin):
    list_display = ("brand", "network", "as_of", "followers_count")
    list_filter = ("brand", "network")
    date_hierarchy = "as_of"
