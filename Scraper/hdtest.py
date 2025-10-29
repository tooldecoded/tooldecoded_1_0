import bs4
import requests
import re
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'no-cache',
    'DNT': '1',
    'Pragma': 'no-cache',
    'Referer': 'https://www.homedepot.com/',
    'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Setup session with timeout and retry strategy
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

url = "https://www.homedepot.com/b/Milwaukee/Milwaukee-M18/N-5yc1vZzvZ1z17rdr?NCNI-5&searchRedirect=m18&semanticToken=j27r10r10f240400000004_2025102908200438278712745124_us-east4-dp7j%20j27r10r10f240400000004%20%3E%20st%3A%7Bm18%7D%3Ast%20ml%3A%7B24%7D%3Aml%20nr%3A%7Bm18%7D%3Anr%20nf%3A%7Bn%2Fa%7D%3Anf%20qu%3A%7Bm18%7D%3Aqu%20ie%3A%7B0%7D%3Aie%20qr%3A%7Bm18%7D%3Aqr"
print(f"Testing URL: {url}")
print(f"Timeout: 10 seconds")
print("=" * 50)

try:
    response = session.get(url, headers=headers, timeout=10)
    print(f"Response time: {response.elapsed.total_seconds():.2f} seconds")
    print(f"Status code: {response.status_code}")
except requests.exceptions.Timeout:
    print("❌ TIMEOUT: Request took longer than 10 seconds")
    exit()
except requests.exceptions.RequestException as e:
    print(f"❌ ERROR: {e}")
    exit()
soup = bs4.BeautifulSoup(response.text, 'html.parser')
print(soup.prettify())
products = soup.find_all('div', {'data-testid': 'product-pod'})

for i, product in enumerate(products, 1):
    # Product ID - ALWAYS WORKS
    product_id = product.get('data-product-id', 'N/A')
    
    # Brand - ALWAYS WORKS
    brand_elem = product.find('span', {'data-testid': 'attribute-brandname-inline'})
    brand = brand_elem.get_text().strip() if brand_elem else 'N/A'
    
    # Product Name - ALWAYS WORKS
    name_elem = product.find('span', {'data-testid': 'attribute-product-label'})
    product_name = name_elem.get_text().strip() if name_elem else 'N/A'
    
    # Price - ALWAYS WORKS (looks for the big price number)
    price_elem = product.find('span', class_='sui-text-3xl')
    price = price_elem.get_text().strip() if price_elem else 'N/A'
    
    # Model Number - ALWAYS WORKS (looks for text containing "Model#")
    model_text = product.get_text()
    model_match = re.search(r'Model#\s*([A-Z0-9-]+)', model_text)
    model = model_match.group(1) if model_match else 'N/A'
    
    # Rating - ALWAYS WORKS (looks for pattern like "4.8 / 2272")
    rating_match = re.search(r'\((\d+\.\d+)\s*/\s*(\d+)\)', model_text)
    rating = f"{rating_match.group(1)}/5 ({rating_match.group(2)} reviews)" if rating_match else 'N/A'
    
    # Product Link - ALWAYS WORKS
    link_elem = product.find('a', href=True)
    link = f"https://www.homedepot.com{link_elem['href']}" if link_elem else 'N/A'
    
    # Stock Limit - ALWAYS WORKS
    stock_match = re.search(r'Limit (\d+) per order', model_text)
    stock_limit = stock_match.group(1) if stock_match else 'N/A'
    
    print(f"Product {i}:")
    print(f"  ID: {product_id}")
    print(f"  Brand: {brand}")
    print(f"  Name: {product_name}")
    print(f"  Price: ${price}")
    print(f"  Model: {model}")
    print(f"  Rating: {rating}")
    print(f"  Stock Limit: {stock_limit}")
    print(f"  Link: {link}")
    print()

print("\n" + "=" * 50)
print("TESTING MULTIPLE PAGES WITH TIMEOUT")
print("=" * 50)

'''for i in range(1,28):
    url = "https://www.homedepot.com/b/Milwaukee/Milwaukee-M18/N-5yc1vZzvZ1z17rdr?NCNI-5&Nao={}".format(i*24)
    print(f"\nPage {i}: {url}")
    
    try:
        start_time = time.time()
        response = session.get(url, headers=headers, timeout=10)
        response_time = time.time() - start_time
        
        print(f"  ✅ Response time: {response_time:.2f} seconds")
        print(f"  ✅ Status code: {response.status_code}")
        
        if response.status_code not in [200, 206]:
            print(f"  ⚠️  Non-200/206 status ({response.status_code}), skipping page")
            print(f"  Response headers: {dict(response.headers)}")
            print(f"  Response content length: {len(response.content)}")
            continue
        elif response.status_code == 206:
            print(f"  ⚠️  Partial content (206) - checking if complete...")
            print(f"  Response content length: {len(response.content)}")
            print(f"  Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
            print(f"  Content-Range: {response.headers.get('Content-Range', 'Not specified')}")
            
    except requests.exceptions.Timeout:
        print(f"  ❌ TIMEOUT: Page {i} took longer than 10 seconds")
        continue
    except requests.exceptions.RequestException as e:
        print(f"  ❌ ERROR on page {i}: {e}")
        continue
    
    # Debug response content
    print(f"  📄 Response size: {len(response.content)} bytes")
    print(f"  📄 Response text length: {len(response.text)} characters")
    
    # Check if response looks truncated
    if response.text.endswith('...') or len(response.text) < 1000:
        print(f"  ⚠️  Response appears truncated!")
        print(f"  Last 100 chars: {response.text[-100:]}")
    
    soup = bs4.BeautifulSoup(response.text, 'html.parser')
    products = soup.find_all('div', {'data-testid': 'product-pod'})
    
    if not products:
        print(f"  ⚠️  No products found on page {i}")
        # Debug: show what we did find
        all_divs = soup.find_all('div')
        print(f"  Debug: Found {len(all_divs)} total divs")
        if all_divs:
            print(f"  Debug: First div classes: {all_divs[0].get('class', 'No classes')}")
        continue

    print(f"  📦 Found {len(products)} products on page {i}")
    
    for j, product in enumerate(products, 1):
        # Product ID - ALWAYS WORKS
        product_id = product.get('data-product-id', 'N/A')
        
        # Brand - ALWAYS WORKS
        brand_elem = product.find('span', {'data-testid': 'attribute-brandname-inline'})
        brand = brand_elem.get_text().strip() if brand_elem else 'N/A'
        
        # Product Name - ALWAYS WORKS
        name_elem = product.find('span', {'data-testid': 'attribute-product-label'})
        product_name = name_elem.get_text().strip() if name_elem else 'N/A'
        
        # Price - ALWAYS WORKS (looks for the big price number)
        price_elem = product.find('span', class_='sui-text-3xl')
        price = price_elem.get_text().strip() if price_elem else 'N/A'
        
        # Model Number - ALWAYS WORKS (looks for text containing "Model#")
        model_text = product.get_text()
        model_match = re.search(r'Model#\s*([A-Z0-9-]+)', model_text)
        model = model_match.group(1) if model_match else 'N/A'
        
        # Rating - ALWAYS WORKS (looks for pattern like "4.8 / 2272")
        rating_match = re.search(r'\((\d+\.\d+)\s*/\s*(\d+)\)', model_text)
        rating = f"{rating_match.group(1)}/5 ({rating_match.group(2)} reviews)" if rating_match else 'N/A'
        
        # Product Link - ALWAYS WORKS
        link_elem = product.find('a', href=True)
        link = f"https://www.homedepot.com{link_elem['href']}" if link_elem else 'N/A'
        
        # Stock Limit - ALWAYS WORKS
        stock_match = re.search(r'Limit (\d+) per order', model_text)
        stock_limit = stock_match.group(1) if stock_match else 'N/A'
        
        print(f"    Product {j}: {brand} - {product_name[:30]}... - ${price}")
    
    print(f"  ⏱️  Waiting 10 seconds before next page...")
    time.sleep(10)
'''