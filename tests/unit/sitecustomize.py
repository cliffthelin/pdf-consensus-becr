# tests/unit/sitecustomize.py
# Ensures 'src' is on sys.path even if pytest is run from tests/unit.
import sys
from pathlib import Path
import pytest

HERE = Path(__file__).resolve()
# tests/unit/sitecustomize.py -> unit -> tests -> <repo-root>
repo_root = HERE.parents[2]
src = repo_root / "src"
if src.exists():
    sys.path.insert(0, str(src))
else:
    # Fail loudly with a friendly message so it's obvious what's wrong
    raise RuntimeError(f"'src' directory not found at expected location: {src}")
