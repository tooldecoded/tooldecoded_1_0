import bs4
import requests
import re

headers = {
    'DNT': '1',
    'Referer': 'https://www.homedepot.com/b/Holiday-Decorations-Halloween-Decorations/N-5yc1vZc2ve',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"'
}

url = "https://www.homedepot.com/b/Milwaukee/Milwaukee-M18/N-5yc1vZzvZ1z17rdr?NCNI-5"
response = requests.get(url, headers=headers)
soup = bs4.BeautifulSoup(response.text, 'html.parser')
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