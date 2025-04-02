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

# === 📊 Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gsheet = gspread.authorize(creds)
sheet = gsheet.open("AI News Tracker").worksheet("Articles")

# === ⚡ Fetch all existing links once at start
existing_links = set()
try:
    link_column = sheet.col_values(3)  # 3rd column is 'Link'
    existing_links = set(link_column)
    print(f"📌 Loaded {len(existing_links)} existing links to check for duplicates")
except Exception as e:
    print(f"⚠️ Could not load existing links: {e}")

# === 📄 Load URLs and Prompt Template
with open("Sites.txt", "r") as f:
    urls = [line.strip() for line in f if line.strip()]

with open("prompt.txt", "r") as f:
    prompt_template = f.read().strip()

# === 🚀 Process each site
for url in urls:
    print(f"\n🔍 Scraping: {url}")

    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        # Extract Top 10 links
        links = []
        for a in soup.find_all("a", href=True):
            text = a.get_text().strip()
            if text and len(text) > 10 and not a['href'].startswith("#"):
                full_url = requests.compat.urljoin(url, a['href'])
                links.append(f"{text} - {full_url}")
            if len(links) >= 10:
                break

        if not links:
            print(f"⚠️ No visible links found.")
            continue

        content = "\n".join(links)
        final_prompt = prompt_template.replace("{{URL}}", url).replace("{{CONTENT}}", content)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an AI that extracts article titles, summaries, and links from a list of articles."},
                {"role": "user", "content": final_prompt}
            ],
            temperature=0.2
        )

        result = response.choices[0].message.content.strip()
        print("🧾 GPT Response:\n", result)

        # === ✂️ Parse GPT table
        rows = result.split("\n")[1:]

        added_count = 0
        for row in rows:
            if not row.strip(): continue
            columns = [c.strip() for c in row.split("|")]
            if len(columns) >= 3:
                title, summary, link = columns[0], columns[1], columns[2]
                if link in existing_links:
                    print(f"⏩ Skipped duplicate link: {link}")
                    continue
                sheet.append_row([title, summary, link])
                existing_links.add(link)
                added_count += 1
            else:
                print(f"⚠️ Skipped row (not 3+ columns): {row}")

        print(f"✅ Added {added_count} new article(s) from {url}")

    except Exception as e:
        print(f"❌ Error on {url}: {e}")
