import os
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Setup Google Sheets
def setup_google_sheets():
    creds_dict = eval(os.getenv("GOOGLE_CREDENTIALS_JSON"))
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open("AI News Tracker")
    return spreadsheet

# Detect RSS Feed
def detect_rss_feed(base_url):
    common_feeds = ["feed", "rss", "blog/rss", "news/rss", "tag/ai/feed"]
    for path in common_feeds:
        feed_url = base_url.rstrip("/") + "/" + path
        feed = feedparser.parse(feed_url)
        if feed.bozo == 0 and len(feed.entries) > 0:
            return feed_url
    return None

# Parse RSS Articles
def parse_rss(feed_url):
    feed = feedparser.parse(feed_url)
    today_str = datetime.now().strftime("%Y-%m-%d")
    articles = []
    for entry in feed.entries:
        if hasattr(entry, 'published_parsed'):
            published = datetime(*entry.published_parsed[:3]).strftime("%Y-%m-%d")
            if published == today_str:
                articles.append([today_str, feed_url, entry.title, entry.link])
    return articles

# Fallback HTML Parsing
def parse_html(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        today_str = datetime.now().strftime("%Y/%m/%d")
        alt_today_str = datetime.now().strftime("%Y-%m-%d")
        articles = []
        for link in soup.find_all("a", href=True):
            href = link['href']
            text = link.get_text().strip()
            if today_str in href or alt_today_str in href:
                full_link = href if href.startswith("http") else url.rstrip("/") + "/" + href.lstrip("/")
                articles.append([datetime.now().strftime("%Y-%m-%d"), url, text[:150], full_link])
        return articles
    except Exception:
        return []

# Avoid duplicates and insert a one-line gap per date
def update_articles_sheet(sheet, new_articles):
    existing_links = set(cell.value for cell in sheet.col_values(4))
    last_row = len(sheet.get_all_values()) + 2
    today = datetime.now().strftime("%Y-%m-%d")

    # Insert 1-line gap for the date
    sheet.update(f"A{last_row}:D{last_row}", [[""]*4])
    last_row += 1

    for article in new_articles:
        if article[3] not in existing_links:
            sheet.update(f"A{last_row}:D{last_row}", [article])
            last_row += 1

# Log to 'Log' sheet
def log_result(log_sheet, website, status, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_sheet.append_row([timestamp, website, status, message])

# Main execution
def main():
    spreadsheet = setup_google_sheets()
    sites_sheet = spreadsheet.worksheet("Sites")
    articles_sheet = spreadsheet.worksheet("Articles")
    log_sheet = spreadsheet.worksheet("Log")
    
    urls = sites_sheet.col_values(1)[1:]  # Skip header if present

    for url in urls:
        try:
            rss_url = detect_rss_feed(url)
            if rss_url:
                articles = parse_rss(rss_url)
                method = "RSS"
            else:
                articles = parse_html(url)
                method = "HTML"

            if articles:
                update_articles_sheet(articles_sheet, articles)
                log_result(log_sheet, url, "✅ Success", f"{len(articles)} articles via {method}")
            else:
                log_result(log_sheet, url, "⚠️ No new articles", f"No articles found today via {method}")
        except Exception as e:
            log_result(log_sheet, url, "❌ Failure", str(e))

main()
