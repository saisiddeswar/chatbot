"""
Build Bot-3 FAISS index from all documents in data/bot3_docs/
This script:
1. Loads all .txt documents from data/bot3_docs/
2. Chunks them with overlap
3. Creates embeddings
4. Builds FAISS index
5. Saves metadata for retrieval

Run this after adding new documents to data/bot3_docs/
"""

import os
import pickle
from typing import Dict, List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# ============== CONFIGURATION ==============
DATA_DIR = "data/bot3_docs"
INDEX_DIR = "embeddings/bot3_faiss"
INDEX_FILE = os.path.join(INDEX_DIR, "index.faiss")
METADATA_FILE = os.path.join(INDEX_DIR, "metadata.pkl")

CHUNK_SIZE = 500  # characters per chunk
CHUNK_OVERLAP = 100  # character overlap between chunks

# ============== LOAD EMBEDDING MODEL ==============
print("[1/5] Loading embedding model...")
try:
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    print("[OK] Embedding model loaded: all-MiniLM-L6-v2")
except Exception as e:
    print(f"[ERROR] Failed to load embedding model: {e}")
    exit(1)


# ============== CHUNK DOCUMENTS ==============
def chunk_document(text: str, source: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[Dict]:
    """
    Split document into overlapping chunks.
    """
    chunks = []
    start = 0
    chunk_id = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end].strip()
        
        if chunk_text:  # Only add non-empty chunks
            chunks.append({
                "text": chunk_text,
                "source": source,
                "chunk_id": chunk_id,
                "start_char": start,
                "end_char": end,
                "chunk_size": chunk_size
            })
            chunk_id += 1
        
        # Move to next chunk with overlap
        start = end - overlap
        if start <= 0:
            break
    
    return chunks


# ============== LOAD DOCUMENTS ==============
print("[2/5] Loading documents from data/bot3_docs/...")
all_chunks = []

if not os.path.exists(DATA_DIR):
    print(f"[ERROR] Data directory not found: {DATA_DIR}")
    exit(1)

txt_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".txt")]
print(f"Found {len(txt_files)} text files")

for filename in sorted(txt_files):
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                # Chunk the document
                chunks = chunk_document(content, filename)
                all_chunks.extend(chunks)
                print(f"  [OK] {filename}: {len(chunks)} chunks ({len(content)} chars)")
    except Exception as e:
        print(f"  [WARNING] Error loading {filename}: {e}")

print(f"\n[STATS] Total chunks created: {len(all_chunks)}")


# ============== CREATE EMBEDDINGS ==============
print("\n[3/5] Creating embeddings for all chunks...")
chunk_texts = [chunk["text"] for chunk in all_chunks]

try:
    embeddings = embed_model.encode(chunk_texts, show_progress_bar=True, convert_to_numpy=True)
    print(f"[OK] Embeddings created: shape {embeddings.shape}")
except Exception as e:
    print(f"[ERROR] Failed to create embeddings: {e}")
    exit(1)


# ============== BUILD FAISS INDEX ==============
print("\n[4/5] Building FAISS index...")
try:
    # Use L2 (Euclidean) distance
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings.astype(np.float32))
    print(f"[OK] FAISS index built: {index.ntotal} vectors, dimension {dimension}")
except Exception as e:
    print(f"[ERROR] Failed to build FAISS index: {e}")
    exit(1)


# ============== SAVE INDEX AND METADATA ==============
print("\n[5/5] Saving index and metadata...")
try:
    # Create output directory
    os.makedirs(INDEX_DIR, exist_ok=True)
    
    # Save FAISS index
    faiss.write_index(index, INDEX_FILE)
    print(f"[OK] Index saved: {INDEX_FILE}")
    
    # Save metadata
    metadata = {
        "total_chunks": len(all_chunks),
        "chunks": all_chunks,
        "embedding_model": "all-MiniLM-L6-v2",
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "documents": list(set([c["source"] for c in all_chunks]))
    }
    
    with open(METADATA_FILE, "wb") as f:
        pickle.dump(metadata, f)
    print(f"[OK] Metadata saved: {METADATA_FILE}")
    
    print("\n" + "="*60)
    print("🎉 Bot-3 FAISS Index Build Complete!")
    print("="*60)
    print(f"Total Chunks: {len(all_chunks)}")
    print(f"Total Documents: {len(metadata['documents'])}")
    print(f"Documents: {', '.join(metadata['documents'])}")
    print(f"Embedding Dimension: {dimension}")
    print("="*60 + "\n")

except Exception as e:
    print(f"[ERROR] Failed to save index: {e}")
    exit(1)
