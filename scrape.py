import requests
from bs4 import BeautifulSoup
import csv

# List of websites to track
websites = [
    {"name": "Reuters", "url": "https://www.reuters.com/technology"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/"}
]

def scrape_articles():
    articles = []
    for site in websites:
        response = requests.get(site["url"])
        soup = BeautifulSoup(response.text, 'html.parser')
        # Example: Scrape first article link (customize per site)
        link = soup.find('a', class_='article-link')['href']
        articles.append({"site": site["name"], "url": link})
    return articles

if __name__ == "__main__":
    scraped_data = scrape_articles()
    # Save to CSV (GitHub Actions can access this)
    with open('articles.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["site", "url"])
        writer.writeheader()
        writer.writerows(scraped_data)
