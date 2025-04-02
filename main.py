import os
import requests
import gspread
from openai import OpenAI
from datetime import datetime
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

# === STEP 1: Load API secrets ===
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
creds_dict = eval(os.getenv("GOOGLE_CREDENTIALS_JSON"))

# === STEP 2: Connect to Google Sheets ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gsheet = gspread.authorize(creds)
sheet = gsheet.open("AI News Tracker").worksheet("Articles")

# === STEP 3: Fetch existing links to avoid duplicates ===
existing_links = set()
try:
    link_column = sheet.col_values(3)  # Column C = Link
    existing_links = set(link_column)
    print(f"📌 Loaded {len(existing_links)} existing links")
except Exception as e:
    print(f"⚠️ Couldn't load existing links: {e}")

# === STEP 4: Load site URLs and prompt ===
with open("Sites.txt", "r") as f:
    urls = [line.strip() for line in f if line.strip()]

with open("prompt.txt", "r") as f:
    prompt_template = f.read().strip()

# === STEP 5: Process each website ===
for url in urls:
    print(f"\n🔍 Scraping: {url}")

    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        # STEP 5A: Extract top 10 visible links with titles
        links = []
        for a in soup.find_all("a", href=True):
            text = a.get_text().strip()
            if text and len(text) > 10 and not a['href'].startswith("#"):
                full_url = requests.compat.urljoin(url, a['href'])
                links.append(f"{text} | {full_url}")  # Clean format for GPT
            if len(links) >= 10:
                break

        if not links:
            print("⚠️ No visible article links found.")
            continue

        # STEP 5B: Inject links into GPT prompt
        link_block = "\n".join(links)
        final_prompt = prompt_template.replace("{{URL}}", url).replace("{{CONTENT}}", link_block)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You extract article titles, summaries, and links."},
                {"role": "user", "content": final_prompt}
            ],
            temperature=0.2
        )

        result = response.choices[0].message.content.strip()
        print("🧾 GPT Response:\n", result)

        # STEP 5C: Parse GPT table output
        lines = result.split("\n")[1:]  # Skip header

        added_count = 0
        for line in lines:
            if not line.strip(): continue
            columns = [c.strip() for c in line.split("|")]
            
            if len(columns) != 3:
                print(f"⚠️ Skipped (invalid column count): {line}")
                continue

            title, summary, link = columns

            if not link.startswith("http"):
                print(f"⚠️ Skipped (invalid link): {link}")
                continue

            if link in existing_links:
                print(f"⏩ Skipped duplicate: {link}")
                continue

            sheet.append_row([title, summary, link])
            existing_links.add(link)
            added_count += 1

        print(f"✅ Added {added_count} new article(s) from {url}")

    except Exception as e:
        print(f"❌ Error while processing {url}: {e}")
