from django.db import models


class Client(models.Model):
    """Tenant root — one per customer of Chirri."""

    name = models.CharField(max_length=200, unique=True)
    logo_url = models.URLField(blank=True)
    primary_color = models.CharField(max_length=20, default="#000000")
    secondary_color = models.CharField(max_length=20, default="#FFFFFF")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Brand(models.Model):
    """A brand managed by Chirri for a Client. One Client can have many brands."""

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="brands")
    name = models.CharField(max_length=200)
    logo_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["client__name", "name"]
        unique_together = [("client", "name")]

    def __str__(self):
        return f"{self.client.name} · {self.name}"
