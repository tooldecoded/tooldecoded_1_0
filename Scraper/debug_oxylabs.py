import requests
import json
from bs4 import BeautifulSoup

# Set your Oxylabs API Credentials
username = "tooldecoded_c7GJz"
password = "5gM_3jpR=afdFAb"

# Structure payload
payload = {
    'source': 'universal',
    'url': 'https://www.homedepot.com/b/Tools-Power-Tools-Drills-Hammer-Drills/Milwaukee/Milwaukee-M18/N-5yc1vZc8wtZzvZ1z17rdr',
}

# Get response
response = requests.request(
    'POST',
    'https://realtime.oxylabs.io/v1/queries',
    auth=(username, password),
    json=payload,
)

if response.status_code == 200:
    data = response.json()
    html_content = data['results'][0]['content']
    
    # Save HTML for inspection
    with open('homedepot_debug.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("HTML saved to homedepot_debug.html")
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for various product container patterns
    print("\n=== DEBUGGING PRODUCT CONTAINERS ===")
    
    # Check for product-pod
    product_pods = soup.find_all('div', {'data-testid': 'product-pod'})
    print(f"Found {len(product_pods)} product-pod elements")
    
    # Check for other common patterns
    product_divs = soup.find_all('div', class_=lambda x: x and 'product' in x.lower())
    print(f"Found {len(product_divs)} divs with 'product' in class")
    
    # Check for data-testid patterns
    testid_elements = soup.find_all(attrs={'data-testid': True})
    testid_values = [elem.get('data-testid') for elem in testid_elements]
    unique_testids = list(set(testid_values))
    print(f"Found {len(unique_testids)} unique data-testid values:")
    for tid in sorted(unique_testids)[:20]:  # Show first 20
        print(f"  - {tid}")
    
    # Look for any divs with product-related attributes
    product_attrs = soup.find_all('div', attrs={'data-product-id': True})
    print(f"Found {len(product_attrs)} divs with data-product-id")
    
    # Check for structured data
    script_tags = soup.find_all('script', type='application/ld+json')
    print(f"Found {len(script_tags)} JSON-LD script tags")
    
    # Look for any script tags with structured data
    structured_scripts = soup.find_all('script', string=lambda text: text and 'product' in text.lower())
    print(f"Found {len(structured_scripts)} script tags containing 'product'")
    
    # Check for specific Home Depot patterns
    hd_patterns = [
        'div[class*="product"]',
        'div[class*="item"]',
        'div[class*="tile"]',
        'article[class*="product"]',
        'div[data-testid*="product"]',
        'div[data-testid*="item"]'
    ]
    
    print("\n=== CHECKING SPECIFIC PATTERNS ===")
    for pattern in hd_patterns:
        elements = soup.select(pattern)
        print(f"Pattern '{pattern}': {len(elements)} elements")
        if elements:
            print(f"  First element classes: {elements[0].get('class', 'No classes')}")
            print(f"  First element data-testid: {elements[0].get('data-testid', 'No data-testid')}")
    
    # Look for any elements that might contain product info
    print("\n=== LOOKING FOR PRODUCT INFO PATTERNS ===")
    
    # Check for price patterns
    price_elements = soup.find_all(string=lambda text: text and '$' in text)
    print(f"Found {len(price_elements)} elements containing '$'")
    
    # Check for brand patterns
    brand_elements = soup.find_all(string=lambda text: text and 'Milwaukee' in text)
    print(f"Found {len(brand_elements)} elements containing 'Milwaukee'")
    
    # Check for model patterns
    model_elements = soup.find_all(string=lambda text: text and 'Model#' in text)
    print(f"Found {len(model_elements)} elements containing 'Model#'")
    
    print("\n=== SAMPLE HTML CONTENT ===")
    print("First 2000 characters of HTML:")
    print(html_content[:2000])
    
else:
    print(f"Request failed with status code: {response.status_code}")
    print(response.text)
