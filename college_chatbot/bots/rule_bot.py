from core.model_manager import ModelManager
from core.logger import get_logger

logger = get_logger("rule_bot")

def get_rule_response(query: str) -> str:
    """
    Returns response from rule-based (AIML) chatbot
    Uses lazy-loaded kernel from ModelManager.
    """
    # Lazy load kernel
    kernel = ModelManager.get_aiml_kernel()
    
    if kernel is None:
        logger.error("Failed to load AIML kernel")
        return "Sorry, I'm having trouble accessing my rule database."

    logger.debug(f"[DEBUG] Bot-1 checking query: {query}")
    
    # Ensure query is uppercase for AIML matching
    clean_query = query.upper().strip()
    response = kernel.respond(clean_query)
    
    logger.debug(f"[DEBUG] AIML Response for '{clean_query}': '{response}'")

    if not response or response.strip() == "":
        return "Sorry, I don't have information on that."
    
    return response
