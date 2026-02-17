import os
import sys

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bots.hybrid_retriever import hybrid_retriever
from config.settings import settings

def test_routing():
    print("=== Testing Router Logic ===")
    
    queries = [
        ("What is the college fee?", "local"),
        ("Tell me about CSE department", "local"),
        ("Latest AI news", "web"),
        ("Current weather in New York", "web"),
        ("Compare our college with IIT Bombay", "hybrid"),
        ("Is RVR better than VR Siddhartha?", "hybrid"),
    ]
    
    passed = 0
    for q, expected in queries:
        route = hybrid_retriever.route_query(q)
        print(f"Query: '{q}' -> Route: {route} (Expected: {expected})")
        if route == expected:
            passed += 1
        else:
            print(f"FAILED: Expected {expected}, got {route}")
            
    print(f"Routing Test: {passed}/{len(queries)} passed.\n")

def test_web_search_mock():
    print("=== Testing Web Search Integration (Mock) ===")
    
    # Mock Tavily if not set up
    if not settings.TAVILY_API_KEY and not os.environ.get("TAVILY_API_KEY"):
        print("No API Key found. Skipping actual web search test.")
        # But we can test the function call structure
        hybrid_retriever.tavily = None # Force None to test graceful failure
        res = hybrid_retriever.search_web("Test Query")
        print(f"Result without key: '{res}' (Expected empty string)")
    else:
        print("API Key found. Attempting real search...")
        try:
           res = hybrid_retriever.search_web("Latest tech news")
           print(f"Result len: {len(res)}")
           print(f"Preview: {res[:200]}...")
        except Exception as e:
           print(f"Search failed: {e}")

def local_retriever_mock(query):
    return ([{"source": "test_doc.txt", "text": "This is local content."}], 0.9)

def test_context_builder():
    print("\n=== Testing Context Builder ===")
    
    # Test Local
    ctx, route = hybrid_retriever.build_hybrid_context("college fee", local_retriever_mock)
    print(f"Route: {route}")
    print(f"Context Preview: {ctx[:100]}...")
    
    # Test Hybrid
    # We need to manually force hybrid for test if routing logic relies on keywords
    # Or just use a hybrid query
    ctx, route = hybrid_retriever.build_hybrid_context("Compare college with IIT", local_retriever_mock)
    print(f"Route: {route}")
    print(f"Context Preview: {ctx[:200]}...")

if __name__ == "__main__":
    test_routing()
    test_web_search_mock()
    test_context_builder()
