# YC & AppSumo Scrapers

Python scrapers to extract startup and software deal data from **Y Combinator** and **AppSumo**.  
Supports **resumable scraping**, **incremental CSV saving**, and fetching **latest data first**.  

---

## Features

### Y Combinator Scraper

- Fetch startup companies from YC OSS API (`https://yc-oss.github.io/api/companies/all.json`)  
- Extract fields:  
  - Company Name  
  - Company Website  
  - Address  
  - Founder Names  
  - Founder LinkedIn  
  - Batch / Year  
- Sort companies by **latest batches first** (newest → oldest)  
- Skip previously scraped companies (resumable via CSV)  
- Incremental save every configurable batch  
- Optional fallback: scrape founder info from company page using **ScraperAPI**  

### AppSumo Software Scraper

- Fetch AppSumo software deals (`https://appsumo.com/software/`)  
- Extract fields:  
  - Product Name  
  - Product Website  
  - Launch Year  
  - Founder Information  
  - AppSumo Deal URL  
- Supports **newest deals first**  
- Skip previously scraped products (resumable)  
- Incremental CSV save  
- Optional **ScraperAPI integration** for dynamic pages / JavaScript content  

---

## Requirements

- Python 3.9+  
- Packages in `requirements.txt`:

```
requests
beautifulsoup4
python-dotenv
pandas
tqdm
```

---

## Installation

1. Clone the repository:

```
git clone https://github.com/emad313/yc-appsumo-scrapers.git
cd yc-appsumo-scrapers
```

2. Install dependencies:

```
pip install -r requirements.txt
```

3. Create a `.env` file (or copy `.env.example`) and configure your settings:

```
# ScraperAPI key (optional but recommended for dynamic JS content)
SCRAPERAPI_KEY=YOUR_SCRAPERAPI_KEY_HERE

# Maximum companies / products to fetch per run
COMPANY_LIMIT=500

# Use HTML fallback to scrape missing founder info
USE_FALLBACK_HTML=true

# Delay between requests (seconds)
DELAY_SECONDS=0.5

# Number of records to save incrementally
BATCH_SAVE=20

# Output CSV filenames
YC_OUTPUT_CSV=yc_companies.csv
APPSUMO_OUTPUT_CSV=appsumo_software.csv
```

---

## Usage

### Y Combinator Scraper

```
python main.py
```

- Fetches **latest YC companies first**, descending year order.  
- Skips already scraped companies if `yc_companies.csv` exists.  
- Incremental save every `BATCH_SAVE` companies.  

### AppSumo Scraper

```
python appsumo_scraper.py
```

- Fetches **AppSumo deals** newest first.  
- Skips previously scraped products if `appsumo_software.csv` exists.  
- Incremental save every `BATCH_SAVE` products.  

---

## ScraperAPI Usage

- **Purpose:** Handle dynamic content / JavaScript-rendered pages, e.g., founder info not in API.  
- **Integration:** The scraper automatically uses your `SCRAPERAPI_KEY` if provided.  
- **Example:**

```python
def build_scraperapi_url(target_url, render=True):
    params = {
        "api_key": SCRAPERAPI_KEY,
        "url": target_url
    }
    if render:
        params["render"] = "true"
    from urllib.parse import urlencode
    return f"http://api.scraperapi.com/?{urlencode(params)}"
```

- Ensure you **set `SCRAPERAPI_KEY`** in `.env` to enable fallback scraping.  

---

## Output CSV Columns

### Y Combinator

```
name,address,website,founders_names,founders_linkedin,batch,year,yc_url,per_company_api
```

### AppSumo

```
product_name,product_website,year,founders_info,product_url
```

---

## Folder Structure

```
yc-appsumo-scrapers/
│
├─ main.py                 # Y Combinator scraper
├─ appsumo_scraper.py      # AppSumo scraper
├─ requirements.txt
├─ .env.example
├─ README.md
└─ (CSV output files will be saved here)
```

---

## Notes

- Always respects **incremental scraping**; rerun will only fetch new entries.  
- Supports **latest-first order** for both YC and AppSumo.  
- Configurable **delay and batch saving** for safe and quota-friendly scraping.  
- Recommended to use **ScraperAPI** for JavaScript-heavy pages to avoid missing data.  

---

## License

MIT License

© 2025 Emad Uddin