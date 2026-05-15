from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from utils.gemma_client import normalize_case


STORE_PATH = Path(__file__).resolve().parents[1] / "data" / "cases.json"


def load_cases() -> list[dict[str, Any]]:
    if not STORE_PATH.exists():
        return []
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    for record in data:
        if isinstance(record, dict) and isinstance(record.get("result"), dict):
            record["result"] = normalize_case(record["result"], record.get("payload", {}))
            if record["result"].get("case_title"):
                record["title"] = record["result"]["case_title"]
    return data


def save_case(payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    cases = load_cases()
    stored_payload = {key: value for key, value in payload.items() if key != "screenshot_base64"}
    record = {
        "id": f"BT-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "title": result.get("case_title") or payload.get("title") or "Untitled bug case",
        "payload": stored_payload,
        "result": result,
    }
    cases.insert(0, record)
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(cases[:50], indent=2), encoding="utf-8")
    return record


def latest_case() -> dict[str, Any] | None:
    cases = load_cases()
    return cases[0] if cases else None
