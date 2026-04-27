"""Django admin para DEV-116 post-refactor.

Polimorfismo de ReportBlock via django-polymorphic:
- Un solo inline en ReportAdmin (StackedPolymorphicInline) con 6 Child sub-inlines.
- ReportBlockAdmin standalone como PolymorphicParentModelAdmin.
- Un PolymorphicChildModelAdmin por subtipo con sus own child row inlines.
"""
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

logger = logging.getLogger(__name__)

from .models import (
    Report, ReportAttachment, ReportBlock,
    TextImageBlock, ImageBlock, KpiGridBlock, KpiTile,
    TableBlock, TableRow,
    TopContentsBlock, TopContentItem,
    TopCreatorsBlock, TopCreatorItem,
    ChartBlock, ChartDataPoint,
    BrandFollowerSnapshot,
)


# -------- Child row inlines --------
#
# Los inlines que exponen un campo de orden usable (KpiTile / ChartDataPoint /
# TopContent) usan SortableTabularInline de adminsortable2 para habilitar
# drag-reorder en el admin. Los modelos tienen Meta.ordering que empieza con
# el FK al parent (para scopar el orden por parent), así que el inline
# explicita su propio `ordering` en el campo de orden real.


class KpiTileInline(SortableTabularInline):
    model = KpiTile
    extra = 0
    fields = ("order", "label", "value", "period_comparison")
    ordering = ("order",)


class ChartDataPointInline(SortableTabularInline):
    model = ChartDataPoint
    extra = 0
    fields = ("order", "label", "value")
    ordering = ("order",)


class TopContentItemInline(SortableTabularInline):
    """Cajitas de 'Top contenidos' — posts/contenidos destacados (DEV-129)."""
    model = TopContentItem
    extra = 0
    fields = (
        "order", "thumbnail", "caption", "source_type", "post_url",
        "views", "likes", "comments", "shares", "saves",
    )
    ordering = ("order",)


class TopCreatorItemInline(SortableTabularInline):
    """Cajitas de 'Top creadores' — retratos con @handle (DEV-129)."""
    model = TopCreatorItem
    extra = 0
    fields = (
        "order", "thumbnail", "handle", "post_url",
        "views", "likes", "comments", "shares",
    )
    ordering = ("order",)


class TableRowInline(SortableTabularInline):
    """Filas de TableBlock — texto plano por celda. Soporta drag-reorder."""
    model = TableRow
    extra = 0
    fields = ("order", "is_header", "cells")
    ordering = ("order",)


class ReportAttachmentInline(SortableTabularInline):
    """Descargas asociadas al reporte (PDF oficial, exports, anexos)."""
    model = ReportAttachment
    extra = 0
    fields = ("order", "title", "file", "kind", "mime_type", "size_bytes")
    readonly_fields = ("mime_type", "size_bytes")
    ordering = ("order",)


# -------- Polymorphic inline for ReportBlock inside ReportAdmin --------

class ReportBlockInline(StackedPolymorphicInline):
    """Stacked polymorphic inline: un solo inline muestra los blocks de todos
    los subtipos en la página de cada Report. El dropdown "Add another" deja
    elegir de qué subtipo crear el nuevo block."""

    class TextImageBlockInline(StackedPolymorphicInline.Child):
        model = TextImageBlock

    class ImageBlockInline(StackedPolymorphicInline.Child):
        model = ImageBlock

    class KpiGridBlockInline(StackedPolymorphicInline.Child):
        model = KpiGridBlock

    class TableBlockInline(StackedPolymorphicInline.Child):
        model = TableBlock

    class TopContentsBlockInline(StackedPolymorphicInline.Child):
        model = TopContentsBlock

    class TopCreatorsBlockInline(StackedPolymorphicInline.Child):
        model = TopCreatorsBlock

    class ChartBlockInline(StackedPolymorphicInline.Child):
        model = ChartBlock

    model = ReportBlock
    child_inlines = (
        TextImageBlockInline,
        ImageBlockInline,
        KpiGridBlockInline,
        TableBlockInline,
        TopContentsBlockInline,
        TopCreatorsBlockInline,
        ChartBlockInline,
    )


# -------- ReportAdmin --------

@admin.register(Report)
class ReportAdmin(SortableAdminBase, PolymorphicInlineSupportMixin, admin.ModelAdmin):
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
    inlines = [ReportAttachmentInline, ReportBlockInline]
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

    # ------------------------------------------------------------------
    # DEV-83 · Importer/Exporter xlsx
    # ------------------------------------------------------------------
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
        """JSON feed para los selects cascading del form (Cliente → Etapa)."""
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
                        f"{report.blocks.count()} blocks).",
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


# -------- Polymorphic parent/child admins for standalone ReportBlock --------

@admin.register(ReportBlock)
class ReportBlockAdmin(PolymorphicParentModelAdmin):
    """Vista standalone de todos los blocks, polimórfica."""
    base_model = ReportBlock
    child_models = (
        TextImageBlock, ImageBlock, KpiGridBlock, TableBlock,
        TopContentsBlock, TopCreatorsBlock, ChartBlock,
    )
    list_display = ("report", "order", "polymorphic_ctype")
    list_filter = ("polymorphic_ctype",)
    search_fields = ("report__title",)


class _BlockChildAdminBase(SortableAdminBase, PolymorphicChildModelAdmin):
    """Base común para los subtipos de ReportBlock. Cada uno puede sobrescribir
    `inlines` para agregar sus child rows.

    Hereda `SortableAdminBase` para que los child admins que hostean
    SortableTabularInline (KpiGrid / Chart / TopContent / Table) emitan el
    CSS/JS de adminsortable2 y habiliten drag-reorder en el UI. Subtipos
    que no usan sortable inlines (TextImage, ImageBlock) lo heredan
    inofensivamente — el mixin es no-op si no hay sortable inlines.
    """
    base_model = ReportBlock
    # Los fields se derivan automáticamente del modelo subtipo.
    # Se podría explicitar cada uno con `base_fieldsets`, pero Django introspection
    # produce un form razonable por default.


@admin.register(TextImageBlock)
class TextImageBlockAdmin(_BlockChildAdminBase):
    list_display = ("report", "order", "title")
    search_fields = ("title", "body")


@admin.register(ImageBlock)
class ImageBlockAdmin(_BlockChildAdminBase):
    list_display = ("report", "order", "title")
    search_fields = ("title", "caption")


@admin.register(KpiGridBlock)
class KpiGridBlockAdmin(_BlockChildAdminBase):
    inlines = [KpiTileInline]
    list_display = ("report", "order", "title")


@admin.register(TableBlock)
class TableBlockAdmin(_BlockChildAdminBase):
    inlines = [TableRowInline]
    list_display = ("report", "order", "title", "show_total")


@admin.register(TopContentsBlock)
class TopContentsBlockAdmin(_BlockChildAdminBase):
    inlines = [TopContentItemInline]
    list_display = ("report", "order", "title", "network", "limit")
    list_filter = ("network",)


@admin.register(TopCreatorsBlock)
class TopCreatorsBlockAdmin(_BlockChildAdminBase):
    inlines = [TopCreatorItemInline]
    list_display = ("report", "order", "title", "network", "limit")
    list_filter = ("network",)


@admin.register(ChartBlock)
class ChartBlockAdmin(_BlockChildAdminBase):
    inlines = [ChartDataPointInline]
    list_display = ("report", "order", "title", "network", "chart_type")
    list_filter = ("network", "chart_type")


# -------- Standalone admins for debugging --------

@admin.register(BrandFollowerSnapshot)
class BrandFollowerSnapshotAdmin(admin.ModelAdmin):
    list_display = ("brand", "network", "as_of", "followers_count")
    list_filter = ("brand", "network")
    date_hierarchy = "as_of"
