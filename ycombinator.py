import os
import time
import json
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY", "").strip()
COMPANY_LIMIT = int(os.getenv("COMPANY_LIMIT", "500"))
USE_FALLBACK_HTML = os.getenv("USE_FALLBACK_HTML", "true").lower() in ("1", "true", "yes")
DELAY_SECONDS = float(os.getenv("DELAY_SECONDS", "0.5"))
BATCH_SAVE = int(os.getenv("BATCH_SAVE", "20"))

YC_API_COMPANIES = "https://yc-oss.github.io/api/companies/all.json"
OUTPUT_CSV = "yc_companies.csv"
HEADERS = {"User-Agent": "YC-Dynamic-Scraper/1.0"}

session = requests.Session()
session.headers.update(HEADERS)
session.timeout = 30


def fetch_json(url):
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"ERROR fetching JSON {url} -> {e}")
        return None


def build_scraperapi_url(target_url, render=True):
    base = "http://api.scraperapi.com"
    params = {"api_key": SCRAPERAPI_KEY, "url": target_url}
    if render:
        params["render"] = "true"
    from urllib.parse import urlencode
    return f"{base}?{urlencode(params)}"


def fetch_html_via_scraperapi(target_url):
    if not SCRAPERAPI_KEY:
        raise RuntimeError("SCRAPERAPI_KEY not set but HTML fallback requested.")
    api_url = build_scraperapi_url(target_url, render=True)
    try:
        resp = session.get(api_url, timeout=60)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"ERROR fetching via ScraperAPI {target_url} -> {e}")
        return None


def extract_founders_from_company_json(company_json):
    founders = []
    for key in ["team", "founders", "people", "members"]:
        if key in company_json and isinstance(company_json[key], (list, tuple)):
            for person in company_json[key]:
                if isinstance(person, str):
                    founders.append({"name": person, "linkedin": ""})
                elif isinstance(person, dict):
                    name = person.get("name") or person.get("full_name") or ""
                    linkedin = person.get("linkedin") or ""
                    if not linkedin and "links" in person and isinstance(person["links"], dict):
                        linkedin = person["links"].get("linkedin", "")
                    founders.append({"name": name, "linkedin": linkedin})
            if founders:
                return founders
    # Fallback: search for LinkedIn URLs in JSON
    text = json.dumps(company_json)
    linkedin_urls = re.findall(r"https?://(?:www\.)?linkedin\.com/in/[A-Za-z0-9\-_]+", text)
    for url in linkedin_urls:
        founders.append({"name": "", "linkedin": url})
    return founders


def extract_founders_from_html(html):
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    founders = []
    anchors = soup.select('a[href*="linkedin.com/in"], a[href*="linkedin.com/company"]')
    seen = set()
    for a in anchors:
        href = a.get("href")
        if not href:
            continue
        if href.startswith("//"):
            href = "https:" + href
        if href in seen:
            continue
        seen.add(href)
        name_text = a.get_text(strip=True) or ""
        if not name_text:
            parent = a.parent
            for _ in range(3):
                if parent:
                    name_text = parent.get_text(" ", strip=True)
                    if name_text:
                        break
                    parent = parent.parent
        founders.append({"name": name_text.strip(), "linkedin": href})
    return founders


def safe_get(d, key, default=""):
    v = d.get(key, default) if isinstance(d, dict) else default
    return default if v is None else v


def get_year_from_batch(batch_str):
    if not batch_str:
        return 0
    match = re.search(r'(\d{2})$', batch_str)
    if match:
        return 2000 + int(match.group(1))
    return 0


def append_to_csv(data_batch):
    df = pd.DataFrame(data_batch)
    if os.path.exists(OUTPUT_CSV):
        df.to_csv(OUTPUT_CSV, index=False, mode='a', header=False, encoding="utf-8-sig")
    else:
        df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")


def main():
    # Load already scraped companies
    already_scraped = set()
    if os.path.exists(OUTPUT_CSV):
        df_existing = pd.read_csv(OUTPUT_CSV)
        already_scraped = set(df_existing["name"].tolist())

    # Fetch all companies
    companies_json = fetch_json(YC_API_COMPANIES)
    if not companies_json or not isinstance(companies_json, list):
        print("Failed to fetch companies list. Exiting.")
        return

    # Sort descending by batch year → newest first
    companies_sorted = sorted(
        companies_json,
        key=lambda x: get_year_from_batch(safe_get(x, "batch")),
        reverse=True
    )

    print(f"Total companies: {len(companies_sorted)}. Processing up to {COMPANY_LIMIT} entries.")

    results_batch = []
    current_idx = 0
    for entry in tqdm(companies_sorted[:COMPANY_LIMIT], desc="Companies"):
        current_idx += 1
        name = safe_get(entry, "name")
        if name in already_scraped:
            continue  # skip already scraped

        batch = safe_get(entry, "batch", "")
        year = get_year_from_batch(batch)

        website = safe_get(entry, "website", "")
        address = safe_get(entry, "all_locations", "")
        url = safe_get(entry, "url", "")
        per_company_api = safe_get(entry, "api", "")

        founders_list = []

        # Try API first
        if per_company_api:
            company_json = fetch_json(per_company_api)
            if company_json and isinstance(company_json, dict):
                founders_list = extract_founders_from_company_json(company_json)

        # Fallback HTML
        if not founders_list and USE_FALLBACK_HTML and url:
            html = fetch_html_via_scraperapi(url)
            founders_list = extract_founders_from_html(html)

        # Format founders
        if founders_list:
            names = "; ".join(f.get("name", "").strip() for f in founders_list if f.get("name"))
            links = "; ".join(f.get("linkedin", "").strip() for f in founders_list if f.get("linkedin"))
        else:
            names = ""
            links = ""

        scraped_data = {
            "name": name,
            "address": address,
            "website": website,
            "founders_names": names,
            "founders_linkedin": links,
            "batch": batch,
            "year": year,
            "yc_url": url,
            "per_company_api": per_company_api
        }

        results_batch.append(scraped_data)

        if current_idx % BATCH_SAVE == 0:
            append_to_csv(results_batch)
            results_batch = []

        time.sleep(DELAY_SECONDS)

    # Save remaining batch
    if results_batch:
        append_to_csv(results_batch)

    # Final sort descending by year
    df = pd.read_csv(OUTPUT_CSV)
    df = df.sort_values(by="year", ascending=False)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"Scraping complete. Total records: {len(df)}")


if __name__ == "__main__":
    main()
