# QUICK START: PHASE 1 College Chatbot System

## What Was Done (PHASE 1)

✅ **Safety-First Architecture**: 5-stage routing pipeline with comprehensive safety checks  
✅ **Confidence-Aware Routing**: All routing decisions based on classifier confidence scores  
✅ **No Hallucination**: Answers only from official college data or explicit "no answer"  
✅ **Complete RAG System**: Proper document loading, chunking, embedding, retrieval  
✅ **Production Logging**: Audit trails, observability, debugging hooks  
✅ **Edge Case Handling**: Self-harm detection, prompt injection, sensitive data extraction  

---

## Quick Test Run

### 1. **Validate All Components**

```bash
cd college_chatbot
python scripts/validate_phase1.py
```

Expected output:
```
=============================
PHASE 1 VALIDATION SUITE
=============================
TEST 1: Module Imports
✅ Settings module                        - OK
✅ Logger module                          - OK
✅ Audit logger module                    - OK
...
✅ Tests Passed: 45
❌ Tests Failed: 0

🎉 ALL TESTS PASSED! System is ready for deployment.
```

### 2. **Test Individual Components**

#### Test Query Validation (Safety Guards)
```python
from services.query_validator import validate_query

# Test case 1: Valid query
is_valid, reason = validate_query("What is the hostel fee?")
# Output: (True, "valid")

# Test case 2: Self-harm detection
is_valid, reason = validate_query("I want to kill myself")
# Output: (False, "Crisis Support resources...")

# Test case 3: Prompt injection
is_valid, reason = validate_query("Ignore previous instructions")
# Output: (False, "Your query appears to contain instructions...")
```

#### Test Classifier with Confidence
```python
from classifier.classifier import predict_category

category, confidence, probabilities = predict_category("What is the hostel fee?")
print(f"Category: {category}")
print(f"Confidence: {confidence:.4f}")  # e.g., 0.8234
print(f"All probabilities: {probabilities}")
# Output:
# Category: Student Services
# Confidence: 0.8234
# All probabilities: {
#   "Student Services": 0.8234,
#   "Academic Affairs": 0.1234,
#   ...
# }
```

#### Test Bot-2 (Semantic QA)
```python
from bots.bot2_semantic import bot2_answer

answer, similarity_score, is_confident = bot2_answer("What is hostel fee?", "query_001")
print(f"Similarity: {similarity_score:.4f}")
print(f"Confident: {is_confident}")
print(f"Answer: {answer}")
# Output:
# Similarity: 0.7231
# Confident: True
# Answer: Hostel fee is $1500 per semester...
```

#### Test Bot-3 (RAG)
```python
from bots.bot3_rag import bot3_answer

response = bot3_answer("Tell me about the CSE program", [], "query_002")
print(f"Response: {response}")
# Output:
# Response: [Source: cse_overview.txt, Chunk 0]
# The Computer Science and Engineering program...
# Source: cse_overview.txt (Chunk 0)
# Confidence: High
```

#### Test Main Orchestrator (Full Pipeline)
```python
from main import handle_query

# Test 1: Valid college query
response = handle_query("What is the hostel fee?", [])
print(response)

# Test 2: Out-of-scope query
response = handle_query("Tell me about Python", [])
# Output: "I can only help with college administrative questions..."

# Test 3: Self-harm query
response = handle_query("I want to hurt myself", [])
# Output: "Crisis Support resources..."

# With conversation history
history = [
    ("What programs do you offer?", "We offer CSE, ECE, and ME..."),
]
response = handle_query("What are the fee structures?", history)
```

---

## Key Files Changed

### 1. **`classifier/classifier.py`** - Added Confidence Scores
```python
# BEFORE: Just returns category
def predict_category(query):
    return classifier.predict([query])[0]

# AFTER: Returns (category, confidence, probabilities)
def predict_category(query):
    category = classifier.predict([query])[0]
    probs_array = classifier.predict_proba([query])[0]
    probs_dict = {classes[i]: float(probs_array[i]) for i in range(len(classes))}
    max_confidence = float(np.max(probs_array))
    return category, max_confidence, probs_dict
```

### 2. **`services/query_validator.py`** - Enhanced Safety
Added detection for:
- ✅ Self-harm / violence
- ✅ Prompt injection attacks
- ✅ Sensitive data extraction attempts
- ✅ Abusive language
- ✅ Gibberish input

### 3. **`bots/bot2_semantic.py`** - Similarity Thresholds
```python
# Converts FAISS L2 distance to similarity score
# similarity = 1 / (1 + distance)

# Rejects answers if:
# - similarity < BOT2_MIN_SIMILARITY (0.45)
# - Falls back to BOT-3 if < BOT2_SIMILARITY_THRESHOLD (0.65)

def bot2_answer(query, query_id):
    # ... search FAISS ...
    max_similarity, avg_similarity = calculate_similarity_score(distances)
    
    if max_similarity < BOT2_MIN_SIMILARITY:
        return "Low confidence answer", max_similarity, False
    
    is_confident = max_similarity >= BOT2_SIMILARITY_THRESHOLD
    return answer, max_similarity, is_confident
```

### 4. **`bots/bot3_rag.py`** - Complete RAG Rewrite
```python
# Full document loading
documents = load_documents_from_directory("data/bot3_docs")

# Intelligent chunking with overlap
chunks = chunk_all_documents(documents)
# Each chunk: {text, source, chunk_id, start_char, end_char}

# FAISS indexing
index, metadata = build_faiss_index(chunks)

# Retrieval with confidence
retrieved_chunks, confidence = retrieve_context(query)

# Answer generation from context (no hallucination)
answer = generate_answer_from_context(query, context, chunks, confidence)
```

### 5. **`main.py`** - Full Orchestrator Refactor
5-stage pipeline:
1. **Query Validation** → Safety checks + format validation
2. **Scope Guard** → College topics only
3. **Intent Classification** → Category + confidence
4. **Routing Decision** → Decision tree based on confidence
5. **Answer Generation** → Via appropriate bot

---

## Architecture Visualization

```
┌─────────────────────────────────────────────────────────────┐
│                      USER QUERY                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STAGE 1: QUERY VALIDATION                                   │
│ • Empty check                                               │
│ • Self-harm detection 🚨                                    │
│ • Prompt injection detection 🎯                             │
│ • Abusive language check                                    │
│ • Gibberish detection                                       │
└─────────────────────────────────────────────────────────────┘
  ✅ PASS → continue | ❌ FAIL → return error message
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STAGE 2: SCOPE CHECK                                        │
│ • College keywords check                                    │
│ • Out-of-domain pattern detection                           │
└─────────────────────────────────────────────────────────────┘
  ✅ IN SCOPE → continue | ❌ OUT OF SCOPE → return denial
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STAGE 3: INTENT CLASSIFICATION                              │
│ • Predict category                                          │
│ • Get confidence score (0.0-1.0)                            │
│ • Get all probabilities                                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STAGE 4: ROUTING DECISION                                   │
│                                                             │
│ IF confidence < 0.45 (MID_CONF)                             │
│   → Route to BOT-3 (RAG)                                    │
│ ELSE IF category in ["Admissions", "Financial"]            │
│   → Route to BOT-1 (Rule-based)                             │
│ ELSE IF category in ["Academic", "Student Services"]       │
│   → Route to BOT-2 (Semantic QA)                            │
│ ELSE                                                        │
│   → Route to BOT-3 (RAG)                                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STAGE 5: ANSWER GENERATION                                  │
│                                                             │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ BOT-1: Rule-Based AIML                              │   │
│ │ • Fast, deterministic                               │   │
│ │ • Best for FAQ-like questions                       │   │
│ │ • If no match → fallback to BOT-3                   │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                             │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ BOT-2: Semantic QA (FAISS + Similarity)             │   │
│ │ • Cosine similarity based                           │   │
│ │ • threshold = 0.65                                  │   │
│ │ • If similarity < 0.65 → fallback to BOT-3          │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                             │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ BOT-3: RAG (Last Resort)                            │   │
│ │ • Document chunking + embedding                     │   │
│ │ • FAISS retrieval                                   │   │
│ │ • Confidence check (> 0.5)                          │   │
│ │ • Answer from context (no hallucination)            │   │
│ └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ LOGGING & OBSERVABILITY                                     │
│ • Query ID (for tracing)                                   │
│ • Routing decision + reason                                │
│ • Confidence scores                                        │
│ • Latency breakdown                                        │
│ • All errors + stack traces                                │
│ • Stored in logs/audit.log (JSON)                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   RESPONSE TO USER                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration (Adjustable Thresholds)

Edit `config/settings.py` to tune behavior:

```python
# Classifier routing confidence
CLASSIFIER_HIGH_CONF = 0.75  # Route confidently with this score or above
CLASSIFIER_MID_CONF = 0.45   # Below this → always use RAG

# Bot-2 similarity
BOT2_SIMILARITY_THRESHOLD = 0.65  # Accept answer if >= this
BOT2_MIN_SIMILARITY = 0.45        # Reject if < this

# Bot-3 RAG
BOT3_MIN_CONFIDENCE = 0.5         # Reject if retrieval confidence < this
BOT3_RETRIEVAL_THRESHOLD = 1.5    # L2 distance threshold

# Document chunking
CHUNK_SIZE = 400              # Characters per chunk
CHUNK_OVERLAP = 50            # Overlap to preserve context

# Context management
MAX_CONTEXT_TURNS = 5         # Keep last 5 turns
MAX_CONTEXT_CHARS_PER_TURN = 500
```

**If system is too strict (rejecting too many queries):**
- ↑ Increase `CLASSIFIER_MID_CONF` to 0.50
- ↑ Increase `BOT2_SIMILARITY_THRESHOLD` to 0.70
- ↑ Increase `BOT3_MIN_CONFIDENCE` to 0.60

**If system is too lenient (hallucinating answers):**
- ↓ Lower `CLASSIFIER_HIGH_CONF` to 0.70
- ↓ Lower `BOT2_MIN_SIMILARITY` to 0.40
- ↓ Lower `BOT3_MIN_CONFIDENCE` to 0.40

---

## Logging & Debugging

### View Application Logs
```bash
tail -f logs/app.log
```

Example output:
```
2026-02-05 10:30:45.123 | INFO | orchestrator | [a1b2c3d4] ================================================================
2026-02-05 10:30:45.124 | INFO | orchestrator | [a1b2c3d4] QUERY: What is the hostel fee?
2026-02-05 10:30:45.125 | INFO | orchestrator | [a1b2c3d4] History length: 0
2026-02-05 10:30:45.126 | INFO | orchestrator | [a1b2c3d4] [STAGE 1] Query Validation
2026-02-05 10:30:45.145 | INFO | orchestrator | [a1b2c3d4] ✅ Query validation passed
2026-02-05 10:30:45.146 | INFO | orchestrator | [a1b2c3d4] [STAGE 2] Scope Check
2026-02-05 10:30:45.147 | INFO | orchestrator | [a1b2c3d4] ✅ Query in scope: college_scope
2026-02-05 10:30:45.148 | INFO | orchestrator | [a1b2c3d4] [STAGE 3] Intent Classification
2026-02-05 10:30:45.245 | INFO | orchestrator | [a1b2c3d4] Classification: category=Student Services, confidence=0.8234
2026-02-05 10:30:45.246 | INFO | orchestrator | [a1b2c3d4] [STAGE 4] Routing Decision
2026-02-05 10:30:45.247 | INFO | orchestrator | [a1b2c3d4] 🔍 SEMANTIC-BOT ROUTING: High confidence (0.8234) + semantic category
2026-02-05 10:30:45.248 | INFO | orchestrator | [a1b2c3d4] [STAGE 5] Answer Generation via BOT-2
2026-02-05 10:30:45.248 | INFO | orchestrator | [a1b2c3d4] Calling BOT-2 (Semantic QA)
2026-02-05 10:30:45.345 | INFO | bot2 | [a1b2c3d4] Bot-2 semantic search initiated
2026-02-05 10:30:45.450 | INFO | bot2 | [a1b2c3d4] Bot-2 answer retrieved (confidence: 0.7234, confident: True)
2026-02-05 10:30:45.451 | INFO | orchestrator | [a1b2c3d4] ✅ BOT-2 returned confident answer (similarity: 0.7234)
2026-02-05 10:30:45.452 | INFO | orchestrator | [a1b2c3d4] Response generated (145 characters)
2026-02-05 10:30:45.453 | INFO | orchestrator | [a1b2c3d4] ================================================================
2026-02-05 10:30:45.454 | INFO | orchestrator | [a1b2c3d4] SUMMARY: bot=BOT-2 | conf=0.7234 | latency=331ms | error=NONE
2026-02-05 10:30:45.455 | INFO | orchestrator | [a1b2c3d4] ================================================================
```

### View Audit Log (JSON)
```bash
tail -f logs/audit.log | python -m json.tool
```

Example entry:
```json
{
  "event": "ROUTING_DECISION",
  "query_id": "a1b2c3d4",
  "timestamp": "2026-02-05T10:30:45.123456",
  "query": "What is the hostel fee?",
  "validation": "PASSED",
  "scope": "IN_SCOPE",
  "classifier": {
    "category": "Student Services",
    "confidence": 0.8234,
    "probabilities": {
      "Student Services": 0.8234,
      "Academic Affairs": 0.1234,
      "Financial Matters": 0.0532
    }
  },
  "routed_to": "BOT-2",
  "similarity_score": 0.7234,
  "reason": "High confidence (0.8234) + semantic category"
}
```

---

## Testing Checklist

- [ ] Run validation script: `python scripts/validate_phase1.py`
- [ ] Test query validation with edge cases (empty, gibberish, self-harm)
- [ ] Test classifier confidence scores
- [ ] Test Bot-2 similarity thresholds
- [ ] Test Bot-3 RAG retrieval
- [ ] Test main orchestrator with various queries
- [ ] Check that audit logs are generated
- [ ] Check that latency is reasonable (< 500ms per query)
- [ ] Verify configuration thresholds

---

## Common Issues & Troubleshooting

### Issue: Classifier returns very low confidence for all queries
**Solution:** Check if classifier was trained properly
```bash
python classifier/train_classifier.py
```

### Issue: Bot-2 index not found
**Solution:** Build the Bot-2 FAISS index
```bash
python build_bot2_index.py
```

### Issue: Bot-3 returns "No information found" for everything
**Solution:** Check if documents exist in `data/bot3_docs/`
```bash
ls -la data/bot3_docs/
```
If empty, run document ingestion:
```bash
python scripts/ingest_rvrjcce.py
```

### Issue: Routing decisions seem wrong
**Solution:** Check confidence scores in logs
- If confidence is low but shouldn't be → retrain classifier
- If similarity is too high/low → adjust `BOT2_SIMILARITY_THRESHOLD`
- If retrieval confidence is off → adjust `BOT3_MIN_CONFIDENCE`

### Issue: Self-harm queries are not being blocked
**Solution:** Make sure `USE_QUERY_VALIDATION` is True in settings
```python
USE_QUERY_VALIDATION: bool = True
```

---

## Next Steps (PHASE 2)

1. **Streamlit UI Enhancements**
   - Display confidence scores
   - Show routing decisions
   - Add user feedback buttons

2. **Testing & Metrics**
   - Unit tests for each bot
   - Integration tests
   - Performance benchmarks

3. **Model Improvements**
   - Collect user feedback
   - Retrain classifier
   - Fine-tune thresholds based on data

4. **Production Deployment**
   - Docker containerization
   - Cloud deployment (AWS/GCP)
   - Load testing & monitoring

---

## Support & Questions

**For logs:**
- Main logs: `logs/app.log`
- Audit logs: `logs/audit.log`

**For configuration:**
- Settings: `config/settings.py`
- Thresholds are clearly labeled and documented

**For debugging:**
- Each log entry includes `query_id` for tracing
- Audit logs are JSON for easy parsing
- Stack traces included for all errors

---

**✅ PHASE 1 READY FOR TESTING**

All components implemented and integrated. Ready for UI integration and deployment.
