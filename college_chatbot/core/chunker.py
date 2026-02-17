
import logging
from typing import List, Dict, Optional
import re

logger = logging.getLogger("chunker")

class Chunk:
    def __init__(self, text: str, source: str, start_char: int, end_char: int, metadata: Dict = None):
        self.text = text
        self.source = source
        self.start_char = start_char
        self.end_char = end_char
        self.metadata = metadata or {}

def chunk_text(text: str, source: str, chunk_size: int = 500, chunk_overlap: int = 50, domain: str = "general") -> List[Chunk]:
    """
    Splits text into chunks of approximately `chunk_size` characters,
    with `chunk_overlap`. Tries to break at sentence boundaries if possible.
    """
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size
        
        # If we are not at the end, try to find a sentence break given overlap window
        if end < text_len:
            # Look for last period/newline in the overlap zone
            # zone is [end - overlap, end]
            search_zone = text[end - chunk_overlap : end]
            last_break = -1
            
            # Simple sentence end detection
            for punct in [". ", "\n", "? ", "! "]:
                idx = search_zone.rfind(punct)
                if idx != -1:
                    last_break = idx + (end - chunk_overlap)
                    break
            
            if last_break != -1:
                end = last_break + 2 # Include punctuation
        
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(Chunk(
                text=chunk_text,
                source=source,
                start_char=start,
                end_char=end, 
                metadata={"domain": domain}
            ))
        
        # Move start forward, considering overlap
        start = end - chunk_overlap
        
        # Safety to prevent infinite loop if overlap >= chunk_size or no progress
        if start >= end:
             start = end
             
    return chunks
