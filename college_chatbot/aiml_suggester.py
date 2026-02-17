"""
AIML Pattern Suggester

Analyzes audit logs to identify high-confidence Semantic Bot (Bot-2) answers
that are frequent candidates for conversion to Rule-Based (Bot-1) patterns.

Logic:
1. Parse logs/audit.log
2. Filter for successful BOT-2 responses with High Similarity (> 0.85)
3. Group by normalized query
4. Identify frequent queries (count >= threshold)
5. Generate AIML template suggestions

Usage:
    python aiml_suggester.py
"""

import json
import os
import re
from collections import Counter
from typing import Dict, List
import xml.etree.ElementTree as ET
from xml.dom import minidom

from config.settings import settings
from core.logger import get_logger

# Setup logger
logger = get_logger("aiml_suggester")

AUDIT_LOG_FILE = "logs/audit.log"
SUGGESTIONS_FILE = "data/suggested_rules.xml"
MIN_FREQ_THRESHOLD = 3
HIGH_SIMILARITY_THRESHOLD = 0.85

def parse_audit_logs() -> List[Dict]:
    """Read and parse audit logs."""
    entries = []
    if not os.path.exists(AUDIT_LOG_FILE):
        logger.warning(f"Audit log file not found: {AUDIT_LOG_FILE}")
        return entries

    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                # Log lines are "DATE | LEVEL | MESSAGE"
                # But audit_logger.py logs JSON in the message part.
                # Format: "%(asctime)s | %(levelname)s | %(message)s"
                
                parts = line.split(" | ", 2)
                if len(parts) < 3:
                    continue
                
                json_part = parts[2].strip()
                try:
                    entry = json.loads(json_part)
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.error(f"Error reading audit logs: {e}")
        
    return entries

def identify_candidates(entries: List[Dict]) -> Dict[str, List[str]]:
    """
    Identify queries suitable for AIML conversion.
    Returns: {query: [list of answers received]}
    """
    candidates = {}
    
    for entry in entries:
        # We look for ROUTING_DECISION where routed_to="BOT-2" 
        # OR ANSWER_GENERATION where bot="BOT-2" (if we logged score there)
        
        # Actually, audit_logger.log_routing_decision logs 'similarity_score'
        
        if entry.get("event") == "ROUTING_DECISION":
            routed_to = entry.get("routed_to")
            score = entry.get("similarity_score")
            
            if routed_to == "BOT-2" and score is not None:
                if score >= HIGH_SIMILARITY_THRESHOLD:
                    query = entry.get("query", "").strip().upper()
                    # Basic cleanup
                    query = re.sub(r'[^\w\s]', '', query) # Remove punctuation
                    
                    if query:
                        if query not in candidates:
                            candidates[query] = []
                        # We don't have the answer text in routing decision...
                        # We need to cross-reference or just log the hit.
                        # For now, we'll just count the query.
                        
    # To get the ANSWER, we might need to look at ANSWER_GENERATION events
    # But those might not link back to the query text easily unless query_id matches.
    
    # Improved strategy: Build a map of query_id -> query
    query_map = {}
    answer_map = {}
    
    for entry in entries:
        qid = entry.get("query_id")
        if not qid:
            continue
            
        if entry.get("event") == "ROUTING_DECISION":
            query_map[qid] = {
                "query": entry.get("query"),
                "score": entry.get("similarity_score"),
                "bot": entry.get("routed_to")
            }
            
        elif entry.get("event") == "ANSWER_GENERATION":
            if entry.get("bot") == "BOT-2":
                 # We don't log the full answer text in ANSWER_GENERATION for privacy/size usually, 
                 # but let's check audit_logger.py...
                 # It logs 'answer': {'length': ...}
                 # It does NOT log the text. 
                 
                 # However, main.py logs the answer summary! 
                 # "SUMMARY: Question='...' | Answer='...'"
                 pass

    # Since we can't easily get the *exact* answer text from structured audit logs to generate the template,
    # we will generate a template with a PLACEHOLDER answer.
    # The admin must fill it in. The value is identifying the *Demand*.
    
    filtered_candidates = {}
    
    # Count frequencies
    query_counts = Counter()
    
    for qid, data in query_map.items():
        if data["bot"] == "BOT-2" and data["score"] and data["score"] >= HIGH_SIMILARITY_THRESHOLD:
            # Normalize
            q_norm = re.sub(r'[^\w\s]', '', data["query"]).strip().upper()
            if len(q_norm) > 5: # Ignore super short junk
                query_counts[q_norm] += 1
                
    for query, count in query_counts.items():
        if count >= MIN_FREQ_THRESHOLD:
            filtered_candidates[query] = count
            
    return filtered_candidates

def generate_xml(candidates: Dict[str, int]):
    """Generate AIML XML file."""
    if not candidates:
        logger.info("No candidates found for AIML suggestion.")
        return

    root = ET.Element("aiml")
    comment = ET.Comment(f" Auto-generated suggestions based on high-frequency Semantic Matches. Generated: {os.times()} ")
    root.append(comment)
    
    for query, count in candidates.items():
        category = ET.SubElement(root, "category")
        
        pattern = ET.SubElement(category, "pattern")
        pattern.text = query
        
        template = ET.SubElement(category, "template")
        template.text = f"<!-- TODO: Insert Answer for '{query}' (Requested {count} times) -->"
        
    # Prettify
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
    
    with open(SUGGESTIONS_FILE, "w", encoding="utf-8") as f:
        f.write(xml_str)
        
    logger.info(f"Generated {len(candidates)} AIML suggestions in {SUGGESTIONS_FILE}")

if __name__ == "__main__":
    logger.info("Starting AIML Suggester...")
    entries = parse_audit_logs()
    candidates = identify_candidates(entries)
    generate_xml(candidates)
