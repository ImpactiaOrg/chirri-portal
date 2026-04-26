"""Form for the PDF importer (DEV-84). Mirrors ImportReportForm but for .pdf only."""
from django import forms
from django.core.validators import FileExtensionValidator

from apps.campaigns.models import Campaign, Stage
from apps.tenants.models import Brand, Client


MAX_PDF_SIZE = 50 * 1024 * 1024  # 50 MB


class ImportPdfForm(forms.Form):
    client = forms.ModelChoiceField(
        queryset=Client.objects.order_by("name"), label="Cliente",
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
        label="PDF del reporte legacy",
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("client", "brand", "campaign", "stage"):
            attrs = self.fields[name].widget.attrs
            attrs["class"] = (attrs.get("class", "") + " report-import-cascade").strip()
            attrs["data-cascade-level"] = name

    def clean_file(self):
        f = self.cleaned_data["file"]
        if f.size > MAX_PDF_SIZE:
            raise forms.ValidationError(
                f"PDF muy grande ({f.size // (1024 * 1024)} MB). "
                f"Máximo: {MAX_PDF_SIZE // (1024 * 1024)} MB."
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
