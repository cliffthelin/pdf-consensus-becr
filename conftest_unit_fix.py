# tests/unit/conftest.py
# Ensure repo-root/src is importable even when running pytest from tests/unit.
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
cur = HERE.parent  # tests/unit
for _ in range(8):
    src = cur / "src"
    if src.exists():
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))
        break
    cur = cur.parent
else:
    raise RuntimeError(
        f"Could not find a 'src' directory above {HERE}. "
        f"Ensure your tree is repo-root/src/compareblocks/..."
    )
