import re

COLLEGE_SCOPE_KEYWORDS = [
    "admission", "apply", "application", "eligibility", "documents",
    "fees", "fee", "refund", "scholarship",
    "hostel", "mess", "transport", "bus",
    "exam", "results", "revaluation", "hall ticket",
    "semester", "timetable", "syllabus", "attendance", "internal",
    "department", "course", "branch", "faculty",
    "bonafide", "noc", "certificate", "id card",
    "placement", "internship", "training", "cdc", "tpo",
    "library", "lab", "campus", "club"
]

OUT_OF_SCOPE_PATTERNS = [
    r"(?i)\bbitcoin|crypto|stock|share market\b",
    r"(?i)\bvirat|kohli|cricket|ipl|football|messi|ronaldo\b",
    r"(?i)\bmovie|actor|actress|netflix|anime\b",
    r"(?i)\bpolitics|election|minister|prime minister\b",
    r"(?i)\bgirlfriend|boyfriend|love letter|breakup\b",
    r"(?i)\bblack hole|galaxy|universe|space\b",
]

PROGRAMMING_PATTERNS = [
    r"(?i)\bpython|java|c\+\+|javascript|react|node|flask|django\b",
    r"(?i)\bwrite code|program|bug|error|exception|stack trace\b",
    r"(?i)\bleetcode|dsa|binary search|dp\b",
]


GREETING_KEYWORDS = ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening"]

OUT_OF_SCOPE_RESPONSE = "I am a college bot. I can only answer questions related to RVR&JC College administration, admissions, and campus life."

def is_greeting(query: str):
    """Check if the query is just a greeting."""
    q = query.strip().lower()
    # Remove punctuation
    q = re.sub(r'[^\w\s]', '', q)
    return q in GREETING_KEYWORDS

def scope_check(query: str):
    q = query.strip().lower()

    # [OK] If query is a greeting, allow it (will be handled by main or bots)
    if is_greeting(query):
        return True, "greeting"

    # [FAIL] Out of scope patterns
    for pat in OUT_OF_SCOPE_PATTERNS:
        if re.search(pat, query):
            return False, "out_of_scope"

    # [FAIL] Programming patterns (unless explicitly about curriculum)
    # We might want to allow "python course" but block "write python code"
    for pat in PROGRAMMING_PATTERNS:
        if re.search(pat, query):
             # Hard block if purely asking for code
             if "code" in q or "program" in q:
                 return False, "programming_out_of_scope"


    # [OK] If query clearly college related
    if any(k in q for k in COLLEGE_SCOPE_KEYWORDS):
        return True, "college_scope"

    # [NEUTRAL] - If it's very short and not matched, it might be out of scope
    # User said: "if they ask out of scope apart from admistration or colege it should say i am college bot"
    # So if it doesn't match college keywords and is not a greeting, we should be strict?
    # But RAG queries might not contain keywords.
    # Let's keep it permissive but rely on Bot 3 to say "No Info" if it really doesn't know.
    
    return True, "neutral_allow"

# ================= RAG Safety =================
RAG_FORBIDDEN_PATTERNS = [
    r"(?i)\blocation|address|where is the college|map\b",
    r"(?i)\bphone|contact|number|email|call\b",
    r"(?i)\btiming|opening hours|working hours|office hours\b",
]

def is_rag_forbidden(query: str) -> bool:
    """
    Check if query touches topics forbidden for RAG (Location, Contact, Timings).
    These MUST be answered by Rule-Based Bot to prevent hallucinations.
    """
    for pat in RAG_FORBIDDEN_PATTERNS:
        if re.search(pat, query):
            return True
    return False

