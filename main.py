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

# === Load API Keys ===
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
creds_dict = eval(os.getenv("GOOGLE_CREDENTIALS_JSON"))

# === Google Sheets Setup ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gsheet = gspread.authorize(creds)
sheet = gsheet.open("AI News Tracker")
article_sheet = gsheet.worksheet("Articles")
log_sheet = gsheet.worksheet("Logs")

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
    existing_links = set(article_sheet.col_values(3))  # 3rd column = Link
    print(f"📌 Loaded {len(existing_links)} existing links.")
except Exception as e:
    print(f"⚠️ Could not load existing links: {e}")
    existing_links = set()

# === Count runs today ===
today = datetime.now().strftime("%Y-%m-%d")
log_records = log_sheet.get_all_values()
daily_count = sum(1 for row in log_records if row and row[0] == today) + 1

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
    added = 0
    status = "✅ Success"
    fail_msg = ""

    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        links = extract_links(soup, url)

        if not links:
            print("⚠️ No links found. Writing fallback row.")
            article_sheet.append_row(["No articles", f"No articles found for {today}", "No articles", source_name])
            status = "⚠️ No articles"
        else:
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

            rows = result.split("\n")[1:]  # Skip header

            for row in rows:
                if not row.strip(): continue
                cols = [c.strip() for c in row.split("|")]
                if len(cols) != 3: print(f"⚠️ Bad row: {row}"); continue

                title, summary, link = cols
                if not link.startswith("http") or link in existing_links:
                    print(f"⏩ Skipped: {link}")
                    continue

                article_sheet.append_row([title, summary, link, source_name])
                existing_links.add(link)
                total_added += 1
                added += 1

            if added == 0:
                article_sheet.append_row(["No articles", f"No articles found for {today}", "No articles", source_name])
                status = "⚠️ No new entries"

    except Exception as e:
        status = "❌ Error"
        fail_msg = str(e)
        article_sheet.append_row(["Connection Error", fail_msg, "Connection failed", source_name])

    log_sheet.append_row([
        today,
        daily_count,
        source_name,
        status,
        added,
        fail_msg
    ])

print(f"\n📊 DONE. Total new articles added: {total_added}")
