# College Chatbot Retraining Guide

This guide explains how to update the chatbot's knowledge base and retrain the models.

## 1. Quick Retraining (All Bots)

To retrain all bots (Classifier, Semantic Search, and RAG) at once, run the master script:

```bash
python train_all_bots.py
```

This script will:
1. Train the Intent Classifier.
2. Rebuild Bot-2 (Semantic) FAISS indices for all domains.
3. Rebuild Bot-3 (RAG) FAISS index from documents.

---

## 2. Updating Specific Components

### A. Updating Bot-1 (Rule-Based AIML)
Bot-1 uses AIML files for pattern matching.

1. **Edit XML files** in `data/aiml/` (e.g., `rvrjcce_comprehensive.aiml`).
2. Add new patterns:
   ```xml
   <category>
       <pattern>WHAT IS THE COLLEGE CODE</pattern>
       <template>The college code is RVRJ.</template>
   </category>
   ```
3. **Restart the application** (`python main.py`). No separate training script is needed; AIML files are loaded on startup.

### B. Updating Bot-2 (Semantic QA)
Bot-2 answers questions from a structured Q&A CSV.

1. **Edit** `data/qa_dataset.csv`.
2. Add a new row:
   ```csv
   "Student Services","Where is the gym?","The gym is located near the sports complex."
   ```
3. **Rebuild Index**:
   ```bash
   python scripts/rebuild_bot2.py
   ```
   *Note: Bot-2 indices are automatically rebuilt on startup if missing, but manual rebuild is required for updates.*

### C. Updating Bot-3 (RAG - Document Search)
Bot-3 answers from text documents.

1. **Add/Update .txt files** in `data/bot3_docs/`.
2. **Rebuild Index**:
   ```bash
   python build_bot3_index.py
   ```

### D. Updating Intent Classifier
The classifier routes queries to domains (e.g., "Hostel" -> "Campus Life").

1. **Edit** `data/classifier_data.csv`.
2. Add training examples:
   ```csv
   "How much is the hostel fee?","Campus Life"
   ```
3. **Retrain**:
   ```bash
   python classifier/train_classifier.py
   ```

---

## Troubleshooting

- **Check Logs**: If a bot fails, check `logs/app.log`.
- **"Resources not available"**: Run `python train_all_bots.py` to ensure all indices are built.
- **Float32 Error**: Use the provided `train_all_bots.py` script; patches have been applied to fix JSON serialization issues.
