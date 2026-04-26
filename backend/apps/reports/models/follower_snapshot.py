from django.db import models

from apps.reports.choices import Network


class BrandFollowerSnapshot(models.Model):
    """Brand-level follower count por red, snapshot por fecha.

    Cross-report (vive a nivel brand, no block): se usa para charts de
    crecimiento mensual que comparan reportes contiguos.
    """

    brand = models.ForeignKey(
        "tenants.Brand",
        on_delete=models.CASCADE,
        related_name="follower_snapshots",
    )
    network = models.CharField(max_length=16, choices=Network.choices)
    as_of = models.DateField()
    followers_count = models.PositiveIntegerField()

    class Meta:
        unique_together = [("brand", "network", "as_of")]
        ordering = ["-as_of"]

    def __str__(self):
        return f"{self.brand_id}/{self.network} @ {self.as_of}: {self.followers_count}"
