from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).with_name("data")


@lru_cache(maxsize=1)
def _load_json(filename: str) -> dict[str, Any]:
    return json.loads((DATA_DIR / filename).read_text(encoding="utf-8"))


def emotion_content() -> dict[str, Any]:
    return _load_json("emotion_config.json")


def companion_content() -> dict[str, Any]:
    return _load_json("companion_config.json")
