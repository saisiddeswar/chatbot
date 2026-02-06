import uuid
import time

def create_context(query: str):
    return {
        "query_id": str(uuid.uuid4())[:8],
        "query": query,
        "start_time": time.time(),   # IMPORTANT
        "validation": None,
        "scope": None,
        "route": None,
        "conf": None,
        "bot_used": None,
        "latency_ms": None,
        "error": None,
    }
