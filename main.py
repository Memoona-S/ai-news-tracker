import os
import requests
import gspread
from openai import OpenAI
from datetime import datetime
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

# === 🔐 Load secrets
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
creds_dict = eval(os.getenv("GOOGLE_CREDENTIALS_JSON"))

# === 📊 Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gsheet = gspread.authorize(creds)
sheet = gsheet.open("AI News Tracker").worksheet("Articles")

# === 📄 Load URLs and prompt
with open("Sites.txt", "r") as f:
    urls = [line.strip() for line in f if line.strip()]

with open("prompt.txt", "r") as f:
    prompt_template = f.read().strip()

# === 🚀 Process each URL
for url in urls:
    print(f"🔍 Fetching: {url}")

    try:
        # === 🌐 Get HTML
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # === 🔎 Extract Top 10 Links with visible text
        links = []
        for a in soup.find_all("a", href=True):
            text = a.get_text().strip()
            if text and len(text) > 10 and not a['href'].startswith("#"):
                link_url = a['href']
                if not link_url.startswith("http"):
                    link_url = requests.compat.urljoin(url, link_url)
                links.append(f"{text} - {link_url}")
            if len(links) >= 10:
                break

        if not links:
            print(f"⚠️ No links found on {url}")
            continue

        link_block = "\n".join(links)

        # === 💬 Build final prompt
        final_prompt = prompt_template.replace("{{URL}}", url).replace("{{CONTENT}}", link_block)

        # === 🤖 GPT-4o Completion
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an AI that extracts article metadata from a list of links and titles."},
                {"role": "user", "content": final_prompt}
            ],
            temperature=0.2
        )

        result = completion.choices[0].message.content.strip()
        print("🧾 GPT Result:\n", result)

        # === ✂️ Parse GPT table
        rows = result.split("\n")
        data_rows = rows[1:]

        for row in data_rows:
            if not row.strip(): continue
            columns = [col.strip() for col in row.split("|")]
            if len(columns) >= 4:
                sheet.append_row([
                    url,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    columns[0],  # Title
                    columns[1],  # Summary
                    columns[2],  # Time
                    columns[3],  # Source
                ])
            else:
                print(f"⚠️ Skipped row (not 4+ columns): {row}")

        print(f"✅ Done with {url}\n")

    except Exception as e:
        print(f"❌ Error on {url}: {e}")
