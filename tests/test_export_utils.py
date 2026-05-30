from __future__ import annotations

from utils.export_utils import slugify, case_markdown, postmortem_markdown


def test_slugify_basic():
    assert slugify("Hello World") == "hello-world"


def test_slugify_special_chars():
    # Non-alphanumeric chars become dashes; consecutive dashes are collapsed
    assert slugify("FastAPI / Pydantic bug!") == "fastapi-pydantic-bug"


def test_slugify_collapse_dashes():
    # Consecutive spaces → consecutive dashes → collapsed to one
    assert slugify("a  b") == "a-b"


def test_slugify_empty_fallback():
    assert slugify("") == "bug-case"
    # All non-alphanumeric chars produce only dashes, which get stripped → fallback
    assert slugify("!@#") == "bug-case"


def _minimal_case() -> dict:
    return {
        "case_title": "Test Bug",
        "summary": "Something broke.",
        "severity": "high",
        "confidence": "high",
        "confidence_score": 90,
        "affected_layer": "backend",
        "risk_if_ignored": "Service down.",
        "prime_suspect": {
            "name": "Null pointer",
            "why_likely": "Obvious from trace.",
            "evidence": ["trace line 42"],
            "first_confirmation_step": "Check logs.",
        },
        "suspects": [],
        "failure_timeline": ["Request received", "Crash"],
        "false_leads": [],
        "fix_plan": {
            "quick_patch": "Add null check.",
            "clean_fix": "Refactor service.",
            "prevention": "Add test.",
            "validation_steps": ["Run tests."],
            "rollback": "Revert commit.",
        },
        "suggested_patch": "- bad_line\n+ good_line",
        "commands_to_run": ["pytest"],
        "missing_evidence": ["Full stack trace"],
        "postmortem": {
            "summary": "Summary.",
            "impact": "Low.",
            "root_cause": "Null pointer.",
            "detection": "Logs.",
            "resolution": "Fixed.",
            "prevention": "Tests.",
            "follow_up_actions": ["Write test"],
        },
    }


def test_case_markdown_contains_title():
    md = case_markdown(_minimal_case())
    assert "Test Bug" in md
    assert "Null pointer" in md


def test_case_markdown_contains_patch():
    md = case_markdown(_minimal_case())
    assert "bad_line" in md
    assert "good_line" in md


def test_postmortem_markdown_contains_title():
    md = postmortem_markdown(_minimal_case())
    assert "Test Bug" in md


def test_postmortem_markdown_follow_up_actions():
    md = postmortem_markdown(_minimal_case())
    assert "Write test" in md


def test_case_markdown_empty_case():
    md = case_markdown({})
    assert "Bug Case" in md


def test_postmortem_markdown_empty_case():
    md = postmortem_markdown({})
    assert "Bug Case" in md
