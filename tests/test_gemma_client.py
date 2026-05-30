from __future__ import annotations

import json
import pytest

from utils.gemma_client import _as_score, _extract_json, normalize_case


def test_as_score_percentage():
    assert _as_score(85) == 85


def test_as_score_fractional():
    assert _as_score(0.85) == 85


def test_as_score_clamps_above_100():
    assert _as_score(150) == 100


def test_as_score_clamps_below_0():
    assert _as_score(-5) == 0


def test_as_score_default_on_invalid():
    assert _as_score("bad") == 70
    assert _as_score(None) == 70


def test_extract_json_plain():
    data = _extract_json('{"key": "value"}')
    assert data == {"key": "value"}


def test_extract_json_fenced():
    data = _extract_json('```json\n{"key": "value"}\n```')
    assert data == {"key": "value"}


def test_extract_json_fenced_no_lang():
    data = _extract_json('```\n{"key": "value"}\n```')
    assert data == {"key": "value"}


def test_extract_json_embedded():
    data = _extract_json('Some text {"key": "value"} trailing')
    assert data == {"key": "value"}


def test_extract_json_invalid_raises():
    with pytest.raises(json.JSONDecodeError):
        _extract_json("not json at all")


def test_normalize_case_fills_defaults():
    result = normalize_case({}, {})
    assert result["case_title"] == "Bug investigation"
    assert "prime_suspect" in result
    assert "fix_plan" in result
    assert "postmortem" in result


def test_normalize_case_preserves_title():
    result = normalize_case({"case_title": "My Bug"}, {})
    assert result["case_title"] == "My Bug"


def test_normalize_case_confidence_high():
    result = normalize_case({"confidence_score": 90}, {})
    assert result["confidence"] == "high"
    assert result["confidence_score"] == 90


def test_normalize_case_confidence_medium():
    result = normalize_case({"confidence_score": 60}, {})
    assert result["confidence"] == "medium"


def test_normalize_case_confidence_low():
    result = normalize_case({"confidence_score": 30}, {})
    assert result["confidence"] == "low"


def test_normalize_case_postmortem_filled():
    result = normalize_case({}, {"title": "Startup crash"})
    pm = result["postmortem"]
    assert pm.get("summary")
    assert pm.get("root_cause")
    assert pm.get("resolution")
