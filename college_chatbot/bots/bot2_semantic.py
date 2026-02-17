"""
Bot-2: Semantic QA with Similarity Threshold Routing.
Uses FAISS + cosine similarity to find most relevant Q&A pairs.
Lazy loads resources via ModelManager.
"""

from typing import Optional, Tuple
import numpy as np
from config.settings import settings
from core.audit_logger import get_audit_logger
from core.logger import get_logger
from core.model_manager import ModelManager

logger = get_logger("bot2")
audit_logger = get_audit_logger("bot2")

def calculate_similarity_score(distances: np.ndarray, top_k: int = 1) -> Tuple[float, float]:
    """
    Calculate similarity score from FAISS L2 distances.
    similarities = 1 / (1 + distance)
    """
    if len(distances) == 0:
        return 0.0, 0.0
    
    similarities = 1.0 / (1.0 + distances)
    max_sim = float(np.max(similarities))
    avg_sim = float(np.mean(similarities))
    return max_sim, avg_sim

def bot2_answer(query: str, query_id: str = "unknown", category: Optional[str] = None) -> Tuple[str, float, bool]:
    """
    Retrieve answer using semantic similarity, optionally prioritized by domain category.
    Returns: (answer: str, confidence: float, is_confident: bool)
    """
    logger.info(f"[{query_id}] Bot-2 semantic search initiated")
    
    # Lazy load resources
    # We will use a helper to load the specific domain index
    index, qa_pairs = ModelManager.get_domain_qa_resources(category)
    
    # Fallback to general/legacy if specific not found (handled in Manager)
    embedder = ModelManager.get_embedder()

    # Check validity
    # PRE-REQUISITE CHECK
    if index is None or index.ntotal == 0 or not qa_pairs:
        logger.error(f"[{query_id}] CRITICAL: Bot-2 resources unavailable for domain '{category}'. Index status: {'OK' if index else 'MISSING'}, QA Pairs: {len(qa_pairs) if qa_pairs else 0}")
        
        # ATTEMPT FALLBACK TO CROSS-DOMAIN / GENERAL
        logger.info(f"[{query_id}] Attempting fallback to 'Cross-Domain Queries'...")
        index, qa_pairs = ModelManager.get_domain_qa_resources("Cross-Domain Queries")
        
        if index is None or index.ntotal == 0 or not qa_pairs:
             logger.error(f"[{query_id}] Fallback failed. Aborting Bot-2.")
             audit_logger.log_retrieval_quality(
                query_id=query_id, bot="BOT-2", top_k=0, scores=[], avg_score=0.0,
                passed_threshold=False, threshold=settings.BOT2_SIMILARITY_THRESHOLD,
                num_docs_retrieved=0
             )
             return "Knowledge base temporarily unavailable.", 0.0, False
             
        logger.info(f"[{query_id}] Fallback successful. Using Cross-Domain index.")
    
    try:
        # Embed query
        query_embedding = embedder.encode([query], show_progress_bar=False)
        query_embedding = query_embedding.astype(np.float32)
        
        # ---------------------------------------------------------
        # DOMAIN-AWARE SEARCH STRATEGY
        # 1. If category is valid, filter search space first (Pre-filtering)
        #    BUT FAISS doesn't support metadata filtering natively in IndexFlatL2 easily without ID mapping.
        #    So we will search normally (Global Search) and then Post-Filter/Boost relevant domains.
        # ---------------------------------------------------------
        
        top_k = settings.TOP_K_BOT2 * 3 # Retrieve more to allow for filtering
        
        # SEARCH THE INDEX
        distances, indices = index.search(query_embedding, top_k)
        
        valid_hits = []
        
        # Iterate over the first batch (since we encoded just 1 query)
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(qa_pairs): 
                continue
                
            item = qa_pairs[idx]
            item_domain = item.get("domain", "General Information") # Default if missing
            
            # Calculate similarity
            similarity = 1.0 / (1.0 + dist)
            
            # Apply Domain Boost
            is_domain_match = False
            effective_score = similarity
            
            if category and item_domain:
                # Normalize strings
                if item_domain.lower() == category.lower():
                    is_domain_match = True
                    # Boost score for ranking (10% boost)
                    effective_score = min(1.0, similarity + 0.1)
                
            valid_hits.append({
                "answer": item.get("answer"),
                "question": item.get("question"),
                "domain": item_domain,
                "similarity": similarity,
                "effective_score": effective_score,
                "distance": dist,
                "is_match": is_domain_match
            })
            
        if not valid_hits:
            return "No relevant information found.", 0.0, False

        # Sort by effective_score descending
        valid_hits.sort(key=lambda x: x["effective_score"], reverse=True)
        
        best_hit = valid_hits[0]
        max_similarity = best_hit["similarity"]
        
        # Log Domain Info
        logger.info(f"[{query_id}] Best Hit Domain: '{best_hit['domain']}' (Predicted: '{category}')")
        
        # Calculate Average of top K
        top_hits_sims = [h["similarity"] for h in valid_hits[:settings.TOP_K_BOT2]]
        avg_similarity = sum(top_hits_sims) / len(top_hits_sims) if top_hits_sims else 0.0

        logger.info(
            f"[{query_id}] Similarity scores - max: {max_similarity:.4f}, avg: {avg_similarity:.4f}"
        )
        
        # Log retrieval quality
        audit_logger.log_retrieval_quality(
            query_id=query_id,
            bot="BOT-2",
            top_k=top_k,
            scores=[float(h["similarity"]) for h in valid_hits[:settings.TOP_K_BOT2]],
            avg_score=float(avg_similarity),
            passed_threshold=bool(max_similarity >= settings.BOT2_SIMILARITY_THRESHOLD),
            num_docs_retrieved=len(valid_hits),
            threshold=settings.BOT2_SIMILARITY_THRESHOLD
        )
        
        # Check thresholds
        # Check thresholds
        if max_similarity < settings.BOT2_MIN_SIMILARITY:
            # Convert float32 to python float
            max_sim_float = float(max_similarity)
            
            logger.info(
                f"[{query_id}] Similarity {max_sim_float:.4f} below minimum "
                f"{settings.BOT2_MIN_SIMILARITY:.4f}."
            )
            
            # ---------------------------------------------------------
            # CROSS-DOMAIN RECOVERY (The "Semantic Backup")
            # If the specific domain failed, let's look everywhere else.
            # ---------------------------------------------------------
            if category and category != "Cross-Domain Queries":
                logger.info(f"[{query_id}] Attempting Cross-Domain Recovery (scanning all other domains)...")
                
                ALL_DOMAINS = [
                    "Admissions & Registrations", "Financial Matters", "Academic Affairs",
                    "Student Services", "Campus Life", "General Information", "Cross-Domain Queries"
                ]
                
                best_recovery_hit = None
                
                for dom in ALL_DOMAINS:
                    if dom == category: continue # Skip already searched
                    
                    # Load index
                    idx, qa = ModelManager.get_domain_qa_resources(dom)
                    if not idx or idx.ntotal == 0: continue
                    
                    # Search
                    # We use the same query_embedding
                    # We need to replicate the search logic briefly here
                    # Since we are inside the function, we can't easily reuse the code above without refactoring
                    # So we will do a quick search
                    
                    D, I = idx.search(query_embedding, 1) # Top 1 only for speed
                    
                    if len(D) > 0 and len(I) > 0:
                        dist = D[0][0]
                        idx_ptr = I[0][0]
                        
                        if idx_ptr >= 0 and idx_ptr < len(qa):
                            # Calc similarity
                            sim = 1.0 / (1.0 + dist)
                            
                            if sim > max_similarity and sim >= settings.BOT2_MIN_SIMILARITY:
                                # Found a better candidate!
                                item = qa[idx_ptr]
                                logger.info(f"[{query_id}] Recovery: Found better match in '{dom}' (Sim: {sim:.4f})")
                                
                                best_recovery_hit = {
                                    "answer": item.get("answer"),
                                    "question": item.get("question"),
                                    "domain": dom,
                                    "similarity": sim,
                                    "is_recovered": True
                                }
                                max_similarity = sim # Update global max
                
                if best_recovery_hit:
                    logger.info(f"[{query_id}] RECOVERY SUCCESSFUL. Returning answer from '{best_recovery_hit['domain']}'.")
                    
                    # Log audit for recovery
                    audit_logger.log_retrieval_quality(
                        query_id=query_id, bot="BOT-2-RECOVERY", top_k=1, 
                        scores=[float(best_recovery_hit["similarity"])], avg_score=float(best_recovery_hit["similarity"]),
                        passed_threshold=True, num_docs_retrieved=1, threshold=settings.BOT2_MIN_SIMILARITY
                    )
                    
                    return (
                        f"{best_recovery_hit['answer']}",
                        float(best_recovery_hit['similarity']),
                        True
                    )

            # If still failing after recovery attempt
            audit_logger.log_answer_rejection(
                query_id=query_id, bot="BOT-2", reason="Below minimum similarity threshold",
                score=float(max_similarity), threshold=settings.BOT2_MIN_SIMILARITY
            )
            return (
                f"I found some related information, but I'm not confident enough. "
                f"Please ask more specifically or contact {best_hit.get('domain', 'administration')}.",
                max_similarity,
                False
            )
        
        answer = best_hit["answer"]
        is_confident = max_similarity >= settings.BOT2_SIMILARITY_THRESHOLD
        
        logger.info(f"[{query_id}] Bot-2 answer retrieved (confidence: {max_similarity:.4f})")
        
        audit_logger.log_answer_generation(
            query_id=query_id, bot="BOT-2", answer_length=len(answer),
            confidence=max_similarity, sources=[best_hit.get("question", "Unknown")],
            metadata={"similarity_score": round(max_similarity, 4), "domain": best_hit["domain"]}
        )
        
        return answer, max_similarity, is_confident
        
    except Exception as e:
        logger.exception(f"[{query_id}] Error in Bot-2 semantic search: {e}")
        audit_logger.log_error(
            query_id=query_id, error_type="BOT2_SEARCH_ERROR", error_message=str(e),
            stage="semantic_retrieval", stacktrace=str(e)
        )
        return f"Error during semantic search: {str(e)}", 0.0, False


