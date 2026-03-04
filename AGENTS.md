# AGENTS.md

## Cursor Cloud specific instructions

### Overview

This is an **eDiscovery Time Entry Analysis System** — a multi-agent AI system using Google ADK + Ollama (local LLM) for privacy-first legal billing analysis. See `dev_docs/CLAUDE101.md` for full architecture details and `README.md` for a project summary.

### Services

| Service | How to start | Notes |
|---------|-------------|-------|
| **Ollama** | `ollama serve` (background) | Required for end-to-end agent interaction. Must pull a model first: `ollama pull qwen2.5:3b` (or `qwen2.5:7b` for higher quality). On CPU-only VMs, `qwen2.5:3b` is recommended for faster inference. |
| **ADK Web UI** | `OLLAMA_API_BASE=http://localhost:11434 OLLAMA_MODEL=qwen2.5:3b PYTHONUTF8=1 adk web --port 8000` | Run from `/workspace`. Requires `~/.local/bin` on PATH. Opens at `http://localhost:8000`. Select `ediscovery_agents` from the agent dropdown. |

### Running tests

```
pytest -v
```

Tests run **without Ollama** — `tests/conftest.py` registers lightweight stubs for all `google.adk` modules. Tests exercise only the pure-Python tool functions (data loading, analysis, ingestion).

### Key caveats

- **No linting tools** are configured in this project (no ruff, flake8, mypy, etc.).
- The `adk` and `ediscovery` CLI commands install to `~/.local/bin`. Ensure it is on `PATH`: `export PATH="$HOME/.local/bin:$PATH"`.
- The `.env` file at `ediscovery_agents/.env` sets default `OLLAMA_API_BASE` and `OLLAMA_MODEL`. Override via environment variables when using a different model size.
- CPU-only inference with `qwen2.5:3b` takes 60-180 seconds per agent turn. Be patient during end-to-end testing.
- Use `ollama_chat/` provider prefix in LiteLlm (not `ollama/`) to avoid infinite tool-call loops.
