
import logging
import os
import pandas as pd
import random

# Configure Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("data_migrator")

SOURCE_QA_FILE = "data/qa_dataset.csv"
BASE_DOMAIN_DIR = "data/domains"

# Map full domain names to folder names
DOMAIN_MAPPING = {
    "Admissions & Registrations": "admissions",
    "Financial Matters": "financial",
    "Academic Affairs": "academic",
    "Student Services": "student_services",
    "Campus Life": "campus_life",
    "General Information": "general",
    "Cross-Domain Queries": "cross_domain"
}

# Paraphrasing Rule Templates (Simple substitution for now)
PARAPHRASE_TEMPLATES = [
    "What is {topic}?",
    "Tell me about {topic}.",
    "I want to know about {topic}.",
    "Can you explain {topic}?",
    "Give me details regarding {topic}.",
    "Information on {topic}.",
    "How does {topic} work?",
    "Please describe {topic}.",
    "What do you know about {topic}?",
    "{topic} details please.",
    "Could you clarify {topic}?",
    "I need info about {topic}.",
    "Search for {topic}.",
    "Is there information on {topic}?",
    "Help me with {topic}.",
    "What about {topic}?",
    "Query: {topic}",
    "Regarding {topic}",
    "Do you have data on {topic}?",
    "Explain the {topic}."
]

def extract_core_topic(question):
    """
    Very simple heuristic to extract 'topic' from question for templating.
    E.g. "What is the admission process?" -> "admission process"
    """
    # Remove common starts
    starts = ["what is the ", "what is ", "how to ", "how do i ", "where is ", "is there ", "do you have ", "are there "]
    q_lower = question.lower().strip("?.,")
    
    for s in starts:
        if q_lower.startswith(s):
            return q_lower[len(s):]
            
    return q_lower

def migrate_and_augment():
    logger.info("Starting Data Migration and Augmentation...")
    
    if not os.path.exists(SOURCE_QA_FILE):
        logger.error(f"Source file not found: {SOURCE_QA_FILE}")
        return

    try:
        df = pd.read_csv(SOURCE_QA_FILE)
        
        # Ensure 'domain' and existing columns
        if "domain" not in df.columns:
            logger.error("No domain column found in QA dataset.")
            return

        for domain_name, group in df.groupby("domain"):
            folder_name = DOMAIN_MAPPING.get(domain_name)
            if not folder_name:
                logger.warning(f"Unknown domain '{domain_name}', skipping...")
                continue
                
            target_file = os.path.join(BASE_DOMAIN_DIR, folder_name, "qa.csv")
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            
            new_rows = []
            
            for _, row in group.iterrows():
                question = row["question"]
                answer = row["answer"]
                
                # Add original
                new_rows.append({"question": question, "answer": answer, "is_paraphrase": False})
                
                # Generate Paraphrases
                # 1. Extract topic
                topic = extract_core_topic(question)
                
                # 2. Apply templates
                for tmpl in PARAPHRASE_TEMPLATES:
                    para_q = tmpl.format(topic=topic)
                    if para_q != question:
                        new_rows.append({"question": para_q, "answer": answer, "is_paraphrase": True})
            
            # Save to domain file
            domain_df = pd.DataFrame(new_rows)
            domain_df.to_csv(target_file, index=False)
            logger.info(f"Saved {len(domain_df)} entries to {target_file}")

    except Exception as e:
        logger.error(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate_and_augment()
