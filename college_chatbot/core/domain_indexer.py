
import os
import faiss
import pickle
import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List

from core.logger import get_logger
from core.model_manager import ModelManager

import sys
# Setup console logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger("domain_indexer")

DOMAIN_DIR = "data/domains"
INDEX_BASE_DIR = "embeddings/domains"

def build_domain_qa_indices():
    """
    Iterates through each domain folder, reads qa.csv,
    embeddings questions (and paraphrases), and saves separate FAISS indices.
    """
    logger.info("=== Starting Domain-Specific QA Indexing ===")
    
    if not os.path.exists(DOMAIN_DIR):
        logger.error(f"Domain directory not found: {DOMAIN_DIR}")
        return

    embedder = ModelManager.get_embedder()
    
    for domain_name in os.listdir(DOMAIN_DIR):
        domain_path = os.path.join(DOMAIN_DIR, domain_name)
        if not os.path.isdir(domain_path):
            continue
            
        qa_file = os.path.join(domain_path, "qa.csv")
        if not os.path.exists(qa_file):
            logger.warning(f"No qa.csv found for domain '{domain_name}'")
            continue
            
        logger.info(f"Processing domain: {domain_name}")
        
        try:
            df = pd.read_csv(qa_file)
            questions = df["question"].tolist()
            # We also need to store metadata to retrieve answers
            metadata = df.to_dict("records")
            
            if not questions:
                logger.warning(f"Empty questions for {domain_name}")
                continue
                
            # Embed
            logger.info(f"Embedding {len(questions)} items for {domain_name}...")
            embeddings = embedder.encode(questions, show_progress_bar=False)
            embeddings = embeddings.astype(np.float32)
            
            # Create Index
            d = embeddings.shape[1]
            index = faiss.IndexFlatL2(d)
            index.add(embeddings)
            
            # Save
            save_dir = os.path.join(INDEX_BASE_DIR, domain_name)
            os.makedirs(save_dir, exist_ok=True)
            
            index_path = os.path.join(save_dir, "qa_index.faiss")
            meta_path = os.path.join(save_dir, "qa_metadata.pkl")
            
            faiss.write_index(index, index_path)
            with open(meta_path, "wb") as f:
                pickle.dump(metadata, f)
                
            logger.info(f"Saved index and metadata for {domain_name} ({index.ntotal} vectors)")
            
        except Exception as e:
            logger.error(f"Error indexing domain {domain_name}: {e}")

if __name__ == "__main__":
    build_domain_qa_indices()
