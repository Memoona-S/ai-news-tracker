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

# === 📄 Load URLs and Prompt Template
with open("Sites.txt", "r") as f:
    urls = [line.strip() for line in f if line.strip()]

with open("prompt.txt", "r") as f:
    prompt_template = f.read().strip()

# === 🚀 Run on each site
for url in urls:
    print(f"🔍 Scraping: {url}")

    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        # Extract Top 10 readable links
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

        # === Parse 3-column table (Title | Summary | Link)
        rows = result.split("\n")[1:]  # skip header

        for row in rows:
            if not row.strip(): continue
            columns = [c.strip() for c in row.split("|")]
            if len(columns) >= 3:
                title = columns[0]
                summary = columns[1]
                link = columns[2]
                sheet.append_row([title, summary, link])
            else:
                print(f"⚠️ Skipped row (not 3+ columns): {row}")

        print(f"✅ Done with {url}")

    except Exception as e:
        print(f"❌ Error on {url}: {e}")
