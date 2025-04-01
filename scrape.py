import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime, timedelta
import re

HEADERS = {'User-Agent': 'Mozilla/5.0'}
URL = "https://www.reuters.com/technology/artificial-intelligence/"

def parse_reuters_time(time_str):
    """Convert relative times ('an hour ago') and 'X:XX PM GMT+5' to datetime"""
    now = datetime.now()
    
    if 'hour ago' in time_str:
        return now - timedelta(hours=1)
    elif 'minute ago' in time_str:
        mins = int(re.search(r'(\d+) minute', time_str).group(1))
        return now - timedelta(minutes=mins)
    elif 'PM' in time_str or 'AM' in time_str:
        # Format like "7:51 PM GMT+5" → assume today
        time_part = re.search(r'(\d+:\d+ [AP]M)', time_str).group(1)
        return datetime.strptime(time_part, '%I:%M %p').replace(
            year=now.year, 
            month=now.month,
            day=now.day
        )
    return None

def scrape_reuters_ai():
    articles = []
    try:
        response = requests.get(URL, headers=HEADERS)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for article in soup.select('[data-testid="MediaStoryCard"]'):
            # Extract URL
            link = article.select_one('a[data-testid="Heading"]')
            if not link or not link.get('href'):
                continue
            full_url = urljoin(URL, link['href'])
            
            # Extract timestamp text
            time_tag = article.select_one('span[class*="timestamp"]')
            if not time_tag:
                continue
                
            pub_time = parse_reuters_time(time_tag.get_text(strip=True))
            if not pub_time:
                continue
                
            # Only keep today's articles
            if pub_time.date() == datetime.now().date():
                articles.append({
                    "title": link.get_text(strip=True),
                    "url": full_url,
                    "time": pub_time.strftime('%Y-%m-%d %H:%M'),
                    "scraped_at": datetime.now().strftime('%Y-%m-%d %H:%M')
                })
                
    except Exception as e:
        print(f"Error: {str(e)}")
    
    return articles

if __name__ == "__main__":
    print("Scraping Reuters AI news...")
    articles = scrape_reuters_ai()
    
    if articles:
        print(f"Found {len(articles)} new articles:")
        for article in articles:
            print(f"- {article['time']}: {article['title']}\n  {article['url']}")
        
        with open('reuters_ai_today.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["title", "url", "time", "scraped_at"])
            writer.writeheader()
            writer.writerows(articles)
    else:
        print("No new articles found today.")
