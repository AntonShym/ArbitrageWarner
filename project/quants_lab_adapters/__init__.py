"""Helpers that extend quants-lab components for this project."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
QUANTS_LAB_PATH = REPO_ROOT / "quants-lab"
if str(QUANTS_LAB_PATH) not in sys.path:
    sys.path.insert(0, str(QUANTS_LAB_PATH))

__all__ = ["QUANTS_LAB_PATH"]
