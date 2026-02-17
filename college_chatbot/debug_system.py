
import sys
import os
import logging

# Ensure we are in the right directory context
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

print("="*50)
print("SYSTEM DIAGNOSTIC TOOL")
print("="*50)

try:
    from core.model_manager import ModelManager
    from main import handle_query
except Exception as e:
    print(f"CRITICAL IMPORT ERROR: {e}")
    sys.exit(1)

def test_model_loading():
    print("\n[1] Testing Model Loading via ModelManager...")
    
    try:
        print("  - Loading Embedder...")
        emb = ModelManager.get_embedder()
        print(f"    SUCCESS: {type(emb)}")
    except Exception as e:
        print(f"    FAIL: {e}")

    try:
        print("  - Loading Classifier...")
        clf = ModelManager.get_classifier()
        print(f"    SUCCESS: {type(clf)}")
    except Exception as e:
        print(f"    FAIL: {e}")

    try:
        print("  - Loading AIML Kernel...")
        kern = ModelManager.get_aiml_kernel()
        print(f"    SUCCESS: {type(kern)}")
    except Exception as e:
        print(f"    FAIL: {e}")

    try:
        print("  - Loading Bot 3 Resources...")
        idx, meta = ModelManager.get_bot3_resources()
        if idx:
            print(f"    SUCCESS: Index has {idx.ntotal} vectors")
        else:
            print("    FAIL: Index is None")
        
        if meta and isinstance(meta, dict): # Should be dict per setup_indices
             print(f"    SUCCESS: Metadata has {len(meta.get('chunks', []))} chunks")
        elif meta and isinstance(meta, list): # Old format was list
             print(f"    SUCCESS: Metadata list has {len(meta)} items")
        else:
             print(f"    FAIL: Metadata is {type(meta)}")

    except Exception as e:
        print(f"    FAIL: {e}")

def test_queries():
    print("\n[2] Testing Queries...")
    
    queries = [
        "How much is the fee?",            # Rule Bot
        "Where is the college located?",   # RAG / General
        "Tell me about CSE department"     # Semantic Bot
    ]

    for q in queries:
        print(f"\n>>> QUERY: {q}")
        try:
            response = handle_query(q)
            print(f"    RESPONSE: {response[:100]}..." if len(response) > 100 else f"    RESPONSE: {response}")
        except Exception as e:
            print(f"    ERROR processing query: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_model_loading()
    test_queries()
    print("\nDiagnostic Complete.")
