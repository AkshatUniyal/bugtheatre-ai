from __future__ import annotations

import json
import os
import base64
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st

from utils.export_utils import case_markdown, postmortem_markdown, save_exports
from utils.gemma_client import gemma_enabled, investigate_with_gemma
from utils.mock_cases import get_demo_case, names as demo_names
from utils.security import redact_secrets
from utils.case_store import latest_case, load_cases, save_case


APP_DIR = Path(__file__).parent
EXPORT_DIR = APP_DIR / "exports"


st.set_page_config(
    page_title="BugTheatre AI",
    page_icon="BT",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
          --bt-bg: #07090d;
          --bt-panel: #11151b;
          --bt-panel-2: #151a21;
          --bt-line: rgba(244, 185, 66, 0.22);
          --bt-line-cool: rgba(255, 255, 255, 0.09);
          --bt-gold: #f4b942;
          --bt-gold-2: #ffd889;
          --bt-text: #f8efe1;
          --bt-muted: #a7a7a7;
          --bt-red: #ff604d;
          --bt-green: #63d485;
          --bt-blue: #6db5ff;
        }

        .stApp {
          background:
            radial-gradient(circle at 78% 8%, rgba(244, 185, 66, 0.13), transparent 25%),
            linear-gradient(135deg, #07090d 0%, #10141a 48%, #090b0f 100%);
          color: var(--bt-text);
        }

        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        #MainMenu,
        footer {
          visibility: hidden;
          height: 0;
        }

        .block-container {
          max-width: 1220px;
          padding-top: 1.4rem;
          padding-bottom: 3rem;
        }

        .stMarkdown p {
          font-size: 0.98rem;
          line-height: 1.55;
        }

        [data-testid="stSidebar"] {
          background:
            linear-gradient(180deg, rgba(6, 8, 11, 0.98) 0%, rgba(15, 19, 24, 0.98) 100%);
          border-right: 1px solid var(--bt-line-cool);
        }

        [data-testid="stSidebar"] .stButton button {
          width: 100%;
          border-radius: 8px;
          border: 1px solid rgba(255, 255, 255, 0.08);
          background: rgba(255, 255, 255, 0.025);
          color: var(--bt-text);
          text-align: left;
          justify-content: flex-start;
          min-height: 2.65rem;
          font-weight: 650;
        }

        [data-testid="stSidebar"] .stButton button:hover {
          border-color: var(--bt-line);
          background: rgba(244, 185, 66, 0.08);
          color: var(--bt-gold-2);
        }

        [data-testid="stSidebar"] .stButton button[kind="primary"] {
          background: linear-gradient(135deg, rgba(244,185,66,0.22), rgba(244,185,66,0.08)) !important;
          color: var(--bt-gold-2) !important;
          border: 1px solid rgba(244,185,66,0.48) !important;
          box-shadow: inset 3px 0 0 var(--bt-gold);
        }

        .brand-lockup {
          display: grid;
          grid-template-columns: 42px 1fr;
          gap: 0.75rem;
          align-items: center;
          margin: 0.65rem 0 0.55rem;
        }

        .logo-mark {
          width: 42px;
          height: 42px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #14100a;
          background: linear-gradient(135deg, #ffe19a, #f0a824);
          font-weight: 950;
          border: 1px solid rgba(244,185,66,0.55);
          box-shadow: 0 0 22px rgba(244,185,66,0.16);
        }

        .brand-title {
          font-size: 1.15rem;
          line-height: 1.1;
          font-weight: 900;
          color: var(--bt-text);
        }

        .brand-title span {
          color: var(--bt-gold);
        }

        .brand-subtitle {
          color: var(--bt-muted);
          font-size: 0.78rem;
          margin-top: 0.2rem;
        }

        .runtime-card {
          border: 1px solid var(--bt-line-cool);
          border-radius: 8px;
          padding: 0.85rem;
          background: rgba(255,255,255,0.025);
          margin-top: 0.75rem;
        }

        .sidebar-gap {
          height: 0.75rem;
        }

        h1, h2, h3 {
          letter-spacing: 0;
        }

        h1 {
          font-size: 2.35rem !important;
          line-height: 1.04 !important;
          margin: 0.1rem 0 0.25rem !important;
        }

        h1 a,
        h2 a,
        h3 a {
          display: none !important;
        }

        h2 {
          margin-top: 0.4rem !important;
        }

        .bt-brand span,
        .gold {
          color: var(--bt-gold);
        }

        .bt-hero {
          padding: 0.55rem 0 0.4rem;
        }

        .topbar {
          display: flex;
          justify-content: flex-end;
          align-items: center;
          gap: 1rem;
          margin-bottom: 1.1rem;
        }

        .top-actions {
          display: flex;
          align-items: center;
          gap: 0.7rem;
          color: var(--bt-muted);
        }

        .bt-subtitle {
          color: #d1c7b8;
          font-size: 0.98rem;
          margin-bottom: 1.2rem;
        }

        .bt-card {
          border: 1px solid var(--bt-line-cool);
          background: linear-gradient(180deg, rgba(25, 29, 36, 0.96), rgba(12, 15, 20, 0.96));
          border-radius: 8px;
          padding: 1.05rem;
          box-shadow: 0 18px 55px rgba(0,0,0,0.25);
        }

        .hero-panel {
          border: 1px solid rgba(244,185,66,0.28);
          background:
            linear-gradient(135deg, rgba(244,185,66,0.12), rgba(109,181,255,0.045) 42%, rgba(255,255,255,0.025)),
            linear-gradient(180deg, rgba(24, 29, 37, 0.96), rgba(10, 13, 18, 0.96));
          border-radius: 8px;
          padding: 1rem 1.1rem;
          margin: 0.5rem 0 1rem;
        }

        .hero-panel-title {
          font-size: 1.05rem;
          font-weight: 900;
          margin-bottom: 0.35rem;
          color: var(--bt-text);
        }

        .demo-path {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 0.6rem;
          margin: 0.95rem 0 1.1rem;
        }

        .demo-step {
          border: 1px solid var(--bt-line-cool);
          background: rgba(255,255,255,0.025);
          border-radius: 8px;
          padding: 0.75rem;
          min-height: 98px;
        }

        .demo-step-number {
          color: var(--bt-gold-2);
          font-size: 0.72rem;
          font-weight: 900;
          margin-bottom: 0.35rem;
        }

        .demo-step-title {
          font-weight: 850;
          margin-bottom: 0.25rem;
        }

        .demo-step-note {
          color: var(--bt-muted);
          font-size: 0.78rem;
          line-height: 1.35;
        }

        .bt-card.gold-border {
          border-color: var(--bt-line);
        }

        .metric-card {
          min-height: 104px;
        }

        .metric-label {
          color: var(--bt-muted);
          font-size: 0.78rem;
          margin-bottom: 0.5rem;
        }

        .metric-value {
          font-size: 1.18rem;
          font-weight: 750;
          line-height: 1.2;
        }

        .metric-note {
          color: var(--bt-muted);
          font-size: 0.82rem;
          margin-top: 0.45rem;
          line-height: 1.42;
        }

        .board-overview {
          display: grid;
          grid-template-columns: minmax(320px, 1.65fr) repeat(4, minmax(142px, 0.8fr));
          gap: 0.8rem;
          align-items: stretch;
        }

        .meta-strip {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 0.3rem;
          padding: 0.85rem 1rem;
          border: 1px solid var(--bt-line-cool);
          border-radius: 8px;
          background: rgba(17, 21, 27, 0.78);
          margin: 0.9rem 0 0.8rem;
        }

        .meta-item {
          border-right: 1px solid var(--bt-line-cool);
          padding-right: 0.75rem;
        }

        .meta-item:last-child {
          border-right: 0;
        }

        .meta-label {
          color: var(--bt-muted);
          font-size: 0.72rem;
          margin-bottom: 0.22rem;
        }

        .meta-value {
          font-size: 0.9rem;
          font-weight: 720;
        }

        .prime-card {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 1rem;
          align-items: start;
        }

        .prime-title {
          font-size: 1.35rem;
          line-height: 1.2;
          font-weight: 850;
          margin: 0.15rem 0 0.45rem;
        }

        .prime-note {
          color: var(--bt-muted);
          font-size: 0.92rem;
          line-height: 1.45;
          max-width: 58rem;
        }

        .score-ring {
          width: 76px;
          height: 76px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          border: 5px solid rgba(99,212,133,0.78);
          color: var(--bt-text);
          font-weight: 850;
          font-size: 1.1rem;
          background: radial-gradient(circle, rgba(99,212,133,0.12), transparent 62%);
          flex: 0 0 auto;
        }

        .compact-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 0.8rem;
        }

        .content-grid {
          display: grid;
          grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.75fr);
          gap: 0.9rem;
          align-items: start;
        }

        .snapshot-row {
          display: grid;
          grid-template-columns: 42px 1fr auto;
          gap: 0.75rem;
          align-items: center;
          padding: 0.72rem;
          border: 1px solid var(--bt-line-cool);
          border-radius: 8px;
          background: rgba(255,255,255,0.025);
          margin: 0.55rem 0;
        }

        .asset-icon {
          width: 42px;
          height: 42px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(244,185,66,0.08);
          border: 1px solid var(--bt-line-cool);
          color: var(--bt-gold-2);
          font-weight: 850;
        }

        .ok-dot {
          color: var(--bt-green);
          font-weight: 900;
        }

        .sample-tile {
          min-height: 330px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }

        .sample-summary {
          color: var(--bt-muted);
          font-size: 0.92rem;
          line-height: 1.48;
          margin: 0.7rem 0 1rem;
        }

        .sample-actions {
          margin-top: 1.1rem;
          padding-top: 0.9rem;
          border-top: 1px solid var(--bt-line-cool);
        }

        .sample-actions .stButton button {
          min-height: 2.75rem;
          border-color: var(--bt-line) !important;
          background: rgba(244,185,66,0.08) !important;
        }

        .postmortem-preview {
          display: grid;
          gap: 1rem;
        }

        .postmortem-title {
          font-size: 1.05rem;
          font-weight: 800;
          margin-bottom: 0.25rem;
        }

        .pm-section {
          padding: 0.85rem 0;
          border-top: 1px solid var(--bt-line-cool);
        }

        .pm-section:first-child {
          border-top: 0;
          padding-top: 0.25rem;
        }

        .pm-heading {
          font-size: 1.05rem;
          line-height: 1.2;
          font-weight: 850;
          margin-bottom: 0.45rem;
          color: var(--bt-text);
        }

        .pm-body {
          color: #d7d0c7;
          font-size: 0.92rem;
          line-height: 1.48;
        }

        .artifact-chips {
          display: flex;
          flex-wrap: wrap;
          gap: 0.55rem 0.65rem;
          padding-top: 0.15rem;
        }

        .artifact-chips .pill {
          margin: 0;
        }

        .export-actions {
          margin-top: 1rem;
          display: grid;
          gap: 0.75rem;
        }

        .dashboard-actions {
          margin-top: 1rem;
          display: grid;
          gap: 0.85rem;
        }

        .saved-case-picker {
          margin-top: 0.95rem;
          padding-top: 0.95rem;
          border-top: 1px solid rgba(255,255,255,0.08);
          display: grid;
          gap: 0.7rem;
        }

        .investigation-actions {
          margin-top: 1.15rem;
          padding-top: 0.2rem;
        }

        .patch-summary-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 0.9rem;
          align-items: stretch;
          margin: 1rem 0 1.35rem;
        }

        .quality-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 0.65rem;
          margin-top: 0.8rem;
        }

        .quality-item {
          border: 1px solid var(--bt-line-cool);
          border-radius: 8px;
          padding: 0.7rem;
          background: rgba(255,255,255,0.025);
        }

        .quality-title {
          font-size: 0.8rem;
          color: var(--bt-gold-2);
          font-weight: 850;
          margin-bottom: 0.25rem;
        }

        .quality-note {
          color: var(--bt-muted);
          font-size: 0.78rem;
          line-height: 1.38;
        }

        .patch-summary-card {
          min-height: 250px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }

        .patch-summary-body {
          font-size: 0.96rem;
          line-height: 1.48;
          color: #efe8dd;
          margin-top: 0.75rem;
        }

        .patch-grid {
          display: grid;
          grid-template-columns: minmax(0, 1.25fr) minmax(340px, 0.95fr);
          gap: 1rem;
          align-items: start;
        }

        .patch-column {
          display: grid;
          gap: 1rem;
        }

        @media (max-width: 1200px) {
          .board-overview {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
          .prime-card-shell {
            grid-column: 1 / -1;
          }
          .content-grid {
            grid-template-columns: 1fr;
          }
          .patch-summary-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
          .demo-path,
          .quality-grid {
            grid-template-columns: 1fr;
          }
          .patch-grid {
            grid-template-columns: 1fr;
          }
          .meta-strip {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
          .meta-item {
            border-right: 0;
          }
        }

        @media (max-width: 760px) {
          h1 {
            font-size: 2rem !important;
          }
          .board-overview,
          .compact-grid,
          .content-grid,
          .prime-card {
            grid-template-columns: 1fr;
          }
          .score-ring {
            width: 62px;
            height: 62px;
          }
          .topbar {
            grid-template-columns: 1fr;
          }
          .top-actions {
            justify-self: start;
          }
          .meta-strip {
            grid-template-columns: 1fr;
          }
          .patch-summary-grid {
            grid-template-columns: 1fr;
          }
          .demo-path,
          .quality-grid {
            grid-template-columns: 1fr;
          }
        }

        .pill {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          border: 1px solid var(--bt-line);
          color: var(--bt-gold-2);
          border-radius: 999px;
          padding: 0.18rem 0.55rem;
          font-size: 0.78rem;
          background: rgba(244, 185, 66, 0.08);
        }

        .pill.red { color: #ff9a8f; border-color: rgba(255,96,77,0.35); background: rgba(255,96,77,0.08); }
        .pill.green { color: #9df2b4; border-color: rgba(99,212,133,0.35); background: rgba(99,212,133,0.08); }
        .pill.blue { color: #b6dbff; border-color: rgba(109,181,255,0.35); background: rgba(109,181,255,0.08); }

        .section-kicker {
          color: var(--bt-gold);
          text-transform: uppercase;
          letter-spacing: 0.08em;
          font-size: 0.78rem;
          font-weight: 800;
          margin-bottom: 0.55rem;
        }

        .bt-table {
          width: 100%;
          border-collapse: collapse;
          overflow: hidden;
          border-radius: 8px;
          font-size: 0.92rem;
        }

        .bt-table th {
          color: var(--bt-gold-2);
          text-align: left;
          font-weight: 750;
          border-bottom: 1px solid var(--bt-line);
          padding: 0.75rem 0.65rem;
          background: rgba(244,185,66,0.05);
        }

        .bt-table td {
          border-bottom: 1px solid var(--bt-line-cool);
          padding: 0.75rem 0.65rem;
          vertical-align: top;
        }

        .timeline-item {
          display: grid;
          grid-template-columns: 34px 1fr;
          gap: 0.7rem;
          margin: 0.62rem 0;
        }

        .timeline-number {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          background: rgba(244,185,66,0.12);
          border: 1px solid var(--bt-line);
          color: var(--bt-gold-2);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 800;
        }

        .diff-box, .command-box {
          background: #080a0d;
          border: 1px solid var(--bt-line-cool);
          border-radius: 8px;
          padding: 0.9rem;
          overflow-x: auto;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          font-size: 0.9rem;
          white-space: pre-wrap;
        }

        .stTextArea textarea,
        .stTextInput input,
        .stSelectbox div[data-baseweb="select"] {
          border: 1px solid rgba(255, 255, 255, 0.16) !important;
          background-color: rgba(5, 8, 12, 0.94) !important;
          box-shadow: inset 0 0 0 1px rgba(255,255,255,0.035) !important;
          color: #f6efe4 !important;
          font-size: 0.94rem !important;
          font-weight: 520 !important;
        }

        .stTextArea textarea:focus,
        .stTextInput input:focus {
          border-color: rgba(244,185,66,0.58) !important;
          box-shadow: 0 0 0 2px rgba(244,185,66,0.12) !important;
        }

        [data-testid="stWidgetLabel"] label,
        [data-testid="stWidgetLabel"] p {
          color: #d6cbbb !important;
          font-size: 0.78rem !important;
          font-weight: 850 !important;
          letter-spacing: 0.02em !important;
          margin-bottom: 0.35rem !important;
        }

        .stButton > button[kind="primary"] {
          background: linear-gradient(135deg, #ffe19a, #f0a824) !important;
          color: #14100a !important;
          border: 0 !important;
          font-weight: 850 !important;
          border-radius: 8px !important;
          min-height: 3rem;
        }

        .stDownloadButton button {
          border-radius: 8px !important;
          border: 1px solid var(--bt-line) !important;
          background: rgba(244,185,66,0.08) !important;
          color: var(--bt-text) !important;
        }

        .small-muted {
          color: var(--bt-muted);
          font-size: 0.88rem;
        }

        .intake-intro {
          margin-bottom: 1.15rem;
        }

        .intake-page {
          max-width: 980px;
        }

        .intake-panel {
          border: 1px solid var(--bt-line-cool);
          background: linear-gradient(180deg, rgba(21, 26, 33, 0.88), rgba(10, 13, 18, 0.88));
          border-radius: 8px;
          padding: 1.05rem 1.15rem;
          margin: 1rem 0;
        }

        .intake-heading {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          align-items: end;
          margin-bottom: 0.9rem;
        }

        .intake-heading-title {
          font-size: 1.05rem;
          font-weight: 850;
          color: var(--bt-text);
        }

        .intake-heading-note {
          color: var(--bt-muted);
          font-size: 0.82rem;
        }

        .processing-banner {
          position: fixed;
          top: 1rem;
          left: 50%;
          transform: translateX(-50%);
          z-index: 9999;
          width: min(620px, calc(100vw - 2rem));
          border: 1px solid rgba(244,185,66,0.52);
          border-radius: 8px;
          background: linear-gradient(135deg, rgba(38, 29, 12, 0.98), rgba(16, 18, 22, 0.98));
          box-shadow: 0 18px 70px rgba(0,0,0,0.45);
          padding: 0.95rem 1.1rem;
        }

        .processing-title {
          font-weight: 900;
          color: var(--bt-gold-2);
          margin-bottom: 0.25rem;
        }

        .processing-note {
          color: #e7dccb;
          font-size: 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def html_card(content: str, class_name: str = "") -> None:
    st.markdown(f'<div class="bt-card {class_name}">{content}</div>', unsafe_allow_html=True)


def e(value: Any) -> str:
    return escape(str(value or ""))


def severity_class(value: str) -> str:
    return "red" if value in {"high", "critical"} else "gold"


def technical_artifacts(case: dict[str, Any]) -> list[str]:
    text = json.dumps(case, default=str)
    candidates = [
        "419 Page Expired",
        "TokenMismatchException",
        "VerifyCsrfToken.php",
        "SESSION_DRIVER",
        "Redis",
        "admin inactivity",
        "new Date()",
        "Date.now()",
        "Math.random()",
        "hydration",
        "Pydantic v2",
        "FastAPI 0.95.0",
        "pydantic.fields.Undefined",
        "EXPOSE 8080",
        "8080:3000",
        "Docker Compose",
    ]
    found = []
    lower_text = text.lower()
    for item in candidates:
        if item.lower() in lower_text and item not in found:
            found.append(item)
    if found:
        return found[:6]
    fallback = case.get("prime_suspect", {}).get("evidence", [])[:3]
    return [str(item) for item in fallback] or ["Evidence artifacts are captured in the investigation board."]


def load_sample_case(name: str) -> None:
    st.session_state.loaded_sample = name
    st.session_state.case_result = get_demo_case(name)
    st.session_state.current_case_id = f"Sample: {name}"
    st.session_state.form_defaults = sample_text(name)
    st.session_state.case_form_version = st.session_state.get("case_form_version", 0) + 1
    st.session_state.page = "Investigation Board"


def open_saved_case(record: dict[str, Any]) -> None:
    st.session_state.case_result = record.get("result") or get_demo_case("React hydration mismatch")
    st.session_state.current_case_id = record.get("id")
    payload = record.get("payload")
    if isinstance(payload, dict):
        st.session_state.form_defaults = {**blank_case_form(), **payload}
        st.session_state.case_form_version = st.session_state.get("case_form_version", 0) + 1
    st.session_state.page = "Investigation Board"


def reset_new_case_form() -> None:
    st.session_state.form_defaults = blank_case_form()
    st.session_state.case_form_version = st.session_state.get("case_form_version", 0) + 1


def render_sidebar() -> str:
    st.sidebar.markdown(
        """
        <div class="brand-lockup">
          <div class="logo-mark">BT</div>
          <div>
            <div class="brand-title">BugTheatre <span>AI</span></div>
            <div class="brand-subtitle">Visual debugging case files</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.divider()

    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"

    nav_items = [
        ("Dashboard", "Dashboard"),
        ("New Case", "Open Case"),
        ("Sample Cases", "Sample Cases"),
        ("Investigations", "Investigation Board"),
        ("Patch Room", "Patch Room"),
        ("Postmortem", "Postmortem"),
    ]
    for label, target in nav_items:
        active = (
            (label == "Dashboard" and st.session_state.page == "Dashboard")
            or
            (label == "New Case" and st.session_state.page == "Open Case")
            or (label == "Sample Cases" and st.session_state.page == "Sample Cases")
            or (label == "Investigations" and st.session_state.page == "Investigation Board")
            or (label == "Patch Room" and st.session_state.page == "Patch Room")
            or (label == "Postmortem" and st.session_state.page == "Postmortem")
        )
        if st.sidebar.button(label, key=f"nav_{label}", type="primary" if active else "secondary", use_container_width=True):
            if target == "Open Case":
                reset_new_case_form()
            st.session_state.page = target
            st.rerun()

    st.sidebar.divider()
    st.session_state.use_gemma = gemma_enabled()
    runtime_label = "Local Gemma connected" if gemma_enabled() else "Demo mode active"
    runtime_note = "Ollama/Gemma is generating investigations locally." if gemma_enabled() else "Uses curated sample analyses until Ollama has the configured Gemma model."
    st.sidebar.markdown(
        f"""
        <div class="runtime-card">
          <div class="section-kicker">Runtime</div>
          <strong>{e(runtime_label)}</strong>
          <p class="small-muted">{e(runtime_note)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown('<div class="sidebar-gap"></div>', unsafe_allow_html=True)

    with st.sidebar.expander("Tech stack", expanded=False):
        st.markdown(
            """
            **AI runtime:** Local Gemma via Ollama  
            **Model:** `gemma4:e2b`  
            **App:** Streamlit + Python  
            **Screenshots:** base64 image input to Ollama  
            **Prompting:** strict JSON investigation schema  
            **Privacy:** local-first flow + secret redaction  
            **Exports:** Markdown + JSON  
            **Demo data:** curated React, FastAPI, Docker cases
            """
        )

    st.sidebar.markdown(
        """
        <div class="bt-card gold-border" style="margin-top: 1rem;">
          <div class="section-kicker">Pro tip</div>
          Provide logs, code, environment details, and expected vs actual behavior for sharper suspects.
        </div>
        """,
        unsafe_allow_html=True,
    )
    return st.session_state.page


def render_topbar() -> None:
    runtime_label = "Local Gemma" if gemma_enabled() else "Demo mode"
    model_label = os.getenv("OLLAMA_MODEL", "gemma4:e2b") if gemma_enabled() else "curated samples"
    st.markdown(
        f"""
        <div class="topbar">
          <div class="top-actions">
            <span class="pill green">{e(runtime_label)}</span>
            <span class="small-muted">Model: {e(model_label)}</span>
            <span class="small-muted">Use Sample Cases for instant demos</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sample_text(name: str) -> dict[str, str]:
    sample_paths = {
        "React hydration mismatch": APP_DIR / "sample_cases" / "react_hydration_bug.md",
        "FastAPI dependency mismatch": APP_DIR / "sample_cases" / "fastapi_pydantic_bug.md",
        "Docker port mismatch": APP_DIR / "sample_cases" / "docker_env_bug.md",
    }
    raw = sample_paths[name].read_text(encoding="utf-8")
    return {
        "title": name,
        "description": raw,
        "actual": "",
        "expected": "",
        "logs": raw,
        "code": raw,
        "environment": "",
    }


def blank_case_form() -> dict[str, str]:
    return {
        "title": "",
        "description": "",
        "actual": "",
        "expected": "",
        "logs": "",
        "code": "",
        "environment": "",
    }


def collect_payload() -> dict[str, Any]:
    defaults = st.session_state.get("form_defaults", blank_case_form())
    version = st.session_state.get("case_form_version", 0)

    st.markdown(
        """
        <div class="intake-panel">
          <div class="intake-heading">
            <div>
              <div class="section-kicker">Step 1</div>
              <div class="intake-heading-title">Case basics</div>
            </div>
            <div class="intake-heading-note">Only the title is required.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([1, 1])
    with c1:
        title = st.text_input("Case title", value=defaults.get("title", ""), placeholder="Example: Checkout button fails on mobile", key=f"case_title_{version}")
        framework = st.selectbox("Language / framework", ["React / Next.js", "Python / FastAPI", "Node.js / Docker", "Other"], key=f"framework_{version}")
    with c2:
        environment = st.text_input("Environment", value=defaults.get("environment", ""), placeholder="Production, staging, local Docker, browser, OS...", key=f"environment_{version}")
        description = st.text_area("Short description", value=defaults.get("description", ""), height=92, placeholder="What is broken? When does it happen?", key=f"description_{version}")

    st.markdown(
        """
        <div class="intake-panel">
          <div class="intake-heading">
            <div>
              <div class="section-kicker">Step 2</div>
              <div class="intake-heading-title">Expected vs actual</div>
            </div>
            <div class="intake-heading-note">This helps separate symptom from intent.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    b1, b2 = st.columns(2)
    with b1:
        expected = st.text_area("Expected behavior", value=defaults.get("expected", ""), height=118, placeholder="What should have happened?", key=f"expected_{version}")
    with b2:
        actual = st.text_area("Actual behavior", value=defaults.get("actual", ""), height=118, placeholder="What happened instead?", key=f"actual_{version}")

    st.markdown(
        """
        <div class="intake-panel">
          <div class="intake-heading">
            <div>
              <div class="section-kicker">Step 3</div>
              <div class="intake-heading-title">Evidence</div>
            </div>
            <div class="intake-heading-note">Logs, code, config, and screenshots improve confidence.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    logs = st.text_area("Stack trace / logs", value=defaults.get("logs", ""), height=150, placeholder="Paste the stack trace, terminal logs, browser console output, or deployment error...", key=f"logs_{version}")
    code = st.text_area("Code or config snippet", value=defaults.get("code", ""), height=150, placeholder="Paste the smallest relevant snippet: component, route, config, package file, Dockerfile...", key=f"code_{version}")
    screenshot = st.file_uploader("Screenshot evidence", type=["png", "jpg", "jpeg", "webp"], key=f"screenshot_{version}")
    screenshot_base64 = None
    screenshot_size = None
    if screenshot:
        screenshot_bytes = screenshot.getvalue()
        screenshot_size = len(screenshot_bytes)
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

    combined = "\n\n".join([description, expected, actual, logs, code, environment])
    redaction = redact_secrets(combined)

    if redaction.findings:
        st.warning(f"Redacted possible secrets before analysis: {', '.join(redaction.findings)}")
    elif screenshot and not combined.strip():
        st.info("Screenshot-only mode active: the uploaded image will be sent to local Gemma for visual debugging analysis.")
    elif screenshot:
        st.info("Screenshot included: local Gemma will analyze the image together with your text evidence.")
    else:
        st.info("Privacy guard active: common secret patterns are scanned before analysis.")

    return {
        "title": title,
        "framework": framework,
        "expected_behavior": expected,
        "actual_behavior": actual,
        "description": description,
        "logs": logs,
        "code": code,
        "environment": environment,
        "redacted_evidence": redaction.text,
        "screenshot_name": screenshot.name if screenshot else None,
        "screenshot_size_bytes": screenshot_size,
        "screenshot_base64": screenshot_base64,
    }


def investigate(payload: dict[str, Any]) -> dict[str, Any]:
    if st.session_state.get("use_gemma") and gemma_enabled():
        try:
            return investigate_with_gemma(payload)
        except Exception as exc:
            st.error(f"Gemma call failed, falling back to demo analysis: {exc}")

    title = payload.get("title", "").lower()
    evidence = payload.get("redacted_evidence", "").lower()
    if payload.get("screenshot_base64") and not (title.strip() or evidence.strip()):
        st.error("Screenshot-only analysis needs Local Gemma connected. The curated demo fallback cannot inspect image content.")
        return get_demo_case("React hydration mismatch")
    if "react" in title or "hydration" in evidence or "next.js" in evidence:
        return get_demo_case("React hydration mismatch")
    if "fastapi" in title or "fastapi" in evidence or "pydantic" in evidence:
        return get_demo_case("FastAPI dependency mismatch")
    if "docker" in title or "docker" in evidence or "compose" in evidence or " port " in f" {evidence} ":
        return get_demo_case("Docker port mismatch")
    return get_demo_case("React hydration mismatch")


def render_open_case() -> None:
    st.markdown(
        """
        <div class="bt-hero">
          <h1>Turn messy bugs into <span class="gold">clear investigations</span></h1>
          <div class="bt-subtitle">Paste logs, snippets, config, and screenshots. BugTheatre builds a case file instead of a generic answer.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="intake-page">', unsafe_allow_html=True)
    html_card(
        '<div class="intake-intro"><div class="section-kicker">New investigation</div><p class="small-muted">Enter your own evidence here. For prepared demos, use the Sample Cases page.</p></div>',
        "gold-border",
    )
    with st.form("new_case_form", clear_on_submit=False, border=False):
        payload = collect_payload()
        submitted = st.form_submit_button("Investigate Bug", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    if submitted:
        st.markdown(
            """
            <div class="processing-banner">
              <div class="processing-title">Investigating bug case...</div>
              <div class="processing-note">Local Gemma is analyzing the evidence. This can take a moment, especially with screenshots.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.spinner("Analyzing evidence with local Gemma..."):
            result = investigate(payload)
            st.session_state.case_result = result
            saved = save_case(payload, result)
            st.session_state.current_case_id = saved["id"]
        st.session_state.page = "Investigation Board"
        st.rerun()


def render_dashboard() -> None:
    current = st.session_state.get("case_result") or get_demo_case("React hydration mismatch")
    saved_cases = load_cases()
    st.markdown("<h1>Dashboard</h1>", unsafe_allow_html=True)
    st.markdown(
        '<div class="bt-subtitle">A quick command center for recent bug cases, demo readiness, and next actions.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="hero-panel">
          <div class="section-kicker">Demo Story</div>
          <div class="hero-panel-title">From messy evidence to a decision-ready debugging case file</div>
          <div class="small-muted">Use this flow for judges or executives: show one real symptom, let local Gemma build the case, then walk through evidence, safe patch, and postmortem output.</div>
          <div class="demo-path">
            <div class="demo-step"><div class="demo-step-number">01</div><div class="demo-step-title">Drop Evidence</div><div class="demo-step-note">Screenshot, logs, code, config, or partial context.</div></div>
            <div class="demo-step"><div class="demo-step-number">02</div><div class="demo-step-title">Local Gemma</div><div class="demo-step-note">Private investigation generated through Ollama.</div></div>
            <div class="demo-step"><div class="demo-step-number">03</div><div class="demo-step-title">Case Board</div><div class="demo-step-note">Prime suspect, evidence, risk, and missing inputs.</div></div>
            <div class="demo-step"><div class="demo-step-number">04</div><div class="demo-step-title">Safe Patch</div><div class="demo-step-note">Fix plan, validation, rollback, and false-lead avoidance.</div></div>
            <div class="demo-step"><div class="demo-step-number">05</div><div class="demo-step-title">Export</div><div class="demo-step-note">Postmortem-ready Markdown and tooling JSON.</div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="board-overview">
          <div class="bt-card gold-border prime-card-shell">
            <div class="section-kicker">Active Investigation</div>
            <div class="prime-title">{e(current.get('case_title', 'No active case'))}</div>
            <div class="prime-note">Current case is ready for board review, patch planning, and postmortem export.</div>
          </div>
          <div class="bt-card metric-card"><div class="metric-label">Saved Cases</div><div class="metric-value">{len(saved_cases)}</div><div class="metric-note">Locally stored investigations</div></div>
          <div class="bt-card metric-card"><div class="metric-label">Exports</div><div class="metric-value">MD + JSON</div><div class="metric-note">Postmortem ready</div></div>
          <div class="bt-card metric-card"><div class="metric-label">Privacy</div><div class="metric-value">Redaction</div><div class="metric-note">Secret scan enabled</div></div>
          <div class="bt-card metric-card"><div class="metric-label">Mode</div><div class="metric-value">{'Local AI' if gemma_enabled() else 'Demo'}</div><div class="metric-note">Works without cloud API key</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    left, right = st.columns([1.25, 0.9])
    with left:
        if saved_cases:
            recent = saved_cases[:6]
            rows = "".join(
                f'<tr>'
                f'<td><strong>{e(item.get("title"))}</strong><br><span class="small-muted">{e(item.get("created_at"))}</span></td>'
                f'<td><span class="pill {severity_class(item.get("result", {}).get("severity", ""))}">{e(item.get("result", {}).get("severity", "").title())}</span></td>'
                f'<td><span class="pill green">{e(item.get("result", {}).get("confidence_score", ""))}%</span></td>'
                f'<td>{e(item.get("result", {}).get("prime_suspect", {}).get("name"))}</td>'
                f'</tr>'
                for item in recent
            )
            table_note = "Recent Cases"
        else:
            rows = "".join(
                f'<tr>'
                f'<td><strong>{e(name)}</strong><br><span class="small-muted">Sample case</span></td>'
                f'<td><span class="pill {severity_class(get_demo_case(name).get("severity", ""))}">{e(get_demo_case(name).get("severity", "").title())}</span></td>'
                f'<td><span class="pill green">{e(get_demo_case(name).get("confidence_score"))}%</span></td>'
                f'<td>{e(get_demo_case(name).get("prime_suspect", {}).get("name"))}</td>'
                f'</tr>'
                for name in demo_names()
            )
            table_note = "Sample Cases"
        st.markdown(
            f"""
            <div class="bt-card">
              <div class="section-kicker">{table_note}</div>
              <table class="bt-table">
                <thead><tr><th>Case</th><th>Severity</th><th>Confidence</th><th>Prime Suspect</th></tr></thead>
                <tbody>{rows}</tbody>
              </table>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if saved_cases:
            st.markdown('<div class="saved-case-picker">', unsafe_allow_html=True)
            saved_case_labels = [
                f"{item.get('title', 'Untitled case')} · {item.get('created_at', '')}" for item in recent
            ]
            selected_label = st.selectbox(
                "Open saved case",
                saved_case_labels,
                label_visibility="collapsed",
                key="dashboard_saved_case_picker",
            )
            selected_index = saved_case_labels.index(selected_label)
            if st.button("Open selected saved case", use_container_width=True):
                open_saved_case(recent[selected_index])
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    with right:
        html_card(
            f"""
            <div class="section-kicker">Next Best Action</div>
            <div class="prime-title">Open the investigation board</div>
            <p class="small-muted">Review the current case: <strong>{e(current.get('case_title'))}</strong></p>
            """,
            "gold-border",
        )
        st.markdown('<div class="dashboard-actions">', unsafe_allow_html=True)
        if st.button("Open Investigation Board", use_container_width=True):
            st.session_state.page = "Investigation Board"
            st.rerun()
        if st.button("Create New Case", use_container_width=True):
            reset_new_case_form()
            st.session_state.page = "Open Case"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def render_sample_cases() -> None:
    st.markdown("<h1>Sample Cases</h1>", unsafe_allow_html=True)
    st.markdown(
        '<div class="bt-subtitle">Prebuilt debugging scenarios for instant demos, judging, and regression testing.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="meta-strip">
          <div class="meta-item"><div class="meta-label">Purpose</div><div class="meta-value">One-click demos</div></div>
          <div class="meta-item"><div class="meta-label">Coverage</div><div class="meta-value">Frontend, backend, deployment</div></div>
          <div class="meta-item"><div class="meta-label">Output</div><div class="meta-value">Full case file</div></div>
          <div class="meta-item"><div class="meta-label">Best For</div><div class="meta-value">Challenge walkthrough</div></div>
          <div class="meta-item"><div class="meta-label">Mode</div><div class="meta-value">Offline-ready</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(3)
    for col, name in zip(cols, demo_names()):
        case = get_demo_case(name)
        with col:
            html_card(
                f"""
                <div class="sample-tile">
                  <div>
                    <div class="section-kicker">{e(case.get('affected_layer', '').title())} Case</div>
                    <div class="prime-title">{e(name)}</div>
                    <div class="sample-summary">{e(case.get('summary', ''))[:235]}...</div>
                    <div style="display:flex; gap:0.45rem; flex-wrap:wrap;">
                      <span class="pill {severity_class(case.get('severity', ''))}">{e(case.get('severity', '').title())}</span>
                      <span class="pill green">{e(case.get('confidence_score'))}% confidence</span>
                    </div>
                  </div>
                </div>
                """,
                "gold-border" if name == st.session_state.get("loaded_sample", "React hydration mismatch") else "",
            )
            st.markdown('<div class="sample-actions">', unsafe_allow_html=True)
            if st.button(f"Load {name}", key=f"load_card_{name}", use_container_width=True):
                st.session_state.loaded_sample = name
                st.session_state.case_result = get_demo_case(name)
                st.session_state.form_defaults = sample_text(name)
                st.session_state.page = "Investigation Board"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    html_card(
        """
        <div class="section-kicker">Why This Page Exists</div>
        <p>New Case is for the user's own bug evidence. Sample Cases is the demo gallery: it lets judges or teammates try the product instantly without inventing a bug report first.</p>
        """,
        "gold-border",
    )


def render_metric_cards(case: dict[str, Any]) -> None:
    prime = case.get("prime_suspect", {})
    fix = case.get("fix_plan", {})
    severity = e(case.get("severity", "unknown").title())
    layer = e(case.get("affected_layer", "unknown").title())
    confidence = e(case.get("confidence", "").title())
    score = e(case.get("confidence_score", 0))

    st.markdown(
        f"""
        <div class="board-overview">
          <div class="bt-card gold-border prime-card-shell">
            <div class="prime-card">
              <div>
                <div class="section-kicker">Prime Suspect</div>
                <div class="prime-title">{e(prime.get("name", "Unknown"))}</div>
                <div class="prime-note">{e(prime.get("why_likely", ""))}</div>
              </div>
              <div class="score-ring">{score}%</div>
            </div>
          </div>
          <div class="bt-card metric-card">
            <div class="metric-label">Confidence</div>
            <div class="metric-value">{confidence}</div>
            <div class="metric-note">{score}% evidence fit</div>
          </div>
          <div class="bt-card metric-card">
            <div class="metric-label">Severity</div>
            <div class="metric-value">{severity}</div>
            <div class="metric-note">User impact likely</div>
          </div>
          <div class="bt-card metric-card">
            <div class="metric-label">Affected Layer</div>
            <div class="metric-value">{layer}</div>
            <div class="metric-note">Start here first</div>
          </div>
          <div class="bt-card metric-card">
            <div class="metric-label">Fastest Fix</div>
            <div class="metric-value">~15-35 min</div>
            <div class="metric-note">{e(fix.get("quick_patch", ""))[:92]}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_investigation(case: dict[str, Any] | None = None) -> None:
    case = case or st.session_state.get("case_result") or get_demo_case("React hydration mismatch")
    case_id = st.session_state.get("current_case_id", "Demo case")
    st.markdown("<h1>Investigation Board</h1>", unsafe_allow_html=True)
    st.markdown('<div class="bt-subtitle">Most probable root cause, evidence, missing inputs, and risk in one place.</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="meta-strip">
          <div class="meta-item"><div class="meta-label">Case ID</div><div class="meta-value">{e(case_id)}</div></div>
          <div class="meta-item"><div class="meta-label">Severity</div><div class="meta-value"><span class="pill {severity_class(case.get('severity', ''))}">{e(case.get('severity', '').title())}</span></div></div>
          <div class="meta-item"><div class="meta-label">Confidence</div><div class="meta-value"><span class="pill green">{e(case.get('confidence_score'))}%</span></div></div>
          <div class="meta-item"><div class="meta-label">Affected Layer</div><div class="meta-value">{e(case.get('affected_layer', '').title())}</div></div>
          <div class="meta-item"><div class="meta-label">Status</div><div class="meta-value">Investigation ready</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_metric_cards(case)
    st.write("")

    evidence = case.get("prime_suspect", {}).get("evidence", [])
    missing = case.get("missing_evidence", [])
    st.markdown(
        f"""
        <div class="content-grid">
          <div>
            <div class="bt-card gold-border">
              <div class="section-kicker">Executive Debug Summary</div>
              <p>{e(case.get('summary', ''))}</p>
            </div>
            <div style="height: 0.9rem;"></div>
            <div class="compact-grid">
              <div class="bt-card">
                <div class="section-kicker">Evidence Found</div>
                {''.join(f"<p>- {e(item)}</p>" for item in evidence)}
              </div>
              <div class="bt-card">
                <div class="section-kicker">Missing Evidence</div>
                {''.join(f"<p>- {e(item)}</p>" for item in missing)}
              </div>
            </div>
          </div>
          <div class="bt-card gold-border">
            <div class="section-kicker">Case Snapshot</div>
            <p><strong>{e(case.get('case_title'))}</strong></p>
            <div class="snapshot-row"><div class="asset-icon">LOG</div><div><strong>Logs</strong><br><span class="small-muted">Evidence parsed from stack trace</span></div><div class="ok-dot">✓</div></div>
            <div class="snapshot-row"><div class="asset-icon">SRC</div><div><strong>Code Snippet</strong><br><span class="small-muted">Relevant source/config included</span></div><div class="ok-dot">✓</div></div>
            <div class="snapshot-row"><div class="asset-icon">ENV</div><div><strong>Framework</strong><br><span class="small-muted">{e(case.get('affected_layer', '').title())} context detected</span></div><div class="ok-dot">✓</div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="investigation-actions">', unsafe_allow_html=True)
    if st.button("Save exports", use_container_width=True):
        paths = save_exports(case, EXPORT_DIR)
        st.success("Exports saved.")
        for label, path in paths.items():
            st.caption(f"{label}: {path}")
    st.markdown("</div>", unsafe_allow_html=True)


def render_suspect_board() -> None:
    case = st.session_state.get("case_result") or get_demo_case("React hydration mismatch")
    st.markdown("<h1>Suspect Board</h1>", unsafe_allow_html=True)
    st.markdown('<div class="bt-subtitle">Ranked hypotheses with evidence for, evidence against, and confirmation steps.</div>', unsafe_allow_html=True)

    prime = case.get("prime_suspect", {})
    html_card(
        f"""
        <div class="section-kicker">Selected Case</div>
        <div style="display:grid; grid-template-columns: 1.5fr 1fr 0.6fr; gap: 1rem; align-items:center;">
          <div><div class="metric-value">{e(case.get('case_title'))}</div><div class="metric-note">Prime suspect: {e(prime.get('name'))}</div></div>
          <div><span class="pill green">{e(case.get('confidence', '').title())} confidence</span></div>
          <div class="metric-value">{e(case.get('confidence_score'))}%</div>
        </div>
        """,
        "gold-border",
    )
    st.write("")

    rows = []
    for suspect in case.get("suspects", []):
        rows.append(
            f"""
            <tr>
              <td><strong>{e(suspect.get('name'))}</strong><br><span class="small-muted">{e(suspect.get('status', '').replace('_', ' ').title())}</span></td>
              <td><span class="pill">{e(suspect.get('probability_score'))}%</span><br>{e(suspect.get('probability', '').title())}</td>
              <td>{'<br>'.join('- ' + e(item) for item in suspect.get('evidence_for', []))}</td>
              <td>{'<br>'.join('- ' + e(item) for item in suspect.get('evidence_against', []))}</td>
              <td>{e(suspect.get('how_to_confirm'))}</td>
            </tr>
            """
        )

    st.markdown(
        f"""
        <table class="bt-table">
          <thead>
            <tr><th>Suspect</th><th>Probability</th><th>Evidence For</th><th>Evidence Against</th><th>How to Confirm</th></tr>
          </thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    left, right = st.columns(2)
    with left:
        html_card(
            "<div class='section-kicker'>Don't Waste Time Here</div>"
            + "".join(
                f"<p><strong>{e(lead.get('lead'))}</strong><br><span class='small-muted'>{e(lead.get('why_to_avoid'))}</span></p>"
                for lead in case.get("false_leads", [])
            )
        )
    with right:
        timeline_html = "<div class='section-kicker'>Failure Timeline</div>"
        for i, step in enumerate(case.get("failure_timeline", []), start=1):
            timeline_html += f"<div class='timeline-item'><div class='timeline-number'>{i}</div><div>{e(step)}</div></div>"
        html_card(timeline_html)


def render_patch_room() -> None:
    case = st.session_state.get("case_result") or get_demo_case("React hydration mismatch")
    fix = case.get("fix_plan", {})
    artifacts = technical_artifacts(case)
    st.markdown("<h1>Patch Room</h1>", unsafe_allow_html=True)
    st.markdown('<div class="bt-subtitle">Turn diagnosis into a careful fix plan, suggested diff, commands, and rollback path.</div>', unsafe_allow_html=True)

    items = [
        ("Quick Patch", fix.get("quick_patch", ""), "Recommended"),
        ("Clean Fix", fix.get("clean_fix", ""), "Low risk"),
        ("Prevention", fix.get("prevention", ""), "Best practice"),
        ("Validation", "Run tests and reproduce the fixed path.", "Quality first"),
    ]
    summary_cards = "".join(
        f'<div class="bt-card patch-summary-card">'
        f'<div><div class="section-kicker">{e(title)}</div>'
        f'<div class="patch-summary-body">{e(body)}</div></div>'
        f'<div><span class="pill">{e(tag)}</span></div>'
        f'</div>'
        for title, body, tag in items
    )
    st.markdown(f'<div class="patch-summary-grid">{summary_cards}</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="bt-card gold-border">
          <div class="section-kicker">Safe Patch Review</div>
          <div class="hero-panel-title">Before changing production behavior, validate the evidence path.</div>
          <div class="quality-grid">
            <div class="quality-item"><div class="quality-title">Risk Check</div><div class="quality-note">Avoid patches that can make timeout, auth, session, dependency, or deployment failures worse.</div></div>
            <div class="quality-item"><div class="quality-title">Concrete Evidence</div><div class="quality-note">{e(', '.join(artifacts))}</div></div>
            <div class="quality-item"><div class="quality-title">Proof Path</div><div class="quality-note">Reproduce first, apply the smallest safe change, then confirm with the listed validation steps.</div></div>
          </div>
        </div>
        <div style="height: 1rem;"></div>
        """,
        unsafe_allow_html=True,
    )

    commands = "\n".join(case.get("commands_to_run", []))
    action_plan = "".join(
        f"<div class='timeline-item'><div class='timeline-number'>{i}</div><div>{e(step)}</div></div>"
        for i, step in enumerate(fix.get("validation_steps", []), start=1)
    )
    st.markdown(
        f"""
        <div class="patch-grid">
          <div class="patch-column">
            <div>
              <h3>Suggested Patch</h3>
              <div class="diff-box">{e(case.get('suggested_patch', ''))}</div>
            </div>
            <div>
              <h3>Commands to Run</h3>
              <div class="command-box">{e(commands)}</div>
            </div>
          </div>
          <div class="patch-column">
            <div class="bt-card gold-border">
              <div class="section-kicker">Action Plan</div>
              {action_plan}
            </div>
            <div class="bt-card">
              <div class="section-kicker">Rollback Plan</div>
              <p>{e(fix.get('rollback', 'Revert the patch if the validation path fails.'))}</p>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_postmortem() -> None:
    case = st.session_state.get("case_result") or get_demo_case("React hydration mismatch")
    pm = case.get("postmortem", {})
    artifacts = technical_artifacts(case)
    st.markdown("<h1>Postmortem</h1>", unsafe_allow_html=True)
    st.markdown('<div class="bt-subtitle">Export a workplace-ready summary your team can use after the fix.</div>', unsafe_allow_html=True)

    md = postmortem_markdown(case)
    full_md = case_markdown(case)
    left, right = st.columns([1.6, 0.9])

    with left:
        st.markdown("### Report Preview")
        actions = pm.get("follow_up_actions", [])
        actions_html = "".join(f"<div class='pm-body'>- {e(item)}</div>" for item in actions)
        st.markdown(
            f"""
            <div class="bt-card gold-border postmortem-preview">
              <div class="postmortem-title">Postmortem: {e(case.get('case_title', 'Bug Case'))}</div>
              <div class="pm-section"><div class="pm-heading">Technical Artifacts</div><div class="pm-body artifact-chips">{''.join(f"<span class='pill'>{e(item)}</span>" for item in artifacts)}</div></div>
              <div class="pm-section"><div class="pm-heading">Summary</div><div class="pm-body">{e(pm.get('summary'))}</div></div>
              <div class="pm-section"><div class="pm-heading">Impact</div><div class="pm-body">{e(pm.get('impact'))}</div></div>
              <div class="pm-section"><div class="pm-heading">Root Cause</div><div class="pm-body">{e(pm.get('root_cause'))}</div></div>
              <div class="pm-section"><div class="pm-heading">Detection</div><div class="pm-body">{e(pm.get('detection'))}</div></div>
              <div class="pm-section"><div class="pm-heading">Resolution</div><div class="pm-body">{e(pm.get('resolution'))}</div></div>
              <div class="pm-section"><div class="pm-heading">Prevention</div><div class="pm-body">{e(pm.get('prevention'))}</div></div>
              <div class="pm-section"><div class="pm-heading">Follow-up Actions</div>{actions_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        html_card(
            """
            <div class="section-kicker">Export Options</div>
            <p>Markdown for docs, JSON for tooling, and a postmortem file for incident review.</p>
            """,
            "gold-border",
        )
        st.markdown('<div class="export-actions">', unsafe_allow_html=True)
        st.download_button("Download Case Markdown", full_md, file_name="bugtheatre-case.md", mime="text/markdown", use_container_width=True)
        st.download_button("Download Postmortem", md, file_name="bugtheatre-postmortem.md", mime="text/markdown", use_container_width=True)
        st.download_button("Download JSON", json.dumps(case, indent=2), file_name="bugtheatre-case.json", mime="application/json", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    inject_css()
    if "case_result" not in st.session_state:
        latest = latest_case()
        st.session_state.case_result = latest["result"] if latest else get_demo_case("React hydration mismatch")
        if latest:
            st.session_state.current_case_id = latest["id"]
    if "form_defaults" not in st.session_state:
        st.session_state.form_defaults = blank_case_form()
    if "case_form_version" not in st.session_state:
        st.session_state.case_form_version = 0

    page_param = st.query_params.get("page")
    valid_pages = {"Dashboard", "Open Case", "Sample Cases", "Investigation Board", "Patch Room", "Postmortem"}
    if page_param in valid_pages:
        st.session_state.page = page_param

    page = render_sidebar()
    render_topbar()
    if page == "Dashboard":
        render_dashboard()
    elif page == "Open Case":
        render_open_case()
    elif page == "Sample Cases":
        render_sample_cases()
    elif page == "Investigation Board":
        render_investigation()
    elif page == "Suspect Board":
        render_suspect_board()
    elif page == "Patch Room":
        render_patch_room()
    else:
        render_postmortem()


if __name__ == "__main__":
    main()
