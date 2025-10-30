from django import forms
from django.forms import ModelChoiceField, ModelMultipleChoiceField

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
    Subcategories,
)


class ComponentForm(forms.ModelForm):
    # Custom choice fields to render human-friendly labels instead of "Model object (id)"
    class _NameChoice(ModelChoiceField):
        def label_from_instance(self, obj):
            return getattr(obj, "name", str(obj))

    class _NameMultiChoice(ModelMultipleChoiceField):
        def label_from_instance(self, obj):
            return getattr(obj, "name", str(obj))

    class _FullnameOrNameMulti(ModelMultipleChoiceField):
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

    brand = _NameChoice(
        queryset=Brands.objects.all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "bo-select"}),
        label="Brand",
    )
    listingtype = _ListingTypeChoice(
        queryset=ListingTypes.objects.select_related("retailer").all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "bo-select"}),
        label="Listingtype",
    )
    motortype = _NameChoice(
        queryset=MotorTypes.objects.all().order_by("name"),
        required=False,
        widget=forms.Select(attrs={"class": "bo-select"}),
        label="Motortype",
    )

    itemtypes = _FullnameOrNameMulti(
        queryset=ItemTypes.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "bo-multiselect"}),
        label="Itemtypes",
    )
    subcategories = _FullnameOrNameMulti(
        queryset=Subcategories.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "bo-multiselect"}),
        label="Subcategories",
    )
    categories = _FullnameOrNameMulti(
        queryset=Categories.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "bo-multiselect"}),
        label="Categories",
    )
    batteryplatforms = _BatteryPlatformMulti(
        queryset=BatteryPlatforms.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "bo-multiselect"}),
        label="Batteryplatforms",
    )
    batteryvoltages = _VoltageMulti(
        queryset=BatteryVoltages.objects.all().order_by("value"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "bo-multiselect"}),
        label="Batteryvoltages",
    )
    productlines = _ProductLineMulti(
        queryset=ProductLines.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "bo-multiselect"}),
        label="Productlines",
    )
    features = _NameMultiChoice(
        queryset=Features.objects.all().order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 6, "class": "bo-multiselect"}),
        label="Features",
    )
    class Meta:
        model = Components
        exclude = ("id",)
        widgets = {
            "name": forms.TextInput(attrs={"class": "bo-input"}),
            "sku": forms.TextInput(attrs={"class": "bo-input"}),
            "description": forms.Textarea(attrs={"rows": 4, "class": "bo-textarea"}),
            "image": forms.TextInput(attrs={"class": "bo-input"}),
            "is_featured": forms.CheckboxInput(attrs={"class": "bo-checkbox"}),
            "standalone_price": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "class": "bo-input"}
            ),
            "showcase_priority": forms.NumberInput(
                attrs={"step": "1", "min": "0", "class": "bo-input"}
            ),
            # FKs and M2Ms will use default selects; can be enhanced later
        }


