import os
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# === Load Secrets from GitHub ===
openai.api_key = os.getenv("OPENAI_API_KEY")

# === Google Sheets Setup ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = eval(os.getenv("GOOGLE_CREDENTIALS_JSON"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("AI News Tracker").worksheet("Articles")

# === Load Sites and Prompt ===
with open("sites.txt", "r") as f:
    urls = [line.strip() for line in f if line.strip()]

with open("prompt.txt", "r") as f:
    prompt_template = f.read().strip()

# === Loop through each URL ===
for url in urls:
    final_prompt = prompt_template.replace("{{URL}}", url)
    print(f"🔍 Checking: {url}")

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an AI that summarizes news into clean tables."},
                {"role": "user", "content": final_prompt}
            ],
            temperature=0.2
        )

        result = response.choices[0].message.content.strip()
        print(result)

        rows = result.split("\n")
        header = rows[0]
        data_rows = rows[1:]

        for row in data_rows:
            if not row.strip(): continue  # skip blank lines
            columns = [c.strip() for c in row.split("|")]
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
                print(f"⚠️ Row skipped (not 4 columns): {row}")

        print(f"✅ Saved {len(data_rows)} articles from {url}")

    except Exception as e:
        print(f"❌ Error on {url}: {e}")
