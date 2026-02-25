# CLAUDE101 — eDiscovery Agent Dev Session Notes

**Last Updated:** 2026-02-24
**ADK Version:** 1.25.1
**Stack:** Google ADK + Ollama (local LLM) + LiteLlm

---

## What This App Does

Privacy-first, fully local legal billing analysis system. Users drop CSV / Excel / Parquet time-entry files into `ediscovery_agents/data/` and interact with a multi-agent system via natural language.

- No cloud API calls. No keys. All LLM inference runs through Ollama on your machine.
- ADK web UI at `http://localhost:8000` (via `adk web`) or run headless via `python -m ediscovery_agents`.

---

## Project Structure

```
ediscovery_agents/
├── __init__.py
├── __main__.py           # python -m entrypoint
├── .env                  # OLLAMA_API_BASE, OLLAMA_MODEL, PYTHONUTF8
├── config.py             # get_model() → LiteLlm("ollama_chat/{model}")
├── agent.py              # Root orchestrator (ediscovery_orchestrator)
├── callbacks.py          # before_model_callback for session context
├── cli.py                # Standalone interactive CLI (with Ollama health check)
├── sub_agents/
│   ├── ingestion_agent.py
│   ├── analysis_agent.py
│   └── reporting_agent.py
├── tools/
│   ├── loader.py         # Shared safe_load() with path traversal protection
│   ├── ingestion.py      # list_uploaded_files, profile_file
│   └── analysis.py       # 8 pandas analysis tools
└── data/                 # Drop zone for data files
```

---

## How to Run

### Prerequisites
```bash
# 1. Ollama must be running
ollama serve   # or launch Ollama desktop app

# 2. Pull a model with tool-calling support
ollama pull qwen2.5:7b
```

### Option A — ADK Web UI (Recommended for testing)
```powershell
# PowerShell
$env:OLLAMA_API_BASE="http://localhost:11434"
$env:PYTHONUTF8="1"
adk web --port 8000
```
Then open `http://localhost:8000` → select **ediscovery_agents** from the dropdown.

### Option B — Standalone CLI
```bash
python -m ediscovery_agents
```

### Option C — ADK CLI
```powershell
$env:OLLAMA_API_BASE="http://localhost:11434"
$env:PYTHONUTF8="1"
adk run ediscovery_agents
```

---

## Session 2026-02-23 — Session State Foundation

### Goal
Add proper Google ADK session/state continuity so agents maintain context across multi-turn conversations (no re-asking for file names, column names, etc.).

### What Was Done
- Created `callbacks.py` with `inject_session_context` before-model callback.
- Wired `before_model_callback` into all four agents (root + 3 sub-agents).
- Added `output_key` to `analysis_agent` and `reporting_agent`.
- Added `ToolContext` state writes to all 10 tool functions.

---

## Session 2026-02-24 — Hardening & State Completeness

### Goal
Close the gaps in the session state loop so all agents have full context,
add path traversal protection, consolidate loaders, and add startup checks.

### Code Changes

#### 1. NEW FILE: `ediscovery_agents/tools/loader.py`
Shared data loader with path traversal protection. All tool modules import
`safe_load()` from here instead of duplicating their own loader.

```python
from .loader import safe_load, DATA_DIR

safe_load(file_name)  # validates basename, resolves path, checks bounds
```

- Rejects filenames containing path separators or `..` sequences.
- Resolves via `os.path.realpath` and confirms result is inside `DATA_DIR`.
- Supports CSV, Excel, and Parquet.

#### 2. UPDATED: `ediscovery_agents/callbacks.py`
Expanded `inject_session_context` to inject **all** meaningful state keys:

| Key injected | Source |
|---|---|
| `available_files` | `list_uploaded_files` tool |
| `active_file` | `profile_file` / analysis tools |
| `active_schema` | `profile_file` |
| `active_column_types` | `profile_file` (no longer truncated to 8) |
| `last_analysis_type` | All analysis tools |
| `last_analysis_result` | ADK `output_key` on `analysis_agent` (trimmed to 2000 chars) |

**Key fix:** The reporting agent can now read analysis results via the
injected context block — previously it only saw the analysis *type* label
but not the actual findings.

#### 3. UPDATED: `ediscovery_agents/tools/ingestion.py`
- Removed duplicate `_load_dataframe()` function.
- Now imports `safe_load` from `loader.py`.

#### 4. UPDATED: `ediscovery_agents/tools/analysis.py`
- Removed duplicate `_load()` function — all 8 tools now use `safe_load`.
- Fixed `analyze_by_timekeeper` and `detect_billing_anomalies`: changed
  `tool_context: ToolContext = None` to a required parameter (consistent
  with all other tools; ADK always injects it).

#### 5. UPDATED: `ediscovery_agents/cli.py`
- Added Ollama health check on startup (`GET /api/tags`).
- If Ollama is unreachable, prints a clear error with instructions
  instead of crashing mid-conversation with an opaque LiteLlm error.

#### 6. UPDATED: `ediscovery_agents/tools/__init__.py`
- Added `safe_load` and `DATA_DIR` exports from the new `loader.py`.

### State Writes per Tool (unchanged from session 1)

| Function | State written |
|---|---|
| `list_uploaded_files` | `available_files` |
| `profile_file` | `active_file`, `active_schema`, `active_column_types` |
| `get_summary_statistics` | `active_file`, `last_analysis_type="summary_statistics"` |
| `analyze_by_timekeeper` | `active_file`, `last_analysis_type="timekeeper_analysis"` |
| `find_duplicate_entries` | `last_analysis_type="duplicate_detection"` |
| `filter_time_entries` | `last_analysis_type="filtered_entries"` |
| `calculate_totals` | `last_analysis_type="totals_calculation"` |
| `detect_billing_anomalies` | `last_analysis_type="billing_anomalies"` |
| `date_range_analysis` | `last_analysis_type="date_range_analysis"` |
| `cross_reference_entries` | `last_analysis_type="cross_reference"` |

---

## Session State Keys Reference

These keys flow through `session.state` (InMemorySessionService) across every turn.
Keys marked with **(injected)** are included in the system instruction by `inject_session_context`.

| Key | Type | Set by | Injected? | Purpose |
|---|---|---|---|---|
| `available_files` | `list[str]` | `list_uploaded_files` | Yes | Files found in data dir |
| `active_file` | `str` | `profile_file`, analysis tools | Yes | Currently active data file |
| `active_schema` | `list[str]` | `profile_file` | Yes | Column names of active file |
| `active_column_types` | `dict[str,str]` | `profile_file` | Yes (full) | Column → dtype map |
| `last_analysis_type` | `str` | Each analysis tool | Yes | Label of last analysis run |
| `last_analysis_result` | `str` | ADK via `output_key` | Yes (2000 char cap) | Full text from analysis_agent |
| `last_report` | `str` | ADK via `output_key` | No | Full text from reporting_agent |

---

## How the Context Loop Works (End-to-End)

```
Turn 1: "What files are available?"
  → ingestion_agent calls list_uploaded_files()
  → writes: available_files → state

Turn 2: "Profile time_entries.csv"
  → inject_session_context fires BEFORE model call
  → appends: Available files: time_entries.csv, invoices.xlsx
  → ingestion_agent calls profile_file()
  → writes: active_file, active_schema, active_column_types → state

Turn 3: "Show billing anomalies"
  → inject_session_context fires BEFORE model call
  → appends to system instruction:
       ## Current Session Context
       - Available files: time_entries.csv, invoices.xlsx
       - Active file: time_entries.csv
       - Known columns: Date, Attorney, Hours, Rate, Description
       - Column types: Date(object), Attorney(object), Hours(float64), ...
  → analysis_agent already knows the file — no need to ask
  → detect_billing_anomalies writes: last_analysis_type="billing_anomalies"
  → ADK saves agent response → state["last_analysis_result"]

Turn 4: "Generate a formal report"
  → inject_session_context injects all of the above PLUS:
       - Last analysis performed: billing_anomalies
       - Last analysis result: (the actual findings, up to 2000 chars)
  → reporting_agent has full context to write the report
  → ADK saves report → state["last_report"]
```

---

## Key ADK Patterns Used

### `before_model_callback`
Runs before every LLM call. Receives `CallbackContext` (has `.state`) and `LlmRequest` (has `.config.system_instruction`). Return `None` to continue, return `LlmResponse` to short-circuit.

```python
agent = LlmAgent(
    ...,
    before_model_callback=my_callback,
)
```

### `output_key`
ADK automatically writes the agent's final text response to `session.state[output_key]` after each turn. Zero extra code required.

```python
agent = LlmAgent(
    ...,
    output_key="my_result",
)
```

### `ToolContext` in tools
ADK auto-injects `ToolContext` at call time. It is excluded from the LLM tool schema automatically — the model never sees it. Just add it as a parameter.

```python
from google.adk.tools.tool_context import ToolContext

def my_tool(param: str, tool_context: ToolContext) -> dict:
    tool_context.state["key"] = "value"
    return {"result": "..."}
```

### `InMemorySessionService` (cli.py — unchanged)
Session is created once per CLI run with a unique `session_id`. All state is held in memory and discarded on exit — no data persistence risk.

---

## ADK Important Notes

- Use `ollama_chat/` provider prefix in LiteLlm, NOT `ollama/` — the plain `ollama` provider causes infinite tool-call loops.
- `adk web` uses a **file-based session storage** rooted at `C:\agent_u` (not InMemory like the CLI) — sessions persist between browser refreshes.
- `adk web` also creates `.adk/artifacts/` for file artifact storage.
- `global_instruction` on LlmAgent is **deprecated** in ADK 1.25 — use `before_model_callback` or `GlobalInstructionPlugin` instead.
- All file loading now goes through `tools/loader.py` → `safe_load()` which validates filenames and blocks path traversal.
- The CLI checks Ollama reachability on startup and prints a clear error if it's down.

---

## Next Steps

- [ ] Pull the model if not done: `ollama pull qwen2.5:7b`
- [ ] Test `adk web --port 8000` end-to-end with a real CSV file in `ediscovery_agents/data/`
- [ ] Verify `inject_session_context` appears in the "Trace" panel of the ADK web UI (check system instruction on each turn)
- [ ] Tune agent instructions for timekeeper utilization analysis workflows
- [ ] Consider `DatabaseSessionService` if you want sessions to persist across `adk web` restarts
- [ ] Consider `output_schema` (Pydantic model) on reporting_agent for structured report output
