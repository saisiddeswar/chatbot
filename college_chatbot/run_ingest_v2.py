
import sys
import os
import time

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.web_ingest import ingest_url

URLS = [
    # Main
    "https://rvrjcce.ac.in/",
    "https://rvrjcce.ac.in/message.php",
    "https://rvrjcce.ac.in/contactus.php",
    "https://rvrjcce.ac.in/principal.php",
    "https://rvrjcce.ac.in/about_rvr.php",
    "https://rvrjcce.ac.in/vision_mission.php",
    "https://rvrjcce.ac.in/ranking.php",
    "https://rvrjcce.ac.in/governingbody.php",
    
    # Academics & Admissions
    "https://rvrjcce.ac.in/admission_procedure.php",
    "https://rvrjcce.ac.in/fee_structure.php",
    "https://rvrjcce.ac.in/academic_calendar.php",
    "https://rvrjcce.ac.in/regulations.php",
    
    # Departments (Main pages)
    "https://rvrjcce.ac.in/chemical_engineering/",
    "https://rvrjcce.ac.in/civil_engineering/",
    "https://rvrjcce.ac.in/computer_science_engineering/",
    "https://rvrjcce.ac.in/computer_science_business_systems_tcs/",
    "https://rvrjcce.ac.in/computer_science_engineering_ds/",
    "https://rvrjcce.ac.in/computer_science_engineering_ai_ml/",
    "https://rvrjcce.ac.in/computer_science_engineering_iot/",
    "https://rvrjcce.ac.in/electronics_communication_engineering/",
    "https://rvrjcce.ac.in/electrical_electronics_engineering/",
    "https://rvrjcce.ac.in/information_technology/",
    "https://rvrjcce.ac.in/mechanical_engineering/",
    "https://rvrjcce.ac.in/computer_applications/",
    "https://rvrjcce.ac.in/management_sciences_bba_mba/",
    "https://rvrjcce.ac.in/mathematics_humanities/",
    "https://rvrjcce.ac.in/chemistry/",
    "https://rvrjcce.ac.in/physics/",
    
    # Placements
    "https://rvrjcce.ac.in/placement_statistics.php",
    "https://rvrjcce.ac.in/placement_recruiters.php",
    "https://rvrjcce.ac.in/placement_training.php",
    
    # Facilities & Students
    "https://rvrjcce.ac.in/library.php",
    "https://rvrjcce.ac.in/hostels.php",
    "https://rvrjcce.ac.in/transport.php",
    "https://rvrjcce.ac.in/sports.php",
    "https://rvrjcce.ac.in/ncc.php",
    "https://rvrjcce.ac.in/nss.php",
    "https://rvrjcce.ac.in/student_activity_center.php",
    "https://rvrjcce.ac.in/anti_ragging.php",
    "https://rvrjcce.ac.in/examination_section.php",
    "https://rvrjcce.ac.in/result.php"
]

print(f"Starting ingestion of {len(URLS)} URLs...")

success_count = 0
with open("ingest_log_v2.txt", "w") as log:
    for u in URLS:
        try:
            print(f"Fetching: {u}")
            log.write(f"Fetching: {u}\n")
            fp = ingest_url(u)
            print(f"  -> Saved: {fp}")
            log.write(f"  -> Saved: {fp}\n")
            success_count += 1
            # time.sleep(0.5) # Reduced sleep
        except Exception as e:
            print(f"  -> FAILED: {u} | Error: {e}")
            log.write(f"  -> FAILED: {u} | Error: {e}\n")

print(f"Ingestion complete. Successfully saved {success_count}/{len(URLS)} pages.")
print("Don't forget to rebuild the Bot-3 index!")
