
import json
import os
import time
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional

from core.logger import get_logger

logger = get_logger("query_tracker")

UNRESOLVED_FILE = "data/unresolved_queries.json"
FILE_LOCK = Lock()

def log_unresolved_query(
    query: str,
    category: str,
    semantic_score: float,
    rag_confidence: float,
    timestamp: Optional[str] = None
):
    """
    Log a query that failed to get a confident answer from any bot.
    Used for future knowledge augmentation.
    """
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat()
        
    entry = {
        "query": query,
        "category": category,
        "semantic_score": round(semantic_score, 4),
        "rag_confidence": round(rag_confidence, 4),
        "timestamp": timestamp,
        "status": "unresolved"
    }
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(UNRESOLVED_FILE), exist_ok=True)
    
    with FILE_LOCK:
        try:
            data = []
            if os.path.exists(UNRESOLVED_FILE):
                try:
                    with open(UNRESOLVED_FILE, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            data = json.loads(content)
                except json.JSONDecodeError:
                    logger.warning(f"Corrupt unresolved queries file found. Resetting.")
            
            # Check for duplicates (simple string match)
            if not any(d['query'] == query for d in data):
                data.append(entry)
                
                with open(UNRESOLVED_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                
                logger.info(f"Logged unresolved query: '{query}'")
            else:
                logger.info(f"Ignored duplicate unresolved query: '{query}'")
                
        except Exception as e:
            logger.error(f"Failed to log unresolved query: {e}")
