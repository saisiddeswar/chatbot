import aiml


import os

# Load AIML kernel
kernel = aiml.Kernel()

# Load both default and RVRJCCE AIML files
AIML_FILES = [
    "data/aiml/admission_financial.aiml",
    "data/aiml/rvrjcce_comprehensive.aiml"
]

for aiml_path in AIML_FILES:
    if os.path.exists(aiml_path):
        kernel.learn(aiml_path)
    else:
        print(f"[WARNING] AIML file not found at {aiml_path}")

def get_rule_response(query: str) -> str:
    """
    Returns response from rule-based (AIML) chatbot
    """
    print("[DEBUG] Bot-1 received query")
    response = kernel.respond(query)

    if response.strip() == "":
        return "Sorry, I don't have information on that."
    return response
