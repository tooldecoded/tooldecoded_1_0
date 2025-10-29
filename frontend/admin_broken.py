from django.contrib import admin
from django.db.models import F
from django.http import JsonResponse
from django.urls import path
from django.shortcuts import render
import requests
from bs4 import BeautifulSoup
import json
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

class ScrapeTestAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('test-scrape/', self.admin_site.admin_view(self.test_scrape_view), name='test_scrape'),
        ]
        return custom_urls + urls

    def test_scrape_view(self, request):
        if request.method == 'POST':
            search_term = request.POST.get('search_term', '2903-20')
            
            url = f"https://www.homedepot.com/s/{search_term}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            try:
                response = requests.get(url, headers=headers, timeout=10)
                result = {
                    'status_code': response.status_code,
                    'response_length': len(response.content),
                    'success': response.status_code == 200
                }
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Check for structured data
                    script_tag = soup.find('script', {'id': 'thd-helmet__script--browseSearchStructuredData'})
                    if script_tag:
                        result['structured_data'] = True
                        try:
                            data = json.loads(script_tag.string)
                            products = data[0].get('mainEntity', {}).get('offers', {}).get('itemOffered', [])
                            result['products_found'] = len(products)
                            result['sample_products'] = products[:3]
                        except:
                            result['structured_data'] = False
                    else:
                        result['structured_data'] = False
                    
                    # Check for product elements
                    product_elements = soup.find_all('div', {'data-testid': 'product-tile'})
                    result['product_elements'] = len(product_elements)
                else:
                    result['error'] = response.text[:500]
                
                return JsonResponse(result)
                
            except Exception as e:
                return JsonResponse({'error': str(e), 'success': False})
        
        return render(request, 'admin/test_scrape.html')

# Add test scrape to admin URLs
from django.urls import path, include
from django.conf.urls import url

# Add the test scrape view to admin URLs
admin.site.get_urls = lambda: admin.site.get_urls() + [
    path('test-scrape/', admin.site.admin_view(test_scrape_view), name='test_scrape'),
]

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

class ScrapeTestAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('test-scrape/', self.admin_site.admin_view(self.test_scrape_view), name='test_scrape'),
        ]
        return custom_urls + urls

    def test_scrape_view(self, request):
        if request.method == 'POST':
            search_term = request.POST.get('search_term', '2903-20')
            
            url = f"https://www.homedepot.com/s/{search_term}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            try:
                response = requests.get(url, headers=headers, timeout=10)
                result = {
                    'status_code': response.status_code,
                    'response_length': len(response.content),
                    'success': response.status_code == 200
                }
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Check for structured data
                    script_tag = soup.find('script', {'id': 'thd-helmet__script--browseSearchStructuredData'})
                    if script_tag:
                        result['structured_data'] = True
                        try:
                            data = json.loads(script_tag.string)
                            products = data[0].get('mainEntity', {}).get('offers', {}).get('itemOffered', [])
                            result['products_found'] = len(products)
                            result['sample_products'] = products[:3]
                        except:
                            result['structured_data'] = False
                    else:
                        result['structured_data'] = False
                    
                    # Check for product elements
                    product_elements = soup.find_all('div', {'data-testid': 'product-tile'})
                    result['product_elements'] = len(product_elements)
                else:
                    result['error'] = response.text[:500]
                
                return JsonResponse(result)
                
            except Exception as e:
                return JsonResponse({'error': str(e), 'success': False})
        
        return render(request, 'admin/test_scrape.html')

