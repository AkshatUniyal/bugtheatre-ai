from __future__ import annotations

from copy import deepcopy


DEMO_CASES: dict[str, dict] = {
    "React hydration mismatch": {
        "case_title": "React Hydration Mismatch on Page Reload",
        "summary": "The failure is most likely caused by non-deterministic render output during server-side rendering. The component renders a live timestamp during the initial render, so the server HTML and client HTML disagree during hydration.",
        "severity": "high",
        "confidence": "high",
        "confidence_score": 88,
        "affected_layer": "frontend",
        "risk_if_ignored": "Users may see flicker, inconsistent UI state, and growing trust issues around page freshness.",
        "prime_suspect": {
            "name": "Non-deterministic SSR render value",
            "why_likely": "The logs explicitly show text content mismatch, and the snippet calls new Date() during render. That creates different server and client text.",
            "evidence": [
                "Hydration failed because initial UI does not match server-rendered HTML.",
                "Server timestamp differs from client timestamp.",
                "Header component calls new Date().toLocaleTimeString() during render."
            ],
            "first_confirmation_step": "Replace the render-time timestamp with a stable server-provided value or move it into a client-only effect, then reload the page."
        },
        "suspects": [
            {
                "name": "Non-deterministic SSR render value",
                "probability": "high",
                "probability_score": 88,
                "evidence_for": ["new Date() appears inside render.", "Error mentions server/client text mismatch."],
                "evidence_against": ["Only one component snippet was provided."],
                "how_to_confirm": "Render a fixed timestamp prop from the server or defer client time rendering until after mount.",
                "status": "prime"
            },
            {
                "name": "Browser extension mutating DOM",
                "probability": "low",
                "probability_score": 12,
                "evidence_for": ["Hydration issues can be caused by external DOM mutation."],
                "evidence_against": ["The app code already contains a direct mismatch source."],
                "how_to_confirm": "Reproduce in a clean browser profile.",
                "status": "low_priority"
            },
            {
                "name": "React version conflict",
                "probability": "medium",
                "probability_score": 32,
                "evidence_for": ["Hydration behavior is framework-sensitive."],
                "evidence_against": ["The stack trace points to text content mismatch, not package resolution."],
                "how_to_confirm": "Check lockfile for duplicate React versions.",
                "status": "investigate"
            }
        ],
        "failure_timeline": [
            "Server renders the Header component.",
            "Header computes the current local time during render.",
            "HTML is sent to the browser with the server-side timestamp.",
            "Client hydrates the page a moment later and computes a different timestamp.",
            "React detects mismatched text and warns that hydration failed."
        ],
        "false_leads": [
            {
                "lead": "Rewriting the whole Header component",
                "why_to_avoid": "The issue is likely one unstable value, not the whole component structure."
            },
            {
                "lead": "Clearing browser cache",
                "why_to_avoid": "The mismatch is generated at render time and will recur after a fresh reload."
            }
        ],
        "fix_plan": {
            "quick_patch": "Render a placeholder until the component mounts, then show the live time on the client.",
            "clean_fix": "Pass a stable formatted timestamp from the server or isolate dynamic time display in a client-only component.",
            "prevention": "Add a lint/review rule for unstable SSR render values such as Date.now(), Math.random(), locale-sensitive formatting, and browser-only APIs.",
            "validation_steps": ["Run the app in production mode.", "Reload the affected route three times.", "Confirm no hydration warnings appear in console."],
            "rollback": "Revert the timestamp display change if the header must remain server-only."
        },
        "suggested_patch": """- <span>Last updated: {new Date().toLocaleTimeString()}</span>
+ <ClientTimeLabel label=\"Last updated\" />""",
        "commands_to_run": ["npm run build", "npm run start", "npx playwright test hydration.spec.ts"],
        "missing_evidence": ["Full console stack trace", "The page or layout where Header is mounted", "Next.js route rendering mode"],
        "postmortem": {
            "summary": "A hydration mismatch occurred because server and client renders produced different timestamp text.",
            "impact": "Some users saw page flicker and console hydration warnings after reload.",
            "root_cause": "A render-time timestamp was computed independently on server and client.",
            "detection": "Detected via React hydration warning and mismatched timestamp text.",
            "resolution": "Moved the dynamic timestamp to a client-stable rendering path.",
            "prevention": "Avoid non-deterministic values during SSR and add regression coverage for reload hydration.",
            "follow_up_actions": ["Add hydration reload test", "Audit SSR components for Date.now() and Math.random()", "Document SSR-safe render rules"]
        }
    },
    "FastAPI dependency mismatch": {
        "case_title": "FastAPI Startup Crash After Pydantic Upgrade",
        "summary": "The application likely combines an older FastAPI release with Pydantic v2. The import error appears during FastAPI dependency setup before business routes run.",
        "severity": "critical",
        "confidence": "high",
        "confidence_score": 91,
        "affected_layer": "dependency",
        "risk_if_ignored": "The API cannot start reliably, blocking all downstream routes and health checks.",
        "prime_suspect": {
            "name": "FastAPI and Pydantic major-version mismatch",
            "why_likely": "The provided requirements pair FastAPI 0.95.0 with Pydantic 2.6.4, and the stack trace fails while importing a Pydantic v1-era symbol.",
            "evidence": ["ImportError references pydantic.fields.Undefined.", "FastAPI 0.95.0 predates Pydantic v2 support.", "Failure happens during app startup."],
            "first_confirmation_step": "Pin Pydantic to a v1-compatible version or upgrade FastAPI to a version compatible with Pydantic v2."
        },
        "suspects": [
            {
                "name": "FastAPI/Pydantic version mismatch",
                "probability": "high",
                "probability_score": 91,
                "evidence_for": ["requirements.txt shows incompatible major versions.", "Import fails in FastAPI dependency utilities."],
                "evidence_against": ["No full lockfile was provided."],
                "how_to_confirm": "Run python -m pip show fastapi pydantic and compare compatibility.",
                "status": "prime"
            },
            {
                "name": "Broken virtual environment",
                "probability": "medium",
                "probability_score": 35,
                "evidence_for": ["Dependency import errors can happen with stale environments."],
                "evidence_against": ["The specific versions already explain the failure."],
                "how_to_confirm": "Create a fresh venv and reinstall from requirements.txt.",
                "status": "investigate"
            }
        ],
        "failure_timeline": [
            "Uvicorn imports the FastAPI app.",
            "FastAPI initializes dependency utilities.",
            "The installed FastAPI version expects Pydantic v1 internals.",
            "Pydantic v2 no longer exposes the expected symbol.",
            "Startup aborts before the health route can serve traffic."
        ],
        "false_leads": [
            {
                "lead": "Changing route handler code",
                "why_to_avoid": "The app fails before route logic executes."
            },
            {
                "lead": "Debugging the database connection",
                "why_to_avoid": "The trace points to dependency imports, not runtime IO."
            }
        ],
        "fix_plan": {
            "quick_patch": "Pin pydantic<2 if the project must stay on the current FastAPI version.",
            "clean_fix": "Upgrade FastAPI and related validation code to a Pydantic v2-compatible stack.",
            "prevention": "Use dependency constraints and a startup smoke test in CI.",
            "validation_steps": ["python -m pip check", "uvicorn app:app --reload", "curl http://localhost:8000/health"],
            "rollback": "Restore the last known-good requirements lockfile."
        },
        "suggested_patch": """- fastapi==0.95.0
- pydantic==2.6.4
+ fastapi>=0.110.0
+ pydantic>=2.6,<3""",
        "commands_to_run": ["python -m pip check", "pytest -q", "uvicorn app:app --host 0.0.0.0 --port 8000"],
        "missing_evidence": ["Full stack trace", "Lockfile", "Current CI dependency install command"],
        "postmortem": {
            "summary": "The API failed to start after incompatible dependency versions were installed.",
            "impact": "Health checks and all API routes were unavailable.",
            "root_cause": "FastAPI expected Pydantic v1 internals while Pydantic v2 was installed.",
            "detection": "Startup import error during dependency initialization.",
            "resolution": "Aligned FastAPI and Pydantic versions.",
            "prevention": "Add constraints, pip check, and startup smoke tests to CI.",
            "follow_up_actions": ["Commit a lockfile", "Add dependency compatibility tests", "Document upgrade policy"]
        }
    },
    "Docker port mismatch": {
        "case_title": "Docker Container Starts But Host Cannot Reach Service",
        "summary": "The container is probably healthy internally but mapped to the wrong exposed port. The app listens on 3000 while Docker metadata and Compose route traffic to 8080.",
        "severity": "medium",
        "confidence": "high",
        "confidence_score": 86,
        "affected_layer": "deployment",
        "risk_if_ignored": "Deployments appear green while the service remains unreachable to users or checks.",
        "prime_suspect": {
            "name": "Container port mapping mismatch",
            "why_likely": "Logs say the app listens on 3000, but Dockerfile and Compose expose/map 8080.",
            "evidence": ["Server listening on port 3000.", "EXPOSE 8080.", "Compose maps 8080:8080."],
            "first_confirmation_step": "Map host port 8080 to container port 3000 or change the app to listen on 8080."
        },
        "suspects": [
            {
                "name": "Port mapping mismatch",
                "probability": "high",
                "probability_score": 86,
                "evidence_for": ["Runtime port and Compose container port differ."],
                "evidence_against": ["No container inspect output provided."],
                "how_to_confirm": "Run docker compose exec web curl localhost:3000 and test host mapping.",
                "status": "prime"
            },
            {
                "name": "Firewall or host network block",
                "probability": "low",
                "probability_score": 14,
                "evidence_for": ["Host cannot connect."],
                "evidence_against": ["The port mismatch explains the symptom directly."],
                "how_to_confirm": "Check docker ps port mapping and local firewall rules.",
                "status": "low_priority"
            }
        ],
        "failure_timeline": [
            "Container starts successfully.",
            "Node app binds to port 3000 inside the container.",
            "Docker exposes and maps container port 8080.",
            "Host requests hit 8080, where no process is listening inside the container.",
            "The service appears up but is unreachable from the host."
        ],
        "false_leads": [
            {
                "lead": "Rebuilding application code",
                "why_to_avoid": "The server starts; the failure is in runtime routing."
            },
            {
                "lead": "Changing DNS",
                "why_to_avoid": "The local localhost mapping fails before DNS is involved."
            }
        ],
        "fix_plan": {
            "quick_patch": "Change Compose to map 8080:3000.",
            "clean_fix": "Standardize PORT across app config, Dockerfile, Compose, and deployment docs.",
            "prevention": "Add a container smoke test that curls the externally mapped port.",
            "validation_steps": ["docker compose up --build", "docker compose ps", "curl http://localhost:8080"],
            "rollback": "Revert Compose port mapping if another service depends on the old port."
        },
        "suggested_patch": """ ports:
-  - "8080:8080"
+  - "8080:3000" """,
        "commands_to_run": ["docker compose up --build", "docker compose ps", "curl -i http://localhost:8080"],
        "missing_evidence": ["docker ps output", "Application PORT environment variable", "Container healthcheck config"],
        "postmortem": {
            "summary": "The app container started but host traffic was mapped to the wrong internal port.",
            "impact": "Developers could not access the service through the documented localhost URL.",
            "root_cause": "App runtime port did not match Dockerfile and Compose port configuration.",
            "detection": "Container logs showed port 3000 while host mapping targeted 8080.",
            "resolution": "Aligned host-to-container port mapping.",
            "prevention": "Centralize PORT configuration and add a smoke test.",
            "follow_up_actions": ["Add docker smoke test", "Document PORT convention", "Review deployment manifests for the same mismatch"]
        }
    }
}


def get_demo_case(name: str) -> dict:
    return deepcopy(DEMO_CASES[name])


def names() -> list[str]:
    return list(DEMO_CASES)
