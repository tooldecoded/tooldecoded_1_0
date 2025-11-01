"""Forms for manufacturer URL import."""

from django import forms
from django.core.exceptions import ValidationError

from product_management.services.manufacturer_import import get_parser_for_url


class ManufacturerImportForm(forms.Form):
    """Form for importing product data from manufacturer URLs."""
    
    manufacturer_url = forms.URLField(
        label="Manufacturer Product URL",
        widget=forms.URLInput(attrs={
            "class": "pm-input",
            "placeholder": "https://www.dewalt.com/product/..."
        }),
        help_text="Enter a manufacturer product page URL to auto-populate fields",
    )
    
    def clean_manufacturer_url(self):
        url = self.cleaned_data.get("manufacturer_url")
        if not url:
            return url
        
        # Check if we have a parser for this URL
        parser = get_parser_for_url(url)
        if not parser:
            raise ValidationError(
                "No parser available for this manufacturer URL. "
                "Supported manufacturers: DEWALT (more coming soon)."
            )
        
        # Validate URL format
        if not parser.validate_url(url):
            raise ValidationError("Invalid URL format for this manufacturer.")
        
        return url


class ImportPreviewForm(forms.Form):
    """Form for approving import preview."""
    
    parsed_data_json = forms.CharField(widget=forms.HiddenInput(), required=False)
    existing_product_id = forms.UUIDField(required=False, widget=forms.HiddenInput())
    existing_component_id = forms.UUIDField(required=False, widget=forms.HiddenInput())
    approve = forms.BooleanField(required=True, widget=forms.HiddenInput())

