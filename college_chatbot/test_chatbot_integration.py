"""
Test script for RVRJCCE Chatbot Integration
Tests all three bots with RVRJCCE-specific queries
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bots.rule_bot import get_rule_response
from bots.bot2_semantic import bot2_answer
from bots.bot3_rag import bot3_answer

def test_bots():
    """Test all three bots with RVRJCCE queries"""
    
    test_queries = [
        "Tell me about RVRJCCE",
        "What B.Tech programs do you offer?",
        "How do I apply for RVRJCCE?",
        "Tell me about placements",
        "What are the admission requirements?",
    ]
    
    print("\n" + "="*80)
    print("RVRJCCE CHATBOT - INTEGRATION TEST")
    print("="*80)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}: {query}")
        print(f"{'='*80}")
        
        # Test Bot-1 (Rule-Based)
        print("\n[BOT-1] Rule-Based Response:")
        try:
            response = get_rule_response(query)
            print(f"Response: {response[:200]}..." if len(response) > 200 else f"Response: {response}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test Bot-2 (Semantic)
        print("\n[BOT-2] Semantic QA Response:")
        try:
            answer, confidence, is_confident = bot2_answer(query, f"test_{i}")
            print(f"Response: {answer[:200]}..." if len(answer) > 200 else f"Response: {answer}")
            print(f"Confidence: {confidence:.2f}")
            print(f"Confident: {is_confident}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test Bot-3 (RAG)
        print("\n[BOT-3] RAG Response:")
        try:
            response = bot3_answer(query, [], f"test_{i}")
            print(f"Response: {response[:200]}..." if len(response) > 200 else f"Response: {response}")
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_bots()
