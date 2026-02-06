import os
import pickle

import faiss
import pandas as pd
from embeddings.embedder import embed

# Load all Q&A datasets (both default and RVRJCCE-specific)
qa_files = [
    "data/bot2_qa/qa_dataset.csv",
    "data/bot2_qa/rvrjcce_qa_dataset.csv"
]

all_questions = []
all_answers = []

for qa_file in qa_files:
    if os.path.exists(qa_file):
        df = pd.read_csv(qa_file)
        all_questions.extend(df["Question"].tolist())
        all_answers.extend(df["Answers"].tolist())
        print(f"[OK] Loaded {qa_file}: {len(df)} Q&A pairs")
    else:
        print(f"[WARNING] Q&A file not found: {qa_file}")

print(f"\n[STATS] Total Q&A pairs loaded: {len(all_questions)}")

# Create embeddings
vectors = embed(all_questions)

# Build FAISS index
index = faiss.IndexFlatL2(vectors.shape[1])
index.add(vectors)

# Save index and QA pairs (with both question and answer for reference)
os.makedirs("embeddings/bot2_faiss", exist_ok=True)

faiss.write_index(index, "embeddings/bot2_faiss/index.faiss")

qa_data = [
    {"question": q, "answer": a} 
    for q, a in zip(all_questions, all_answers)
]

with open("embeddings/bot2_faiss/qa.pkl", "wb") as f:
    pickle.dump(qa_data, f)

print("[OK] Bot-2 FAISS index created successfully with all Q&A pairs")
