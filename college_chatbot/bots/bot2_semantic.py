"""
Bot-2: Semantic QA with Similarity Threshold Routing.

Uses FAISS + cosine similarity to find most relevant Q&A pairs.
Includes confidence checking and fallback to Bot-3 for low-confidence matches.
"""

import pickle
from typing import Optional, Tuple

import faiss
import numpy as np
from config.settings import settings
from core.audit_logger import get_audit_logger
from core.logger import get_logger
from embeddings.embedder import embed

logger = get_logger("bot2")
audit_logger = get_audit_logger("bot2")

# Load FAISS index and Q&A pairs
INDEX_PATH = "embeddings/bot2_faiss/index.faiss"
QA_PKL_PATH = "embeddings/bot2_faiss/qa.pkl"

try:
    index = faiss.read_index(INDEX_PATH)
    with open(QA_PKL_PATH, "rb") as f:
        qa_pairs = pickle.load(f)  # List of {"question": str, "answer": str}
    logger.info(f"[OK] Bot-2 FAISS index loaded: {index.ntotal} QA pairs")
except Exception as e:
    logger.error(f"[ERROR] Failed to load Bot-2 FAISS index: {e}")
    index = None
    qa_pairs = []


def calculate_similarity_score(distances: np.ndarray, top_k: int = 1) -> Tuple[float, float]:
    """
    Calculate similarity score from FAISS L2 distances.
    
    FAISS uses L2 (Euclidean) distance. Lower is better.
    We convert to similarity: similarity = 1 / (1 + distance)
    
    Returns:
        (max_similarity, avg_similarity)
    """
    if len(distances) == 0:
        return 0.0, 0.0
    
    # Convert L2 distance to similarity
    # This formula ensures similarity is in [0, 1] range
    similarities = 1.0 / (1.0 + distances)
    
    max_sim = float(np.max(similarities))
    avg_sim = float(np.mean(similarities))
    
    return max_sim, avg_sim


def bot2_answer(query: str, query_id: str = "unknown") -> Tuple[str, float, bool]:
    """
    Retrieve answer using semantic similarity.
    
    Returns:
        (answer: str, confidence: float, is_confident: bool)
    """
    
    logger.info(f"[{query_id}] Bot-2 semantic search initiated")
    
    # Check if index is loaded
    if index is None or index.ntotal == 0:
        logger.warning(f"[{query_id}] Bot-2 index not available, cannot search")
        audit_logger.log_retrieval_quality(
            query_id=query_id,
            bot="BOT-2",
            top_k=0,
            scores=[],
            avg_score=0.0,
            passed_threshold=False,
            threshold=settings.BOT2_SIMILARITY_THRESHOLD,
            num_docs_retrieved=0
        )
        return "No index available for semantic search.", 0.0, False
    
    try:
        # Embed query
        query_embedding = embed([query])
        
        # Search FAISS index
        top_k = settings.TOP_K_BOT2
        distances, indices = index.search(query_embedding, top_k)
        
        # Extract distances and indices (batch size is 1)
        distances = distances[0]
        indices = indices[0]
        
        logger.debug(f"[{query_id}] Retrieved indices: {indices}, distances: {distances}")
        
        # Calculate similarity scores
        max_similarity, avg_similarity = calculate_similarity_score(distances, top_k)
        
        logger.info(
            f"[{query_id}] Similarity scores - max: {max_similarity:.4f}, avg: {avg_similarity:.4f}"
        )
        
        # Log retrieval quality
        audit_logger.log_retrieval_quality(
            query_id=query_id,
            bot="BOT-2",
            top_k=top_k,
            scores=distances.tolist(),
            avg_score=float(avg_similarity),
            passed_threshold=max_similarity >= settings.BOT2_SIMILARITY_THRESHOLD,
            threshold=settings.BOT2_SIMILARITY_THRESHOLD,
            num_docs_retrieved=int(np.sum(indices >= 0))
        )
        
        # Check if similarity is above minimum threshold
        if max_similarity < settings.BOT2_MIN_SIMILARITY:
            logger.info(
                f"[{query_id}] Similarity {max_similarity:.4f} below minimum "
                f"{settings.BOT2_MIN_SIMILARITY:.4f}, returning low confidence"
            )
            audit_logger.log_answer_rejection(
                query_id=query_id,
                bot="BOT-2",
                reason="Below minimum similarity threshold",
                score=max_similarity,
                threshold=settings.BOT2_MIN_SIMILARITY
            )
            return (
                f"I found some related information, but I'm not confident enough. "
                f"Please ask more specifically or contact student services.",
                max_similarity,
                False
            )
        
        # Get top answer
        best_idx = indices[0]
        best_qa = qa_pairs[best_idx] if best_idx < len(qa_pairs) else None
        
        if best_qa is None:
            logger.error(f"[{query_id}] Invalid index {best_idx} in qa_pairs")
            return "Error retrieving answer. Please try again.", 0.0, False
        
        answer = best_qa.get("answer", "No answer found.")
        
        # High confidence if similarity is above high threshold
        is_confident = max_similarity >= settings.BOT2_SIMILARITY_THRESHOLD
        
        logger.info(
            f"[{query_id}] Bot-2 answer retrieved "
            f"(confidence: {max_similarity:.4f}, confident: {is_confident})"
        )
        
        audit_logger.log_answer_generation(
            query_id=query_id,
            bot="BOT-2",
            answer_length=len(answer),
            confidence=max_similarity,
            sources=[best_qa.get("question", "Unknown")],
            metadata={"similarity_score": round(max_similarity, 4)}
        )
        
        return answer, max_similarity, is_confident
        
    except Exception as e:
        logger.exception(f"[{query_id}] Error in Bot-2 semantic search: {e}")
        audit_logger.log_error(
            query_id=query_id,
            error_type="BOT2_SEARCH_ERROR",
            error_message=str(e),
            stage="semantic_retrieval",
            stacktrace=str(e)
        )
        return f"Error during semantic search: {str(e)}", 0.0, False

