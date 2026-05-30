from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from utils.gemma_client import normalize_case

logger = logging.getLogger(__name__)

STORE_PATH = Path(__file__).resolve().parents[1] / "data" / "cases.json"
CASE_LIMIT = 50

_store_lock = threading.Lock()


def load_cases() -> list[dict[str, Any]]:
    if not STORE_PATH.exists():
        return []
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    for record in data:
        if isinstance(record, dict) and isinstance(record.get("result"), dict):
            try:
                record["result"] = normalize_case(record["result"], record.get("payload", {}))
            except Exception:
                logger.exception("normalize_case failed for record %s — keeping raw result", record.get("id"))
            if record["result"].get("case_title"):
                record["title"] = record["result"]["case_title"]
    return data


def save_case(payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    stored_payload = {key: value for key, value in payload.items() if key != "screenshot_base64"}
    record = {
        "id": f"BT-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "title": result.get("case_title") or payload.get("title") or "Untitled bug case",
        "payload": stored_payload,
        "result": result,
    }
    with _store_lock:
        cases = load_cases()
        cases.insert(0, record)
        if len(cases) > CASE_LIMIT:
            logger.warning(
                "Case store reached the %d-case limit. Oldest %d case(s) will be dropped.",
                CASE_LIMIT,
                len(cases) - CASE_LIMIT,
            )
        STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STORE_PATH.write_text(json.dumps(cases[:CASE_LIMIT], indent=2), encoding="utf-8")
    return record


def latest_case() -> dict[str, Any] | None:
    cases = load_cases()
    return cases[0] if cases else None
