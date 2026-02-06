from functools import lru_cache

@lru_cache(maxsize=300)
def cached_response(query: str):
    return None
