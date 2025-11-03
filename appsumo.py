import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from time import sleep
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY")
OUTPUT_CSV = "appsumo_software.csv"
BATCH_SAVE = int(os.getenv("BATCH_SAVE", 20))
DELAY_SECONDS = float(os.getenv("DELAY_SECONDS", 0.5))

BASE_URL = "https://appsumo.com/software/"

# Load previously fetched products to skip duplicates
if os.path.exists(OUTPUT_CSV):
    df_existing = pd.read_csv(OUTPUT_CSV)
    existing_urls = set(df_existing['product_url'].tolist())
else:
    df_existing = pd.DataFrame()
    existing_urls = set()

results = []

def fetch_html(url):
    """Fetch HTML using ScraperAPI with JS rendering"""
    api_url = f"http://api.scraperapi.com/?api_key={SCRAPERAPI_KEY}&url={url}&render=true"
    response = requests.get(api_url)
    if response.status_code != 200:
        print(f"Error fetching {url}: {response.status_code}")
        return None
    return response.text

def parse_main_page(html):
    """Parse main software page and return product URLs and names"""
    soup = BeautifulSoup(html, "html.parser")
    product_cards = soup.select("a[href*='/products/']")  # All product links
    products = []
    for card in product_cards:
        product_url = "https://appsumo.com" + card['href']
        name = card.get_text(strip=True)
        if product_url not in existing_urls:
            products.append({"name": name, "product_url": product_url})
    return products

def parse_product_page(product_url):
    """Fetch individual product page to get website, founder, year"""
    html = fetch_html(product_url)
    if not html:
        return None, None, None
    soup = BeautifulSoup(html, "html.parser")

    # Extract website
    website_tag = soup.select_one("a[href^='http']:not([href*='appsumo.com'])")
    product_website = website_tag['href'] if website_tag else None

    # Extract founder info (may require specific selectors)
    founder_tag = soup.select_one("div:contains('Founder')")  # update as needed
    founder_info = founder_tag.get_text(strip=True) if founder_tag else None

    # Extract launch year if available
    year_tag = soup.select_one("div:contains('Launched')")
    year = year_tag.get_text(strip=True) if year_tag else None

    return product_website, founder_info, year

# Step 1: Fetch main page
html = fetch_html(BASE_URL)
if not html:
    print("Failed to fetch main AppSumo page")
    exit(1)

products_list = parse_main_page(html)

# Step 2: Visit each product page
for i, product in enumerate(tqdm(products_list, desc="Scraping products")):
    website, founder, year = parse_product_page(product['product_url'])
    results.append({
        "product_name": product['name'],
        "product_website": website,
        "year": year,
        "founders_info": founder,
        "product_url": product['product_url']
    })
    sleep(DELAY_SECONDS)

    # Incremental save
    if (i + 1) % BATCH_SAVE == 0:
        df = pd.DataFrame(results)
        if not df_existing.empty:
            df = pd.concat([df_existing, df], ignore_index=True)
        df.to_csv(OUTPUT_CSV, index=False)
        print(f"Saved {i + 1} products to {OUTPUT_CSV}")

# Final save
if results:
    df = pd.DataFrame(results)
    if not df_existing.empty:
        df = pd.concat([df_existing, df], ignore_index=True)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Scraping complete. Total fetched: {len(results)}")
else:
    print("Scraping complete. Total fetched: 0")
