from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuration for College Administrative Chatbot System.
    
    Thresholds are critical to prevent hallucination and ensure quality answers.
    """
    
    # ============ BOT-2: SEMANTIC QA ============
    # Number of top-k similar documents to retrieve
    TOP_K_BOT2: int = 3
    
    # Cosine similarity threshold for Bot-2
    # If similarity < threshold, fallback to Bot-3 (RAG)
    BOT2_SIMILARITY_THRESHOLD: float = 0.65
    
    # Minimum similarity to return answer from Bot-2
    # Below this, we say "No information found"
    BOT2_MIN_SIMILARITY: float = 0.45
    
    # ============ BOT-3: RAG ============
    # Number of top-k documents to retrieve
    TOP_K_BOT3: int = 5
    
    # FAISS retrieval threshold (L2 distance)
    # Lower is better match. If distance > threshold, low confidence
    BOT3_RETRIEVAL_THRESHOLD: float = 1.5
    
    # Minimum retrieval confidence to generate answer
    # Below this, return "No official information found"
    BOT3_MIN_CONFIDENCE: float = 0.5
    
    # ============ CLASSIFIER ROUTING ============
    # High confidence threshold for confident routing
    CLASSIFIER_HIGH_CONF: float = 0.75
    
    # Mid confidence threshold
    # Between MID and HIGH → route based on category
    # Below MID → fallback to Bot-3 (RAG)
    CLASSIFIER_MID_CONF: float = 0.45
    
    # Low confidence fallback strategy:
    # If confidence < MID_CONF, always use Bot-3
    
    # ============ CONTEXT MANAGEMENT ============
    # Maximum conversation turns to keep in memory
    MAX_CONTEXT_TURNS: int = 5
    
    # Maximum characters per context turn
    MAX_CONTEXT_CHARS_PER_TURN: int = 500
    
    # ============ RETRIEVAL & RAG ============
    # Document chunk size (characters)
    CHUNK_SIZE: int = 400
    
    # Overlap between chunks (characters)
    CHUNK_OVERLAP: int = 50
    
    # ============ GENERAL ============
    # Enable query validation
    USE_QUERY_VALIDATION: bool = True
    
    # Enable scope checking
    USE_SCOPE_GUARD: bool = True
    
    # Debug mode (verbose logging)
    DEBUG: bool = False
    
    # Request timeout (seconds)
    REQUEST_TIMEOUT: int = 30

settings = Settings()

