import os
import requests
from bs4 import BeautifulSoup

def fetch_page_text(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    # remove noise
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def ingest_url(url: str, out_dir="data/bot3_docs/website"):
    os.makedirs(out_dir, exist_ok=True)

    safe_name = url.replace("https://", "").replace("http://", "")
    safe_name = safe_name.replace("/", "_").replace("?", "_").replace("&", "_")

    file_path = os.path.join(out_dir, f"{safe_name}.txt")

    text = fetch_page_text(url)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"Source URL: {url}\n\n")
        f.write(text)

    return file_path
