from django.contrib import admin

from .models import CampaignInfluencer, Influencer


class CampaignInfluencerInline(admin.TabularInline):
    model = CampaignInfluencer
    extra = 0
    fields = ("campaign", "narrative_line", "stage", "status", "fee_ars", "includes_content", "includes_paid_boost")
    autocomplete_fields = ("campaign", "narrative_line", "stage")


@admin.register(Influencer)
class InfluencerAdmin(admin.ModelAdmin):
    list_display = ("handle_ig", "handle_tiktok", "size_tier", "followers_ig", "followers_tiktok", "niche")
    list_filter = ("size_tier", "niche")
    search_fields = ("handle_ig", "handle_tiktok", "handle_x", "niche")
    inlines = [CampaignInfluencerInline]


@admin.register(CampaignInfluencer)
class CampaignInfluencerAdmin(admin.ModelAdmin):
    list_display = ("influencer", "campaign", "narrative_line", "stage", "status", "fee_ars")
    list_filter = ("status", "campaign")
    search_fields = ("influencer__handle_ig", "campaign__name")
    autocomplete_fields = ("influencer", "campaign", "narrative_line", "stage")
