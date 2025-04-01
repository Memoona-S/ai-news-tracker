import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
from urllib.parse import urljoin

# Configure for Reuters AI section
TODAY = datetime.now().strftime('%Y-%m-%d')
HEADERS = {'User-Agent': 'Mozilla/5.0'}
URL = "https://www.reuters.com/technology/artificial-intelligence/"

def scrape_reuters_ai():
    articles = []
    try:
        response = requests.get(URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all article cards on the page
        for article in soup.select('[data-testid="MediaStoryCard"]'):
            # Extract URL
            link = article.select_one('a[data-testid="Heading"]')
            if not link or not link.get('href'):
                continue
            
            full_url = urljoin(URL, link['href'])
            
            # Extract publish date (from <time> tag)
            time_tag = article.select_one('time')
            if not time_tag or not time_tag.get('datetime'):
                continue
                
            pub_date = time_tag['datetime'].split('T')[0]  # Get YYYY-MM-DD
            
            # Only keep today's articles
            if pub_date == TODAY:
                articles.append({
                    "title": link.get_text(strip=True),
                    "url": full_url,
                    "date": pub_date,
                    "scraped_at": datetime.now().isoformat()
                })
                
    except Exception as e:
        print(f"Error: {str(e)}")
    
    return articles

# Test immediately
if __name__ == "__main__":
    print(f"Scraping Reuters AI articles for {TODAY}...")
    articles = scrape_reuters_ai()
    
    if articles:
        print(f"Found {len(articles)} new articles:")
        for article in articles:
            print(f"- {article['title']}\n  {article['url']}")
        
        # Save to CSV
        with open('reuters_ai_today.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["title", "url", "date", "scraped_at"])
            writer.writeheader()
            writer.writerows(articles)
    else:
        print("No new articles found today.")
