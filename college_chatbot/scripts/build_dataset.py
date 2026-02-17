
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import json
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RVRJC_Crawler")

BASE_URL = "https://rvrjcce.ac.in/"
ALLOWED_DOMAIN = "rvrjcce.ac.in"
DATA_DIR = os.path.join("data", "bot3_docs")
os.makedirs(DATA_DIR, exist_ok=True)

# Important sections user asked for
TARGET_SECTIONS = {
    "about": "aboutus.php",
    "contact": "contactus.php",
    "admissions": "admission.php",
    "academics": "academics.php",
    "placements": "placement.php",
    "exam_cell": "examination.php",
    "library": "library.php",
    "transport": "transport.php",
    "hostel": "hostel.php"
}

def clean_text(text):
    """Remove extra whitespace and noise."""
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    cleaned = '\n'.join(chunk for chunk in chunks if chunk)
    return cleaned

def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme) and ALLOWED_DOMAIN in parsed.netloc

def crawl_and_save():
    """Crawls prioritized pages and saves structured text."""
    logger.info("Starting targeted crawl of RVR&JC College website...")
    
    unique_links = set()
    
    # 1. First Pass: Targeted Sections
    for section_name, path in TARGET_SECTIONS.items():
        url = urljoin(BASE_URL, path)
        unique_links.add(url)
        
        try:
            logger.info(f"Crawling: {url}")
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {url}: {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove scripts and styles
            for script in soup(["script", "style", "nav", "footer"]):
                script.decompose()
                
            # Extract main content (Heuristic based on RVRJC structure)
            # Usually in a container or main div. Fallback to body.
            main_content = soup.find('div', class_='content') or soup.find('div', class_='main') or soup.body
            
            if main_content:
                text = clean_text(main_content.get_text())
                if len(text) < 100:
                    text = clean_text(soup.body.get_text())
            else:
                 text = clean_text(soup.get_text())

            # Save to file
            filename = f"rvrjc_{section_name}_{int(time.time())}.txt"
            filepath = os.path.join(DATA_DIR, filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"Source: {url}\n")
                f.write(f"Section: {section_name.upper()}\n")
                f.write("-" * 50 + "\n")
                f.write(text)
                
            logger.info(f"Saved {len(text)} chars to {filename}")
            
            # Find more relevant links in this page
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(url, href)
                if is_valid_url(full_url) and full_url not in unique_links:
                     # Only add specific deep links (e.g., pdfs or sub-pages)
                     if "pdf" in full_url or "php" in full_url:
                         unique_links.add(full_url)

        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            
    logger.info("Crawl completed. Data stored in data/bot3_docs/")

if __name__ == "__main__":
    crawl_and_save()
