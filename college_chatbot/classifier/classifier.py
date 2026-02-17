from typing import Dict, Tuple
import numpy as np
from core.model_manager import ModelManager

def predict_category(query: str) -> Tuple[str, float, Dict[str, float]]:
    """
    Predict the category of a user query with confidence scores.
    Uses lazy-loaded classifier from ModelManager.
    
    Returns:
        (category: str, max_confidence: float, probabilities: Dict[str, float])
    """
    classifier = ModelManager.get_classifier()
    
    if classifier is None:
        # Fallback if classifier failed to load
        return "General", 0.0, {}

    # Get prediction
    category = classifier.predict([query])[0]
    
    # Get probability for each class
    if hasattr(classifier, 'predict_proba'):
        probs_array = classifier.predict_proba([query])[0]
        classes = classifier.classes_
        probs_dict = {classes[i]: float(probs_array[i]) for i in range(len(classes))}
        max_confidence = float(np.max(probs_array))
    else:
        # Fallback: assume high confidence if no proba available
        probs_dict = {category: 1.0}
        max_confidence = 1.0
    
    return category, max_confidence, probs_dict

