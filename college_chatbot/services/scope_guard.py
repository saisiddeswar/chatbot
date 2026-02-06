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


def scope_check(query: str):
    q = query.strip().lower()

    # [OK] If query clearly college related
    if any(k in q for k in COLLEGE_SCOPE_KEYWORDS):
        return True, "college_scope"

    # [FAIL] Out of scope patterns
    for pat in OUT_OF_SCOPE_PATTERNS:
        if re.search(pat, query):
            return False, "out_of_scope"

    # [FAIL] programming scope (unless it's college portal related)
    for pat in PROGRAMMING_PATTERNS:
        if re.search(pat, query):
            return False, "programming_out_of_scope"

    # Neutral (unknown) → allow (do not block)
    return True, "neutral_allow"
