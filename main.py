import os
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# === 🔐 Load secrets from GitHub Actions ===
openai.api_key = os.getenv("OPENAI_API_KEY")
creds_dict = eval(os.getenv("GOOGLE_CREDENTIALS_JSON"))

# === 📊 Connect to Google Sheets ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("AI News Tracker").worksheet("Articles")

# === 📥 Load sites and prompt ===
with open("Sites.txt", "r") as f:
    urls = [line.strip() for line in f if line.strip()]

with open("prompt.txt", "r") as f:
    prompt_template = f.read().strip()

# === 🧠 Run GPT-4o on each site ===
for url in urls:
    final_prompt = prompt_template.replace("{{URL}}", url)
    print(f"🔍 Checking: {url}")

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an AI that summarizes news articles into clean tables."},
                {"role": "user", "content": final_prompt}
            ],
            temperature=0.2
        )

        result = response.choices[0].message.content.strip()
        print("🧾 GPT Result:\n", result)

        # === ✂️ Parse GPT table (skip header) ===
        rows = result.split("\n")
        data_rows = rows[1:]  # skip header

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

        print(f"✅ Added {len(data_rows)} rows from {url}\n")

    except Exception as e:
        print(f"❌ Error on {url}: {e}")
