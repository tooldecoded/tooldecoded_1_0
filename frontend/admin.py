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
            'fields': ('title', 'slug', 'summary')
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
    
    actions = ['reset_order_by_published_date', 'set_custom_order_sequence', 'pin_articles', 'unpin_articles']
    
    def reset_order_by_published_date(self, request, queryset):
        """Reset articles to be ordered by published date"""
        # Get all articles ordered by published_at desc, then assign custom_order
        articles = queryset.order_by('-published_at', '-created_at')
        for index, article in enumerate(articles, start=1):
            article.custom_order = index
            article.save(update_fields=['custom_order'])
        
        self.message_user(request, f"Reset order for {queryset.count()} articles based on published date.")
    
    reset_order_by_published_date.short_description = "Reset order by published date"
    
    def set_custom_order_sequence(self, request, queryset):
        """Set custom order sequence for selected articles"""
        articles = list(queryset.order_by('custom_order', '-published_at', '-created_at'))
        for index, article in enumerate(articles, start=1):
            article.custom_order = index
            article.save(update_fields=['custom_order'])
        
        self.message_user(request, f"Set custom order sequence for {queryset.count()} articles.")
    
    set_custom_order_sequence.short_description = "Set custom order sequence"
    
    def pin_articles(self, request, queryset):
        """Pin selected articles"""
        updated = queryset.update(is_pinned=True)
        self.message_user(request, f"Pinned {updated} articles.")
    
    pin_articles.short_description = "Pin selected articles"
    
    def unpin_articles(self, request, queryset):
        """Unpin selected articles"""
        updated = queryset.update(is_pinned=False)
        self.message_user(request, f"Unpinned {updated} articles.")
    
    unpin_articles.short_description = "Unpin selected articles"

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
