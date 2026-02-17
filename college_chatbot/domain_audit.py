
import json
import os
import pandas as pd
from typing import List, Dict

import logging
import sys

# Setup simple console logger for this script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("domain_audit")

QA_FILE = "data/qa_dataset.csv"
REPORT_FILE = "data/domain_gap_report.json"

REQUIRED_TOPICS = {
    "Admissions & Registrations": ["eligibility", "documents", "entrance exam", "counseling", "management quota"],
    "Financial Matters": ["tuition fees", "hostel fees", "scholarships", "refund policy", "payment methods"],
    "Academic Affairs": ["branches", "course structure", "academic calendar", "exam regulations", "departments"],
    "Student Services": ["certificates", "bonafide", "noc", "grievance redressal", "transcripts"],
    "Campus Life": ["hostel", "transport", "clubs", "sports", "facilities", "library"],
    "General Information": ["college name", "location", "accreditation", "autonomy", "history"],
    "Cross-Domain Queries": ["placement", "internships", "industry", "recruitment"]
}

MIN_ENTRIES_PER_DOMAIN = 5

def audit_domains():
    print("DEBUG: Script started")
    logger.info("Starting Domain Knowledge Audit...")
    
    if not os.path.exists(QA_FILE):
        logger.error(f"QA Dataset not found: {QA_FILE}")
        return

    try:
        df = pd.read_csv(QA_FILE)
        
        # Ensure 'domain' column exists
        if "domain" not in df.columns:
            logger.warning("QA Dataset missing 'domain' column. Defaulting all to 'General Information'.")
            df["domain"] = "General Information"
            
    except Exception as e:
        logger.error(f"Error reading dataset: {e}")
        return

    from datetime import datetime
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_entries": len(df),
        "domain_stats": {},
        "gaps": []
    }
    
    # Analyze per domain
    for domain, required_topics in REQUIRED_TOPICS.items():
        domain_df = df[df["domain"] == domain]
        count = len(domain_df)
        
        missing_topics = []
        
        # Check topic coverage (simple keyword match)
        combined_text = " ".join(domain_df["question"].astype(str).tolist() + domain_df["answer"].astype(str).tolist()).lower()
        
        for topic in required_topics:
            if topic not in combined_text:
                missing_topics.append(topic)
                
        status = "HEALTHY"
        if count < MIN_ENTRIES_PER_DOMAIN:
            status = "LOW_DATA"
        if missing_topics:
            status = "MISSING_TOPICS"
            
        if status != "HEALTHY":
            report["gaps"].append({
                "domain": domain,
                "status": status,
                "entry_count": count,
                "missing_topics": missing_topics
            })
            
        report["domain_stats"][domain] = {
            "count": count,
            "status": status
        }
        
    # Save Report
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    logger.info(f"Audit Complete. Found {len(report['gaps'])} domain gaps.")
    logger.info(f"Report saved to {REPORT_FILE}")

if __name__ == "__main__":
    audit_domains()
