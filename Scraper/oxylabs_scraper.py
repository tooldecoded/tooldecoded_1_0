import requests
from bs4 import BeautifulSoup
# Set your Oxylabs API Credentials.
username = "tooldecoded_c7GJz"
password = "5gM_3jpR=afdFAb"

# Structure payload.
payload = {
    'source': 'universal',
    'url': 'https://www.homedepot.com/p/Milwaukee-M18-FUEL-18V-Lithium-Ion-Brushless-Cordless-1-2-in-Hammer-Drill-Driver-Tool-Only-2904-20/320326855',
    'geo_location': 'United States',
}

# Get response.
response = requests.request(
    'POST',
    'https://realtime.oxylabs.io/v1/queries',
    auth=(username, password),
    json=payload,
)

# Debug information
print(f"Status Code: {response.status_code}")
print(f"Response Headers: {response.headers}")
print(f"Response Text: {response.text[:500]}...")  # First 500 chars

# Try to parse JSON only if response is successful
if response.status_code == 200:
    try:
        html_content = response.json()['results'][0]['content']
        soup = BeautifulSoup(html_content, 'html.parser')
        print(soup.prettify())
        script_tag = soup.find('script', {'data-th': 'server'})
        if script_tag:
            script_content = script_tag.string
            print(script_content)
        else:
            print("No script tag found")

        products = soup.find_all('div', {'data-testid': 'product-pod'})
        for product in products:
            print(product.prettify())
            
















    except requests.exceptions.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        print("Response is not valid JSON")
else:
    print(f"Request failed with status code: {response.status_code}")