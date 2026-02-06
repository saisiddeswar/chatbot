"""
Audit Logger for System Observability & Accountability.

Logs all routing decisions, confidence scores, retrieval quality, and failures.
Enables debugging, monitoring, and future feedback collection.
"""

import json
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Optional


class AuditLogger:
    """
    Specialized logger for audit trails and system observability.
    
    Tracks:
    - Routing decisions and confidence scores
    - Retrieval quality metrics
    - Failures and error handling
    - User feedback hooks
    """
    
    def __init__(self, name: str = "audit"):
        os.makedirs("logs", exist_ok=True)
        
        self.logger = logging.getLogger(f"audit.{name}")
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            # Main audit log file
            handler = RotatingFileHandler(
                "logs/audit.log",
                maxBytes=10_000_000,  # 10MB
                backupCount=5
            )
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_routing_decision(
        self,
        query_id: str,
        query: str,
        validation_status: str,
        scope_status: str,
        classifier_category: str,
        classifier_confidence: float,
        classifier_probs: Dict[str, float],
        routed_to_bot: str,
        similarity_score: Optional[float] = None,
        reason: Optional[str] = None
    ):
        """Log the complete routing decision for a query."""
        
        entry = {
            "event": "ROUTING_DECISION",
            "query_id": query_id,
            "timestamp": datetime.utcnow().isoformat(),
            "query": query[:200],  # First 200 chars for privacy
            "validation": validation_status,
            "scope": scope_status,
            "classifier": {
                "category": classifier_category,
                "confidence": round(classifier_confidence, 4),
                "probabilities": {k: round(v, 4) for k, v in classifier_probs.items()}
            },
            "routed_to": routed_to_bot,
            "similarity_score": round(similarity_score, 4) if similarity_score else None,
            "reason": reason
        }
        
        self.logger.info(json.dumps(entry))
    
    def log_retrieval_quality(
        self,
        query_id: str,
        bot: str,
        top_k: int,
        scores: list,
        avg_score: float,
        passed_threshold: bool,
        threshold: float,
        num_docs_retrieved: int
    ):
        """Log retrieval quality metrics from FAISS or semantic search."""
        
        entry = {
            "event": "RETRIEVAL_QUALITY",
            "query_id": query_id,
            "bot": bot,
            "timestamp": datetime.utcnow().isoformat(),
            "retrieval": {
                "top_k": top_k,
                "scores": [round(s, 4) for s in scores],
                "avg_score": round(avg_score, 4),
                "num_docs_retrieved": num_docs_retrieved,
                "passed_threshold": passed_threshold,
                "threshold": round(threshold, 4)
            }
        }
        
        self.logger.info(json.dumps(entry))
    
    def log_answer_generation(
        self,
        query_id: str,
        bot: str,
        answer_length: int,
        confidence: float,
        sources: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log when an answer is generated."""
        
        entry = {
            "event": "ANSWER_GENERATION",
            "query_id": query_id,
            "bot": bot,
            "timestamp": datetime.utcnow().isoformat(),
            "answer": {
                "length": answer_length,
                "confidence": round(confidence, 4),
                "num_sources": len(sources) if sources else 0,
                "sources": sources
            },
            "metadata": metadata
        }
        
        self.logger.info(json.dumps(entry))
    
    def log_answer_rejection(
        self,
        query_id: str,
        bot: str,
        reason: str,
        score: Optional[float] = None,
        threshold: Optional[float] = None
    ):
        """Log when a potential answer is rejected due to low quality."""
        
        entry = {
            "event": "ANSWER_REJECTION",
            "query_id": query_id,
            "bot": bot,
            "timestamp": datetime.utcnow().isoformat(),
            "rejection": {
                "reason": reason,
                "score": round(score, 4) if score else None,
                "threshold": round(threshold, 4) if threshold else None
            }
        }
        
        self.logger.info(json.dumps(entry))
    
    def log_error(
        self,
        query_id: str,
        error_type: str,
        error_message: str,
        stage: str,
        stacktrace: Optional[str] = None
    ):
        """Log errors with context for debugging."""
        
        entry = {
            "event": "ERROR",
            "query_id": query_id,
            "timestamp": datetime.utcnow().isoformat(),
            "error": {
                "type": error_type,
                "message": error_message,
                "stage": stage,
                "stacktrace": stacktrace
            }
        }
        
        self.logger.error(json.dumps(entry))
    
    def log_feedback_hook(
        self,
        query_id: str,
        user_id: Optional[str],
        rating: Optional[int],  # 1-5 stars
        comment: Optional[str],
        bot: str,
        correctness: Optional[bool] = None
    ):
        """Log user feedback for future model improvement."""
        
        entry = {
            "event": "USER_FEEDBACK",
            "query_id": query_id,
            "timestamp": datetime.utcnow().isoformat(),
            "feedback": {
                "user_id": user_id,
                "rating": rating,
                "correctness": correctness,
                "comment": comment,
                "bot": bot
            }
        }
        
        self.logger.info(json.dumps(entry))
    
    def log_latency(
        self,
        query_id: str,
        latency_ms: int,
        stages: Optional[Dict[str, int]] = None
    ):
        """Log request latency and stage breakdown."""
        
        entry = {
            "event": "LATENCY",
            "query_id": query_id,
            "timestamp": datetime.utcnow().isoformat(),
            "latency": {
                "total_ms": latency_ms,
                "stages": stages
            }
        }
        
        self.logger.info(json.dumps(entry))


# Global audit logger instance
_audit_logger = None

def get_audit_logger(name: str = "system") -> AuditLogger:
    """Get or create global audit logger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(name)
    return _audit_logger
