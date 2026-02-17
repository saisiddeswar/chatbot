import sys
import os

# FORCE CPU ONLY & SUPPRESS TF LOGS
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

from flask import Flask, render_template, request, jsonify

# -------------------------
# Path setup
# -------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from main import handle_query

from core.model_manager import ModelManager
from core.logger import get_logger
from config.settings import settings

logger = get_logger("server")
app = Flask(__name__)

# -------------------------
# Home route
# -------------------------
@app.route("/")
def home():
    return render_template("index.html")

# -------------------------
# Chat API
# -------------------------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        # Accept both JSON and form-data safely
        data = request.get_json(silent=True)
        # logger.debug(f"RAW REQUEST DATA: {data}")

        user_message = ""
        history = []

        if data:
            # Accept multiple possible keys (frontend-safe)
            user_message = (
                data.get("message")
                or data.get("question")
                or data.get("query")
                or ""
            )
            history = data.get("history", [])
        else:
            # Fallback for HTML form submit
            user_message = request.form.get("message") or ""
            history = []

        # logger.debug(f"USER MESSAGE: {user_message}")

        # Guard against empty input
        if not user_message.strip():
            return jsonify({
                "response": "No question received. Please type a question."
            }), 400

        # Normalize history into [(q, a), ...]
        formatted_history = []
        if isinstance(history, list):
            for item in history:
                if isinstance(item, list) and len(item) == 2:
                    formatted_history.append((item[0], item[1]))

        # Call core logic
        response = handle_query(user_message, formatted_history)

        return jsonify({
            "response": response
        })

    except Exception as e:
        logger.exception(f"CHAT ENDPOINT ERROR: {e}")
        return jsonify({
            "response": "Server error. Please try again."
        }), 500

# -------------------------
# Stats API
# -------------------------
@app.route("/stats/top", methods=["GET"])
def get_top_stats():
    """Return top 4 frequent questions."""
    try:
        from core.stats_manager import StatsManager
        top_questions = StatsManager.get_top_queries(n=4)
        return jsonify({
            "questions": top_questions
        })
    except Exception as e:
        logger.error(f"Failed to fetch stats: {e}")
        return jsonify({"questions": []}), 500

# -------------------------
# App entry
# -------------------------
def warmup_models():
    """
    Explicit Model Loading Phase.
    Loads Embeddings and FAISS indices to RAM before serving requests.
    Does NOT load LLM (Lazy loaded ONLY).
    """
    logger.info("=== STARTING MODEL WARMUP PHASE ===")
    try:
        # 1. Load Embeddings (Lightweight)
        ModelManager.get_embedder()
        
        # 2. Load Classifiers
        ModelManager.get_classifier()
        
        # 3. Load Vector Indices (Bot 2 & Bot 3)
        ModelManager.get_bot2_resources()
        ModelManager.get_bot3_resources()
        
        # 4. Load Rule Kernel
        ModelManager.get_aiml_kernel()
        
        logger.info("=== MODEL WARMUP COMPLETE ===")
    except Exception as e:
        logger.critical(f"Model Warmup Failed: {e}")
        # We continue, as lazy loading might still work or fail gracefully later

if __name__ == "__main__":
    # Explicit Initialization Phase
    warmup_models()
    
    # Request Handling Phase
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=settings.DEBUG 
    )
