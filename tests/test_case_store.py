from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

import utils.case_store as cs


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(cs, "STORE_PATH", tmp_path / "cases.json")
    yield tmp_path / "cases.json"


def _make_result(title: str = "Test bug") -> dict:
    return {
        "case_title": title,
        "summary": "Something broke.",
        "severity": "medium",
        "confidence": "medium",
        "confidence_score": 70,
        "affected_layer": "backend",
        "risk_if_ignored": "Low.",
        "prime_suspect": {"name": "Root cause", "why_likely": "Evidence.", "evidence": [], "first_confirmation_step": "Check."},
        "suspects": [],
        "failure_timeline": ["Step 1"],
        "false_leads": [],
        "fix_plan": {"quick_patch": "Patch.", "clean_fix": "Fix.", "prevention": "Test.", "validation_steps": ["Verify."], "rollback": "Revert."},
        "suggested_patch": "",
        "commands_to_run": [],
        "missing_evidence": [],
        "postmortem": {},
    }


def test_load_cases_empty_when_no_file():
    assert cs.load_cases() == []


def test_save_and_load_round_trip():
    result = _make_result("My Bug")
    record = cs.save_case({"title": "My Bug"}, result)
    assert record["title"] == "My Bug"
    cases = cs.load_cases()
    assert len(cases) == 1
    assert cases[0]["id"] == record["id"]


def test_save_case_strips_screenshot():
    payload = {"title": "Bug", "screenshot_base64": "data..."}
    cs.save_case(payload, _make_result())
    stored = json.loads(cs.STORE_PATH.read_text())
    assert "screenshot_base64" not in stored[0]["payload"]


def test_save_case_inserts_at_front():
    cs.save_case({"title": "First"}, _make_result("First"))
    cs.save_case({"title": "Second"}, _make_result("Second"))
    cases = cs.load_cases()
    assert cases[0]["title"] == "Second"


def test_case_limit_enforced(monkeypatch):
    monkeypatch.setattr(cs, "CASE_LIMIT", 3)
    for i in range(5):
        cs.save_case({"title": f"Bug {i}"}, _make_result(f"Bug {i}"))
    cases = cs.load_cases()
    assert len(cases) == 3


def test_latest_case_returns_most_recent():
    cs.save_case({"title": "First"}, _make_result("First"))
    cs.save_case({"title": "Second"}, _make_result("Second"))
    latest = cs.latest_case()
    assert latest is not None
    assert latest["title"] == "Second"


def test_latest_case_none_when_empty():
    assert cs.latest_case() is None


def test_corrupt_json_returns_empty(tmp_store):
    tmp_store.write_text("not json", encoding="utf-8")
    assert cs.load_cases() == []


def test_concurrent_writes_no_corruption():
    errors = []

    def write_case(i):
        try:
            cs.save_case({"title": f"Case {i}"}, _make_result(f"Case {i}"))
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=write_case, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], f"Errors in threads: {errors}"
    stored = json.loads(cs.STORE_PATH.read_text())
    assert isinstance(stored, list)
    assert len(stored) > 0
