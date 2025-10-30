import requests
import json
import csv
import time
import re
from datetime import datetime
from pprint import pprint
from bs4 import BeautifulSoup
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OxylabsBlockingSolution:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.base_url = "https://realtime.oxylabs.io/v1/queries"
        self.session = requests.Session()
        
    def test_oxylabs_access(self, url):
        """Test if Oxylabs can access the URL and diagnose issues"""
        payload = {
            'source': 'universal',
            'url': url,
        }
        
        try:
            response = self.session.request(
                'POST',
                self.base_url,
                auth=(self.username, self.password),
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data['results'][0]
                
                status_code = result.get('status_code', 'Unknown')
                content_length = len(result.get('content', ''))
                
                logger.info(f"Oxylabs Response Analysis:")
                logger.info(f"  Status Code: {status_code}")
                logger.info(f"  Content Length: {content_length}")
                logger.info(f"  Type: {result.get('type', 'Unknown')}")
                
                # Interpret status codes
                status_interpretations = {
                    200: "Success - Content retrieved",
                    403: "Forbidden - Access denied by website",
                    404: "Not Found - URL doesn't exist",
                    429: "Rate Limited - Too many requests",
                    500: "Server Error - Website server issue",
                    613: "Blocked by Website - Anti-bot protection",
                    614: "Blocked by Website - CAPTCHA required",
                    615: "Blocked by Website - JavaScript challenge",
                    616: "Blocked by Website - Cloudflare protection"
                }
                
                interpretation = status_interpretations.get(status_code, f"Unknown status code: {status_code}")
                logger.info(f"  Interpretation: {interpretation}")
                
                if status_code == 613:
                    logger.warning("🚫 Home Depot is blocking Oxylabs with anti-bot protection")
                    logger.warning("This is common with major e-commerce sites")
                    return False, "blocked"
                elif status_code == 200 and content_length > 0:
                    logger.info("✅ Oxylabs can access the content successfully")
                    return True, "success"
                else:
                    logger.warning(f"⚠️ Oxylabs returned status {status_code} with {content_length} bytes of content")
                    return False, f"status_{status_code}"
                    
            else:
                logger.error(f"Oxylabs API error: {response.status_code}")
                return False, f"api_error_{response.status_code}"
                
        except Exception as e:
            logger.error(f"Error testing Oxylabs access: {e}")
            return False, "error"
    
    def try_oxylabs_alternatives(self, url):
        """Try different Oxylabs configurations to bypass blocking"""
        alternatives = [
            {
                'name': 'Standard Universal',
                'payload': {
                    'source': 'universal',
                    'url': url,
                }
            },
            {
                'name': 'Universal with Custom Headers',
                'payload': {
                    'source': 'universal',
                    'url': url,
                    'headers': [
                        {'name': 'User-Agent', 'value': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'},
                        {'name': 'Accept', 'value': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'},
                        {'name': 'Accept-Language', 'value': 'en-US,en;q=0.5'},
                        {'name': 'Accept-Encoding', 'value': 'gzip, deflate, br'},
                        {'name': 'DNT', 'value': '1'},
                        {'name': 'Connection', 'value': 'keep-alive'},
                        {'name': 'Upgrade-Insecure-Requests', 'value': '1'},
                    ]
                }
            },
            {
                'name': 'Universal with Render',
                'payload': {
                    'source': 'universal',
                    'url': url,
                    'render': 'html'
                }
            },
            {
                'name': 'Universal with Custom User Agent',
                'payload': {
                    'source': 'universal',
                    'url': url,
                    'user_agent_type': 'desktop'
                }
            }
        ]
        
        for alt in alternatives:
            logger.info(f"Trying alternative: {alt['name']}")
            
            try:
                response = self.session.request(
                    'POST',
                    self.base_url,
                    auth=(self.username, self.password),
                    json=alt['payload'],
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    result = data['results'][0]
                    status_code = result.get('status_code', 'Unknown')
                    content_length = len(result.get('content', ''))
                    
                    logger.info(f"  Status: {status_code}, Content: {content_length} bytes")
                    
                    if status_code == 200 and content_length > 0:
                        logger.info(f"✅ Success with {alt['name']}!")
                        return True, data
                    elif status_code == 613:
                        logger.warning(f"❌ Still blocked with {alt['name']}")
                    else:
                        logger.info(f"⚠️ Different issue with {alt['name']}: {status_code}")
                else:
                    logger.warning(f"API error with {alt['name']}: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Error with {alt['name']}: {e}")
            
            time.sleep(2)  # Wait between attempts
        
        return False, None
    
    def recommend_solutions(self, url, blocking_reason):
        """Recommend solutions based on the blocking reason"""
        logger.info("\n" + "="*60)
        logger.info("RECOMMENDED SOLUTIONS")
        logger.info("="*60)
        
        if blocking_reason == "blocked":
            logger.info("🚫 Home Depot is blocking Oxylabs with anti-bot protection")
            logger.info("\n📋 RECOMMENDED SOLUTIONS:")
            logger.info("\n1. 🔄 USE YOUR EXISTING DIRECT SCRAPER")
            logger.info("   - Your homedepotscraper.py already works!")
            logger.info("   - It uses direct HTTP requests with proper headers")
            logger.info("   - It has proven selectors and extraction methods")
            logger.info("   - Command: python Scraper/homedepotscraper.py")
            
            logger.info("\n2. 🌐 TRY DIFFERENT OXYLABS SOURCES")
            logger.info("   - Use 'google' source instead of 'universal'")
            logger.info("   - Use 'bing' source for different IP ranges")
            logger.info("   - Use residential proxies if available")
            
            logger.info("\n3. ⏰ TIMING STRATEGY")
            logger.info("   - Try scraping during off-peak hours")
            logger.info("   - Use longer delays between requests")
            logger.info("   - Rotate between different URLs")
            
            logger.info("\n4. 🔧 OXYLABS CONFIGURATION")
            logger.info("   - Enable JavaScript rendering")
            logger.info("   - Use different user agents")
            logger.info("   - Try different geographic locations")
            
            logger.info("\n5. 🛠️ HYBRID APPROACH")
            logger.info("   - Use Oxylabs for simple pages")
            logger.info("   - Use direct scraping for complex pages")
            logger.info("   - Combine both methods for best results")
            
        elif "status_" in blocking_reason:
            logger.info(f"⚠️ Different issue: {blocking_reason}")
            logger.info("Try the solutions above or contact Oxylabs support")
        
        logger.info("\n" + "="*60)
    
    def test_alternative_urls(self, base_url):
        """Test if simpler URLs work with Oxylabs"""
        test_urls = [
            "https://www.homedepot.com/",
            "https://www.homedepot.com/b/Tools-Power-Tools/N-5yc1vZc8wt",
            "https://www.homedepot.com/b/Milwaukee/N-5yc1vZzvZ1z17rdr",
            "https://httpbin.org/get",  # Simple test URL
        ]
        
        logger.info("Testing alternative URLs with Oxylabs...")
        
        for url in test_urls:
            logger.info(f"\nTesting: {url}")
            success, reason = self.test_oxylabs_access(url)
            
            if success:
                logger.info(f"✅ {url} works with Oxylabs!")
                return url
            else:
                logger.info(f"❌ {url} failed: {reason}")
        
        return None

def main():
    # Set your Oxylabs API Credentials
    username = "tooldecoded_c7GJz"
    password = "5gM_3jpR=afdFAb"
    
    # Initialize solution
    solution = OxylabsBlockingSolution(username, password)
    
    # Test URL
    test_url = 'https://www.homedepot.com/b/Tools-Power-Tools-Drills-Hammer-Drills/Milwaukee/Milwaukee-M18/N-5yc1vZc8wtZzvZ1z17rdr'
    
    print("=== Oxylabs Blocking Analysis ===")
    print(f"Testing URL: {test_url}")
    print()
    
    # Test access
    success, reason = solution.test_oxylabs_access(test_url)
    
    if not success:
        # Try alternatives
        print("\n=== Trying Alternative Configurations ===")
        alt_success, alt_data = solution.try_oxylabs_alternatives(test_url)
        
        if not alt_success:
            # Test simpler URLs
            print("\n=== Testing Simpler URLs ===")
            working_url = solution.test_alternative_urls(test_url)
            
            if working_url:
                print(f"\n✅ Found working URL: {working_url}")
            else:
                print("\n❌ No URLs work with current Oxylabs configuration")
        
        # Provide recommendations
        solution.recommend_solutions(test_url, reason)
    
    else:
        print("✅ Oxylabs is working! You can proceed with scraping.")

if __name__ == "__main__":
    main()
