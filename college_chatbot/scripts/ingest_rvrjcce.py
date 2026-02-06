from services.web_ingest import ingest_url

URLS = [
    "https://rvrjcce.ac.in/",
    "https://rvrjcce.ac.in/message.php",
    "https://rvrjcce.ac.in/contactus.php",
    "https://rvrjcce.ac.in/principal.php",
]

for u in URLS:
    fp = ingest_url(u)
    print("Saved:", fp)
