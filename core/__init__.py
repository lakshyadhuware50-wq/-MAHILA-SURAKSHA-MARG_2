"""
core/__init__.py
================
Core logic for MAHILA SURAKSHA MARG (scoring, routing, ML, database, feedback).
Ensures the project root is always in sys.path regardless of where Python is invoked from.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
