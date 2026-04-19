from django.contrib import admin

from .models import Brand, Client


class BrandInline(admin.TabularInline):
    model = Brand
    extra = 0


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "primary_color", "secondary_color", "created_at")
    search_fields = ("name",)
    inlines = [BrandInline]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "client", "created_at")
    list_filter = ("client",)
    search_fields = ("name", "client__name")
