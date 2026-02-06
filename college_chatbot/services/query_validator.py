import re
from typing import Tuple

# ============== GIBBERISH & FORMAT VALIDATION ==============
GIBBERISH_PATTERNS = [
    r"^(asdf|qwer|zxcv|1234|0000)+$",
    r"^(....)\1+$",   # repeated same chunk like abcdabcdabcd
    r"^[0-9]+$",      # only digits (unless it's a numeric query like "123 fees")
]

# ============== SAFETY: ABUSE / HARASSMENT ==============
ABUSE_PATTERNS = [
    r"(?i)\b(fuck|bitch|madarchod|chutiya)\b",
    r"(?i)\b(asshole|bastard|damn|crap)\b",
    r"(?i)\b(idiot|moron|stupid|retard)\b",
]

# ============== SAFETY: SELF-HARM / VIOLENCE ==============
SELF_HARM_PATTERNS = [
    r"(?i)\b(kill|suicide|hang|cut wrist|slit|overdose|jump off)\b",
    r"(?i)\b(hurt myself|harm myself|end life|die|die soon)\b",
]

# ============== SAFETY: PROMPT INJECTION ==============
# Common prompt injection attack patterns
PROMPT_INJECTION_PATTERNS = [
    r"(?i)\bignore previous|disregard|forget|system prompt\b",
    r"(?i)\brole-play as|pretend|you are now|you are a\b",
    r"(?i)\bfrom now on|henceforth|starting now\b",
    r"(?i)\b(follow these instructions|new instructions|updated rules)\b",
    # SQL injection patterns (unlikely but check)
    r"(?i)\b(DROP|DELETE|INSERT|UPDATE|SELECT|UNION|WHERE 1=1)\b",
    # Python code injection
    r"(?i)\b(eval|exec|import|__import__|compile|globals|locals)\b",
]

# ============== SAFETY: SENSITIVE DATA HARVESTING ==============
# Queries trying to extract lists of all students, admin accounts, etc.
SENSITIVE_EXTRACTION_PATTERNS = [
    r"(?i)\b(all student names|list of password|admin account|secret|api key|access token)\b",
    r"(?i)\b(all emails|all phone number|database dump|backup)\b",
]


def is_gibberish(q: str) -> bool:
    """Check if query is gibberish or nonsensical."""
    q_clean = q.strip().lower().replace(" ", "")
    
    # Empty or too short
    if len(q_clean) <= 2:
        return True

    # Too many special characters
    special_ratio = sum(not ch.isalnum() for ch in q) / max(len(q), 1)
    if special_ratio > 0.5:
        return True

    # Matches gibberish patterns
    for pat in GIBBERISH_PATTERNS:
        if re.match(pat, q_clean):
            return True

    return False


def is_self_harm_or_violence(q: str) -> bool:
    """Detect if query contains self-harm or violence keywords."""
    for pat in SELF_HARM_PATTERNS:
        if re.search(pat, q):
            return True
    return False


def is_abusive(q: str) -> bool:
    """Detect if query contains abusive language."""
    for pat in ABUSE_PATTERNS:
        if re.search(pat, q):
            return True
    return False


def is_prompt_injection(q: str) -> bool:
    """Detect if query is attempting prompt injection."""
    for pat in PROMPT_INJECTION_PATTERNS:
        if re.search(pat, q):
            return True
    return False


def is_sensitive_extraction_attempt(q: str) -> bool:
    """Detect if query is trying to extract sensitive data."""
    for pat in SENSITIVE_EXTRACTION_PATTERNS:
        if re.search(pat, q):
            return True
    return False


def validate_query(query: str) -> Tuple[bool, str]:
    """
    Comprehensive query validation with safety checks.
    
    Returns:
        (is_valid: bool, reason: str)
    """
    q = query.strip()

    # 1) EMPTY CHECK
    if not q:
        return False, "Query is empty. Please type your question."

    # 2) SAFETY: SELF-HARM FIRST (CRITICAL)
    if is_self_harm_or_violence(q):
        return False, (
            "[ALERT] **Crisis Support** [ALERT]\n\n"
            "If you're having thoughts of self-harm, please reach out:\n"
            "- National Suicide Prevention Lifeline: 988 (US)\n"
            "- International Association for Suicide Prevention: https://www.iasp.info/resources/Crisis_Centres/\n"
            "- Your university counseling center or campus healthcare\n"
            "\nI'm here to help with academic questions, not crisis support."
        )

    # 3) SAFETY: ABUSIVE LANGUAGE
    if is_abusive(q):
        return False, "Please use respectful language. This assistant is here to help you."

    # 4) SAFETY: PROMPT INJECTION
    if is_prompt_injection(q):
        return False, (
            "[WARNING] **Invalid Query**\n\n"
            "Your query appears to contain instructions to modify my behavior. "
            "I can only answer questions about college administrative support.\n"
            "Please ask a direct question."
        )

    # 5) SAFETY: SENSITIVE DATA EXTRACTION
    if is_sensitive_extraction_attempt(q):
        return False, (
            "[DENIED] **Access Denied**\n\n"
            "I cannot provide sensitive student or administrative data. "
            "For official information, please contact the registrar or student services directly."
        )

    # 6) FORMAT: GIBBERISH
    if is_gibberish(q):
        return False, "Your message looks invalid. Please ask a proper question."

    # 7) LENGTH: MINIMUM CONTEXT
    if len(q.split()) < 2:
        return False, "Please provide more detail. Example: 'What is the hostel fee?'"

    # [OK] VALIDATION PASSED
    return True, "valid"

