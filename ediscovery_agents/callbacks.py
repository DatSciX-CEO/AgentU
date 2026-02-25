"""ADK callbacks for session-aware context injection across all agents.

The before_model_callback reads the current session state and appends a
context block to the system instruction so every agent is aware of:
  - Which file is currently active
  - What columns were discovered during profiling
  - The last analysis type performed
  - Recent analysis history (last 3 results) for multi-step report synthesis
"""

from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse


def inject_session_context(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """Before-model callback: injects session state into every model call.

    Reads well-known state keys written by tools during the session and
    appends a concise context block to the system instruction so every
    agent turn is aware of the current analysis context without the user
    having to repeat themselves.

    State keys consumed:
        available_files      - List of data files found in the data directory.
        active_file          - Name of the most recently profiled/analysed file.
        active_schema        - List of column names from the active file.
        active_column_types  - Dict of column_name -> dtype string.
        last_analysis_type   - Short label of the last analysis performed.
        last_analysis_result - Full text output from the analysis agent.
        analysis_history     - List of dicts with type/result/timestamp for
                               recent analyses (last 3 shown, 500 char cap).
    """
    state = callback_context.state

    context_lines: list[str] = []

    available = state.get("available_files")
    if available and isinstance(available, list):
        context_lines.append(f"Available files: {', '.join(available)}")

    active_file = state.get("active_file")
    if active_file:
        context_lines.append(f"Active file: {active_file}")

    active_schema = state.get("active_schema")
    if active_schema and isinstance(active_schema, list):
        context_lines.append(f"Known columns: {', '.join(str(c) for c in active_schema)}")

    col_types = state.get("active_column_types")
    if col_types and isinstance(col_types, dict):
        type_summary = ", ".join(f"{k}({v})" for k, v in col_types.items())
        context_lines.append(f"Column types: {type_summary}")

    last_analysis = state.get("last_analysis_type")
    if last_analysis:
        context_lines.append(f"Last analysis performed: {last_analysis}")

    last_result = state.get("last_analysis_result")
    if last_result and isinstance(last_result, str):
        trimmed = last_result[:2000]
        if len(last_result) > 2000:
            trimmed += "\n... (truncated)"
        context_lines.append(f"Last analysis result:\n{trimmed}")

    analysis_history = state.get("analysis_history")
    if analysis_history and isinstance(analysis_history, list):
        recent = analysis_history[-3:]
        history_parts = []
        for entry in recent:
            entry_type = entry.get("type", "unknown")
            entry_result = str(entry.get("result", ""))[:500]
            entry_ts = entry.get("timestamp", "")
            history_parts.append(
                f"  [{entry_type}] ({entry_ts}): {entry_result}"
            )
        context_lines.append(
            "Recent analysis history:\n" + "\n".join(history_parts)
        )

    if not context_lines or not llm_request.config:
        return None  # Nothing to inject — pass through unchanged

    context_block = "\n\n## Current Session Context\n" + "\n".join(
        f"- {line}" for line in context_lines
    )

    si = llm_request.config.system_instruction
    if si is None:
        llm_request.config.system_instruction = context_block
    elif isinstance(si, str):
        llm_request.config.system_instruction = si + context_block
    elif hasattr(si, "parts"):
        from google.genai import types as genai_types
        si.parts.append(genai_types.Part(text=context_block))

    return None  # Always continue to the model
