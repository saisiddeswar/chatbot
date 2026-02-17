import json
import re
from typing import Dict, Any, List

def render_response(json_data: Dict[str, Any]) -> str:
    """
    Renders a structured JSON response into a user-friendly string format.
    
    Expected JSON Structure:
    {
        "title": "Topic Name",
        "items": [
            {"label": "Label 1", "value": "Value 1"},
            {"label": "Label 2", "value": "Value 2"}
        ],
        "notes": "Optional short note"
    }
    
    Rendering Rules:
    1. Title on top (Bold)
    2. Each item in new line
    3. Format: **Label:** Value
    4. Max 6 lines total for items (though usually 5 per prompt)
    5. Notes at bottom in italics
    """
    try:
        if not json_data or not isinstance(json_data, dict):
            return "Information not found."

        lines = []
        
        # 1. Title
        title = json_data.get("title", "").strip()
        if title:
            lines.append(f"**{title}**")
            
        # 2. Items
        items = json_data.get("items", [])
        if not items:
            return "The requested information is not available."
            
        count = 0
        for item in items:
            if count >= 6: break # strict limit
            
            label = item.get("label", "").strip()
            value = item.get("value", "").strip()
            
            if label and value:
                # Remove emojis if any exist (basic regex)
                label = re.sub(r'[^\w\s,:.\-₹$€£%()]', '', label).strip()
                lines.append(f"**{label}:** {value}")
                count += 1
                
        # 3. Notes
        notes = json_data.get("notes", "").strip()
        if notes:
            lines.append(f"\n_{notes}_")
            
        return "\n".join(lines)
        
    except Exception as e:
        return f"Error formatting response: {str(e)}"

def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    Robustly extracts JSON object from LLM response text.
    Handles markdown code blocks and raw text.
    """
    try:
        # cleanup
        text = text.strip()
        
        # Try finding JSON block
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            json_str = match.group(0)
        else:
            json_str = text
            
        # Parse
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None
