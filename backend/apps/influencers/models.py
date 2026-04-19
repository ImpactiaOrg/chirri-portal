from django.db import models

from apps.campaigns.models import Campaign, NarrativeLine, Stage


class Influencer(models.Model):
    """Global influencer profile. Not scoped to a Client — the same person may
    work across multiple clients' campaigns."""

    class SizeTier(models.TextChoices):
        NANO = "NANO", "Nano"
        MICRO = "MICRO", "Micro"
        MACRO = "MACRO", "Macro"
        MEGA = "MEGA", "Mega"

    handle_ig = models.CharField(max_length=100, blank=True)
    handle_tiktok = models.CharField(max_length=100, blank=True)
    handle_x = models.CharField(max_length=100, blank=True)
    link_ig = models.URLField(blank=True)
    link_tiktok = models.URLField(blank=True)

    followers_ig = models.PositiveIntegerField(default=0)
    followers_tiktok = models.PositiveIntegerField(default=0)
    size_tier = models.CharField(max_length=8, choices=SizeTier.choices, blank=True)

    er_ig = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    er_tiktok = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    engagement_level = models.CharField(max_length=50, blank=True)

    niche = models.CharField(max_length=100, blank=True)
    main_audience = models.CharField(max_length=200, blank=True)
    age_range = models.CharField(max_length=50, blank=True)
    gender = models.CharField(max_length=50, blank=True)

    top_format = models.CharField(max_length=100, blank=True)
    comm_style = models.CharField(max_length=100, blank=True)
    ideal_campaign_type = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["handle_ig"]

    def __str__(self):
        return self.handle_ig or self.handle_tiktok or self.handle_x or f"Influencer #{self.pk}"


class CampaignInfluencer(models.Model):
    """Through table: an influencer's participation in a specific campaign."""

    class Status(models.TextChoices):
        MUST = "MUST", "Must"
        ALTERNATIVE = "ALTERNATIVE", "Alternative"
        NEGOTIATE_FEE = "NEGOTIATE_FEE", "Negotiate fee"
        DISCARDED = "DISCARDED", "Discarded"

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="campaign_influencers")
    influencer = models.ForeignKey(Influencer, on_delete=models.CASCADE, related_name="campaign_assignments")
    narrative_line = models.ForeignKey(
        NarrativeLine, on_delete=models.SET_NULL, null=True, blank=True, related_name="influencers"
    )
    stage = models.ForeignKey(
        Stage, on_delete=models.SET_NULL, null=True, blank=True, related_name="campaign_influencers"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.MUST)
    fee_ars = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    cost_per_engagement = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    includes_content = models.BooleanField(default=True)
    includes_paid_boost = models.BooleanField(default=False)
    previous_collabs = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [("campaign", "influencer")]
        ordering = ["campaign", "-status"]

    def __str__(self):
        return f"{self.campaign.name} ← {self.influencer}"
