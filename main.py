import os
import requests
import gspread
from openai import OpenAI
from datetime import datetime
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

# === 🔐 Load API secrets
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
creds_dict = eval(os.getenv("GOOGLE_CREDENTIALS_JSON"))

# === 📊 Connect to Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gsheet = gspread.authorize(creds)
sheet = gsheet.open("AI News Tracker").worksheet("Articles")

# === 🧠 Load existing links to prevent duplicates
try:
    existing_links = set(sheet.col_values(3))  # 3rd column = Link
    print(f"📌 Loaded {len(existing_links)} existing links.")
except Exception as e:
    print(f"⚠️ Could not load existing links: {e}")
    existing_links = set()

# === 📂 Load sites and prompt
with open("Sites.txt", "r") as f:
    urls = [line.strip() for line in f if line.strip()]

with open("prompt.txt", "r") as f:
    prompt_template = f.read().strip()

total_added = 0
total_skipped = 0

# === 🔁 Process each site
for url in urls:
    print(f"\n🔍 Scraping: {url}")

    # Skip known broken or paywalled domains
    if any(domain in url for domain in ["ft.com", "bloomberg.com", "economist.com"]):
        print(f"🚫 Skipped paywalled site: {url}")
        total_skipped += 1
        continue

    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        # === 🌐 Extract top 10 usable links
        links = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(separator=" ").strip()
            if text and len(text) > 10 and not a['href'].startswith("#"):
                full_url = requests.compat.urljoin(url, a['href'])
                links.append(f"{text} | {full_url}")
            if len(links) >= 10:
                break

        if not links:
            print("⚠️ No usable <a> tags found — skipping site.")
            total_skipped += 1
            continue

        print("🔗 Top 10 links scraped:")
        for l in links:
            print("→", l)

        content = "\n".join(links)
        prompt = prompt_template.replace("{{URL}}", url).replace("{{CONTENT}}", content)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an AI that extracts article titles, summaries, and links from a list."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        result = response.choices[0].message.content.strip()
        print("🧾 GPT Result:\n", result)

        # === ✂️ Parse table output
        rows = result.split("\n")[1:]  # Skip header
        site_added = 0

        for row in rows:
            if not row.strip(): continue
            columns = [c.strip() for c in row.split("|")]

            if len(columns) != 3:
                print(f"⚠️ Bad format: {row}")
                total_skipped += 1
                continue

            title, summary, link = columns

            if not link.startswith("http"):
                print(f"⚠️ Invalid link: {link}")
                total_skipped += 1
                continue

            if link in existing_links:
                print(f"⏩ Duplicate skipped: {link}")
                total_skipped += 1
                continue

            sheet.append_row([title, summary, link])
            existing_links.add(link)
            total_added += 1
            site_added += 1

        print(f"✅ Added {site_added} new article(s) from {url}")

    except Exception as e:
        print(f"❌ Error on {url}: {e}")
        total_skipped += 1

# === ✅ Summary
print("\n📊 FINAL SUMMARY")
print(f"✅ Total articles added: {total_added}")
print(f"⏭️ Total skipped (errors, dupes, paywalls): {total_skipped}")
