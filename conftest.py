"""
conftest.py
===========
pytest adds this folder to sys.path, so tests can simply do
`import config as cfg` no matter where pytest is started from.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
