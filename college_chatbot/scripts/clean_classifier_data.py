
import pandas as pd
import os

INPUT_FILE = "data/classifier_data.csv"
OUTPUT_FILE = "data/classifier_data_cleaned.csv"

def clean_data():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    df = pd.read_csv(INPUT_FILE)
    print(f"Original Row Count: {len(df)}")
    
    # 1. Standardize Columns
    df.columns = [c.strip() for c in df.columns]
    
    # 2. Define Rules for consistency
    # (keyword, target_category)
    # Priority: The checks are sequential. First match wins? No, we should be careful.
    # Let's iterate and apply corrections.
    
    corrections = 0
    
    def get_corrected_category(row):
        q = str(row['Question']).lower()
        cat = str(row['Category']).strip()
        
        # --- HOSTEL RULES ---
        if "hostel" in q:
            if any(x in q for x in ["fee", "cost", "charge", "amount", "payment", "bill"]):
                return "Financial Matters"
            elif any(x in q for x in ["apply", "application", "room change", "allotment", "register"]):
                return "Student Services"
            elif any(x in q for x in ["available", "facility", "facilities", "mess", "rules", "time", "timing", "boys", "girls", "accommodation", "stay"]):
                return "Campus Life"
            # Default for hostel availability
            if "hostel" in q and "available" in q:
                return "Campus Life"
                
        # --- BUS / TRANSPORT RULES ---
        if "bus" in q or "transport" in q:
            if any(x in q for x in ["fee", "cost", "charge", "pay"]):
                return "Financial Matters"
            return "Campus Life" # Routes, timings, availability
            
        # --- ADMISSION RULES ---
        if "admission" in q or "eapcet" in q or "cutoff" in q or "rank" in q or "quota" in q or "management" in q:
            # Some fee questions might overlap, but generally Admission & Registration
            if "fee" in q and "structure" in q: 
                 return "Financial Matters" 
            return "Admissions & Registrations"

        # --- FEE RULES ---
        if "fee" in q or "tuition" in q or "scholarship" in q or "fine" in q or "due" in q or "payment" in q:
            return "Financial Matters"
            
        # --- LIBRARY ---
        if "library" in q or "book" in q:
            return "Student Services" # Or Campus Life? Let's stick to valid existing pattern
            
        # --- PLACEMENT ---
        if "placement" in q or "package" in q or "recruit" in q or "company" in q or "companies" in q or "internship" in q:
            return "Cross-Domain Queries" # Or General Information? 
            # The QA dataset has placements in "Cross-Domain Queries" (Lines 32-36)
            # But duplicate rows in classifier might say 'General Information' or 'Academic Affairs'
            return "Cross-Domain Queries"

        return cat

    # Apply corrections
    # We create a new list to avoid modifying during iteration issues
    new_rows = []
    
    for _, row in df.iterrows():
        old_cat = row['Category']
        new_cat = get_corrected_category(row)
        
        # Override specific known bads
        if "is hostel available" in str(row['Question']).lower():
            new_cat = "Campus Life"
        
        new_rows.append({
            "Question": row['Question'],
            "Category": new_cat
        })
        
    new_df = pd.DataFrame(new_rows)
    
    # 3. Drop Duplicates
    # Drop rows where Question is identical (keep first or last? doesn't matter if we standardized label)
    # But wait, we want to ensure we don't have (Q, Cat1) and (Q, Cat2).
    # Since we corrected categories based on content, duplicates should now have SAME category.
    # So we can just drop duplicate Questions.
    
    before_dedup = len(new_df)
    new_df = new_df.drop_duplicates(subset=['Question'], keep='last')
    print(f"Dropped {before_dedup - len(new_df)} duplicate questions.")
    
    # 4. Save
    print(f"Final count: {len(new_df)}")
    new_df.to_csv(INPUT_FILE, index=False) # Overwrite original
    print(f"cleaned_data saved to {INPUT_FILE}")

if __name__ == "__main__":
    clean_data()
