"""
Knowledge Updater Script

Automates the process of:
1. Identifying new documents in data/bot3_docs
2. Incrementally updating the FAISS index with new content
3. Re-evaluating previously 'unresolved' queries to see if new info solves them
4. If solved, adds to semantic dataset (QA pairs)

Usage:
    python knowledge_updater.py
"""

import sys
import os
import json
import pandas as pd
import numpy as np
import faiss
import pickle
from datetime import datetime
from typing import List, Dict, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
import logging

# Setup simple console logger for this script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("knowledge_updater")

from core.model_manager import ModelManager
from bots.bot3_rag import (
    load_documents_from_directory, 
    chunk_all_documents, 
    Document, 
    Chunk, 
    INDEX_FILE, 
    METADATA_FILE,
    DATA_DIR
)

logger = get_logger("knowledge_updater")

PROCESSED_FILES_TRACKER = "embeddings/bot3_faiss/processed_files.json"
UNRESOLVED_FILE = "data/unresolved_queries.json"
QA_DATASET_FILE = "data/qa_dataset.csv"

def get_processed_files() -> List[str]:
    if os.path.exists(PROCESSED_FILES_TRACKER):
        with open(PROCESSED_FILES_TRACKER, "r") as f:
            return json.load(f)
    return []

def save_processed_files(files: List[str]):
    os.makedirs(os.path.dirname(PROCESSED_FILES_TRACKER), exist_ok=True)
    with open(PROCESSED_FILES_TRACKER, "w") as f:
        json.dump(files, f, indent=2)

def incremental_index_update():
    """
    Scans for new files and updates FAISS index incrementally.
    """
    logger.info("=== STARTING INCREMENTAL UPDATE ===")
    
    # 1. Identify New Files
    processed = get_processed_files()
    processed_set = set(processed)
    
    all_docs = load_documents_from_directory(DATA_DIR)
    new_docs = [d for d in all_docs if d.source not in processed_set]
    
    if not new_docs:
        logger.info("No new documents found. Index is up to date.")
        return False

    logger.info(f"Found {len(new_docs)} new documents to index.")
    
    # 2. Chunk & Embed New Docs
    new_chunks = chunk_all_documents(new_docs)
    if not new_chunks:
        logger.warning("No chunks created from new documents.")
        return False

    embed_model = ModelManager.get_embedder()
    texts = [c.text for c in new_chunks]
    
    logger.info(f"Embedding {len(texts)} new chunks...")
    embeddings = embed_model.encode(texts, show_progress_bar=True)
    embeddings = embeddings.astype(np.float32)
    
    # 3. Update Index (Load -> Add -> Save)
    index = None
    metadata_list = []
    
    if os.path.exists(INDEX_FILE) and os.path.exists(METADATA_FILE):
        logger.info("Loading existing FAISS index...")
        index = faiss.read_index(INDEX_FILE)
        with open(METADATA_FILE, "rb") as f:
            raw_meta = pickle.load(f)
            # Handle dict vs list wrapper
            if isinstance(raw_meta, dict):
                metadata_list = raw_meta.get("chunks", [])
            else:
                metadata_list = raw_meta
    else:
        logger.info("Creating NEW FAISS index...")
        index = faiss.IndexFlatL2(embeddings.shape[1])
    
    # Add new vectors
    index.add(embeddings)
    
    # Update Metadata
    new_metadata = [
        {
            "text": c.text, 
            "source": c.source, 
            "chunk_id": c.chunk_id,
            "start_char": c.start_char,
            "end_char": c.end_char
        }
        for c in new_chunks
    ]
    metadata_list.extend(new_metadata)
    
    # 4. Persist Changes
    logger.info(f"Saving updated index ({index.ntotal} vectors)...")
    faiss.write_index(index, INDEX_FILE)
    
    with open(METADATA_FILE, "wb") as f:
        pickle.dump({"chunks": metadata_list}, f)
        
    # Update processed tracker logic
    processed.extend([d.source for d in new_docs])
    save_processed_files(processed)
    
    logger.info("=== INDEX UPDATE COMPLETE ===")
    return True

def reevaluate_unresolved_queries():
    """
    Checks unresolved queries against the updated index.
    If a good match is found, promotes it to the QA dataset.
    """
    logger.info("=== RE-EVALUATING UNRESOLVED QUERIES ===")
    
    if not os.path.exists(UNRESOLVED_FILE):
        logger.info("No unresolved queries file found.")
        return

    try:
        with open(UNRESOLVED_FILE, "r", encoding="utf-8") as f:
            unresolved = json.load(f)
    except Exception as e:
        logger.error(f"Error reading unresolved queries: {e}")
        return
        
    if not unresolved:
        logger.info("No queries to re-evaluate.")
        return

    # Load Resources
    embed_model = ModelManager.get_embedder()
    index = faiss.read_index(INDEX_FILE)
    with open(METADATA_FILE, "rb") as f:
        meta_data = pickle.load(f)
        if isinstance(meta_data, dict):
            chunks = meta_data.get("chunks", [])
        else:
            chunks = meta_data
            
    resolved_count = 0
    remaining_queries = []
    new_qa_pairs = []
    
    for query_entry in unresolved:
        q_text = query_entry["query"]
        q_vec = embed_model.encode([q_text]).astype(np.float32)
        
        # Search
        D, I = index.search(q_vec, 1)
        dist = D[0][0]
        idx = I[0][0]
        
        confidence = 1.0 / (1.0 + dist)
        
        # Threshold: Must be very high to auto-promote (e.g., > 0.75)
        # We use a stricter threshold than RAG lookup to ensure quality
        AUTO_RESOLVE_THRESHOLD = 0.75 
        
        if confidence >= AUTO_RESOLVE_THRESHOLD and idx < len(chunks):
            best_chunk = chunks[idx]
            answer_text = best_chunk['text']
            
            logger.info(f"[RESOLVED] '{q_text}' -> Match Score: {confidence:.4f}")
            
            # Add to list for QA Dataset
            new_qa_pairs.append({
                "domain": query_entry.get("category", "General Information"),
                "question": q_text,
                "answer": answer_text,
                "source": "knowledge_updater_auto"
            })
            resolved_count += 1
        else:
            remaining_queries.append(query_entry)
            
    # Update Files
    if new_qa_pairs:
        # Append to QA Dataset
        if os.path.exists(QA_DATASET_FILE):
            df = pd.read_csv(QA_DATASET_FILE)
            new_df = pd.DataFrame(new_qa_pairs)
            df = pd.concat([df, new_df], ignore_index=True)
            df.to_csv(QA_DATASET_FILE, index=False)
        else:
            pd.DataFrame(new_qa_pairs).to_csv(QA_DATASET_FILE, index=False)
            
        logger.info(f"Added {len(new_qa_pairs)} new QA pairs to {QA_DATASET_FILE}")

    # Update Unresolved List
    with open(UNRESOLVED_FILE, "w", encoding="utf-8") as f:
        json.dump(remaining_queries, f, indent=2)
        
    logger.info(f"Re-evaluation Complete. Resolved: {resolved_count}, Remaining: {len(remaining_queries)}")


if __name__ == "__main__":
    # Ensure directories exist
    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(UNRESOLVED_FILE), exist_ok=True)
    
    # 1. Update Index
    updated = incremental_index_update()
    
    # 2. Re-evaluate queries (only if we have an index)
    if os.path.exists(INDEX_FILE):
        reevaluate_unresolved_queries()
    else:
        logger.warning("Skipping re-evaluation: No index found.")
