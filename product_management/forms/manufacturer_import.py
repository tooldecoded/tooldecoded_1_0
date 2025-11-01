"""Forms for manufacturer URL import."""

from django import forms
from django.core.exceptions import ValidationError

from product_management.services.manufacturer_import import get_parser_for_brand


class ManufacturerImportForm(forms.Form):
    """Form for importing product data from manufacturer URLs."""
    
    manufacturer_url = forms.URLField(
        label="Manufacturer Product URL",
        required=False,
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
        
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            raise ValidationError("URL must start with http:// or https://")
        
        return url


class ManufacturerHTMLImportForm(forms.Form):
    """Form for importing product data from pasted HTML source."""
    
    manufacturer_brand = forms.ChoiceField(
        label="Manufacturer Brand",
        choices=[("DEWALT", "DEWALT")],
        widget=forms.Select(attrs={"class": "pm-select"}),
        help_text="Select the manufacturer brand",
    )
    
    page_source = forms.CharField(
        label="Page Source Code",
        widget=forms.Textarea(attrs={
            "class": "pm-textarea",
            "rows": "20",
            "placeholder": "Paste the complete HTML source code of the product page here..."
        }),
        help_text="Paste the complete HTML source code (View Page Source or Ctrl+U)",
    )
    
    def clean_page_source(self):
        html = self.cleaned_data.get("page_source", "").strip()
        if not html:
            raise ValidationError("HTML source code is required.")
        
        if len(html) < 500:
            raise ValidationError("HTML source appears too short. Please paste the complete page source.")
        
        return html


class ImportPreviewForm(forms.Form):
    """Form for editing and approving import preview."""
    
    # Product fields
    product_name = forms.CharField(
        label="Product Name",
        widget=forms.TextInput(attrs={"class": "pm-input"}),
        required=True
    )
    product_sku = forms.CharField(
        label="Product SKU",
        widget=forms.TextInput(attrs={"class": "pm-input"}),
        required=True
    )
    product_description = forms.CharField(
        label="Product Description",
        widget=forms.Textarea(attrs={"class": "pm-textarea", "rows": "8"}),
        required=False
    )
    product_image = forms.CharField(
        label="Product Image URL",
        widget=forms.TextInput(attrs={"class": "pm-input"}),
        required=False
    )
    
    # Component fields
    component_name = forms.CharField(
        label="Component Name",
        widget=forms.TextInput(attrs={"class": "pm-input"}),
        required=True
    )
    component_sku = forms.CharField(
        label="Component SKU",
        widget=forms.TextInput(attrs={"class": "pm-input"}),
        required=True
    )
    component_description = forms.CharField(
        label="Component Description",
        widget=forms.Textarea(attrs={"class": "pm-textarea", "rows": "8"}),
        required=False
    )
    component_image = forms.CharField(
        label="Component Image URL",
        widget=forms.TextInput(attrs={"class": "pm-input"}),
        required=False
    )
    
    # Hidden fields for approval
    parsed_data_json = forms.CharField(widget=forms.HiddenInput(), required=False)
    preview_data_json = forms.CharField(widget=forms.HiddenInput(), required=False)
    existing_product_id = forms.UUIDField(required=False, widget=forms.HiddenInput())
    existing_component_id = forms.UUIDField(required=False, widget=forms.HiddenInput())
    approve = forms.BooleanField(required=True, widget=forms.HiddenInput(), initial=True)

