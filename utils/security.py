from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactionResult:
    text: str
    findings: list[str]


SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----")),
    ("bearer token", re.compile(r"(?i)\bbearer\s+[a-z0-9._\-]{20,}")),
    ("api key", re.compile(r"(?i)\b(api[_-]?key|secret[_-]?key|token)\s*[:=]\s*['\"]?([a-z0-9_\-./+=]{16,})['\"]?")),
    ("password", re.compile(r"(?i)\b(password|passwd|pwd)\s*[:=]\s*['\"]?([^'\"\s]{6,})['\"]?")),
    ("database url", re.compile(r"(?i)\b[a-z]+://[^:\s]+:[^@\s]+@[^/\s]+/[^\s]+")),
    ("aws access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("generic long secret", re.compile(r"\b[a-zA-Z0-9_\-]{32,}\b")),
]


def redact_secrets(text: str) -> RedactionResult:
    findings: list[str] = []
    redacted = text

    for label, pattern in SECRET_PATTERNS:
        if pattern.search(redacted):
            findings.append(label)
            redacted = pattern.sub(f"[REDACTED {label.upper()}]", redacted)

    return RedactionResult(text=redacted, findings=sorted(set(findings)))
