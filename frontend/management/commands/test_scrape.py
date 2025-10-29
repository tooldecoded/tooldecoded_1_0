import os
import django
import sys
from django.core.management.base import BaseCommand
from django.http import JsonResponse
import requests
from bs4 import BeautifulSoup
import json

class Command(BaseCommand):
    help = 'Test a single Home Depot scrape'

    def add_arguments(self, parser):
        parser.add_argument('--search', type=str, default='2903-20', help='Search term to test')
        parser.add_argument('--url', type=str, help='Custom URL to test')

    def handle(self, *args, **options):
        search_term = options['search']
        custom_url = options.get('url')
        
        self.stdout.write(f"Testing scrape for: {search_term}")
        
        if custom_url:
            url = custom_url
        else:
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
            self.stdout.write(f"Status Code: {response.status_code}")
            self.stdout.write(f"Response Length: {len(response.content)}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for structured data
                script_tag = soup.find('script', {'id': 'thd-helmet__script--browseSearchStructuredData'})
                if script_tag:
                    self.stdout.write("✅ Found structured data!")
                    try:
                        data = json.loads(script_tag.string)
                        products = data[0].get('mainEntity', {}).get('offers', {}).get('itemOffered', [])
                        self.stdout.write(f"Found {len(products)} products in structured data")
                        
                        for i, product in enumerate(products[:3], 1):
                            name = product.get('name', 'N/A')
                            price = product.get('offers', {}).get('price', 'N/A')
                            self.stdout.write(f"{i}. {name} - ${price}")
                    except Exception as e:
                        self.stdout.write(f"Error parsing structured data: {e}")
                else:
                    self.stdout.write("❌ No structured data found")
                
                # Look for product elements
                product_elements = soup.find_all('div', {'data-testid': 'product-tile'})
                self.stdout.write(f"Found {len(product_elements)} product elements")
                
            else:
                self.stdout.write(f"❌ Bad status: {response.status_code}")
                self.stdout.write(f"Response: {response.text[:500]}")
                
        except Exception as e:
            self.stdout.write(f"❌ Error: {e}")
