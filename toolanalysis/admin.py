from django.contrib import admin
from .models import Components

@admin.register(Components)
class ComponentsAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'sku', 'is_featured', 'showcase_priority')
    list_filter = ('is_featured', 'brand', 'categories')
    search_fields = ('name', 'sku', 'description')
    list_editable = ('is_featured', 'showcase_priority')
    ordering = ('-showcase_priority', 'name')
    
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
            'fields': ('fair_price_narrative',)
        }),
    )
