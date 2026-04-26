from django.contrib import admin

from .models import Campaign, Stage


class StageInline(admin.TabularInline):
    model = Stage
    extra = 0
    fields = ("order", "kind", "name", "start_date", "end_date")


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "status", "start_date", "end_date", "is_ongoing_operation")
    list_filter = ("status", "brand__client", "brand", "is_ongoing_operation")
    search_fields = ("name", "tagline", "brand__name")
    inlines = [StageInline]
    fieldsets = (
        (None, {"fields": ("brand", "name", "status", "is_ongoing_operation")}),
        ("Narrativa", {"fields": ("mother_concept", "tagline", "objective", "brief")}),
        ("Fechas", {"fields": ("start_date", "end_date")}),
    )


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display = ("name", "campaign", "kind", "order", "start_date", "end_date")
    list_filter = ("kind", "campaign__brand")
    search_fields = ("name", "campaign__name")
