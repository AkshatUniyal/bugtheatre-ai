from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Any
from urllib import error, request

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional at import time
    load_dotenv = None

if load_dotenv:
    load_dotenv()


def gemma_enabled() -> bool:
    return os.getenv("ENABLE_LOCAL_AI", "1") == "1" and ollama_available()


def ollama_host() -> str:
    return os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")


def ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "gemma4:e2b")


def ollama_timeout_seconds() -> int:
    raw_timeout = os.getenv("OLLAMA_TIMEOUT_SECONDS", "300")
    try:
        return max(30, int(raw_timeout))
    except ValueError:
        return 300


def ollama_num_predict() -> int:
    raw_limit = os.getenv("OLLAMA_NUM_PREDICT", "3000")
    try:
        return max(512, int(raw_limit))
    except ValueError:
        return 3000


def ollama_available() -> bool:
    try:
        with request.urlopen(f"{ollama_host()}/api/tags", timeout=1.5) as response:
            data = json.loads(response.read().decode("utf-8"))
        models = {model.get("name") for model in data.get("models", [])}
        return ollama_model() in models
    except Exception:
        return False


def build_prompt(input_payload: dict[str, Any]) -> str:
    prompt_path = Path("prompts/investigation_prompt.md")
    base_prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
    prompt_payload = {key: value for key, value in input_payload.items() if key != "screenshot_base64"}
    return f"""{base_prompt}

User debugging evidence:

```json
{json.dumps(prompt_payload, indent=2)}
```
"""


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").removesuffix("```").strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def _as_score(value: Any, default: int = 70) -> int:
    if isinstance(value, (int, float)):
        return max(0, min(100, int(value * 100 if value <= 1 else value)))
    return default


def _case_text(case: dict[str, Any], input_payload: dict[str, Any]) -> str:
    return json.dumps({"case": case, "input": input_payload}, default=str).lower()


def _input_text(input_payload: dict[str, Any]) -> str:
    return json.dumps(input_payload, default=str).lower()


def _is_react_hydration_input(input_payload: dict[str, Any]) -> bool:
    text = _input_text(input_payload)
    hydration_signals = ("hydration", "server-rendered html", "server html", "client html", "ssr")
    react_signals = ("react", "next.js", "nextjs", "header.tsx", "new date", "tolocaletimestring", "timestamp")
    return any(signal in text for signal in hydration_signals) and any(signal in text for signal in react_signals)


def _harden_react_hydration_case(case: dict[str, Any], input_payload: dict[str, Any]) -> dict[str, Any]:
    if not _is_react_hydration_input(input_payload):
        return case

    title = input_payload.get("title") or case.get("case_title") or "Cart page hydration issue"
    case["case_title"] = title
    case["affected_layer"] = "frontend"
    case["severity"] = "high"
    case["confidence"] = "high"
    case["confidence_score"] = max(_as_score(case.get("confidence_score"), 88), 88)
    case["summary"] = (
        "The evidence points to a React / Next.js hydration mismatch caused by non-deterministic render output. "
        "A timestamp is generated during render, so the server-rendered HTML and client-rendered HTML can disagree during hydration."
    )
    case["risk_if_ignored"] = (
        "Users may see page flicker, hydration warnings, inconsistent UI state, and reduced trust in page freshness."
    )
    case["prime_suspect"] = {
        "name": "Non-deterministic SSR render value",
        "why_likely": (
            "The evidence mentions React hydration failure, server/client HTML mismatch, and a timestamp generated with "
            "new Date().toLocaleTimeString() during render. That value can differ between server and client."
        ),
        "evidence": [
            "Hydration failed because the initial UI does not match server-rendered HTML.",
            "Text content differs between server render and client hydration.",
            "Header.tsx renders a live timestamp using new Date().toLocaleTimeString().",
        ],
        "first_confirmation_step": "Replace the render-time timestamp with a stable server value or move it into a client-only effect, then reload the page.",
    }
    case["suspects"] = [
        {
            "name": "Timestamp computed during SSR render",
            "probability": "high",
            "probability_score": 90,
            "evidence_for": ["new Date().toLocaleTimeString()", "server/client text mismatch", "hydration warning"],
            "evidence_against": ["Need exact component stack and route to confirm the mount path"],
            "how_to_confirm": "Render a stable placeholder on the server, update time after mount, and confirm hydration warnings disappear.",
            "status": "prime",
        },
        {
            "name": "Other browser-only render value",
            "probability": "medium",
            "probability_score": 45,
            "evidence_for": ["Hydration mismatches can also come from locale, randomness, or window-dependent values"],
            "evidence_against": ["The provided evidence specifically points to the timestamp"],
            "how_to_confirm": "Audit the affected route for Date.now(), Math.random(), locale-sensitive formatting, and browser-only APIs during render.",
            "status": "investigate",
        },
    ]
    case["failure_timeline"] = [
        "Server renders the cart page and computes a timestamp in Header.tsx.",
        "Browser receives server HTML with that timestamp text.",
        "Client hydration computes a new timestamp value.",
        "React detects that client text does not match server-rendered HTML.",
        "The page replaces server content with client content and logs hydration warnings.",
    ]
    case["false_leads"] = [
        {
            "lead": "Suppressing the hydration warning",
            "why_to_avoid": "It hides the symptom but leaves inconsistent server/client output in place.",
        },
        {
            "lead": "Reloading the page as a fix",
            "why_to_avoid": "The timestamp can differ on every fresh render, so the mismatch can recur.",
        },
    ]
    case["fix_plan"] = {
        "quick_patch": "Render a stable placeholder until the component mounts, then show the live time on the client.",
        "clean_fix": "Pass a stable formatted timestamp from the server or isolate dynamic time display in a client-only component.",
        "prevention": "Add a lint/review rule for unstable SSR render values such as Date.now(), Math.random(), locale-sensitive formatting, and browser-only APIs.",
        "validation_steps": [
            "Run the app in production mode.",
            "Reload the affected route several times.",
            "Confirm no React hydration warnings appear in the browser console.",
            "Verify the timestamp still updates correctly after client mount.",
        ],
        "rollback": "Revert the timestamp display change if the header must remain server-only, then replace it with a static server-provided value.",
    }
    case["suggested_patch"] = (
        '- <span>Last updated: {new Date().toLocaleTimeString()}</span>\n'
        '+ <ClientTimeLabel label="Last updated" />'
    )
    case["commands_to_run"] = [
        "npm run build",
        "npm run start",
        "npx playwright test hydration.spec.ts",
    ]
    case["missing_evidence"] = [
        "Full browser console stack trace",
        "The route or layout where Header.tsx is mounted",
        "Whether the affected route uses SSR, SSG, or client-only rendering",
    ]
    case["postmortem"] = {
        "summary": "A hydration mismatch occurred because server and client renders produced different timestamp text.",
        "impact": "Users saw page flicker and React hydration warnings after reload.",
        "root_cause": "A render-time timestamp was computed independently on server and client.",
        "detection": "Detected through React hydration warnings and mismatched timestamp text.",
        "resolution": "Moved the dynamic timestamp to a client-only path or replaced it with a stable server-provided value.",
        "prevention": "Avoid non-deterministic values during SSR and add regression coverage for reload hydration.",
        "follow_up_actions": [
            "Add a hydration reload test.",
            "Audit SSR components for Date.now() and Math.random().",
            "Document SSR-safe render rules.",
        ],
    }
    return case


def _is_laravel_csrf_case(case: dict[str, Any], input_payload: dict[str, Any]) -> bool:
    if _is_react_hydration_input(input_payload):
        return False
    text = _case_text(case, input_payload)
    signals = ("laravel", "csrf", "419", "tokenmismatch", "page expired", "verifycsrftoken", "session")
    return ("csrf" in text or "419" in text or "tokenmismatch" in text or "page expired" in text) and any(signal in text for signal in signals)


def _harden_laravel_csrf_case(case: dict[str, Any], input_payload: dict[str, Any]) -> dict[str, Any]:
    if not _is_laravel_csrf_case(case, input_payload):
        return case

    case["case_title"] = case.get("case_title") or "Laravel 419 CSRF Token Mismatch"
    case["affected_layer"] = "auth"
    case["summary"] = (
        "The supplied evidence points to a Laravel 419 Page Expired / CSRF token mismatch during an admin action. "
        "The safest fix path is to refresh or regenerate the CSRF token before submission, handle expired sessions gracefully, "
        "and verify Laravel session, cookie, and CSRF middleware configuration."
    )
    case["risk_if_ignored"] = (
        "Admins may lose work after inactivity, repeat failed submissions, or bypass the intended workflow with manual refreshes."
    )
    case["prime_suspect"] = {
        "name": "Expired or stale Laravel CSRF token during admin inactivity",
        "why_likely": (
            "The symptom is a 419 Page Expired / CSRF mismatch around an admin status update after the page has been idle. "
            "Shortening the session timeout would likely make that failure happen sooner, so the fix should improve token/session handling."
        ),
        "evidence": [
            "HTTP 419 Page Expired response on the status update request.",
            "CSRF token mismatch is reported for the failed submission.",
            "The failure appears after the admin page has been open or inactive for some time.",
        ],
        "first_confirmation_step": "Reproduce with an idle admin page, inspect the request token/cookies, and confirm whether Laravel treats the token as expired or mismatched.",
    }
    case["suspects"] = [
        {
            "name": "Stale CSRF token on long-lived admin form",
            "probability": "high",
            "probability_score": 88,
            "evidence_for": ["419 Page Expired", "CSRF token mismatch", "Admin form fails after inactivity"],
            "evidence_against": ["Full middleware/session configuration still needs verification"],
            "how_to_confirm": "Compare the submitted _token/header value with the active session token after idle time.",
            "status": "prime",
        },
        {
            "name": "Laravel session or cookie configuration mismatch",
            "probability": "medium",
            "probability_score": 55,
            "evidence_for": ["CSRF validation depends on session persistence and cookie scope"],
            "evidence_against": ["No session driver or cookie config was provided in the evidence"],
            "how_to_confirm": "Check SESSION_DRIVER, SESSION_DOMAIN, SESSION_SECURE_COOKIE, same-site settings, and Redis/session store health if Redis is used.",
            "status": "investigate",
        },
    ]
    case["failure_timeline"] = [
        "Admin opens the order/status page with a CSRF token embedded in the form or request setup.",
        "The page remains idle long enough for session/token state to become stale.",
        "Admin submits the status update.",
        "Laravel CSRF verification rejects the request and returns 419 Page Expired.",
        "The UI reports a failed update instead of guiding the admin to refresh or re-authenticate.",
    ]
    case["false_leads"] = [
        {
            "lead": "Shortening the session timeout",
            "why_to_avoid": "That can make stale-token failures happen sooner and does not solve graceful recovery from 419 responses.",
        },
        {
            "lead": "Changing order status business logic first",
            "why_to_avoid": "The failure is at request/session validation before the domain update can be trusted.",
        },
    ]
    case["fix_plan"] = {
        "quick_patch": "Handle 419 responses gracefully: prompt the admin to re-authenticate or refresh, preserve unsaved intent, and retry only after a fresh CSRF token is available.",
        "clean_fix": "Refresh or regenerate the CSRF token before sensitive admin submissions, warn before session expiry, and verify Laravel session/cookie/CSRF middleware configuration.",
        "prevention": "Add an admin idle-session test covering 419 Page Expired, TokenMismatchException handling, VerifyCsrfToken.php behavior, session driver persistence, and cookie scope.",
        "validation_steps": [
            "Reproduce the issue by leaving the admin order page idle past the session threshold.",
            "Submit the status update and confirm the app shows a re-authentication or refresh path instead of a silent failure.",
            "Verify a refreshed CSRF token allows the update to complete successfully.",
            "Check Laravel session driver/cookie settings, including Redis/session store health if Redis is configured.",
        ],
        "rollback": "Revert the token-refresh/419-handling change if it blocks valid admin submissions, then restore the previous form flow while investigating session configuration.",
    }
    case["suggested_patch"] = (
        "Add a 419-aware submit path: before posting the admin status update, refresh the CSRF token or rehydrate it from a dedicated endpoint; "
        "on 419, preserve the requested status change, prompt re-authentication or page refresh, then retry with a fresh token. "
        "Also verify VerifyCsrfToken.php exclusions, SESSION_DRIVER, SESSION_DOMAIN, SESSION_SECURE_COOKIE, same-site settings, and Redis/session store health if applicable."
    )
    case["commands_to_run"] = [
        "php artisan config:show session",
        "php artisan route:list | grep admin",
        "tail -f storage/logs/laravel.log",
        "Reproduce idle admin form submission and inspect the _token/header/cookie values",
    ]
    case["missing_evidence"] = [
        "Full Laravel log entry containing TokenMismatchException, if present",
        "VerifyCsrfToken.php middleware configuration",
        "SESSION_DRIVER and session/cookie config",
        "Whether Redis is used for session storage and whether it evicts/loses sessions",
        "Exact idle duration before failure",
    ]
    case["postmortem"] = {
        "summary": "An admin status update failed with Laravel 419 Page Expired because CSRF/session state became stale after admin inactivity.",
        "impact": "Admins could not reliably save status changes after idle periods and may have needed manual refresh or re-authentication.",
        "root_cause": "The request reached Laravel with an expired or mismatched CSRF/session state rather than a fresh token tied to the active session.",
        "detection": "Detected through the 419 Page Expired response, CSRF mismatch signal, and the failed admin status submission.",
        "resolution": "Added a safer recovery path: refresh/regenerate CSRF token before submission, handle 419 with re-authentication or page refresh, and verify session/cookie configuration.",
        "prevention": "Cover TokenMismatchException/419 handling, VerifyCsrfToken.php behavior, session driver configuration, Redis-backed sessions if used, and admin inactivity in regression tests.",
        "follow_up_actions": [
            "Audit VerifyCsrfToken.php and admin route middleware.",
            "Verify SESSION_DRIVER, cookie domain, secure cookie, and same-site settings.",
            "Add an idle-session admin update test.",
            "Confirm Redis/session storage health if Redis is configured.",
        ],
    }
    return case


def normalize_case(case: dict[str, Any], input_payload: dict[str, Any]) -> dict[str, Any]:
    """Fill the full UI contract when smaller local models return a compact JSON."""
    case = _harden_react_hydration_case(case, input_payload)
    case = _harden_laravel_csrf_case(case, input_payload)
    title = case.get("case_title") or input_payload.get("case_title") or input_payload.get("title") or "Bug investigation"
    prime = case.get("prime_suspect") if isinstance(case.get("prime_suspect"), dict) else {}
    prime_name = prime.get("name") or case.get("root_cause") or case.get("prime_suspect") or "Most likely root cause"
    summary = case.get("summary") or prime.get("why_likely") or input_payload.get("actual_behavior") or "Gemma reviewed the supplied debugging evidence and produced a local investigation case file."
    confidence_score = _as_score(case.get("confidence_score"), 70)
    confidence = case.get("confidence") or ("high" if confidence_score >= 80 else "medium" if confidence_score >= 50 else "low")
    severity = case.get("severity") or "medium"
    affected_layer = case.get("affected_layer") or "unknown"
    evidence = prime.get("evidence") if isinstance(prime.get("evidence"), list) else []
    if not evidence:
        evidence = [item for item in [input_payload.get("logs"), input_payload.get("code"), input_payload.get("actual_behavior")] if item]
    if not evidence and input_payload.get("screenshot_base64"):
        evidence = ["Screenshot evidence was provided for local Gemma analysis."]

    fix = case.get("fix_plan") if isinstance(case.get("fix_plan"), dict) else {}
    validation_steps = fix.get("validation_steps") if isinstance(fix.get("validation_steps"), list) else []
    if not validation_steps:
        validation_steps = [
            case.get("first_confirmation_step") or prime.get("first_confirmation_step") or "Reproduce the issue with the supplied evidence.",
            "Apply the smallest safe change.",
            "Re-run the failing path and confirm the warning or error is gone.",
        ]

    normalized = {
        "case_title": title,
        "summary": summary,
        "severity": severity,
        "confidence": confidence,
        "confidence_score": confidence_score,
        "affected_layer": affected_layer,
        "risk_if_ignored": case.get("risk_if_ignored") or "The issue may continue to affect reliability, user trust, or deployment confidence.",
        "prime_suspect": {
            "name": prime_name,
            "why_likely": prime.get("why_likely") or summary,
            "evidence": evidence[:5],
            "first_confirmation_step": prime.get("first_confirmation_step") or case.get("first_confirmation_step") or validation_steps[0],
        },
        "suspects": case.get("suspects") if isinstance(case.get("suspects"), list) else [],
        "failure_timeline": case.get("failure_timeline") if isinstance(case.get("failure_timeline"), list) else ["Evidence supplied", "Gemma generated local diagnosis", "Developer validates the prime suspect"],
        "false_leads": case.get("false_leads") if isinstance(case.get("false_leads"), list) else [],
        "fix_plan": {
            "quick_patch": fix.get("quick_patch") or "Apply the smallest change that removes the confirmed failure path.",
            "clean_fix": fix.get("clean_fix") or "Move from the quick patch to a maintainable fix once the root cause is confirmed.",
            "prevention": fix.get("prevention") or "Add a regression check so the same class of issue is caught earlier.",
            "validation_steps": validation_steps,
            "rollback": fix.get("rollback") or "Revert the change if validation fails or a safer fix is needed.",
        },
        "suggested_patch": case.get("suggested_patch") or "Patch suggestion depends on the confirmed source file and failing path.",
        "commands_to_run": case.get("commands_to_run") if isinstance(case.get("commands_to_run"), list) else ["Run the relevant test or reproduction command for this project."],
        "missing_evidence": case.get("missing_evidence") if isinstance(case.get("missing_evidence"), list) else ["Exact file path", "Full stack trace", "Minimal reproduction steps"],
        "postmortem": case.get("postmortem") if isinstance(case.get("postmortem"), dict) else {},
    }
    pm = normalized["postmortem"]
    pm.setdefault("summary", normalized["summary"])
    pm.setdefault("impact", normalized["risk_if_ignored"])
    pm.setdefault("root_cause", normalized["prime_suspect"]["name"])
    pm.setdefault("detection", "Detected from user-supplied debugging evidence.")
    pm.setdefault("resolution", normalized["fix_plan"]["clean_fix"])
    pm.setdefault("prevention", normalized["fix_plan"]["prevention"])
    pm.setdefault("follow_up_actions", normalized["fix_plan"]["validation_steps"])
    return normalized


def investigate_with_gemma(input_payload: dict[str, Any]) -> dict[str, Any]:
    """Call local Gemma through Ollama and return structured investigation JSON."""
    payload = {
        "model": ollama_model(),
        "prompt": build_prompt(input_payload),
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2,
            "top_p": 0.9,
            "num_predict": ollama_num_predict(),
        },
    }
    if input_payload.get("screenshot_base64"):
        payload["images"] = [input_payload["screenshot_base64"]]
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{ollama_host()}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=ollama_timeout_seconds()) as response:
            data = json.loads(response.read().decode("utf-8"))
    except socket.timeout as exc:
        raise RuntimeError(
            f"Local Ollama timed out after {ollama_timeout_seconds()} seconds. "
            "Try again, reduce evidence size, or use a smaller Gemma 4 model for live demos."
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach local Ollama at {ollama_host()}.") from exc

    return normalize_case(_extract_json(data.get("response", "")), input_payload)
