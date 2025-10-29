import beautifulsoup4 as bs4
import requests

data-testid="product-pod"

url = "https://www.homedepot.com/b/Milwaukee/Milwaukee-M18/N-5yc1vZzvZ1z17rdr?NCNI-5"
response = requests.get(url)
soup = bs4.BeautifulSoup(response.text, 'html.parser')
products = soup.find_all('div', {'data-testid': 'product-pod'})
for product in products:
    print(product.text)