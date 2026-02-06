import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def extract_pdf_links(page_url: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(page_url, headers=headers, timeout=20)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")
    links = soup.find_all("a", href=True)

    pdf_urls = []
    for a in links:
        href = a["href"].strip()
        if ".pdf" in href.lower():
            pdf_urls.append(urljoin(page_url, href))

    # remove duplicates
    return list(dict.fromkeys(pdf_urls))


def download_pdf(pdf_url: str, out_dir="data/bot3_docs/pdfs"):
    os.makedirs(out_dir, exist_ok=True)

    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(pdf_url, headers=headers, timeout=30)
    r.raise_for_status()

    # extract filename
    path = urlparse(pdf_url).path
    fname = os.path.basename(path)
    if not fname.lower().endswith(".pdf"):
        fname = re.sub(r"[^a-zA-Z0-9_]+", "_", fname) + ".pdf"

    file_path = os.path.join(out_dir, fname)

    with open(file_path, "wb") as f:
        f.write(r.content)

    return file_path
