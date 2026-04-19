from django.db import models

from apps.campaigns.models import Campaign, Stage
from apps.influencers.models import CampaignInfluencer
from apps.tenants.models import Brand


class ScheduledPost(models.Model):
    """Content calendar entry: a post scheduled for a given brand on a given date."""

    class Network(models.TextChoices):
        INSTAGRAM = "INSTAGRAM", "Instagram"
        TIKTOK = "TIKTOK", "TikTok"
        X = "X", "X/Twitter"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        APPROVED = "APPROVED", "Approved"
        PUBLISHED = "PUBLISHED", "Published"

    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="scheduled_posts")
    campaign = models.ForeignKey(
        Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name="scheduled_posts"
    )
    stage = models.ForeignKey(
        Stage, on_delete=models.SET_NULL, null=True, blank=True, related_name="scheduled_posts"
    )
    campaign_influencer = models.ForeignKey(
        CampaignInfluencer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scheduled_posts",
    )
    network = models.CharField(max_length=16, choices=Network.choices, default=Network.INSTAGRAM)
    scheduled_for = models.DateTimeField()
    caption = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_for"]

    def __str__(self):
        return f"{self.brand.name} · {self.scheduled_for:%Y-%m-%d} · {self.status}"
