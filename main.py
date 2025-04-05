import os
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser as date_parser
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def setup_google_sheets():
    creds_dict = eval(os.getenv("GOOGLE_CREDENTIALS_JSON"))
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open("AI News Tracker")
    return spreadsheet

def detect_rss_feed(base_url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(base_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        for link in soup.find_all('link', type='application/rss+xml'):
            href = link.get('href')
            if href:
                return href if href.startswith('http') else base_url.rstrip('/') + '/' + href.lstrip('/')

        common_paths = ["feed", "rss", "blog/rss", "category/artificial-intelligence/feed", "tag/ai/feed"]
        for path in common_paths:
            test_url = base_url.rstrip("/") + "/" + path
            feed = feedparser.parse(test_url)
            if feed.bozo == 0 and len(feed.entries) > 0:
                return test_url
    except:
        pass
    return None

def parse_rss(feed_url):
    feed = feedparser.parse(feed_url)
    today = datetime.now().date()
    articles = []
    for entry in feed.entries:
        pub_date = None

        if hasattr(entry, 'published_parsed'):
            pub_date = datetime(*entry.published_parsed[:3]).date()
        elif hasattr(entry, 'updated_parsed'):
            pub_date = datetime(*entry.updated_parsed[:3]).date()
        elif hasattr(entry, 'published'):
            try:
                pub_date = date_parser.parse(entry.published).date()
            except:
                continue
        elif hasattr(entry, 'updated'):
            try:
                pub_date = date_parser.parse(entry.updated).date()
            except:
                continue

               if pub_date:
            if pub_date == today:
                ...
            else:
                print(f"Skipped (Not Today): {entry.title} - {pub_date}")
        else:
            print(f"Skipped (No Date): {entry.title}")

            title = getattr(entry, 'title', 'No title')
            link = getattr(entry, 'link', '')
            articles.append([today.strftime("%Y-%m-%d"), feed_url, title[:150], link])
    return articles

def parse_html(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        today = datetime.now()
        date_patterns = [
            today.strftime("%Y/%m/%d"),
            today.strftime("%Y-%m-%d"),
            today.strftime("%Y%m%d")
        ]
        articles = []
        for link in soup.find_all("a", href=True):
            href = link['href']
            text = link.get_text().strip()
            if any(date_pattern in href for date_pattern in date_patterns):
                full_link = href if href.startswith("http") else url.rstrip("/") + "/" + href.lstrip("/")
                articles.append([today.strftime("%Y-%m-%d"), url, text[:150], full_link])
        return articles
    except:
        return []

def update_articles_sheet(sheet, new_articles):
    existing_links = set(cell.value for cell in sheet.col_values(4))
    last_row = len(sheet.get_all_values()) + 2
    today = datetime.now().strftime("%Y-%m-%d")
    sheet.update(f"A{last_row}:D{last_row}", [[""]*4])
    last_row += 1
    for article in new_articles:
        if article[3] not in existing_links:
            sheet.update(f"A{last_row}:D{last_row}", [article])
            last_row += 1

def log_result(log_sheet, website, status, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_sheet.append_row([timestamp, website, status, message])

def main():
    spreadsheet = setup_google_sheets()
    sites_sheet = spreadsheet.worksheet("Sites")
    articles_sheet = spreadsheet.worksheet("Articles")
    log_sheet = spreadsheet.worksheet("Log")
    urls = sites_sheet.col_values(1)[1:]  # Skip header

    for url in urls:
        try:
            rss_url = detect_rss_feed(url)
            articles = []

            if rss_url:
                articles = parse_rss(rss_url)
                method = f"RSS ({rss_url})"
            else:
                articles = parse_html(url)
                method = "HTML fallback"

            if articles:
                update_articles_sheet(articles_sheet, articles)
                log_result(log_sheet, url, "✅ Success", f"{len(articles)} articles via {method}")
            else:
                log_result(log_sheet, url, "⚠️ No new articles", f"No articles found today via {method}")
        except Exception as e:
            log_result(log_sheet, url, "❌ Failure", str(e))

if __name__ == "__main__":
    main()
