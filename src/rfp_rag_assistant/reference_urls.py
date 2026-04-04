from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _inventory_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "reference_url_inventory.json"


@lru_cache(maxsize=1)
def load_reference_url_inventory() -> list[dict[str, Any]]:
    return json.loads(_inventory_path().read_text(encoding="utf-8"))
