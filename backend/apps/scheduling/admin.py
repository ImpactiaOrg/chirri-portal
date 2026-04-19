from django.contrib import admin

from .models import ScheduledPost


@admin.register(ScheduledPost)
class ScheduledPostAdmin(admin.ModelAdmin):
    list_display = ("brand", "network", "scheduled_for", "status", "campaign", "stage")
    list_filter = ("status", "network", "brand")
    search_fields = ("caption", "brand__name")
    autocomplete_fields = ("brand", "campaign", "stage", "campaign_influencer")
    date_hierarchy = "scheduled_for"
