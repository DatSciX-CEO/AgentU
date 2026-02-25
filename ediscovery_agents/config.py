"""Centralized configuration for the eDiscovery agent system.

All inference runs locally via Ollama. No data leaves the machine.
Change OLLAMA_MODEL to swap the local model used by all agents.
"""

import os

from google.adk.models.lite_llm import LiteLlm

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")

def get_model() -> LiteLlm:
    """Return a LiteLlm instance pointing at the local Ollama server.

    Uses the ``ollama_chat`` provider (NOT ``ollama``) to avoid infinite
    tool-call loops, per the official ADK Ollama documentation.
    """
    return LiteLlm(model=f"ollama_chat/{OLLAMA_MODEL}")
