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
        # Handle Greetings specifically
        if scope_reason == "greeting":
            logger.info(f"[{ctx['query_id']}] GREETING DETECTED")
            # Update context for final logging
            ctx["final_bot"] = "BOT-1 (RULE-BASED)"
            ctx["answer_confidence"] = 1.0
            
            # Log routing decision
            audit_logger.log_routing_decision(
                query_id=ctx['query_id'],
                query=query,
                validation_status="PASSED",
                scope_status="IN_SCOPE",
                classifier_category="Greeting",
                classifier_confidence=1.0,
                classifier_probs={},
                routed_to_bot="BOT-1",
                reason="Greeting detected by Scope Guard"
            )
            
            greeting_msg = "Hi! I am the RVR&JC College Chatbot. How can I assist you with admissions, fees, or campus life today?"
            ctx["final_response"] = greeting_msg
            return greeting_msg

        if not in_scope:
            logger.info(
                f"[{ctx['query_id']}] [FAIL] Query out of scope: {scope_reason}"
            )
            
            # Use the user-defined out-of-scope response
            out_of_scope_response = OUT_OF_SCOPE_RESPONSE
            
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
            out_of_scope_response = OUT_OF_SCOPE_RESPONSE
            ctx["final_response"] = out_of_scope_response
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
        
        # ============ [STAGE 4] ROUTING DECISION ============
        stage_start = time.time()
        
        from services.scope_guard import OUT_OF_SCOPE_RESPONSE, is_rag_forbidden

        logger.info(f"[{ctx['query_id']}] [STAGE 4] Routing Decision")
        
        routed_to_bot = None
        routing_reason = None
        
        # STRICT ESCALATION POLICY (UPDATED)
        # 1. ALWAYS try Rule Bot (Bot-1) first.
        # 2. If no match -> Semantic Bot (Bot-2).
        # 3. If no match/low confidence -> RAG (Bot-3).
        # Classifier Confidence is METADATA ONLY, not a gate.
        
        if is_rag_forbidden(query):
            # Forbidden RAG topics -> Force Rule Bot
            routed_to_bot = "BOT-1"
            routing_reason = "RAG Forbidden Topic -> Force Rule-Based"
            logger.warning(f"[{ctx['query_id']}] {routing_reason}")
            
        else:
            # Standard Escalation Chain
            routed_to_bot = "BOT-1-CHAIN"
            routing_reason = "Standard Escalation: Rule -> Semantic -> RAG"
            logger.info(f"[{ctx['query_id']}] {routing_reason}")
            
            if confidence < MID_CONF_THRESHOLD:
                logger.info(f"[{ctx['query_id']}] Low Classifier Confidence ({confidence:.2f}). Continuing chain.")

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
        
        # --------------------------------------------------
        # DYNAMIC ROUTING EXECUTION
        # --------------------------------------------------
        
        # Define execution order based on domain
        # Default: Rule -> Semantic -> RAG
        execution_order = ["BOT-1", "BOT-2", "BOT-3"]
        
        # Apply Domain Preferences
        if category in ["Admissions & Registrations", "Financial Matters", "Academic Affairs", "Campus Life", "Cross-Domain Queries"]:
            # User specified Primary: Tier-2 for these
            # This implies checking Semantic BEFORE Rule-based? 
            # Or just that Semantic is the main source.
            # To be safe and compliant with "Primary: Tier-2", we place BOT-2 first.
            execution_order = ["BOT-2", "BOT-1", "BOT-3"]
        elif category == "Student Services":
            # Primary: Tier-1
            execution_order = ["BOT-1", "BOT-2", "BOT-3"]
        elif category == "General Information":
            # Primary: Tier-2
            execution_order = ["BOT-2", "BOT-1", "BOT-3"]
            
        logger.info(f"[{ctx['query_id']}] Domain: {category} -> Execution Order: {execution_order}")

        for bot_name in execution_order:
            if response: break # Stop if we found an answer
            
            # --- EXECUTE BOT-1 ---
            if bot_name == "BOT-1":
                try:
                    logger.info(f"[{ctx['query_id']}] Checking BOT-1 (Rule-based)...")
                    # Bot-1 is fast, but we only use it if it has a specific response
                    rule_resp = get_rule_response(query)
                    if rule_resp and rule_resp != "Sorry, I don't have information on that.":
                         logger.info(f"[{ctx['query_id']}] [SUCCESS] BOT-1 found answer")
                         response = rule_resp
                         bot_used_final = "BOT-1"
                         answer_confidence = 0.95
                    else:
                        logger.info(f"[{ctx['query_id']}] BOT-1 has no answer.")
                except Exception as e:
                    logger.exception(f"[{ctx['query_id']}] BOT-1 Failed: {e}")

            # --- EXECUTE BOT-2 ---
            elif bot_name == "BOT-2":
                try:
                    logger.info(f"[{ctx['query_id']}] Checking BOT-2 (Semantic)...")
                    # Pass category for domain-specific retrieval
                    b2_ans, b2_score, b2_conf = bot2_answer(query, ctx['query_id'], category=category)
                    ctx["bot2_similarity"] = b2_score
                    
                    if b2_conf:
                        logger.info(f"[{ctx['query_id']}] [SUCCESS] BOT-2 confident (Score: {b2_score:.4f})")
                        response = b2_ans
                        bot_used_final = "BOT-2"
                        answer_confidence = b2_score
                    else:
                        logger.info(f"[{ctx['query_id']}] BOT-2 not confident (Score: {b2_score:.4f}).")
                except Exception as e:
                    logger.exception(f"[{ctx['query_id']}] BOT-2 Failed: {e}")
            
            # --- EXECUTE BOT-3 ---
            elif bot_name == "BOT-3":
                 # Bot-3 is always the last resort in this loop
                 pass

        # 3. IF NO RESPONSE -> FALLBACK TO BOT-3 (RAG)
        # We explicitly handle Bot-3 here to keep the centralized RAG logic / tuple unpacking separate
        # or we could have included it in the loop. 
        # But 'main.py' existing structure handles Bot-3 with specific logic.
        # So we just ensure we reach here if response is None.


        # 3. TRY BOT-3 (RAG)
        # Execute if previous bots failed OR explicitly routed to Bot-3
        if response is None:
            try:
                logger.info(f"[{ctx['query_id']}] Escalating to BOT-3 (RAG)...")
                # Bot-3 returns (answer, confidence, is_confident)
                rag_result = bot3_answer(query, history, ctx['query_id'])
                
                # Unwrap tuple (safe handling for legacy return if any)
                if isinstance(rag_result, tuple):
                    answer, rag_confidence, rag_is_confident = rag_result
                else:
                    answer = rag_result
                    rag_confidence = 0.5
                    rag_is_confident = True if "[NO INFO]" not in answer else False

                bot_used_final = "BOT-3"
                answer_confidence = rag_confidence
                response = answer
                
                # CHECK FOR UNRESOLVED QUERY
                # If Semantic was low AND RAG is not confident -> Log it
                bot2_score = ctx.get("bot2_similarity", 0.0)
                if not rag_is_confident and bot2_score < settings.BOT2_MIN_SIMILARITY:
                    from core.query_tracker import log_unresolved_query
                    logger.info(f"[{ctx['query_id']}] [TRACKER] Logging unresolved query.")
                    log_unresolved_query(
                        query=query,
                        category=category,
                        semantic_score=bot2_score,
                        rag_confidence=rag_confidence
                    )
                    
            except Exception as e:
                logger.exception(f"[{ctx['query_id']}] BOT-3 CRASHED: {e}")
                response = "I encountered a system error while searching. Please try again later."
                bot_used_final = "BOT-3"
                
        # Skip old logic blocks by not including them in replacement if I replace the whole thing properly
        # But since I am editing existing file, I must target existing content exactly.


        

        
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
        
        ctx["final_response"] = response
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
        # Final summary (User-Requested Format)
        logger.info(f"[{ctx['query_id']}] " + "="*70)
        
        q_text = ctx.get('query', 'N/A')
        
        # Determine Category
        scope_reason = ctx.get('scope', {}).get('reason', 'unknown')
        if scope_reason == 'greeting':
             cat_text = 'Greeting'
        elif scope_reason and 'out of scope' in str(scope_reason).lower():
             cat_text = 'Out of Scope'
        else:
             cat_text = ctx.get('classifier', {}).get('category', 'Unknown')
             
        bot_text = ctx.get('final_bot', 'UNKNOWN')
        ans_text = ctx.get('final_response', '')
        
        # Truncate answer for clean logging
        ans_preview = (ans_text[:75] + "...") if ans_text and len(ans_text) > 75 else ans_text
        ans_preview = ans_preview.replace("\n", " ") # Single line
        
        status_text = "FAILURE" if ctx.get('error') or (ans_text and ans_text.startswith("[ERROR]")) else "SUCCESS"
        
        if status_text == "SUCCESS" and cat_text != "Greeting" and cat_text != "Out of Scope":
            # Track Usage Stats
            try:
                from core.stats_manager import StatsManager
                StatsManager.increment_query_count(q_text)
            except Exception as e:
                logger.warning(f"Failed to update query stats: {e}")

        logger.info(
            f"[{ctx['query_id']}] SUMMARY: "
            f"Question='{q_text}' | "
            f"Category='{cat_text}' | "
            f"Bot='{bot_text}' | "
            f"Answer='{ans_preview}' | "
            f"Status='{status_text}'"
        )
        logger.info(f"[{ctx['query_id']}] " + "="*70)

def validate_system():
    """Run critical startup checks."""
    try:
        from core.model_manager import ModelManager
        logger.info("--------------------------------------------------")
        logger.info("SYSTEM STARTUP VALIDATION")
        logger.info("--------------------------------------------------")
        
        # 1. Embedding Model
        logger.info("Checking Embedding Model...")
        ModelManager.get_embedder()
        
        # 2. QA Dataset & Index (Specifically Campus Life as requested)
        logger.info("Checking 'Campus Life' Domain Resources...")
        idx, qa = ModelManager.get_domain_qa_resources("Campus Life")
        
        if idx and qa:
            logger.info(f"[PASS] Campus Life Index: {idx.ntotal} vectors")
            logger.info(f"[PASS] Campus Life QA Entries: {len(qa)}")
        else:
            logger.error("[FAIL] Campus Life Resources NOT LOADED.")
            
        logger.info("--------------------------------------------------")
        logger.info("SYSTEM READY")
        logger.info("--------------------------------------------------")
        
    except Exception as e:
        logger.exception(f"Startup Validation Failed: {e}")

# Run validation on module import (effectively app startup)
validate_system()
