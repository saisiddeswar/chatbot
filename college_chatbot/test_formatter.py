import sys
import os
import json

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.response_formatter import render_response, extract_json_from_text

def test_formatter():
    print("=== Testing Response Formatter ===")
    
    # 1. Test Valid JSON
    valid_json = {
        "title": "College Fee",
        "items": [
            {"label": "Tuition Fee", "value": "₹50,000"},
            {"label": "Hostel Fee", "value": "₹60,000"}
        ],
        "notes": "Fees are subject to change."
    }
    
    output = render_response(valid_json)
    print("\n[Test 1] Valid JSON Output:")
    print("-" * 30)
    print(output)
    print("-" * 30)
    
    assert "**College Fee**" in output
    assert "**Tuition Fee:** ₹50,000" in output
    assert "_Fees are subject to change._" in output
    
    # 2. Test JSON Extraction from Markdown
    llm_output = """Here is the data:
    ```json
    {
        "title": "B.Tech Depts",
        "items": [
            {"label": "CSE", "value": "180 seats"},
            {"label": "ECE", "value": "180 seats"}
        ]
    }
    ```
    Values extracted."""
    
    extracted = extract_json_from_text(llm_output)
    print(f"\n[Test 2] Extracted JSON Title: {extracted.get('title')}")
    assert extracted['title'] == "B.Tech Depts"
    assert len(extracted['items']) == 2
    
    # 3. Test Empty Items
    empty_json = {"title": "Unknown", "items": []}
    output_empty = render_response(empty_json)
    print(f"\n[Test 3] Empty Items Output: {output_empty}")
    assert "not available" in output_empty or "not found" in output_empty.lower()
    
    # 4. Test Error Handling (Bad JSON)
    bad_json_text = "{title: 'Bad JSON'" # Missing quotes
    extracted_bad = extract_json_from_text(bad_json_text)
    print(f"\n[Test 4] Bad JSON Extraction Result: {extracted_bad}") 
    # Should probably satisfy the fallback or return None? Currently returns None or raises?
    # My extract_json_from_text returns None on error.
    assert extracted_bad is None

    print("\nAll formatter tests passed!")

if __name__ == "__main__":
    test_formatter()
