# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

eDiscovery Time Entry Analysis System — a multi-agent AI app using Google ADK + Ollama for local LLM inference. See `README.md` and `pyproject.toml` for details.

### Services

| Service | How to start | Port |
|---|---|---|
| **Ollama** | `ollama serve` (background) | 11434 |
| **ADK Web UI** | `adk web --port 8000` (from repo root) | 8000 |

### Running commands

- **Tests**: `pytest -v` (tests stub out google-adk; no Ollama needed)
- **Dev UI**: `OLLAMA_MODEL=<model> adk web --port 8000` (requires Ollama running)
- **CLI**: `OLLAMA_MODEL=<model> python -m ediscovery_agents` (requires Ollama running)
- **Lint**: No dedicated linter configured in the project

### Gotchas

- Ollama must be started manually (`ollama serve &`) since systemd is not available in the cloud VM.
- The default model `qwen2.5:7b` is large for CPU-only inference; use `qwen2.5:0.5b` for faster iteration in cloud VMs without GPU by setting `OLLAMA_MODEL=qwen2.5:0.5b`.
- `~/.local/bin` must be on `PATH` for `adk`, `pytest`, and `ediscovery` CLI tools (pip user-install location).
- The `conftest.py` registers fake `google.adk` stubs so tests run without the real SDK being imported at module level. This means tests exercise only the tool functions, not the agent orchestration.
