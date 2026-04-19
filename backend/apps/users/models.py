from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.tenants.models import Client

from .managers import ClientUserManager


class ClientUser(AbstractBaseUser, PermissionsMixin):
    """Portal user. Scoped to a single Client (tenant). Superusers may have no client."""

    class Role(models.TextChoices):
        VIEWER = "VIEWER", "Viewer"
        ADMIN_CLIENT = "ADMIN_CLIENT", "Client admin"

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=200, blank=True)
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
        help_text="Null for Chirri staff / superusers with cross-tenant access.",
    )
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.VIEWER)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = ClientUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email
