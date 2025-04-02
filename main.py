import os
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# 🟢 Load OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

# 🟢 Google Sheets Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = eval(os.getenv("GOOGLE_CREDENTIALS_JSON"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("AI News Tracker").worksheet("Articles")

# 🟢 Load sites and prompt
with open("sites.txt", "r") as f:
    urls = [line.strip() for line in f if line.strip()]

with open("prompt.txt", "r") as f:
    prompt_template = f.read().strip()

# 🟢 Loop through each site
for url in urls:
    prompt = prompt_template.replace("{{URL}}", url)
    print(f"🔍 Fetching for: {url}")

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an AI that summarizes new articles in tables."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        result = response.choices[0].message.content.strip()

        sheet.append_row([
            url,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            result
        ])

        print("✅ Saved to sheet")
    except Exception as e:
        print(f"❌ Error on {url}: {e}")
