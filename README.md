# BugTheatre AI

BugTheatre AI turns messy debugging evidence into a structured investigation board.

Repository: [github.com/AkshatUniyal/bugtheatre-ai](https://github.com/AkshatUniyal/bugtheatre-ai)

Instead of acting like a generic chatbot, it creates a case file with:

- prime suspect
- evidence and missing evidence
- alternate suspects
- failure timeline
- false leads to avoid
- quick patch and clean fix
- validation steps
- postmortem-ready export

The local AI path supports text evidence and screenshot evidence. Uploaded screenshots are encoded and sent to the local Ollama/Gemma endpoint as image input.

## Demo Story

BugTheatre is designed to demo as a five-step debugging investigation:

1. Drop messy evidence: a screenshot, logs, code, config, or a partial bug report.
2. Run local Gemma through Ollama so private debugging evidence stays local.
3. Review the Investigation Board for prime suspect, evidence, missing inputs, severity, and risk.
4. Use Patch Room to turn the diagnosis into a safer fix plan with validation and rollback.
5. Export a postmortem-ready Markdown report and machine-readable JSON.

## Output Quality Guardrails

The prompt and response layer are tuned to avoid generic or risky fixes:

- patch recommendations must not make timeout, auth, session, dependency, or deployment failures worse
- Laravel 419 / CSRF cases are hardened against unsafe “shorter timeout” advice
- dependency fixes must reference versions, compatibility ranges, lockfiles, and validation commands
- deployment fixes must validate runtime facts such as bound port, exposed port, healthcheck, logs, and mapping
- postmortems include concrete technical artifacts from the case evidence

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app starts in polished demo mode, so it works without an API key.

## Local Gemma Mode

BugTheatre AI is designed to run with a locally hosted Gemma model through Ollama.

```bash
ollama pull gemma4:e2b
ollama serve
```

Then configure:

```bash
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=gemma4:e2b
OLLAMA_TIMEOUT_SECONDS=300
OLLAMA_NUM_PREDICT=3000
ENABLE_LOCAL_AI=1
```

The default uses Gemma 4 E2B because it is better suited to a live local demo. Gemma 4 E4B is also supported for higher-quality runs by setting `OLLAMA_MODEL=gemma4:e4b`. The first request can be slower while Ollama loads the model. `OLLAMA_TIMEOUT_SECONDS` keeps the app patient enough for local hardware, and `OLLAMA_NUM_PREDICT` caps response length for a tighter demo.

The app falls back to curated demo mode if Ollama is unavailable or the configured model is not installed.

## Project Structure

```text
app.py
requirements.txt
prompts/
sample_cases/
utils/
assets/
```

Private planning documents, submission drafts, local exports, saved case history, and working screenshots are intentionally excluded from the public repository.
