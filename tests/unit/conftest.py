# tests/unit/conftest.py
import pytest
import sys
from pathlib import Path

HERE = Path(__file__).resolve()           # ...\tests\unit\conftest.py
cur = HERE.parent                         # ...\tests\unit
for _ in range(10):
    src = cur / "src"
    if src.exists():
        sp = str(src)
        if sp not in sys.path:
            sys.path.insert(0, sp)
        break
    cur = cur.parent
else:
    raise RuntimeError(f"Could not find 'src' directory walking up from {HERE}")
