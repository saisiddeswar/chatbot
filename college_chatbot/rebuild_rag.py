
import os
import pickle
import faiss
import numpy as np
import traceback
from sentence_transformers import SentenceTransformer

# Setup logging to file
log_file = open("rebuild_rag_2.log", "w")

def log(msg):
    print(msg)
    log_file.write(msg + "\n")
    log_file.flush()

try:
    # Paths - ADAPTED FOR RUNNING INSIDE PACKAGE
    # __file__ is inside college_chatbot/
    BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
    DATA_DIR = os.path.join(BASE_DIR, "data", "bot3_docs")
    OUT_DIR = os.path.join(BASE_DIR, "embeddings", "bot3_faiss")

    log(f"Data Dir: {DATA_DIR}")
    log(f"Out Dir: {OUT_DIR}")

    os.makedirs(OUT_DIR, exist_ok=True)

    # 1. Load Model
    log("Loading Embedding Model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # 2. Read Documents
    log("Reading Documents...")
    documents = []
    if os.path.exists(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            if f.endswith(".txt"):
                path = os.path.join(DATA_DIR, f)
                try:
                    with open(path, "r", encoding="utf-8") as file:
                        text = file.read()
                        if text.strip():
                            documents.append({"source": f, "text": text})
                            log(f"  - Loaded {f} ({len(text)} chars)")
                except Exception as e:
                    log(f"  ! Error reading {f}: {e}")
    else:
        log("! Data directory missing")

    log(f"Loaded {len(documents)} documents.")

    # 3. Chunking
    log("Chunking...")
    chunks = []
    chunk_id = 0
    CHUNK_SIZE = 500
    OVERLAP = 100

    for doc in documents:
        text = doc["text"]
        source = doc["source"]
        
        start = 0
        while start < len(text):
            end = min(start + CHUNK_SIZE, len(text))
            chunk_text = text[start:end].strip()
            
            if len(chunk_text) > 50: # Skip very small chunks
                chunks.append({
                    "text": chunk_text,
                    "source": source,
                    "chunk_id": chunk_id,
                    "start_char": start,
                    "end_char": end
                })
                chunk_id += 1
            
            start += (CHUNK_SIZE - OVERLAP)

    log(f"Created {len(chunks)} chunks.")

    if not chunks:
        log("! No chunks to index. Exiting.")
        exit(1)

    # 4. Embeddings
    log("Generating Embeddings...")
    full_texts = [c["text"] for c in chunks]
    embeddings = model.encode(full_texts, show_progress_bar=True)
    log(f"Embeddings shape: {embeddings.shape}")

    # 5. Build Index
    log("Building FAISS Index...")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings.astype(np.float32))
    log(f"Index contains {index.ntotal} vectors.")

    # 6. Save
    log("Saving Files...")
    index_path = os.path.join(OUT_DIR, "index.faiss")
    meta_path = os.path.join(OUT_DIR, "metadata.pkl")

    faiss.write_index(index, index_path)
    log(f"  - Saved index to {index_path}")

    metadata = {
        "chunks": chunks,
        "total": len(chunks)
    }
    with open(meta_path, "wb") as f:
        pickle.dump(metadata, f)
    log(f"  - Saved metadata to {meta_path}")

    log("DONE.")

except Exception as e:
    log(f"CRITICAL ERROR: {e}")
    traceback.print_exc(file=log_file)

finally:
    log_file.close()
