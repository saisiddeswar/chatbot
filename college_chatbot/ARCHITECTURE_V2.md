# Hybrid Chatbot Architecture (V2) - Enhanced & Production Ready

## 1. Overview
This system implements a strict **Hybrid Chatbot Model** as defined in the IEEE paper "A Hybrid Chatbot Model for Enhancing Administrative Support in Education", with key enhancements for RAG safety and offline dataset generation.

## 2. Core Components

### 2.1 Query Classifier (Multinomial Naive Bayes)
- **Role**: Validates and routes every user query.
- **Categories**:
  - **A:** Admissions & Registration
  - **B:** Financial Matters
  - **C:** Academic Affairs
  - **D:** Student Services
  - **E:** Campus Life
  - **F:** General Information
  - **G:** Cross-domain / Open-ended

### 2.2 Strict Routing Logic
- **Rule-Based (Bot-1)**: Handles **A & B** (Admissions, Fees) and **Forbidden RAG Topics** (Location, Contacts).
- **Semantic Search (Bot-2)**: Handles **C, D, E** (Academics, Student, Campus). Uses similarity thresholds.
- **RAG (Bot-3)**: Handles **F, G** (General, Open-Ended) ONLY if safe.
- **Safety**: "Location", "Phone", "Timings" are strictly routed to Bot-1 to prevent hallucination.

### 2.3 RAG Engine (Bot-3)
- **Source**: ONLY locally stored documents in `data/bot3_docs`.
- **Fallbacks**: Explicit `[NO INFO]` response if no relevant chunks found.
- **Internet Usage**: STRICTLY via `scripts/build_dataset.py` for dataset creation. No live query web search.

### 2.4 Data Ingestion Module (New)
- **Script**: `scripts/build_dataset.py`
- **Function**: Crawls official `rvrjcce.ac.in` pages.
- **Processing**: Cleans text and saves to `data/bot3_docs`.
- **Usage**: Run strictly offline/background (not during user query).

## 3. How to Run

1. **Build Dataset** (Internet Required):
   ```bash
   python scripts/build_dataset.py
   ```

2. **Rebuild Indices** (Process Local Data):
   ```bash
   python rebuild_rag.py
   python train_classifier.py
   ```

3. **Start Server**:
   ```bash
   python server.py
   ```

## 4. Safety Guarantees
- **No Hallucinations**: Low confidence RAG returns standardized "No Official Information" message.
- **Contact Info**: Hard-coded in AIML to ensure 100% accuracy for phone numbers/emails.
- **Scope**: Out-of-scope queries (politics, crypto) blocked at Gate 1.
