"""
MAIN ORCHESTRATOR: Compute-Aware, Confidence-Aware, Safety-Aware Hybrid RAG System

Routing Pipeline:
  User Query
    ↓
  [1] Query Validation (format, safety, gibberish check)
    ↓
  [2] Safety Guard (self-harm, prompt injection, sensitive data extraction)
    ↓
  [3] Scope Check (college-related topics only)
    ↓
  [4] Intent Classification (get category + confidence)
    ↓
  [5] Routing Decision (based on confidence & category)
    ├→ HIGH confidence + Rule category → BOT-1 (Rule-based AIML)
    ├→ HIGH confidence + Semantic category → BOT-2 (Semantic QA)
    ├→ LOW confidence → BOT-3 (RAG)
    └→ BOT-2 fails (low similarity) → BOT-3 (RAG)
    
Answer Generation:
  - BOT-1: Rule-based deterministic
  - BOT-2: Similarity threshold + fallback to BOT-3
  - BOT-3: RAG with retrieval confidence check

Logging & Observability:
  - Every routing decision logged with confidence scores
  - Retrieval quality metrics logged
  - All failures logged with context for debugging
  - Audit trail for compliance & model improvement
"""

import time
from typing import List, Optional, Tuple

from bots.bot2_semantic import bot2_answer
from bots.bot3_rag import bot3_answer
from bots.rule_bot import get_rule_response
from classifier.classifier import predict_category
from config.settings import settings
from core.audit_logger import get_audit_logger
from core.context import create_context
from core.logger import get_logger
from services.query_validator import validate_query
from services.scope_guard import scope_check

logger = get_logger("orchestrator")
audit_logger = get_audit_logger("main")

# ============ ROUTING THRESHOLDS ============
# (Also defined in settings.py, but repeated here for clarity)
HIGH_CONF_THRESHOLD = settings.CLASSIFIER_HIGH_CONF
MID_CONF_THRESHOLD = settings.CLASSIFIER_MID_CONF


def handle_query(query: str, history: Optional[List[Tuple[str, str]]] = None) -> str:
    """
    Main orchestrator function for routing user queries.
    
    Args:
        query: User's question/statement
        history: Conversation history [(user_msg, assistant_response), ...]
    
    Returns:
        Response string (grounded in college data or denial message)
    """
    
    # Initialize context (query_id, timing, metadata)
    ctx = create_context(query)
    stage_times = {}
    
    if history is None:
        history = []
    
    try:
        logger.info(f"[{ctx['query_id']}] " + "="*70)
        logger.info(f"[{ctx['query_id']}] QUERY: {query}")
        logger.info(f"[{ctx['query_id']}] History length: {len(history)}")
        
        # ============================================================
        # [STAGE 1] QUERY VALIDATION
        # ============================================================
        stage_start = time.time()
        
        logger.info(f"[{ctx['query_id']}] [STAGE 1] Query Validation")
        is_valid, validation_reason = validate_query(query)
        ctx["validation"] = {"valid": is_valid, "reason": validation_reason}
        
        if not is_valid:
            logger.info(
                f"[{ctx['query_id']}] [FAIL] Query failed validation: {validation_reason}"
            )
            audit_logger.log_routing_decision(
                query_id=ctx['query_id'],
                query=query,
                validation_status="FAILED",
                scope_status="NOT_CHECKED",
                classifier_category="NONE",
                classifier_confidence=0.0,
                classifier_probs={},
                routed_to_bot="NONE",
                reason=validation_reason
            )
            return validation_reason
        
        logger.info(f"[{ctx['query_id']}] [OK] Query validation passed")
        stage_times["validation"] = int((time.time() - stage_start) * 1000)
        
        # ============================================================
        # [STAGE 2] SCOPE CHECK (Out-of-domain detection)
        # ============================================================
        stage_start = time.time()
        
        logger.info(f"[{ctx['query_id']}] [STAGE 2] Scope Check")
        in_scope, scope_reason = scope_check(query)
        ctx["scope"] = {"in_scope": in_scope, "reason": scope_reason}
        
        if not in_scope:
            logger.info(
                f"[{ctx['query_id']}] [FAIL] Query out of scope: {scope_reason}"
            )
            out_of_scope_response = (
                "[INFO] I can only help with college administrative questions.\n\n"
                "I'm designed to answer questions about:\n"
                "- Admissions, eligibility, application documents\n"
                "- Fees, scholarships, financial aid\n"
                "- Academic programs, courses, syllabus\n"
                "- Exams, results, revaluation, timetable\n"
                "- Hostel, mess, transport, campus facilities\n"
                "- Bonafide, NOC, certificates, ID cards\n"
                "- Placements, internships, training\n\n"
                "Please ask a question related to these topics, or contact student services."
            )
            audit_logger.log_routing_decision(
                query_id=ctx['query_id'],
                query=query,
                validation_status="PASSED",
                scope_status="OUT_OF_SCOPE",
                classifier_category="NONE",
                classifier_confidence=0.0,
                classifier_probs={},
                routed_to_bot="NONE",
                reason=scope_reason
            )
            return out_of_scope_response
        
        logger.info(f"[{ctx['query_id']}] [OK] Query in scope: {scope_reason}")
        stage_times["scope_check"] = int((time.time() - stage_start) * 1000)
        
        # ============================================================
        # [STAGE 3] INTENT CLASSIFICATION
        # ============================================================
        stage_start = time.time()
        
        logger.info(f"[{ctx['query_id']}] [STAGE 3] Intent Classification")
        category, confidence, probabilities = predict_category(query)
        ctx["classifier"] = {
            "category": category,
            "confidence": confidence,
            "all_probabilities": probabilities
        }
        
        logger.info(
            f"[{ctx['query_id']}] Classification: category={category}, confidence={confidence:.4f}"
        )
        logger.debug(f"[{ctx['query_id']}] All probabilities: {probabilities}")
        stage_times["classification"] = int((time.time() - stage_start) * 1000)
        
        # ============================================================
        # [STAGE 4] ROUTING DECISION
        # ============================================================
        stage_start = time.time()
        
        logger.info(f"[{ctx['query_id']}] [STAGE 4] Routing Decision")
        logger.info(f"[{ctx['query_id']}] Confidence thresholds: HIGH={HIGH_CONF_THRESHOLD}, MID={MID_CONF_THRESHOLD}")
        
        # Decision tree
        routed_to_bot = None
        routing_reason = None
        
        # Check confidence level
        if confidence < MID_CONF_THRESHOLD:
            # [4a] LOW CONFIDENCE → Always use Bot-3 (RAG)
            routed_to_bot = "BOT-3"
            routing_reason = f"Low classifier confidence ({confidence:.4f} < {MID_CONF_THRESHOLD})"
            logger.info(
                f"[{ctx['query_id']}] [ROUTING] LOW CONFIDENCE ROUTING: {routing_reason}"
            )
        
        elif category in ["Admissions & Registrations", "Financial Matters"]:
            # [4b] Rule-based categories → Use Bot-1
            if confidence >= HIGH_CONF_THRESHOLD:
                routed_to_bot = "BOT-1"
                routing_reason = f"High confidence ({confidence:.4f}) + rule category"
                logger.info(
                    f"[{ctx['query_id']}] [ROUTING] RULE-BOT ROUTING: {routing_reason}"
                )
            else:
                # Medium confidence on rule category → still try Bot-1, fallback to Bot-3
                routed_to_bot = "BOT-1-WITH-FALLBACK"
                routing_reason = f"Medium confidence ({confidence:.4f}) + rule category"
                logger.info(
                    f"[{ctx['query_id']}] [ROUTING] RULE-BOT (with RAG fallback): {routing_reason}"
                )
        
        elif category in ["Academic Affairs", "Student Services", "Campus Life"]:
            # [4c] Semantic categories → Use Bot-2
            if confidence >= HIGH_CONF_THRESHOLD:
                routed_to_bot = "BOT-2"
                routing_reason = f"High confidence ({confidence:.4f}) + semantic category"
                logger.info(
                    f"[{ctx['query_id']}] [ROUTING] SEMANTIC-BOT ROUTING: {routing_reason}"
                )
            else:
                # Medium confidence → still try Bot-2, fallback to Bot-3
                routed_to_bot = "BOT-2-WITH-FALLBACK"
                routing_reason = f"Medium confidence ({confidence:.4f}) + semantic category"
                logger.info(
                    f"[{ctx['query_id']}] [ROUTING] SEMANTIC-BOT (with RAG fallback): {routing_reason}"
                )
        
        else:
            # [4d] Unknown category → Use Bot-3 (RAG)
            routed_to_bot = "BOT-3"
            routing_reason = f"Unknown category: {category}"
            logger.info(
                f"[{ctx['query_id']}] ❓ UNKNOWN CATEGORY → RAG: {routing_reason}"
            )
        
        ctx["routing_decision"] = {
            "routed_to": routed_to_bot,
            "reason": routing_reason,
            "classifier_confidence": confidence
        }
        stage_times["routing"] = int((time.time() - stage_start) * 1000)
        
        # ============================================================
        # [STAGE 5] ANSWER GENERATION
        # ============================================================
        stage_start = time.time()
        
        logger.info(f"[{ctx['query_id']}] [STAGE 5] Answer Generation via {routed_to_bot}")
        
        response = None
        bot_used_final = None
        answer_confidence = None
        
        # [5a] BOT-1: Rule-based AIML
        if routed_to_bot in ["BOT-1", "BOT-1-WITH-FALLBACK"]:
            try:
                logger.info(f"[{ctx['query_id']}] Calling BOT-1 (Rule-based)")
                response = get_rule_response(query)
                
                # Check if Bot-1 has a real answer (not just default fallback)
                if response and response != "Sorry, I don't have information on that.":
                    logger.info(f"[{ctx['query_id']}] [OK] BOT-1 returned answer")
                    bot_used_final = "BOT-1"
                    answer_confidence = 0.9  # High confidence for rule-based
                else:
                    # Bot-1 has no answer, fallback to Bot-3 if allowed
                    if routed_to_bot == "BOT-1-WITH-FALLBACK":
                        logger.info(f"[{ctx['query_id']}] BOT-1 returned empty, falling back to BOT-3")
                        routed_to_bot = "BOT-3"
                    else:
                        logger.info(f"[{ctx['query_id']}] BOT-1 returned empty answer")
                        audit_logger.log_answer_rejection(
                            query_id=ctx['query_id'],
                            bot="BOT-1",
                            reason="Rule-bot has no matching rule",
                        )
            except Exception as e:
                logger.exception(f"[{ctx['query_id']}] Error in BOT-1: {e}")
                if routed_to_bot == "BOT-1-WITH-FALLBACK":
                    logger.info(f"[{ctx['query_id']}] BOT-1 error, falling back to BOT-3")
                    routed_to_bot = "BOT-3"
                else:
                    audit_logger.log_error(
                        query_id=ctx['query_id'],
                        error_type="BOT1_ERROR",
                        error_message=str(e),
                        stage="rule_bot",
                        stacktrace=str(e)
                    )
                    response = "[ERROR] Error in rule-based system. Please try again."
                    bot_used_final = "BOT-1"
        
        # [5b] BOT-2: Semantic QA with Similarity Threshold
        if response is None and routed_to_bot in ["BOT-2", "BOT-2-WITH-FALLBACK"]:
            try:
                logger.info(f"[{ctx['query_id']}] Calling BOT-2 (Semantic QA)")
                answer, similarity_score, is_confident = bot2_answer(query, ctx['query_id'])
                
                ctx["bot2_similarity"] = similarity_score
                
                if is_confident:
                    logger.info(
                        f"[{ctx['query_id']}] [OK] BOT-2 returned confident answer "
                        f"(similarity: {similarity_score:.4f})"
                    )
                    response = answer
                    bot_used_final = "BOT-2"
                    answer_confidence = similarity_score
                else:
                    # Low similarity, fallback to Bot-3
                    logger.info(
                        f"[{ctx['query_id']}] BOT-2 low confidence "
                        f"(similarity: {similarity_score:.4f}), falling back to BOT-3"
                    )
                    routed_to_bot = "BOT-3"
                    audit_logger.log_answer_rejection(
                        query_id=ctx['query_id'],
                        bot="BOT-2",
                        reason="Similarity score below threshold",
                        score=similarity_score,
                        threshold=settings.BOT2_SIMILARITY_THRESHOLD
                    )
            except Exception as e:
                logger.exception(f"[{ctx['query_id']}] Error in BOT-2: {e}")
                if routed_to_bot == "BOT-2-WITH-FALLBACK":
                    logger.info(f"[{ctx['query_id']}] BOT-2 error, falling back to BOT-3")
                    routed_to_bot = "BOT-3"
                else:
                    audit_logger.log_error(
                        query_id=ctx['query_id'],
                        error_type="BOT2_ERROR",
                        error_message=str(e),
                        stage="semantic_qa",
                        stacktrace=str(e)
                    )
                    response = "[ERROR] Error in semantic search. Please try again."
                    bot_used_final = "BOT-2"
        
        # [5c] BOT-3: RAG (last resort or fallback)
        if response is None and routed_to_bot in ["BOT-3", "BOT-2-WITH-FALLBACK", "BOT-1-WITH-FALLBACK"]:
            try:
                logger.info(f"[{ctx['query_id']}] Calling BOT-3 (RAG)")
                response = bot3_answer(query, history, ctx['query_id'])
                bot_used_final = "BOT-3"
                answer_confidence = 0.7  # Medium confidence for RAG
                logger.info(f"[{ctx['query_id']}] [OK] BOT-3 returned answer")
            except Exception as e:
                logger.exception(f"[{ctx['query_id']}] Error in BOT-3: {e}")
                audit_logger.log_error(
                    query_id=ctx['query_id'],
                    error_type="BOT3_ERROR",
                    error_message=str(e),
                    stage="rag_generation",
                    stacktrace=str(e)
                )
                response = "[ERROR] Critical error in RAG system. Please contact support."
                bot_used_final = "BOT-3"
        
        stage_times["answer_generation"] = int((time.time() - stage_start) * 1000)
        
        # Log final routing and answer
        audit_logger.log_routing_decision(
            query_id=ctx['query_id'],
            query=query,
            validation_status="PASSED",
            scope_status="IN_SCOPE",
            classifier_category=category,
            classifier_confidence=confidence,
            classifier_probs=probabilities,
            routed_to_bot=bot_used_final or routed_to_bot,
            similarity_score=ctx.get("bot2_similarity"),
            reason=routing_reason
        )
        
        ctx["final_bot"] = bot_used_final
        ctx["answer_confidence"] = answer_confidence
        
        if response is None:
            response = "[ERROR] No bot was able to generate an answer. Please try rephrasing your question."
        
        logger.info(f"[{ctx['query_id']}] Response generated ({len(response)} chars)")
        
        return response
    
    except Exception as e:
        logger.exception(f"[{ctx['query_id']}] CRITICAL ERROR in orchestrator: {e}")
        audit_logger.log_error(
            query_id=ctx['query_id'],
            error_type="ORCHESTRATOR_ERROR",
            error_message=str(e),
            stage="main_orchestrator",
            stacktrace=str(e)
        )
        return "[ERROR] A critical error occurred. Please try again or contact support."
    
    finally:
        # ============================================================
        # LOGGING & OBSERVABILITY
        # ============================================================
        
        total_latency_ms = int((time.time() - ctx['start_time']) * 1000)
        ctx["latency_ms"] = total_latency_ms
        
        # Log stage breakdown
        audit_logger.log_latency(
            query_id=ctx['query_id'],
            latency_ms=total_latency_ms,
            stages=stage_times
        )
        
        # Final summary
        logger.info(f"[{ctx['query_id']}] " + "="*70)
        logger.info(
            f"[{ctx['query_id']}] SUMMARY: "
            f"bot={ctx.get('final_bot', 'UNKNOWN')} | "
            f"conf={ctx.get('answer_confidence', 0):.4f} | "
            f"latency={total_latency_ms}ms | "
            f"error={ctx.get('error', 'NONE')}"
        )
        logger.info(f"[{ctx['query_id']}] " + "="*70)
