import os
import time
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY", "").strip()
COMPANY_LIMIT = int(os.getenv("COMPANY_LIMIT", "500"))
USE_FALLBACK_HTML = os.getenv("USE_FALLBACK_HTML", "true").lower() in ("1", "true", "yes")
DELAY_SECONDS = float(os.getenv("DELAY_SECONDS", "0.5"))
BATCH_SAVE = int(os.getenv("BATCH_SAVE", "20"))
OUTPUT_CSV = "appsumo_software.csv"

BASE_URL = "https://appsumo.com/software/"
API_URL = "https://api.appsumo.com/products"  # hypothetical API endpoint; else we scrape HTML

session = requests.Session()
session.headers.update({
    "User-Agent": "AppSumo-Scraper/1.0 (+https://example.com)"
})

def build_scraperapi_url(target_url, render=True):
    if not SCRAPERAPI_KEY:
        raise RuntimeError("SCRAPERAPI_KEY not set")
    params = {"api_key": SCRAPERAPI_KEY, "url": target_url}
    if render:
        params["render"] = "true"
    from urllib.parse import urlencode
    return f"http://api.scraperapi.com/?{urlencode(params)}"

def fetch_html(url):
    if SCRAPERAPI_KEY:
        url = build_scraperapi_url(url)
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text

def extract_founder_info(product_url):
    try:
        html = fetch_html(product_url)
        soup = BeautifulSoup(html, "html.parser")
        # Founder info might be in a section like "About the Founders" or "Created by"
        founders = []
        sections = soup.find_all(string=lambda s: "founder" in s.lower() or "created by" in s.lower())
        for sec in sections:
            parent = sec.parent
            if parent:
                text = parent.get_text(" ", strip=True)
                if text:
                    founders.append(text)
        return "; ".join(founders)
    except Exception as e:
        print(f"Failed to fetch founder info for {product_url}: {e}")
        return ""

def append_to_csv(data_batch):
    df = pd.DataFrame(data_batch)
    if os.path.exists(OUTPUT_CSV):
        df.to_csv(OUTPUT_CSV, index=False, mode='a', header=False, encoding="utf-8-sig")
    else:
        df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

def main():
    already_scraped = set()
    if os.path.exists(OUTPUT_CSV):
        df_existing = pd.read_csv(OUTPUT_CSV)
        already_scraped = set(df_existing["product_name"].tolist())

    # Load product list from AppSumo HTML (infinite scroll handled manually with pagination)
    products = []  # final list of dicts
    page = 1
    total_fetched = 0

    while total_fetched < COMPANY_LIMIT:
        url = f"{BASE_URL}?page={page}"
        html = fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")
        items = soup.select("a[data-test='product-card-link']")  # selector may vary

        if not items:
            break  # no more products

        for item in items:
            product_name = item.get_text(strip=True)
            product_url = item.get("href")
            if not product_url.startswith("http"):
                product_url = "https://appsumo.com" + product_url

            if product_name in already_scraped:
                continue

            # Optional: extract product website from product page
            website = ""
            try:
                product_html = fetch_html(product_url)
                psoup = BeautifulSoup(product_html, "html.parser")
                link_tag = psoup.select_one("a[href^='http']:not([href*='appsumo'])")
                if link_tag:
                    website = link_tag.get("href")
            except:
                pass

            # Year: approximate from product launch date if available
            year = ""
            try:
                meta_date = psoup.find("meta", {"property": "product:release_date"})
                if meta_date and meta_date.get("content"):
                    year = meta_date.get("content")[:4]
            except:
                pass

            founders = extract_founder_info(product_url) if USE_FALLBACK_HTML else ""

            products.append({
                "product_name": product_name,
                "product_website": website,
                "year": year,
                "founders_info": founders,
                "product_url": product_url
            })

            total_fetched += 1
            if total_fetched % BATCH_SAVE == 0:
                append_to_csv(products)
                products = []

            if total_fetched >= COMPANY_LIMIT:
                break
            time.sleep(DELAY_SECONDS)
        page += 1

    # Save remaining batch
    if products:
        append_to_csv(products)

    print(f"Scraping complete. Total fetched: {total_fetched}")

if __name__ == "__main__":
    main()
