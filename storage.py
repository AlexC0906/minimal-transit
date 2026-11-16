"""Persistence for the best score."""

import json
from pathlib import Path

SAVE_PATH = Path(__file__).parent / "save.json"


def load_best_score():
    try:
        return max(0, int(json.loads(SAVE_PATH.read_text(encoding="utf-8")).get("best_score", 0)))
    except (OSError, ValueError, TypeError, AttributeError):
        return 0


def save_best_score(score):
    try:
        SAVE_PATH.write_text(json.dumps({"best_score": int(score)}), encoding="utf-8")
    except OSError:
        pass
