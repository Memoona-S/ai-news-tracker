# === scalable_news_scraper/main.py ===
import os
import json
import requests
import gspread
from openai import OpenAI
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# === Load API Keys ===
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
creds_dict = eval(os.getenv("GOOGLE_CREDENTIALS_JSON"))

# === Google Sheets Setup ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gsheet = gspread.authorize(creds)
sheet = gsheet.open("AI News Tracker").worksheet("Articles")

# === Load custom selectors ===
with open("parsers.json") as f:
    selector_config = json.load(f)

# === Load sites ===
with open("Sites.txt") as f:
    urls = [line.strip() for line in f if line.strip()]

# === Load prompt template ===
with open("prompt.txt") as f:
    prompt_template = f.read().strip()

# === Load existing links ===
try:
    existing_links = set(sheet.col_values(3))  # 3rd column = Link
    print(f"📌 Loaded {len(existing_links)} existing links.")
except Exception as e:
    print(f"⚠️ Could not load existing links: {e}")
    existing_links = set()

# === Setup retryable session ===
session = requests.Session()
retry = Retry(total=2, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

# === Start processing ===
total_added = 0

def get_domain(url):
    return urlparse(url).netloc.replace("www.", "")

def extract_links(soup, url):
    domain = get_domain(url)
    selector = selector_config.get(domain, selector_config.get("default", {})).get("selector", "a[href]")
    print(f"🔧 Using selector for {domain}: {selector}")

    elements = soup.select(selector)
    links = []

    for el in elements:
        if not el.has_attr("href"): continue
        text = el.get_text(separator=" ").strip()
        if text and len(text) > 10:
            full_url = requests.compat.urljoin(url, el['href'])
            links.append(f"{text} | {full_url}")
        if len(links) >= 10:
            break

    return links

# === Loop through each URL ===
for url in urls:
    print(f"\n🔍 Scraping: {url}")
    domain = get_domain(url)
    source_name = domain.split(".")[0].capitalize()

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
        }
        res = session.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        links = extract_links(soup, url)

        if not links:
            print("⚠️ No links found. Writing fallback row.")
            sheet.append_row(["No articles", f"No articles found for {datetime.now().strftime('%Y-%m-%d')}", "No articles", source_name])
            continue

        print("🔗 Found links:")
        for l in links: print("→", l)

        content = "\n".join(links)
        prompt = prompt_template.replace("{{URL}}", url).replace("{{CONTENT}}", content)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You extract article titles, summaries, and links."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        result = response.choices[0].message.content.strip()
        print("🧾 GPT Result:\n", result)

        # === Parse table rows ===
        rows = result.split("\n")[1:]  # Skip header
        added = 0

        for row in rows:
            if not row.strip(): continue
            cols = [c.strip() for c in row.split("|")]
            if len(cols) != 3: print(f"⚠️ Bad row: {row}"); continue

            title, summary, link = cols
            if not link.startswith("http") or link in existing_links:
                print(f"⏩ Skipped: {link}")
                continue

            sheet.append_row([title, summary, link, source_name])
            existing_links.add(link)
            total_added += 1
            added += 1

        if added == 0:
            sheet.append_row(["No articles", f"No articles found for {datetime.now().strftime('%Y-%m-%d')}", "No articles", source_name])
        else:
            print(f"✅ {added} new articles from {url}")

    except requests.exceptions.ConnectionError as e:
        print(f"🌐 Connection error for {url}: {e}")
        sheet.append_row(["Connection Error", str(e), "Connection failed", source_name])
        continue
    except Exception as e:
        print(f"❌ Error on {url}: {e}")

print(f"\n📊 DONE. Total new articles added: {total_added}")
