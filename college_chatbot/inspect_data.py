
import pickle
import os
import faiss

METADATA_PATH = r"d:\college_chatbot\college_chatbot\embeddings\bot3_faiss\metadata.pkl"
INDEX_PATH = r"d:\college_chatbot\college_chatbot\embeddings\bot3_faiss\index.faiss"

print(f"Checking {METADATA_PATH}...")
if os.path.exists(METADATA_PATH):
    try:
        with open(METADATA_PATH, "rb") as f:
            data = pickle.load(f)
            print(f"Type: {type(data)}")
            if isinstance(data, dict):
                print(f"Keys: {data.keys()}")
                if "chunks" in data:
                    print(f"Chunks len: {len(data['chunks'])}")
                    if len(data['chunks']) > 0:
                        print(f"Sample chunk: {data['chunks'][0]}")
            elif isinstance(data, list):
                print(f"List len: {len(data)}")
            else:
                print("Unknown structure")
    except Exception as e:
        print(f"Error reading metadata: {e}")
else:
    print("Metadata file NOT FOUND")

print(f"\nChecking {INDEX_PATH}...")
if os.path.exists(INDEX_PATH):
    try:
        index = faiss.read_index(INDEX_PATH)
        print(f"Index ntotal: {index.ntotal}")
    except Exception as e:
        print(f"Error reading index: {e}")
else:
    print("Index file NOT FOUND")
