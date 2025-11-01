"""Form layer for the product management backoffice."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelChoiceField, ModelMultipleChoiceField

from product_management.services import (
    BundleComponentItem,
    create_bare_tool,
    create_bundle_from_products,
)
from toolanalysis.models import (
    BatteryPlatforms,
    BatteryVoltages,
    Brands,
    Categories,
    Components,
    Features,
    ItemTypes,
    ListingTypes,
    MotorTypes,
    ProductLines,
    Products,
    Statuses,
    Subcategories,
)


class _NameChoice(ModelChoiceField):
    def label_from_instance(self, obj):
        return getattr(obj, "fullname", getattr(obj, "name", str(obj)))


class _ListingTypeChoice(ModelChoiceField):
    def label_from_instance(self, obj):
        retailer = getattr(obj, "retailer", None)
        if retailer:
            return f"{obj.name} — {retailer.name}"
        return obj.name


class _BatteryPlatformMulti(ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        brand = getattr(obj, "brand", None)
        if brand:
            return f"{brand.name} — {obj.name}"
        return obj.name


class _VoltageMulti(ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return str(getattr(obj, "value", obj))


class _ProductLineMulti(ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        brand = getattr(obj, "brand", None)
        if brand:
            return f"{brand.name} — {obj.name}"
        return obj.name


class _SimpleMulti(ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return getattr(obj, "fullname", getattr(obj, "name", str(obj)))


class ComponentQuickForm(forms.ModelForm):
    brand = _NameChoice(
        queryset=Brands.objects.all().order_by("name"),
        required=True,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Brand",
    )
    listingtype = _ListingTypeChoice(
        queryset=ListingTypes.objects.select_related("retailer").all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Listing type",
    )
    motortype = _NameChoice(
        queryset=MotorTypes.objects.all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Motor type",
    )
    itemtypes = _SimpleMulti(
        queryset=ItemTypes.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Item types",
    )
    subcategories = _SimpleMulti(
        queryset=Subcategories.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Subcategories",
    )
    categories = _SimpleMulti(
        queryset=Categories.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Categories",
    )
    batteryplatforms = _BatteryPlatformMulti(
        queryset=BatteryPlatforms.objects.select_related("brand").all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Battery platforms",
    )
    batteryvoltages = _VoltageMulti(
        queryset=BatteryVoltages.objects.all().order_by("value"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Battery voltages",
    )
    productlines = _ProductLineMulti(
        queryset=ProductLines.objects.select_related("brand").all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Product lines",
    )
    features = _SimpleMulti(
        queryset=Features.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Features",
    )
    fair_price_narrative = forms.JSONField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "class": "pm-textarea"}),
        label="Fair price narrative (JSON)",
    )

    class Meta:
        model = Components
        fields = [
            "name",
            "sku",
            "description",
            "brand",
            "listingtype",
            "motortype",
            "itemtypes",
            "subcategories",
            "categories",
            "batteryplatforms",
            "batteryvoltages",
            "productlines",
            "features",
            "image",
            "is_featured",
            "standalone_price",
            "showcase_priority",
            "fair_price_narrative",
            "isaccessory",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "pm-input"}),
            "sku": forms.TextInput(attrs={"class": "pm-input"}),
            "description": forms.Textarea(attrs={"rows": 4, "class": "pm-textarea"}),
            "image": forms.TextInput(attrs={"class": "pm-input"}),
            "is_featured": forms.CheckboxInput(attrs={"class": "pm-checkbox"}),
            "standalone_price": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "class": "pm-input"}
            ),
            "showcase_priority": forms.NumberInput(
                attrs={"step": "1", "min": "0", "class": "pm-input"}
            ),
            "isaccessory": forms.CheckboxInput(attrs={"class": "pm-checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._constrain_productlines()

    def _constrain_productlines(self) -> None:
        brand = None
        if self.is_bound:
            brand_field = f"{self.prefix}-brand" if self.prefix else "brand"
            brand_id = self.data.get(brand_field)
            if brand_id:
                brand = Brands.objects.filter(id=brand_id).first()
        elif self.instance.pk:
            brand = self.instance.brand

        if brand:
            self.fields["productlines"].queryset = ProductLines.objects.filter(brand=brand).order_by("name")
        else:
            self.fields["productlines"].queryset = ProductLines.objects.all().order_by("name")

    def clean(self):
        cleaned = super().clean()
        brand = cleaned.get("brand")
        sku = cleaned.get("sku")
        if brand and sku:
            qs = Components.objects.filter(brand=brand, sku=sku)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("sku", "Component SKU already exists for this brand.")
        return cleaned

    def save(self, commit: bool = True):
        instance = super().save(commit=commit)
        return instance

    def get_payload(self) -> Dict[str, Any]:
        if not hasattr(self, "cleaned_data"):
            raise ValueError("Form must be validated before extracting payload.")
        return {field: self.cleaned_data.get(field) for field in self.Meta.fields}


class ProductQuickForm(forms.ModelForm):
    brand = _NameChoice(
        queryset=Brands.objects.all().order_by("name"),
        required=True,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Brand",
    )
    listingtype = _ListingTypeChoice(
        queryset=ListingTypes.objects.select_related("retailer").all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Listing type",
    )
    motortype = _NameChoice(
        queryset=MotorTypes.objects.all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Motor type",
    )
    status = _NameChoice(
        queryset=Statuses.objects.all().order_by("sortorder", "name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Status",
    )
    itemtypes = _SimpleMulti(
        queryset=ItemTypes.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Item types",
    )
    subcategories = _SimpleMulti(
        queryset=Subcategories.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Subcategories",
    )
    categories = _SimpleMulti(
        queryset=Categories.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Categories",
    )
    batteryplatforms = _BatteryPlatformMulti(
        queryset=BatteryPlatforms.objects.select_related("brand").all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Battery platforms",
    )
    batteryvoltages = _VoltageMulti(
        queryset=BatteryVoltages.objects.all().order_by("value"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Battery voltages",
    )
    features = _SimpleMulti(
        queryset=Features.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Features",
    )
    bullets = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "class": "pm-textarea"}),
        label="Bullets",
    )

    class Meta:
        model = Products
        fields = [
            "name",
            "sku",
            "description",
            "brand",
            "listingtype",
            "motortype",
            "status",
            "itemtypes",
            "subcategories",
            "categories",
            "batteryplatforms",
            "batteryvoltages",
            "features",
            "image",
            "bullets",
            "isaccessory",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "pm-input"}),
            "sku": forms.TextInput(attrs={"class": "pm-input"}),
            "description": forms.Textarea(attrs={"rows": 4, "class": "pm-textarea"}),
            "image": forms.TextInput(attrs={"class": "pm-input"}),
            "isaccessory": forms.CheckboxInput(attrs={"class": "pm-checkbox"}),
        }

    def clean(self):
        cleaned = super().clean()
        brand = cleaned.get("brand")
        sku = cleaned.get("sku")
        if brand and sku:
            qs = Products.objects.filter(brand=brand, sku=sku)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("sku", "Product SKU already exists for this brand.")
        return cleaned

    def save(self, commit: bool = True):
        instance = super().save(commit=False)
        # Default status to "Active" if not set
        if not instance.status:
            from toolanalysis.models import Statuses
            active_status, _ = Statuses.objects.get_or_create(name="Active", defaults={"sortorder": 1})
            instance.status = active_status
        if commit:
            instance.save()
            self.save_m2m()
        return instance

    def get_payload(self) -> Dict[str, Any]:
        if not hasattr(self, "cleaned_data"):
            raise ValueError("Form must be validated before extracting payload.")
        return {field: self.cleaned_data.get(field) for field in self.Meta.fields}


class BareToolForm(ComponentQuickForm):
    create_product = forms.BooleanField(
        required=False,
        initial=True,
        label="Also create product shell",
    )
    product_brand = _NameChoice(
        queryset=Brands.objects.all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Product brand",
    )
    product_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "pm-input"}),
        label="Product name",
    )
    product_sku = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "pm-input"}),
        label="Product SKU",
    )
    product_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "class": "pm-textarea"}),
        label="Product description",
    )
    product_listingtype = _ListingTypeChoice(
        queryset=ListingTypes.objects.select_related("retailer").all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Product listing type",
    )
    product_motortype = _NameChoice(
        queryset=MotorTypes.objects.all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Product motor type",
    )
    product_status = _NameChoice(
        queryset=Statuses.objects.all().order_by("sortorder", "name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Product status",
    )
    product_itemtypes = _SimpleMulti(
        queryset=ItemTypes.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Product item types",
    )
    product_subcategories = _SimpleMulti(
        queryset=Subcategories.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Product subcategories",
    )
    product_categories = _SimpleMulti(
        queryset=Categories.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Product categories",
    )
    product_batteryplatforms = _BatteryPlatformMulti(
        queryset=BatteryPlatforms.objects.select_related("brand").all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Product battery platforms",
    )
    product_batteryvoltages = _VoltageMulti(
        queryset=BatteryVoltages.objects.all().order_by("value"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Product battery voltages",
    )
    product_features = _SimpleMulti(
        queryset=Features.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Product features",
    )
    product_image = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "pm-input"}),
        label="Product image",
    )
    product_bullets = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "class": "pm-textarea"}),
        label="Product bullets",
    )
    product_isaccessory = forms.BooleanField(
        required=False,
        initial=False,
        label="Product marked as accessory",
    )
    product_component_quantity = forms.IntegerField(
        required=False,
        min_value=1,
        initial=1,
        label="Quantity of component in product",
    )

    _product_m2m_fields: Sequence[str] = (
        "product_itemtypes",
        "product_subcategories",
        "product_categories",
        "product_batteryplatforms",
        "product_batteryvoltages",
        "product_features",
    )

    _product_field_map: Dict[str, str] = {
        "product_name": "name",
        "product_sku": "sku",
        "product_description": "description",
        "product_brand": "brand",
        "product_listingtype": "listingtype",
        "product_motortype": "motortype",
        "product_status": "status",
        "product_image": "image",
        "product_bullets": "bullets",
        "product_isaccessory": "isaccessory",
    }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("create_product"):
            # Product name will auto-populate from component name if not provided
            # No need to require it explicitly
            pass
        return cleaned

    def save(self, user=None):
        if not hasattr(self, "cleaned_data"):
            raise ValidationError("BareToolForm must be validated before saving.")

        component_payload = self.get_payload()
        product_payload: Optional[Dict[str, Any]] = None

        if self.cleaned_data.get("create_product"):
            product_payload = {}
            # Auto-populate product fields from component fields, only override if explicitly provided
            for form_field, model_field in self._product_field_map.items():
                value = self.cleaned_data.get(form_field)
                # If product field is empty/None, use component's value
                if not value and form_field not in ("product_bullets", "product_status"):  # bullets and status don't exist on components
                    if form_field == "product_name":
                        value = component_payload.get("name")
                    elif form_field == "product_sku":
                        value = component_payload.get("sku")
                    elif form_field == "product_description":
                        value = component_payload.get("description")
                    elif form_field == "product_brand":
                        value = component_payload.get("brand")
                    elif form_field == "product_listingtype":
                        value = component_payload.get("listingtype")
                    elif form_field == "product_motortype":
                        value = component_payload.get("motortype")
                    elif form_field == "product_image":
                        value = component_payload.get("image")
                    elif form_field == "product_isaccessory":
                        value = component_payload.get("isaccessory")
                product_payload[model_field] = value
            
            # Default status to "Active" if not provided
            if not product_payload.get("status"):
                from toolanalysis.models import Statuses
                active_status, _ = Statuses.objects.get_or_create(name="Active", defaults={"sortorder": 1})
                product_payload["status"] = active_status

            # Auto-populate M2M fields from component if not provided
            for m2m_field in self._product_m2m_fields:
                model_field = m2m_field.replace("product_", "")
                value = self.cleaned_data.get(m2m_field)
                if not value:
                    # Use component's M2M values
                    component_field = model_field
                    if component_field in component_payload:
                        value = component_payload[component_field]
                product_payload[model_field] = value or []

            product_payload["component_quantity"] = self.cleaned_data.get(
                "product_component_quantity", 1
            )

        component, product = create_bare_tool(
            component_data=component_payload,
            product_data=product_payload,
            user=user,
        )

        return component, product


class BundleProductForm(ProductQuickForm):
    source_products = forms.CharField(
        label="Source products",
        required=True,
        widget=forms.HiddenInput(),
        help_text="Select products to bundle in the search interface above.",
    )

    def clean_source_products(self):
        value = self.cleaned_data["source_products"]
        if not value:
            raise ValidationError("At least one product must be selected.")
        
        product_ids = [pid.strip() for pid in value.split(",") if pid.strip()]
        if not product_ids:
            raise ValidationError("No valid product IDs provided.")
        
        from toolanalysis.models import Products, ProductComponents
        products = Products.objects.filter(id__in=product_ids).prefetch_related(
            'productcomponents_set__component'
        )
        
        found_ids = {str(p.id) for p in products}
        missing = set(product_ids) - found_ids
        if missing:
            raise ValidationError(f"Products not found: {', '.join(list(missing)[:5])}.")
        
        # Ensure all selected products have components
        products_without_components = []
        component_items_dict: Dict[str, BundleComponentItem] = {}
        
        for product in products:
            product_components = ProductComponents.objects.filter(product=product).select_related('component')
            if not product_components.exists():
                products_without_components.append(product.name)
            else:
                # Aggregate components (in case same component appears multiple times)
                for pc in product_components:
                    component_id = str(pc.component.id)
                    if component_id in component_items_dict:
                        # Same component in multiple products - aggregate quantity
                        component_items_dict[component_id].quantity += pc.quantity
                    else:
                        component_items_dict[component_id] = BundleComponentItem(
                            component=pc.component,
                            quantity=pc.quantity
                        )
        
        if products_without_components:
            raise ValidationError(
                f"These products have no components and cannot be bundled: {', '.join(products_without_components[:3])}."
            )
        
        if not component_items_dict:
            raise ValidationError("No components found in the selected products.")
        
        self._parsed_component_items = list(component_items_dict.values())
        self._selected_products = list(products)
        return value

    def save(self, user=None):
        if not hasattr(self, "cleaned_data"):
            raise ValidationError("BundleProductForm must be validated before saving.")

        bundle_payload = self.get_payload()
        component_items: Sequence[BundleComponentItem] = getattr(
            self, "_parsed_component_items", []
        )

        product = create_bundle_from_products(
            bundle_data=bundle_payload,
            component_items=component_items,
            user=user,
        )
        return product


class BundleProductSelectorForm(forms.Form):
    """Form for selecting products to bundle - only shows products that have components."""
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={"class": "pm-input", "placeholder": "Search products"}),
    )
    brand = _NameChoice(
        queryset=Brands.objects.all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Brand",
    )
    motortype = _NameChoice(
        queryset=MotorTypes.objects.all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Motor type",
    )
    listingtype = _ListingTypeChoice(
        queryset=ListingTypes.objects.select_related("retailer").all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Listing type",
    )
    status = _NameChoice(
        queryset=Statuses.objects.all().order_by("sortorder", "name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Status",
    )
    itemtype = _SimpleMulti(
        queryset=ItemTypes.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 4, "class": "pm-multiselect"}),
        label="Item type",
    )
    category = _SimpleMulti(
        queryset=Categories.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 4, "class": "pm-multiselect"}),
        label="Category",
    )


class ComponentSelectorForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={"class": "pm-input", "placeholder": "Search components"}),
    )
    brand = _NameChoice(
        queryset=Brands.objects.all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Brand",
    )
    motortype = _NameChoice(
        queryset=MotorTypes.objects.all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Motor type",
    )
    listingtype = _ListingTypeChoice(
        queryset=ListingTypes.objects.select_related("retailer").all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Listing type",
    )
    itemtype = _SimpleMulti(
        queryset=ItemTypes.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 4, "class": "pm-multiselect"}),
        label="Item type",
    )
    category = _SimpleMulti(
        queryset=Categories.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 4, "class": "pm-multiselect"}),
        label="Category",
    )
    componentclass = _NameChoice(
        queryset=None,  # Will be set in __init__
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Component class",
    )
    is_featured = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "pm-checkbox"}),
        label="Featured only",
    )
    isaccessory = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "pm-checkbox"}),
        label="Accessories only",
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from toolanalysis.models import ComponentClasses
        self.fields["componentclass"].queryset = ComponentClasses.objects.all().order_by("sortorder", "name")


class ProductSelectorForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(attrs={"class": "pm-input", "placeholder": "Search products"}),
    )
    brand = _NameChoice(
        queryset=Brands.objects.all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Brand",
    )
    motortype = _NameChoice(
        queryset=MotorTypes.objects.all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Motor type",
    )
    listingtype = _ListingTypeChoice(
        queryset=ListingTypes.objects.select_related("retailer").all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Listing type",
    )
    status = _NameChoice(
        queryset=Statuses.objects.all().order_by("sortorder", "name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Status",
    )
    itemtype = _SimpleMulti(
        queryset=ItemTypes.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 4, "class": "pm-multiselect"}),
        label="Item type",
    )
    category = _SimpleMulti(
        queryset=Categories.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 4, "class": "pm-multiselect"}),
        label="Category",
    )
    isaccessory = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "pm-checkbox"}),
        label="Accessories only",
    )


class BatchComponentEditForm(forms.Form):
    """Form for batch editing multiple components."""
    
    component_ids = forms.CharField(widget=forms.HiddenInput(), required=True)
    
    brand = _NameChoice(
        queryset=Brands.objects.all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Brand",
        help_text="Leave blank to keep existing values",
    )
    listingtype = _ListingTypeChoice(
        queryset=ListingTypes.objects.select_related("retailer").all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Listing type",
        help_text="Leave blank to keep existing values",
    )
    motortype = _NameChoice(
        queryset=MotorTypes.objects.all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Motor type",
        help_text="Leave blank to keep existing values",
    )
    is_featured = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "pm-checkbox"}),
        label="Featured",
        help_text="Check to set all to featured (leave unchecked to keep existing values)",
    )
    isaccessory = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "pm-checkbox"}),
        label="Accessory",
        help_text="Check to set all as accessories (leave unchecked to keep existing values)",
    )
    itemtypes = _SimpleMulti(
        queryset=ItemTypes.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Item types",
        help_text="Leave blank to keep existing values, or select to replace all",
    )
    categories = _SimpleMulti(
        queryset=Categories.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Categories",
        help_text="Leave blank to keep existing values, or select to replace all",
    )
    subcategories = _SimpleMulti(
        queryset=Subcategories.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Subcategories",
        help_text="Leave blank to keep existing values, or select to replace all",
    )
    batteryplatforms = _BatteryPlatformMulti(
        queryset=BatteryPlatforms.objects.select_related("brand").all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Battery platforms",
        help_text="Leave blank to keep existing values, or select to replace all",
    )
    batteryvoltages = _VoltageMulti(
        queryset=BatteryVoltages.objects.all().order_by("value"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Battery voltages",
        help_text="Leave blank to keep existing values, or select to replace all",
    )
    productlines = _ProductLineMulti(
        queryset=ProductLines.objects.select_related("brand").all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Product lines",
        help_text="Leave blank to keep existing values, or select to replace all",
    )
    features = _SimpleMulti(
        queryset=Features.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Features",
        help_text="Leave blank to keep existing values, or select to replace all",
    )
    image = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "pm-input"}),
        label="Image URL",
        help_text="Leave blank to keep existing values",
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "class": "pm-textarea"}),
        label="Description",
        help_text="Leave blank to keep existing values",
    )
    showcase_priority = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={"step": "1", "class": "pm-input"}),
        label="Showcase priority",
        help_text="Leave blank to keep existing values",
    )
    standalone_price = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0", "class": "pm-input"}),
        label="Standalone price",
        help_text="Leave blank to keep existing values",
    )
    componentclass = _NameChoice(
        queryset=None,  # Will be set dynamically or use all
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Component class",
        help_text="Leave blank to keep existing values",
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from toolanalysis.models import ComponentClasses
        self.fields["componentclass"].queryset = ComponentClasses.objects.all().order_by("sortorder", "name")
    
    def clean_component_ids(self):
        value = self.cleaned_data.get("component_ids", "")
        if not value:
            raise ValidationError("No components selected.")
        ids = [id.strip() for id in value.split(",") if id.strip()]
        if not ids:
            raise ValidationError("No valid component IDs provided.")
        # Validate IDs exist
        from toolanalysis.models import Components
        found = Components.objects.filter(id__in=ids).count()
        if found != len(ids):
            raise ValidationError(f"Some component IDs were not found. Found {found} of {len(ids)}.")
        return ids


class BatchProductEditForm(forms.Form):
    """Form for batch editing multiple products."""
    
    product_ids = forms.CharField(widget=forms.HiddenInput(), required=True)
    
    brand = _NameChoice(
        queryset=Brands.objects.all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Brand",
        help_text="Leave blank to keep existing values",
    )
    listingtype = _ListingTypeChoice(
        queryset=ListingTypes.objects.select_related("retailer").all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Listing type",
        help_text="Leave blank to keep existing values",
    )
    motortype = _NameChoice(
        queryset=MotorTypes.objects.all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Motor type",
        help_text="Leave blank to keep existing values",
    )
    status = _NameChoice(
        queryset=Statuses.objects.all().order_by("sortorder", "name"),
        required=False,
        widget=forms.Select(attrs={"class": "pm-select"}),
        label="Status",
        help_text="Leave blank to keep existing values",
    )
    isaccessory = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "pm-checkbox"}),
        label="Accessory",
        help_text="Check to set all as accessories (leave unchecked to keep existing values)",
    )
    itemtypes = _SimpleMulti(
        queryset=ItemTypes.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Item types",
        help_text="Leave blank to keep existing values, or select to replace all",
    )
    categories = _SimpleMulti(
        queryset=Categories.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Categories",
        help_text="Leave blank to keep existing values, or select to replace all",
    )
    subcategories = _SimpleMulti(
        queryset=Subcategories.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Subcategories",
        help_text="Leave blank to keep existing values, or select to replace all",
    )
    batteryplatforms = _BatteryPlatformMulti(
        queryset=BatteryPlatforms.objects.select_related("brand").all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Battery platforms",
        help_text="Leave blank to keep existing values, or select to replace all",
    )
    batteryvoltages = _VoltageMulti(
        queryset=BatteryVoltages.objects.all().order_by("value"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Battery voltages",
        help_text="Leave blank to keep existing values, or select to replace all",
    )
    features = _SimpleMulti(
        queryset=Features.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "pm-multiselect"}),
        label="Features",
        help_text="Leave blank to keep existing values, or select to replace all",
    )
    image = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "pm-input"}),
        label="Image URL",
        help_text="Leave blank to keep existing values",
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "class": "pm-textarea"}),
        label="Description",
        help_text="Leave blank to keep existing values",
    )
    bullets = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "class": "pm-textarea"}),
        label="Bullets",
        help_text="Leave blank to keep existing values",
    )
    
    def clean_product_ids(self):
        value = self.cleaned_data.get("product_ids", "")
        if not value:
            raise ValidationError("No products selected.")
        ids = [id.strip() for id in value.split(",") if id.strip()]
        if not ids:
            raise ValidationError("No valid product IDs provided.")
        # Validate IDs exist
        from toolanalysis.models import Products
        found = Products.objects.filter(id__in=ids).count()
        if found != len(ids):
            raise ValidationError(f"Some product IDs were not found. Found {found} of {len(ids)}.")
        return ids


__all__ = [
    "ComponentQuickForm",
    "ProductQuickForm",
    "BareToolForm",
    "BundleProductForm",
    "BundleProductSelectorForm",
    "ComponentSelectorForm",
    "ProductSelectorForm",
    "BatchComponentEditForm",
    "BatchProductEditForm",
]

# Import manufacturer import forms (separate module)
try:
    from .manufacturer_import import ManufacturerImportForm, ImportPreviewForm
    __all__.extend(["ManufacturerImportForm", "ImportPreviewForm"])
except ImportError:
    pass

