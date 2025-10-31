from django.contrib import admin
from django.db.models import F
from .models import LearningArticle, Tag, SiteSettings

# Register your models here.

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'color', 'is_predefined', 'article_count', 'created_at']
    list_filter = ['is_predefined', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at']
    list_editable = ['color', 'is_predefined']
    list_display_links = ['name']
    
    def article_count(self, obj):
        return obj.articles.count()
    article_count.short_description = 'Articles'

@admin.register(LearningArticle)
class LearningArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'is_published', 'is_pinned', 'published_at', 'custom_order', 'tag_list', 'created_at', 'updated_at']
    list_filter = ['is_published', 'is_pinned', 'tags', 'created_at', 'updated_at']
    search_fields = ['title', 'summary', 'content']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['custom_order', 'is_pinned']
    list_display_links = ['title']
    filter_horizontal = ['tags']
    
    def tag_list(self, obj):
        return ", ".join([tag.name for tag in obj.tags.all()])
    tag_list.short_description = 'Tags'
    
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'summary', 'image')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Tags', {
            'fields': ('tags',)
        }),
        ('Publication', {
            'fields': ('is_published', 'is_pinned', 'published_at')
        }),
        ('Ordering', {
            'fields': ('custom_order',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['show_fair_price_status', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']
    
    def show_fair_price_status(self, obj):
        return "Enabled" if obj.show_fair_price_feature else "Disabled"
    show_fair_price_status.short_description = "Fair Price Feature"
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of the settings instance
        return False
    
    fieldsets = (
        ('Site Configuration', {
            'fields': ('show_fair_price_feature',),
            'description': 'Control site-wide features and settings'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )