from services.pdf_downloader import extract_pdf_links, download_pdf

PAGES = [
    "https://rvrjcce.ac.in/",
    "https://rvrjcce.ac.in/contactus.php",
]

for page in PAGES:
    pdfs = extract_pdf_links(page)
    print(f"\nPage: {page}")
    print("PDF links found:", len(pdfs))

    for pdf_url in pdfs[:10]:   # limit for safety
        fp = download_pdf(pdf_url)
        print("Downloaded:", fp)
