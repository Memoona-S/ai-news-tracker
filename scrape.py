import requests
from bs4 import BeautifulSoup
import csv
from urllib.parse import urljoin
from datetime import datetime

headers = {'User-Agent': 'Mozilla/5.0'}
TODAY = datetime.now().strftime('%Y-%m-%d')  # Format: 2023-11-15

def is_today(timestamp_str):
    """Check if article was published today"""
    return timestamp_str and TODAY in timestamp_str

def scrape_articles():
    websites = [
        {
            "name": "Reuters Tech",
            "url": "https://www.reuters.com/technology/artificial-intelligence",
            "link_selector": "a[data-testid='Heading']",
            "date_selector": "time"  # Reuters uses <time> element
        }
    ]
    
    articles = []
    for site in websites:
        try:
            response = requests.get(site["url"], headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all article containers
            articles_html = soup.select('[data-testid="MediaStoryCard"]')  # Reuters specific
            
            for article in articles_html:
                # Extract link
                link = article.select_one(site["link_selector"])
                if not link or not link.has_attr('href'):
                    continue
                
                url = urljoin(site["url"], link['href'])
                
                # Extract date (format varies by site)
                date_element = article.select_one(site["date_selector"])
                pub_date = date_element['datetime'] if date_element else None
                
                # Only keep today's articles
                if is_today(pub_date):
                    articles.append({
                        "site": site["name"],
                        "url": url,
                        "date": pub_date,
                        "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M')
                    })
                    
        except Exception as e:
            print(f"Error scraping {site['name']}: {str(e)}")
    
    return articles

if __name__ == "__main__":
    today_articles = scrape_articles()
    with open('articles.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["site", "url", "date", "scraped_at"])
        writer.writeheader()
        writer.writerows(today_articles)
