from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Components, ComponentPricingHistory


class ComponentPricingHistoryInline(admin.TabularInline):
    model = ComponentPricingHistory
    extra = 0
    readonly_fields = ('calculation_date', 'source_type', 'price', 'source_product', 'source_pricelisting', 'metadata')
    fields = ('calculation_date', 'source_type', 'price', 'source_product', 'source_pricelisting')
    ordering = ('-calculation_date',)
    
    def has_add_permission(self, request, obj=None):
        return False  # Historical data should not be manually added


@admin.register(Components)
class ComponentsAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'sku', 'effective_price_display', 'price_source_display', 'is_featured', 'showcase_priority')
    list_filter = ('is_featured', 'brand', 'categories', 'use_manual_price')
    search_fields = ('name', 'sku', 'description')
    list_editable = ('is_featured', 'showcase_priority')
    ordering = ('-showcase_priority', 'name')
    inlines = [ComponentPricingHistoryInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'brand', 'sku', 'image')
        }),
        ('Showcase Settings', {
            'fields': ('is_featured', 'showcase_priority'),
            'description': 'Use showcase_priority to control order in browse page. Higher numbers appear first.'
        }),
        ('Categories & Classifications', {
            'fields': ('categories', 'subcategories', 'itemtypes', 'itemcategories')
        }),
        ('Technical Specifications', {
            'fields': ('batteryvoltages', 'batteryplatforms', 'productlines', 'listingtype')
        }),
        ('Pricing', {
            'fields': (
                'use_manual_price', 'manual_price', 'manual_override_note',
                'calculated_price', 'last_calculated_date', 'price_currency',
                'price_source_product', 'price_source_pricelisting', 'fair_price_narrative'
            ),
            'description': 'Manual pricing overrides calculated pricing. Use manual_override_note to explain why.'
        }),
    )
    
    readonly_fields = ('calculated_price', 'last_calculated_date', 'price_source_product', 'price_source_pricelisting')
    
    def effective_price_display(self, obj):
        """Display the effective price with indicator"""
        if obj.use_manual_price and obj.manual_price:
            return format_html(
                '<span style="color: #d63384; font-weight: bold;">${} (Manual)</span>',
                obj.manual_price
            )
        elif obj.calculated_price:
            return format_html(
                '<span style="color: #198754;">${} (Calculated)</span>',
                obj.calculated_price
            )
        else:
            return format_html('<span style="color: #6c7575;">No Price</span>')
    
    effective_price_display.short_description = 'Effective Price'
    effective_price_display.admin_order_field = 'calculated_price'
    
    def price_source_display(self, obj):
        """Display the source of the price"""
        if obj.use_manual_price:
            return "Manual Override"
        elif obj.price_source_product:
            return f"Product: {obj.price_source_product.name[:30]}..."
        else:
            return "Unknown"
    
    price_source_display.short_description = 'Price Source'
    
    def has_calculated_price(self, obj):
        """Filter for components with calculated prices"""
        return obj.calculated_price is not None
    has_calculated_price.boolean = True
    has_calculated_price.short_description = 'Has Calculated Price'


@admin.register(ComponentPricingHistory)
class ComponentPricingHistoryAdmin(admin.ModelAdmin):
    list_display = ('component_name', 'component_sku', 'price', 'source_type', 'source_product_name', 'calculation_date')
    list_filter = ('source_type', 'component__brand', 'calculation_date')
    search_fields = ('component__name', 'component__sku', 'source_product__name')
    readonly_fields = ('component', 'price', 'source_type', 'source_product', 'source_pricelisting', 'calculation_date', 'metadata')
    ordering = ('-calculation_date',)
    
    def component_name(self, obj):
        return obj.component.name
    component_name.short_description = 'Component Name'
    component_name.admin_order_field = 'component__name'
    
    def component_sku(self, obj):
        return obj.component.sku or '-'
    component_sku.short_description = 'Component SKU'
    component_sku.admin_order_field = 'component__sku'
    
    def source_product_name(self, obj):
        return obj.source_product.name if obj.source_product else '-'
    source_product_name.short_description = 'Source Product'
    source_product_name.admin_order_field = 'source_product__name'
    
    def has_add_permission(self, request):
        return False  # Historical data should not be manually added
    
    def has_change_permission(self, request, obj=None):
        return False  # Historical data should not be modified
    
    def has_delete_permission(self, request, obj=None):
        return False  # Historical data should not be deleted
