#!/usr/bin/env python
"""Test script to verify all imports work correctly."""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("[1/5] Testing core logger import...")
try:
    from core.logger import get_logger
    print("[OK] Core logger imported successfully")
except Exception as e:
    print(f"[ERROR] Failed to import core logger: {e}")
    sys.exit(1)

print("\n[2/5] Testing audit logger import...")
try:
    from core.audit_logger import get_audit_logger
    print("[OK] Audit logger imported successfully")
except Exception as e:
    print(f"[ERROR] Failed to import audit logger: {e}")
    sys.exit(1)

print("\n[3/5] Testing config import...")
try:
    from config.settings import settings
    print("[OK] Settings imported successfully")
except Exception as e:
    print(f"[ERROR] Failed to import settings: {e}")
    sys.exit(1)

print("\n[4/5] Testing bot imports...")
try:
    from bots.bot2_semantic import bot2_answer
    from bots.bot3_rag import bot3_answer
    from bots.rule_bot import get_rule_response
    print("[OK] All bots imported successfully")
except Exception as e:
    print(f"[ERROR] Failed to import bots: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[5/5] Testing main handler import...")
try:
    from main import handle_query
    print("[OK] Main handler imported successfully")
except Exception as e:
    print(f"[ERROR] Failed to import main handler: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[SUCCESS] All imports verified successfully!")
print("\nYou can now run: streamlit run app.py")
