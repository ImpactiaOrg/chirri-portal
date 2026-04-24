"""Form del admin para importar reports desde xlsx/zip (DEV-83 · Etapa 2)."""
from django import forms
from django.core.validators import FileExtensionValidator

from apps.campaigns.models import Campaign, Stage
from apps.tenants.models import Brand, Client


# Caps alineados con bundle_reader.
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


class ImportReportForm(forms.Form):
    """Form con cascading selects: Cliente → Brand → Campaña → Etapa.

    El server valida la jerarquía (que la Stage pertenezca al Client elegido).
    El JS del template pinta/repuebla cada select al cambiar el padre, usando
    los endpoints JSON expuestos en ReportAdmin.
    """
    client = forms.ModelChoiceField(
        queryset=Client.objects.order_by("name"),
        label="Cliente",
    )
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.select_related("client").order_by("name"),
        label="Brand",
    )
    campaign = forms.ModelChoiceField(
        queryset=Campaign.objects.select_related("brand").order_by("name"),
        label="Campaña",
    )
    stage = forms.ModelChoiceField(
        queryset=Stage.objects.select_related("campaign__brand__client").order_by(
            "campaign__name", "order",
        ),
        label="Etapa",
    )
    file = forms.FileField(
        label="Archivo (.zip con Excel + imágenes, o .xlsx solo si no hay thumbnails)",
        validators=[FileExtensionValidator(allowed_extensions=["zip", "xlsx"])],
    )

    def __init__(self, *args, admin_site=None, **kwargs):
        # `admin_site` aceptado por compat con el caller — no se usa.
        super().__init__(*args, **kwargs)
        # Todos los selects reciben una clase para que el JS los enganche.
        for name in ("client", "brand", "campaign", "stage"):
            self.fields[name].widget.attrs["class"] = (
                self.fields[name].widget.attrs.get("class", "") + " report-import-cascade"
            ).strip()
            self.fields[name].widget.attrs["data-cascade-level"] = name

    def clean_file(self):
        f = self.cleaned_data["file"]
        if f.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError(
                f"Archivo muy grande ({f.size // (1024 * 1024)} MB). "
                f"Máximo permitido: {MAX_UPLOAD_SIZE // (1024 * 1024)} MB."
            )
        return f

    def clean(self):
        cleaned = super().clean()
        client = cleaned.get("client")
        brand = cleaned.get("brand")
        campaign = cleaned.get("campaign")
        stage = cleaned.get("stage")
        if brand and client and brand.client_id != client.pk:
            self.add_error("brand", "El brand no pertenece al cliente elegido.")
        if campaign and brand and campaign.brand_id != brand.pk:
            self.add_error("campaign", "La campaña no pertenece al brand elegido.")
        if stage and campaign and stage.campaign_id != campaign.pk:
            self.add_error("stage", "La etapa no pertenece a la campaña elegida.")
        return cleaned
