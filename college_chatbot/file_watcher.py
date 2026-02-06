import os
import pickle
import time

import faiss
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# ---------------- CONFIG ----------------
DATA_DIR = "data/bot3_docs"
INDEX_DIR = "embeddings/bot3_faiss"

INDEX_FILE = os.path.join(INDEX_DIR, "index.faiss")
TEXT_FILE = os.path.join(INDEX_DIR, "texts.pkl")
TRACK_FILE = os.path.join(INDEX_DIR, "indexed_files.pkl")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)

# ---------------- LOAD EMBEDDING MODEL ----------------
print("[WAIT] Loading embedding model...")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
print("[OK] Embedding model loaded")

# ---------------- LOAD OR CREATE FAISS ----------------
if os.path.exists(INDEX_FILE) and os.path.exists(TEXT_FILE):
    print("[LOAD] Loading existing FAISS index...")
    index = faiss.read_index(INDEX_FILE)
    with open(TEXT_FILE, "rb") as f:
        stored_texts = pickle.load(f)
else:
    print("[CREATE] Creating new FAISS index")
    index = faiss.IndexFlatL2(384)
    stored_texts = []

# ---------------- LOAD OR CREATE FILE REGISTRY ----------------
if os.path.exists(TRACK_FILE):
    with open(TRACK_FILE, "rb") as f:
        indexed_files = pickle.load(f)
else:
    indexed_files = set()

# ---------------- HELPERS ----------------
def read_document(path):
    if path.endswith(".pdf"):
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text
    else:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

def chunk_text(text, chunk_size=200):
    words = text.split()
    return [
        " ".join(words[i:i + chunk_size])
        for i in range(0, len(words), chunk_size)
    ]

def index_document(file_path):
    global index, stored_texts, indexed_files

    filename = os.path.basename(file_path)

    # [CHECK] SAFE CHECK (NO DUPLICATES)
    if filename in indexed_files:
        print(f"[SKIP] Skipping already indexed file: {filename}")
        return

    print(f"[INDEX] Indexing file: {filename}")

    text = read_document(file_path)
    if not text.strip():
        print("[WARNING] Empty document, skipped")
        return

    chunks = chunk_text(text)
    print(f"[CHUNKS] {filename} → {len(chunks)} chunks")

    embeddings = embed_model.encode(chunks)

    index.add(embeddings)
    stored_texts.extend(chunks)

    indexed_files.add(filename)

    # [SAVE] SAVE EVERYTHING
    faiss.write_index(index, INDEX_FILE)

    with open(TEXT_FILE, "wb") as f:
        pickle.dump(stored_texts, f)

    with open(TRACK_FILE, "wb") as f:
        pickle.dump(indexed_files, f)

    print(f"[OK] FAISS updated | Total vectors: {index.ntotal}")

# ---------------- INITIAL BULK INDEX ----------------
def index_existing_files():
    print("📂 Checking existing files...")
    for filename in os.listdir(DATA_DIR):
        file_path = os.path.join(DATA_DIR, filename)
        if os.path.isfile(file_path) and filename.endswith((".txt", ".pdf")):
            index_document(file_path)

# ---------------- WATCHER ----------------
class DocumentHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith((".pdf", ".txt")):
            index_document(event.src_path)

# ---------------- MAIN ----------------
if __name__ == "__main__":

    # 🔥 SAFE INITIAL INDEXING
    index_existing_files()

    observer = Observer()
    observer.schedule(DocumentHandler(), DATA_DIR, recursive=False)
    observer.start()

    print("👀 Watching folder:", DATA_DIR)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
