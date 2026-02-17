
import os
import sys
import subprocess
import time

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logger import get_logger

logger = get_logger("train_all_bots")

def run_step(description, command):
    logger.info(f"[{description}] Starting...")
    print(f"\n>>> {description}...")
    
    start_time = time.time()
    try:
        # Use sys.executable to ensure we use the same python environment
        cmd_list = [sys.executable] + command.split() if command.startswith("scripts") or command.endswith(".py") else command.split()
        
        result = subprocess.run(cmd_list, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"[{description}] SUCCESS ({time.time() - start_time:.2f}s)")
            print(f"    [OK] Completed in {time.time() - start_time:.2f}s")
            return True
        else:
            logger.error(f"[{description}] FAILED")
            logger.error(result.stderr)
            print(f"    [FAIL] Error:\n{result.stderr}")
            return False
    except Exception as e:
        logger.error(f"[{description}] EXCEPTION: {e}")
        print(f"    [ERROR] {e}")
        return False

def main():
    print("="*60)
    print("🤖  COLLEGE CHATBOT - FULL RETRAINING SUITE")
    print("="*60)
    
    # 1. Train Classifier
    step1 = run_step("Training Intent Classifier", "classifier/train_classifier.py")
    
    # 2. Rebuild Bot-2 Indices (Semantic QA)
    # We can use the script we created earlier
    step2 = run_step("Rebuilding Bot-2 (Semantic) Indices", "scripts/rebuild_bot2.py")
    
    # 3. Rebuild Bot-3 Index (RAG Documents)
    # We should use build_bot3_index.py as it seems more robust/recent than rebuild_rag.py
    step3 = run_step("Rebuilding Bot-3 (RAG) Index", "build_bot3_index.py")
    
    # 4. Bot-1 (AIML)
    print("\n>>> Reloading Bot-1 (Rule-based)...")
    print("    [INFO] AIML files are loaded dynamically on restart. No build step required.")
    
    print("\n" + "="*60)
    if step1 and step2 and step3:
        print("✅  ALL SYSTEMS RETRAINED SUCCESSFULLY!")
        print("    Please restart the application server to apply changes.")
    else:
        print("❌  SOME STEPS FAILED. Check logs/train_all_bots.log for details.")
    print("="*60)

if __name__ == "__main__":
    main()
