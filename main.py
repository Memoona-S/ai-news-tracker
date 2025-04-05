import os
import requests
from datetime import datetime
import gspread
from urllib.parse import urlparse
from oauth2client.service_account import ServiceAccountCredentials

# === Setup Google Sheets ===
def setup_google_sheets():
    creds_dict = eval(os.getenv("GOOGLE_CREDENTIALS_JSON"))
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open("AI News Tracker")
    return spreadsheet

# === Call Brave Search API ===
def search_brave(query):
    api_key = os.getenv("OPENAI_API_KEY")
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key
    }
    params = {
        "q": query,
        "count": 10,
        "freshness": "day"
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get("web", {}).get("results", [])
    else:
        raise Exception(f"Brave API error: {response.status_code} - {response.text}")

# === Normalize domain from any URL ===
def extract_domain(url):
    return urlparse(url).netloc.replace("www.", "").strip().lower()

# === Update Articles Sheet ===
def update_articles_sheet(sheet, articles, allowed_domains, log_sheet):
    existing_links = set(sheet.col_values(4))
    last_row = len(sheet.get_all_values()) + 2
    today = datetime.now().strftime("%Y-%m-%d")
    sheet.update(f"A{last_row}:D{last_row}", [[""] * 4])
    last_row += 1
    pushed = 0
    skipped = 0

    for article in articles:
        url = article['url']
        domain = extract_domain(url)
        allowed_match = domain in allowed_domains

        if url not in existing_links and allowed_match:
            sheet.update(f"A{last_row}:D{last_row}", [[
                today,
                domain,
                article['title'][:150],
                url
            ]])
            last_row += 1
            pushed += 1
        else:
            skipped += 1
            log_result(log_sheet, url, "⛔ Skipped", f"{article['title'][:80]} | domain={domain} allowed={allowed_match}")
    return pushed, skipped

# === Log Result ===
def log_result(sheet, query, status, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([timestamp, query, status, message])

# === Main ===
def main():
    spreadsheet = setup_google_sheets()
    sites_sheet = spreadsheet.worksheet("Sites")
    articles_sheet = spreadsheet.worksheet("Articles")
    log_sheet = spreadsheet.worksheet("Log")

    site_urls = sites_sheet.col_values(1)[1:]
    if not site_urls:
        log_result(log_sheet, "N/A", "⚠️ No Sites", "No site URLs found in Sites sheet.")
        return

    # Extract only the root domains
    allowed_domains = [extract_domain(url) for url in site_urls if url.startswith("http")]
    query = "AI articles " + " OR ".join([f"site:{d}" for d in allowed_domains])

    try:
        results = search_brave(query)
        if results:
            pushed, skipped = update_articles_sheet(articles_sheet, results, allowed_domains, log_sheet)
            log_result(log_sheet, query, "✅ Success", f"{pushed} pushed / {skipped} skipped")
        else:
            log_result(log_sheet, query, "⚠️ No Results", "No fresh articles found")
    except Exception as e:
        log_result(log_sheet, query, "❌ Failure", str(e))

if __name__ == "__main__":
    main()
