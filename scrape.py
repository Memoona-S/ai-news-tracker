import requests
from bs4 import BeautifulSoup
import pandas as pd
import dateparser
from datetime import datetime, timedelta
import re

# ========== CORE ENGINE ==========
def is_today(text, url):
    """Smart date detection using AI-like parsing"""
    now = datetime.now()
    
    # Strategy 1: Look for dates in text/URL
    text = text.lower() + " " + url.lower()
    today_patterns = [
        r'\b(today)\b',
        r'\b(\d{1,2} hours? ago)\b',
        datetime.now().strftime(r'%b %-d, %Y').lower(),
        datetime.now().strftime(r'%-m/%-d/%Y')
    ]
    
    if any(re.search(p, text) for p in today_patterns):
        return True
    
    # Strategy 2: Parse with dateparser
    parsed_date = dateparser.parse(text, settings={'RELATIVE_BASE': now})
    if parsed_date and (now - parsed_date) < timedelta(hours=36):
        return True
    
    return False

def scrape_site(url):
    """Universal scraper for news articles"""
    try:
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36'
        }, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all potential article links
        articles = []
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            href = link['href']
            
            if not text or len(text) < 20:  # Filter non-articles
                continue
                
            full_url = requests.compat.urljoin(url, href)
            
            # Check date in text/URL
            if is_today(text + " " + full_url, full_url):
                articles.append({
                    'title': text,
                    'url': full_url,
                    'source': url
                })
        
        return articles
    
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return []

# ========== EXECUTION ==========
if __name__ == "__main__":
    # Add your URLs here
    SITES = [
        "https://www.reuters.com/technology/artificial-intelligence/"    ]
    
    all_articles = []
    for site in SITES:
        print(f"Checking {site}...")
        articles = scrape_site(site)
        all_articles.extend(articles)
    
    # Save to Excel
    if all_articles:
        df = pd.DataFrame(all_articles)
        df = df.drop_duplicates(subset=['url'])
        df.to_excel("Today's Articles.xlsx", index=False)
        print(f"Saved {len(df)} articles to 'Today's Articles.xlsx'")
    else:
        print("No new articles found today")
