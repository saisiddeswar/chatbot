
import sys
import os
import traceback

# Add project root to sys.path explicitly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bots.bot3_rag import retrieve_context
from core.model_manager import ModelManager

print("=== DIAGNOSTIC START ===")

def test_retrieval(q):
    print(f"\nTesting Retrieval for: '{q}'")
    try:
        # This will trigger the print statements I added to bot3_rag.py
        chunks, score = retrieve_context(q, "test_id")
        print(f"Returned {len(chunks)} chunks. Score: {score}")
        for c in chunks:
            print(f" - [{c.get('source', 'unknown')}] {c.get('text', '')[:50]}...")
    except Exception as e:
        print("CRASHED!")
        traceback.print_exc()

# 1. Check Resources
print("\n[1] Checking Resources...")
try:
    # Force load to see logs
    idx, meta = ModelManager.get_bot3_resources()
    print(f"Bot 3 Index: {idx.ntotal if idx else 'None'}")
except Exception as e:
    print(f"Resource Load Error: {e}")
    traceback.print_exc()

# 2. Test Retrieval
test_retrieval("where is the college")

print("\n=== DIAGNOSTIC END ===")
