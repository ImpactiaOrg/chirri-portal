from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import ClientUser


@admin.register(ClientUser)
class ClientUserAdmin(DjangoUserAdmin):
    list_display = ("email", "full_name", "client", "role", "is_staff", "is_active")
    list_filter = ("client", "role", "is_staff", "is_active")
    search_fields = ("email", "full_name")
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Perfil", {"fields": ("full_name", "client", "role")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "client", "role", "is_staff", "is_active"),
        }),
    )
    readonly_fields = ("date_joined", "last_login")
