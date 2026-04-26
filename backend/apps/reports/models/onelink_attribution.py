from django.db import models


class OneLinkAttribution(models.Model):
    """Row de la tabla de atribución de un AttributionTableBlock.

    Cada row es un handle de influencer con su clicks + app_downloads.
    Post-DEV-116 la FK pasó de Report a AttributionTableBlock (las rows
    pertenecen al block tipado, no al reporte directo).
    """

    attribution_block = models.ForeignKey(
        "reports.AttributionTableBlock",
        on_delete=models.CASCADE,
        related_name="entries",
    )
    influencer_handle = models.CharField(max_length=120)
    clicks = models.PositiveIntegerField(default=0)
    app_downloads = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["attribution_block", "-app_downloads"]
        indexes = [models.Index(fields=["attribution_block"])]

    def __str__(self):
        return f"{self.attribution_block_id} · {self.influencer_handle}: {self.app_downloads}d/{self.clicks}c"
