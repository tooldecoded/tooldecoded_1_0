import requests
import json
import time

KEYWORD = "hammer drill"
NUM_PAGES = 2
PAGE_SIZE = 24
DELAY = 1  # seconds
COOKIE = ""  # ← Paste your cookie here if needed
OUTPUT_FILE = f"{KEYWORD}_products.json"

headers = {
    "Host": "apionline.homedepot.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.homedepot.com/",
    "Content-Type": "application/json",
    "Origin": "https://www.homedepot.com",
    "Upgrade-Insecure-Requests": "1",
    "Connection": "keep-alive",
    "x-experience-name": "general-merchandise",
    "x-hd-dc": "origin",
    "x-debug": "false"
}

if COOKIE:
    headers["Cookie"] = COOKIE

graphql_query = """
query searchModel(
  $storeId: String,
  $startIndex: Int,
  $pageSize: Int,
  $orderBy: ProductSort,
  $filter: ProductFilter,
  $isBrandPricingPolicyCompliant: Boolean,
  $keyword: String,
  $navParam: String,
  $storefilter: StoreFilter = ALL,
  $channel: Channel = DESKTOP,
  $additionalSearchParams: AdditionalParams
) {
  searchModel(
    keyword: $keyword,
    navParam: $navParam,
    storefilter: $storefilter,
    isBrandPricingPolicyCompliant: $isBrandPricingPolicyCompliant,
    storeId: $storeId,
    channel: $channel,
    additionalSearchParams: $additionalSearchParams
  ) {
    products(startIndex: $startIndex, pageSize: $pageSize, orderBy: $orderBy, filter: $filter) {
      itemId
      identifiers {
        brandName
        modelNumber
        canonicalUrl
        productLabel
      }
      pricing(storeId: $storeId, isBrandPricingPolicyCompliant: $isBrandPricingPolicyCompliant) {
        value
        original
      }
      reviews {
        ratingsReviews {
          averageRating
          totalReviews
        }
      }
      media {
        images {
          url
        }
      }
    }
  }
}
"""
def fetch_page(keyword, start=0, page_size=24):
    url = "https://apionline.homedepot.com/federation-gateway/graphql?opname=searchModel"
    payload = {
        "operationName": "searchModel",
        "variables": {
            "skipInstallServices": False,
            "skipFavoriteCount": False,
            "storefilter": "ALL",
            "channel": "DESKTOP",
            "skipDiscoveryZones": False,
            "skipBuyitagain": True,
            "additionalSearchParams": {
                "deliveryZip": "96913",
                "multiStoreIds": []
            },
            "filter": {},
            "isBrandPricingPolicyCompliant": False,
            "keyword": keyword,
            "navParam": None,
            "orderBy": {
                "field": "BEST_MATCH",
                "order": "ASC"
            },
            "pageSize": page_size,
            "startIndex": start,
            "storeId": "1710"
        },
        "query": graphql_query
    }

    response = requests.post(url, headers=headers, json=payload)
    print(response.text)

    if response.status_code != 200:
        print(f"[HTTP {response.status_code}] Blocked or failed.")
        try:
            print("Server response:", response.json())
        except:
            print(response.text)
        raise Exception(f"Request failed with status: {response.status_code}")

    return response.json()

def collect_products(keyword, pages=5, page_size=24, delay=1):
    all_products = []

    for i in range(0, pages * page_size, page_size):
        page_num = i // page_size + 1
        print(f"Scraping page: {page_num}")
        try:
            data = fetch_page(keyword, start=i, page_size=page_size)

            if "data" not in data or "searchModel" not in data["data"]:
                print("Unexpected response structure")
                print(json.dumps(data, indent=2)[:1000])
                raise Exception("'data.searchModel' not found")

            products = data["data"]["searchModel"]["products"]
            all_products.extend(products)
            time.sleep(delay)

        except Exception as e:
            print(f"Failed page {page_num}: {e}")

if __name__ == "__main__":
    print(f"Starting to scrape '{KEYWORD}' for {NUM_PAGES} pages...")
    try:
        products = collect_products(KEYWORD, pages=NUM_PAGES, page_size=PAGE_SIZE, delay=DELAY)
        print(f"Found {len(products)} total products")
        
        # Save to file
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(products, f, indent=2)
        print(f"Saved to {OUTPUT_FILE}")
        
        # Show first few products
        for i, product in enumerate(products[:3]):
            print(f"\nProduct {i+1}:")
            if 'identifiers' in product:
                print(f"  Name: {product['identifiers'].get('productLabel', 'N/A')}")
                print(f"  Brand: {product['identifiers'].get('brandName', 'N/A')}")
                print(f"  Model: {product['identifiers'].get('modelNumber', 'N/A')}")
            if 'pricing' in product:
                print(f"  Price: ${product['pricing'].get('value', 'N/A')}")
                
    except Exception as e:
        print(f"Error: {e}")