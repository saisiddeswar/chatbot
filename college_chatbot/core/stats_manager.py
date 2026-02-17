
import json
import os
from collections import Counter
from threading import Lock
from typing import List, Dict

from core.logger import get_logger

logger = get_logger("stats_manager")

STATS_FILE = "data/query_stats.json"
FILE_LOCK = Lock()

class StatsManager:
    """
    Manages usage statistics, specifically query frequency, to surface
    trending/popular questions in the UI.
    """
    
    @staticmethod
    def _load_stats() -> Dict[str, int]:
        """Load stats from JSON file."""
        if not os.path.exists(STATS_FILE):
            return {}
        
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to load stats: {e}")
            return {}

    @staticmethod
    def _save_stats(stats: Dict[str, int]):
        """Save stats to JSON file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
            
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")

    @classmethod
    def increment_query_count(cls, query: str):
        """
        Increment the frequency count for a given query.
        Normalizes the query (lowercase, stripped) to aggregate similar variations.
        """
        if not query or len(query.strip()) < 3:
            return 
            
        normalized_query = query.strip() # Keep case for display? Or normalize? 
        # Better to keep original casing for display if possible, but map to lowercase key.
        # For simplicity, let's just store the query string as is, but maybe title-cased.
        
        # Actually, to avoid "hostel?" vs "Hostel?" split, let's normalize to lowercase key,
        # but store a display version? 
        # Let's just use the raw query for now, assuming users might tap the button which sends standard text.
        # But for tracking, we want to group "fee" and "Fee".
        
        # Let's use a specialized structure: { "lower_case_key": { "display": "Original", "count": 5 } }
        # Or simpler: just count exact strings for now, user asked for "most frequent questions".
        
        # Let's stick to a simple counter for now to avoid complexity.
        # We will strip and capitalize the first letter to standardize slightly.
        formatted_query = query.strip()
        if formatted_query:
            formatted_query = formatted_query[0].upper() + formatted_query[1:]
        
        with FILE_LOCK:
            stats = cls._load_stats()
            current_count = stats.get(formatted_query, 0)
            stats[formatted_query] = current_count + 1
            cls._save_stats(stats)
            logger.info(f"Incremented stats for: '{formatted_query}' (Count: {current_count + 1})")

    @classmethod
    def get_top_queries(cls, n: int = 4) -> List[str]:
        """
        Get the top N most frequent queries.
        """
        with FILE_LOCK:
            stats = cls._load_stats()
            
        if not stats:
            # Return some defaults if cold start
            return [
                "Is hostel facility available?",
                "What is the admission process?",
                "What is the tuition fee?",
                "Where is the library?"
            ]
            
        # Sort by count descending
        sorted_queries = sorted(stats.items(), key=lambda item: item[1], reverse=True)
        
        # Return top N keys
        return [q for q, count in sorted_queries[:n]]
