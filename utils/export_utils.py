from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "bug-case"


def postmortem_markdown(case: dict[str, Any]) -> str:
    pm = case.get("postmortem", {})
    actions = pm.get("follow_up_actions", [])
    action_lines = "\n".join(f"- [ ] {item}" for item in actions) or "- [ ] Add follow-up actions"

    return f"""# Postmortem: {case.get("case_title", "Bug Case")}

## Summary
{pm.get("summary", case.get("summary", ""))}

## Impact
{pm.get("impact", "Impact not yet quantified.")}

## Root Cause
{pm.get("root_cause", case.get("prime_suspect", {}).get("name", "Unknown"))}

## Detection
{pm.get("detection", "Detected through supplied debugging evidence.")}

## Resolution
{pm.get("resolution", case.get("fix_plan", {}).get("clean_fix", ""))}

## Prevention
{pm.get("prevention", case.get("fix_plan", {}).get("prevention", ""))}

## Follow-up Actions
{action_lines}
"""


def case_markdown(case: dict[str, Any]) -> str:
    suspects = "\n".join(
        f"- **{s.get('name')}** ({s.get('probability')}): {s.get('how_to_confirm')}"
        for s in case.get("suspects", [])
    )
    timeline = "\n".join(f"{i}. {step}" for i, step in enumerate(case.get("failure_timeline", []), start=1))
    false_leads = "\n".join(
        f"- **{lead.get('lead')}**: {lead.get('why_to_avoid')}"
        for lead in case.get("false_leads", [])
    )
    validation = "\n".join(f"- {step}" for step in case.get("fix_plan", {}).get("validation_steps", []))

    return f"""# BugTheatre Case File: {case.get("case_title", "Bug Case")}

## Executive Debug Summary
{case.get("summary", "")}

## Prime Suspect
**{case.get("prime_suspect", {}).get("name", "Unknown")}**

{case.get("prime_suspect", {}).get("why_likely", "")}

## Suspect Board
{suspects}

## Failure Timeline
{timeline}

## Fix Plan
### Quick Patch
{case.get("fix_plan", {}).get("quick_patch", "")}

### Clean Fix
{case.get("fix_plan", {}).get("clean_fix", "")}

### Prevention
{case.get("fix_plan", {}).get("prevention", "")}

## Validation
{validation}

## Don't Waste Time Here
{false_leads}

## Suggested Patch
```diff
{case.get("suggested_patch", "")}
```
"""


def save_exports(case: dict[str, Any], export_dir: Path) -> dict[str, Path]:
    export_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = slugify(case.get("case_title", "bug-case"))
    base = export_dir / f"{stamp}-{slug}"

    md_path = base.with_suffix(".md")
    json_path = base.with_suffix(".json")
    postmortem_path = export_dir / f"{stamp}-{slug}-postmortem.md"

    md_path.write_text(case_markdown(case), encoding="utf-8")
    postmortem_path.write_text(postmortem_markdown(case), encoding="utf-8")
    json_path.write_text(json.dumps(case, indent=2), encoding="utf-8")

    return {"case_markdown": md_path, "postmortem": postmortem_path, "json": json_path}
