
import os
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

print("Starting quick repair for Bot 3...")

# Config
DATA_DIR = "college_chatbot/data/bot3_docs"
INDEX_DIR = "college_chatbot/embeddings/bot3_faiss"
os.makedirs(INDEX_DIR, exist_ok=True)

# 1. Load Model
print("Loading model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# 2. Load Docs
print("Loading docs...")
documents = []
if os.path.exists(DATA_DIR):
    for f in os.listdir(DATA_DIR):
        if f.endswith(".txt"):
            path = os.path.join(DATA_DIR, f)
            with open(path, "r", encoding="utf-8") as file:
                documents.append({"source": f, "text": file.read()})
print(f"Loaded {len(documents)} docs")

# 3. Chunk
print("Chunking...")
chunks = []
chunk_id = 0
for doc in documents:
    text = doc["text"]
    for i in range(0, len(text), 400): # Simple chunking
        chunk_text = text[i:i+500]
        if len(chunk_text) > 20: 
            chunks.append({
                "text": chunk_text,
                "source": doc["source"],
                "chunk_id": chunk_id,
                "start_char": i,
                "end_char": i+len(chunk_text)
            })
            chunk_id += 1
print(f"Created {len(chunks)} chunks")

if not chunks:
    print("No chunks created! Check data dir.")
    exit(1)

# 4. Embed
print("Embedding...")
embeddings = model.encode([c["text"] for c in chunks], show_progress_bar=True)

# 5. Index
print("indexing...")
index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings.astype(np.float32))

# 6. Save
print("Saving...")
faiss.write_index(index, os.path.join(INDEX_DIR, "index.faiss"))

metadata = {
    "chunks": chunks,
    "documents": [d["source"] for d in documents]
}
with open(os.path.join(INDEX_DIR, "metadata.pkl"), "wb") as f:
    pickle.dump(metadata, f)

print("DONE. metadata.pkl created.")
