import sys
from pathlib import Path

# Ensure the worktree root is first on sys.path so pytest uses this worktree's
# aujobsscraper package rather than any globally installed editable version.
_root = str(Path(__file__).parent)
if _root not in sys.path:
    sys.path.insert(0, _root)
