
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.model_manager import ModelManager
from core.logger import get_logger

logger = get_logger("rebuild_script")

if __name__ == "__main__":
    logger.info("Manually triggering Bot-2 Index Rebuild...")
    try:
        success = ModelManager.rebuild_domain_indices()
        if success:
            logger.info("Rebuild Successful!")
            # Validate Campus Life
            idx, qa = ModelManager.get_domain_qa_resources("Campus Life")
            if idx:
                logger.info(f"Validation: 'Campus Life' has {idx.ntotal} vectors.")
                # Validate Student Services
                idx_ss, qa_ss = ModelManager.get_domain_qa_resources("Student Services")
                if idx_ss:
                    logger.info(f"Validation: 'Student Services' has {idx_ss.ntotal} vectors.")
                else:
                    logger.error("Validation: 'Student Services' index missing.")
            else:
                logger.error("Validation: 'Campus Life' index missing.")
        else:
            logger.error("Rebuild Failed.")
    except Exception as e:
        logger.error(f"SCRIPT CRASH: {e}")
        import traceback
        logger.error(traceback.format_exc())
