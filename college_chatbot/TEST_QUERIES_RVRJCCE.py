"""
Test queries to validate RVRJCCE data integration in all three bots

This script provides sample queries organized by category that can be used to verify
that Bot-1, Bot-2, and Bot-3 properly respond with RVRJCCE-specific information.

Usage:
    Run individual queries through the main.py application or use this for manual testing
"""

# Sample test queries organized by category

TEST_QUERIES = {
    "college_information": {
        "queries": [
            "Tell me about RVRJCCE",
            "Where is RVRJCCE located?",
            "What does RVRJCCE stand for?",
            "Give me information about the college",
            "What is the full name of RVRJCCE?",
        ],
        "expected_topics": ["location", "Guntur", "engineering", "college"]
    },
    
    "undergraduate_programs": {
        "queries": [
            "What B.Tech programs does RVRJCCE offer?",
            "List all engineering programs",
            "How many UG programs are there?",
            "Tell me about CSE AI and ML",
            "What is the difference between CSE and CSE Data Science?",
            "How many seats in Civil Engineering?",
            "What specialized CSE tracks are available?",
            "Tell me about Data Science program",
            "Which program has the most seats?",
        ],
        "expected_topics": ["B.Tech", "CSE", "programs", "seats", "specialization"]
    },
    
    "postgraduate_programs": {
        "queries": [
            "What PG programs does RVRJCCE offer?",
            "Tell me about MCA program",
            "What is the MBA program like?",
            "How many M.Tech specializations are available?",
            "What PG programs exist?",
        ],
        "expected_topics": ["M.Tech", "MBA", "MCA", "postgraduate"]
    },
    
    "admission_process": {
        "queries": [
            "How do I apply for RVRJCCE?",
            "What is the admission process?",
            "What is EAPCET counselling?",
            "Tell me about management quota",
            "What is lateral entry?",
            "How to get admission?",
            "What are the eligibility criteria?",
            "When are admissions open?",
            "How many seats are filled through management quota?",
            "What percentage of seats are via EAPCET?",
        ],
        "expected_topics": ["EAPCET", "admission", "eligibility", "management"]
    },
    
    "facilities": {
        "queries": [
            "Tell me about hostel facilities",
            "What is the library like?",
            "Are there transport facilities?",
            "Tell me about the canteen",
            "What sports facilities are available?",
            "Is there a gymnasium?",
            "What are campus facilities?",
            "Can I get accommodation on campus?",
        ],
        "expected_topics": ["hostel", "library", "canteen", "transport", "sports"]
    },
    
    "placements": {
        "queries": [
            "Which companies visit RVRJCCE?",
            "What is the placement record?",
            "How many recruiters come?",
            "Tell me about placements",
            "What is the average salary package?",
            "Which batch is being placed?",
            "Are there internship opportunities?",
        ],
        "expected_topics": ["companies", "placement", "TCS", "Cognizant", "recruiters"]
    },
    
    "student_services": {
        "queries": [
            "How do I get a bonafide certificate?",
            "What student services are available?",
            "Tell me about grievance redressal",
            "What is the anti-ragging policy?",
            "Where is the student wellness center?",
            "How to get transcripts?",
            "What support services exist?",
            "Tell me about counseling services",
        ],
        "expected_topics": ["bonafide", "certificate", "grievance", "student", "services"]
    },
    
    "fees_and_scholarships": {
        "queries": [
            "What is the fee structure?",
            "Are there scholarships available?",
            "How to pay fees online?",
            "What is the total fee?",
            "Tell me about scholarship opportunities",
            "Can I pay fees in installments?",
            "What scholarships does RVRJCCE offer?",
        ],
        "expected_topics": ["fee", "scholarship", "payment", "financial"]
    },
    
    "campus_life": {
        "queries": [
            "Tell me about campus life",
            "What clubs are available?",
            "What is NCC and NSS?",
            "Tell me about cultural activities",
            "Are there tech clubs?",
            "What co-curricular activities exist?",
            "Tell me about annual events",
        ],
        "expected_topics": ["NCC", "NSS", "club", "activity", "cultural"]
    },
    
    "research_and_innovation": {
        "queries": [
            "Tell me about research centers",
            "What is RJ E-NEST?",
            "Tell me about innovation facilities",
            "What research opportunities exist?",
            "What is AICTE-IDEA Lab?",
            "Tell me about the Institution Innovation Council",
        ],
        "expected_topics": ["research", "innovation", "E-NEST", "AICTE"]
    },
    
    "accreditations": {
        "queries": [
            "What accreditations does RVRJCCE have?",
            "Is RVRJCCE NAAC accredited?",
            "Tell me about college rankings",
            "What is the autonomous status?",
            "What accrediting bodies approve RVRJCCE?",
        ],
        "expected_topics": ["NAAC", "AICTE", "accreditation", "autonomous"]
    },
    
    "contact_information": {
        "queries": [
            "What is the college contact number?",
            "How do I contact admissions?",
            "What is the college email?",
            "Give me college contact details",
            "What is the admissions phone number?",
            "How to contact the principal?",
        ],
        "expected_topics": ["contact", "phone", "number", "email", "address"]
    }
}


# Expected responses for each bot type

EXPECTED_BOT_RESPONSES = {
    "bot1_rule_based": {
        "description": "Bot-1 should provide exact, deterministic AIML pattern-matched responses",
        "characteristics": [
            "Consistent across multiple requests",
            "Pre-written template responses",
            "Fast response time",
            "Exact matches for FAQ-style queries",
            "May not handle complex variations well"
        ]
    },
    
    "bot2_semantic": {
        "description": "Bot-2 should find similar Q&A pairs from dataset and return answers",
        "characteristics": [
            "Flexible to paraphrased questions",
            "Similarity-based matching",
            "Should retrieve from Q&A dataset",
            "Confidence scores indicate match quality",
            "May vary slightly for different phrasings"
        ]
    },
    
    "bot3_rag": {
        "description": "Bot-3 should retrieve from documents and generate grounded answers",
        "characteristics": [
            "Context-aware responses",
            "Grounded in actual documents",
            "Can handle complex questions",
            "May include document citations",
            "Reduces hallucination through retrieval"
        ]
    }
}


# Test scenarios and expected outcomes

TEST_SCENARIOS = {
    "exact_faq_queries": {
        "description": "Queries that exactly match AIML patterns - Bot-1 should handle these",
        "queries": [
            "Tell me about RVRJCCE",
            "What B.Tech programs do you offer?",
            "How do I apply?",
        ],
        "expected_bot": "BOT-1",
        "reason": "Exact AIML pattern matches"
    },
    
    "similar_faq_queries": {
        "description": "Queries similar to Q&A dataset - Bot-2 should handle these",
        "queries": [
            "Which engineering courses does the college have?",
            "What is the application process?",
            "Which companies hire from here?",
        ],
        "expected_bot": "BOT-2",
        "reason": "Similarity matching to Q&A pairs"
    },
    
    "complex_queries": {
        "description": "Complex queries needing document context - Bot-3 should handle these",
        "queries": [
            "Tell me in detail about the CSE AI&ML program structure",
            "What is the complete admissions process with all steps?",
            "Describe the entire student life at RVRJCCE",
        ],
        "expected_bot": "BOT-3",
        "reason": "Requires comprehensive document retrieval and synthesis"
    }
}


# Testing checklist

TESTING_CHECKLIST = """
[OK] RVRJCCE Data Integration Testing Checklist

Before deployment, verify:

1. Bot-1 (Rule-Based) Tests:
   ☐ AIML file loads without errors
   ☐ Sample AIML queries return responses
   ☐ Responses contain RVRJCCE-specific information
   ☐ Multiple AIML files load correctly
   ☐ No conflicts between AIML patterns

2. Bot-2 (Semantic QA) Tests:
   ☐ FAISS index builds successfully
   ☐ Sample Q&A queries return relevant answers
   ☐ Confidence scores are calculated
   ☐ Both default and RVRJCCE Q&A pairs are indexed
   ☐ Vector embeddings are correct dimension
   ☐ Query embeddings and similarity work

3. Bot-3 (RAG) Tests:
   ☐ FAISS index builds with documents
   ☐ Documents are properly chunked
   ☐ Metadata is saved and loaded
   ☐ All three documents are included
   ☐ Chunk retrieval works
   ☐ Embeddings are computed correctly

4. Routing Tests:
   ☐ Safety checks don't block valid queries
   ☐ Scope guards allow college queries
   ☐ Classifier routes to appropriate bot
   ☐ Confidence thresholds work correctly
   ☐ Fallback routing functions properly

5. End-to-End Tests:
   ☐ Sample queries complete full pipeline
   ☐ Responses are RVRJCCE-specific
   ☐ No errors in logs
   ☐ Response times are acceptable
   ☐ Audit logs record interactions

6. Data Coverage Tests:
   ☐ All programs mentioned in responses
   ☐ All facilities described
   ☐ All services explained
   ☐ Contact information provided
   ☐ Admissions details correct
   ☐ Placement info accurate

7. Performance Tests:
   ☐ Queries respond < 500ms typically
   ☐ No memory leaks observed
   ☐ FAISS indices load quickly
   ☐ AIML pattern matching is fast
   ☐ Embeddings computed efficiently

8. Integration Tests:
   ☐ Works with existing pipeline
   ☐ Backward compatible with old data
   ☐ Metrics evaluation runs successfully
   ☐ No conflicts with other components

"""


# Sample testing code

SAMPLE_TEST_CODE = """
# Example: Testing Bot-3 with RVRJCCE query

from bots.bot3_rag import bot3_answer

query = "Tell me about the CSE AI and ML program"
history = []
query_id = "test_001"

response = bot3_answer(query, history, query_id)
print(f"Query: {query}")
print(f"Response: {response}")

# Expected: Response mentioning CSE AI&ML program details, 180 seats,
# specialization tracks, career opportunities, etc.


# Example: Testing Bot-2 with RVRJCCE query

from bots.bot2_semantic import bot2_answer

query = "What engineering programs are available?"
query_id = "test_002"

answer, confidence, is_confident = bot2_answer(query, query_id)
print(f"Query: {query}")
print(f"Answer: {answer}")
print(f"Confidence: {confidence}")
print(f"Confident: {is_confident}")

# Expected: Answer listing B.Tech programs with seat counts


# Example: Testing Bot-1 with RVRJCCE query

from bots.rule_bot import get_rule_response

query = "Tell me about RVRJCCE"
response = get_rule_response(query)
print(f"Query: {query}")
print(f"Response: {response}")

# Expected: AIML pattern-matched response about college

"""


if __name__ == "__main__":
    print("RVRJCCE Data Integration - Test Queries Reference")
    print("=" * 70)
    print()
    
    # Print all test queries
    for category, data in TEST_QUERIES.items():
print(f"\n[DOCS] {category.upper().replace('_', ' ')}")
        print("-" * 70)
        for query in data["queries"]:
            print(f"  • {query}")
        print(f"  Expected topics: {', '.join(data['expected_topics'])}")
    
    print("\n\n" + "=" * 70)
    print("For more details, see the test file or documentation")
