"""
Setup script to build all bot indices after adding new data

This script:
1. Builds Bot-2 FAISS index from Q&A datasets
2. Builds Bot-3 FAISS index from documents
3. Verifies all indices are properly loaded

Run this script after:
- Adding new AIML files to data/aiml/
- Adding new Q&A pairs to data/bot2_qa/
- Adding new documents to data/bot3_docs/
"""

import os
import sys

print("="*70)
print("[SETUP] RVRJCCE Chatbot - Index Setup Script")
print("="*70)

# Change to project directory
project_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_dir)

# Global imports
import pickle
import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

# Load embedding model ONCE
print("\n[INIT] Loading shared embedding model...")
try:
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    print("  [OK] Embedding model loaded: all-MiniLM-L6-v2")
except Exception as e:
    print(f"  [ERROR] Failed to load embedding model: {e}")
    sys.exit(1)

# ============== BUILD BOT-2 INDEX ==============
print("\n[Step 1/3] Building Bot-2 (Semantic QA) FAISS Index...")
print("-" * 70)

try:
    qa_files = [
        "data/bot2_qa/qa_dataset.csv",
        "data/bot2_qa/rvrjcce_qa_dataset.csv"
    ]
    
    all_questions = []
    all_answers = []
    
    for qa_file in qa_files:
        if os.path.exists(qa_file):
            df = pd.read_csv(qa_file)
            all_questions.extend(df["Question"].tolist())
            all_answers.extend(df["Answers"].tolist())
            print(f"  [OK] Loaded {qa_file}: {len(df)} Q&A pairs")
        else:
            print(f"  [WARNING] Q&A file not found: {qa_file}")
    
    print(f"\n  [STATS] Total Q&A pairs: {len(all_questions)}")
    
    if all_questions:
        # Create embeddings
        print("  [WAIT] Creating embeddings...")
        vectors = embed_model.encode(all_questions, show_progress_bar=True)
        print(f"  [OK] Embeddings created: shape {vectors.shape}")
        
        # Build FAISS index
        print("  [WAIT] Building FAISS index...")
        index = faiss.IndexFlatL2(vectors.shape[1])
        index.add(vectors.astype(np.float32))
        print(f"  [OK] FAISS index built: {index.ntotal} vectors")
        
        # Save index and QA pairs
        os.makedirs("embeddings/bot2_faiss", exist_ok=True)
        faiss.write_index(index, "embeddings/bot2_faiss/index.faiss")
        
        qa_data = [
            {"question": q, "answer": a} 
            for q, a in zip(all_questions, all_answers)
        ]
        
        with open("embeddings/bot2_faiss/qa.pkl", "wb") as f:
            pickle.dump(qa_data, f)
        
        print("  [OK] Bot-2 index saved successfully")
    else:
        print("  [WARNING] No Q&A pairs found, skipping Bot-2 index build.")
    
except Exception as e:
    print(f"\n  [ERROR] Error building Bot-2 index: {e}")
    sys.exit(1)


# ============== BUILD BOT-3 INDEX ==============
print("\n[Step 2/3] Building Bot-3 (RAG) FAISS Index...")
print("-" * 70)

try:
    # Configuration
    DATA_DIR = "data/bot3_docs"
    INDEX_DIR = "embeddings/bot3_faiss"
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 100
    
    # Chunk documents
    def chunk_document(text, source, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "source": source,
                    "chunk_id": chunk_id,
                    "start_char": start,
                    "end_char": end,
                    "chunk_size": chunk_size
                })
                chunk_id += 1
            
            start = end - overlap
            if start <= 0:
                break
        
        return chunks
    
    # Load documents
    print("  [WAIT] Loading documents...")
    all_chunks = []
    
    if os.path.exists(DATA_DIR):
        txt_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".txt")])
        print(f"     Found {len(txt_files)} text files")
        
        for filename in txt_files:
            filepath = os.path.join(DATA_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        chunks = chunk_document(content, filename)
                        all_chunks.extend(chunks)
                        print(f"     [OK] {filename}: {len(chunks)} chunks")
            except Exception as e:
                print(f"     [WARNING] Error loading {filename}: {e}")
    else:
        print(f"  [WARNING] Data directory not found: {DATA_DIR}")
    
    print(f"\n  [STATS] Total chunks: {len(all_chunks)}")
    
    if all_chunks:
        # Create embeddings
        print("  [WAIT] Creating embeddings...")
        chunk_texts = [chunk["text"] for chunk in all_chunks]
        embeddings = embed_model.encode(chunk_texts, show_progress_bar=True, convert_to_numpy=True)
        print(f"  [OK] Embeddings created: shape {embeddings.shape}")
        
        # Build FAISS index
        print("  [WAIT] Building FAISS index...")
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings.astype(np.float32))
        print(f"  [OK] FAISS index built: {index.ntotal} vectors")
        
        # Save index and metadata
        print("  [WAIT] Saving index and metadata...")
        os.makedirs(INDEX_DIR, exist_ok=True)
        
        faiss.write_index(index, os.path.join(INDEX_DIR, "index.faiss"))
        
        metadata = {
            "total_chunks": len(all_chunks),
            "chunks": all_chunks,
            "embedding_model": "all-MiniLM-L6-v2",
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
            "documents": list(set([c["source"] for c in all_chunks]))
        }
        
        with open(os.path.join(INDEX_DIR, "metadata.pkl"), "wb") as f:
            pickle.dump(metadata, f)
        
        print("  [OK] Bot-3 index saved successfully")
    else:
        print("  [WARNING] No chunks found, skipping Bot-3 index build.")

except Exception as e:
    print(f"\n  [ERROR] Error building Bot-3 index: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


# ============== VERIFY INDICES ==============
print("\n[Step 3/3] Verifying Indices...")
print("-" * 70)

try:
    # Verify Bot-2
    print("  [WAIT] Verifying Bot-2 index...")
    if os.path.exists("embeddings/bot2_faiss/index.faiss"):
        bot2_index = faiss.read_index("embeddings/bot2_faiss/index.faiss")
        with open("embeddings/bot2_faiss/qa.pkl", "rb") as f:
            bot2_qa = pickle.load(f)
        print(f"  [OK] Bot-2 index verified: {bot2_index.ntotal} vectors, {len(bot2_qa)} Q&A pairs")
    else:
        print("  [WARN] Bot-2 index not found.")
    
    # Verify Bot-3
    print("  [WAIT] Verifying Bot-3 index...")
    if os.path.exists("embeddings/bot3_faiss/index.faiss"):
        bot3_index = faiss.read_index("embeddings/bot3_faiss/index.faiss")
        with open("embeddings/bot3_faiss/metadata.pkl", "rb") as f:
            bot3_meta = pickle.load(f)
        print(f"  [OK] Bot-3 index verified: {bot3_index.ntotal} vectors, {bot3_meta['total_chunks']} chunks")
    else:
        print("  [WARN] Bot-3 index not found.")
    
    print("\n" + "="*70)
    print("[OK] SETUP COMPLETED!")
    print("="*70)

except Exception as e:
    print(f"\n  [ERROR] Error verifying indices: {e}")
    sys.exit(1)
