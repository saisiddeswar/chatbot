import os
import requests
from bs4 import BeautifulSoup
import time

URLS = [
    "https://rvrjcce.ac.in/",
    "https://rvrjcce.ac.in/academic_calendar.php",
    "https://rvrjcce.ac.in/fee_structure.php",
    "https://rvrjcce.ac.in/computer_science_engineering/",
    "https://rvrjcce.ac.in/placement_statistics.php"
]

OUT_DIR = "data/bot3_docs/website_quick"
os.makedirs(OUT_DIR, exist_ok=True)

with open("quick_ingest_log.txt", "w") as log:
    log.write("Starting...\n")
    print("Starting...")
    
    for url in URLS:
        try:
            print(f"Fetching {url}")
            log.write(f"Fetching {url}\n")
            
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers, timeout=10)
            
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                text = soup.get_text(separator="\n")
                clean_text = "\n".join([l.strip() for l in text.splitlines() if l.strip()])
                
                safe_name = url.replace("https://", "").replace("/", "_") + ".txt"
                fp = os.path.join(OUT_DIR, safe_name)
                
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(f"Source: {url}\n\n{clean_text}")
                    
                print(f"Saved {fp}")
                log.write(f"Saved {fp}\n")
            else:
                print(f"Failed {url}: {r.status_code}")
                log.write(f"Failed {url}: {r.status_code}\n")
                
        except Exception as e:
            print(f"Error {url}: {e}")
            log.write(f"Error {url}: {e}\n")

    log.write("Done.\n")
    print("Done.")
