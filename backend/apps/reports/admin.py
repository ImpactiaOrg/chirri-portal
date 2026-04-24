"""Django admin para DEV-116 post-refactor.

Polimorfismo de ReportBlock via django-polymorphic:
- Un solo inline en ReportAdmin (StackedPolymorphicInline) con 6 Child sub-inlines.
- ReportBlockAdmin standalone como PolymorphicParentModelAdmin.
- Un PolymorphicChildModelAdmin por subtipo con sus own child row inlines.
"""
from adminsortable2.admin import SortableAdminBase, SortableTabularInline
from django.contrib import admin
from polymorphic.admin import (
    PolymorphicInlineSupportMixin,
    PolymorphicParentModelAdmin,
    PolymorphicChildModelAdmin,
    StackedPolymorphicInline,
)

from .models import (
    Report, ReportAttachment, ReportBlock,
    TextImageBlock, KpiGridBlock, KpiTile,
    MetricsTableBlock, MetricsTableRow,
    TopContentsBlock, TopContentItem,
    TopCreatorsBlock, TopCreatorItem,
    AttributionTableBlock,
    ChartBlock, ChartDataPoint,
    OneLinkAttribution, BrandFollowerSnapshot,
)


# -------- Child row inlines --------
#
# Los 4 inlines que exponen un campo de orden usable (KpiTile / MetricsTableRow
# / ChartDataPoint / TopContent) usan SortableTabularInline de adminsortable2
# para habilitar drag-reorder en el admin. Los modelos tienen Meta.ordering que
# empieza con el FK al parent (para scopar el orden por parent), así que el
# inline explicita su propio `ordering` en el campo de orden real.
#
# OneLinkAttributionInline queda como TabularInline plain: el orden canonical
# es por `-app_downloads` (descending) y no es user-reorderable.


class KpiTileInline(SortableTabularInline):
    model = KpiTile
    extra = 0
    fields = ("order", "label", "value", "period_comparison")
    ordering = ("order",)


class MetricsTableRowInline(SortableTabularInline):
    model = MetricsTableRow
    extra = 0
    fields = ("order", "metric_name", "value", "source_type", "period_comparison")
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


class OneLinkAttributionInline(admin.TabularInline):
    """Inline de OneLinkAttribution dentro de AttributionTableBlock admin.

    Plain TabularInline (no sortable): el orden canonical es `-app_downloads`
    y no es user-reorderable, así que drag-reorder no aplica.
    """
    model = OneLinkAttribution
    extra = 0
    fields = ("influencer_handle", "clicks", "app_downloads")


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

    class KpiGridBlockInline(StackedPolymorphicInline.Child):
        model = KpiGridBlock

    class MetricsTableBlockInline(StackedPolymorphicInline.Child):
        model = MetricsTableBlock

    class TopContentsBlockInline(StackedPolymorphicInline.Child):
        model = TopContentsBlock

    class TopCreatorsBlockInline(StackedPolymorphicInline.Child):
        model = TopCreatorsBlock

    class AttributionTableBlockInline(StackedPolymorphicInline.Child):
        model = AttributionTableBlock

    class ChartBlockInline(StackedPolymorphicInline.Child):
        model = ChartBlock

    model = ReportBlock
    child_inlines = (
        TextImageBlockInline,
        KpiGridBlockInline,
        MetricsTableBlockInline,
        TopContentsBlockInline,
        TopCreatorsBlockInline,
        AttributionTableBlockInline,
        ChartBlockInline,
    )


# -------- ReportAdmin --------

@admin.register(Report)
class ReportAdmin(SortableAdminBase, PolymorphicInlineSupportMixin, admin.ModelAdmin):
    list_display = ("display_title", "stage", "kind", "period_start", "period_end", "status", "published_at")
    list_filter = ("status", "kind", "stage__campaign__brand")
    search_fields = ("title", "stage__name", "stage__campaign__name")
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


# -------- Polymorphic parent/child admins for standalone ReportBlock --------

@admin.register(ReportBlock)
class ReportBlockAdmin(PolymorphicParentModelAdmin):
    """Vista standalone de todos los blocks, polimórfica."""
    base_model = ReportBlock
    child_models = (
        TextImageBlock, KpiGridBlock, MetricsTableBlock,
        TopContentsBlock, TopCreatorsBlock, AttributionTableBlock, ChartBlock,
    )
    list_display = ("report", "order", "polymorphic_ctype")
    list_filter = ("polymorphic_ctype",)
    search_fields = ("report__title",)


class _BlockChildAdminBase(SortableAdminBase, PolymorphicChildModelAdmin):
    """Base común de los 6 subtipos. Cada uno puede sobrescribir `inlines`
    para agregar sus child rows.

    Hereda `SortableAdminBase` para que los child admins que hostean
    SortableTabularInline (KpiGrid / MetricsTable / Chart / TopContent) emitan
    el CSS/JS de adminsortable2 y habiliten drag-reorder en el UI. Subtipos
    que no usan sortable inlines (TextImage, AttributionTable) lo heredan
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


@admin.register(KpiGridBlock)
class KpiGridBlockAdmin(_BlockChildAdminBase):
    inlines = [KpiTileInline]
    list_display = ("report", "order", "title")


@admin.register(MetricsTableBlock)
class MetricsTableBlockAdmin(_BlockChildAdminBase):
    inlines = [MetricsTableRowInline]
    list_display = ("report", "order", "title", "network")
    list_filter = ("network",)


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


@admin.register(AttributionTableBlock)
class AttributionTableBlockAdmin(_BlockChildAdminBase):
    inlines = [OneLinkAttributionInline]
    list_display = ("report", "order", "title", "show_total")


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
