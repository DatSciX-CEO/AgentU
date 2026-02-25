"""Standalone interactive CLI for the eDiscovery Time Entry Analysis System.

Usage:
    python -m ediscovery_agents.cli

All inference runs locally via Ollama. No data leaves the machine.
"""

import asyncio
import os
import uuid
from urllib.request import urlopen
from urllib.error import URLError

os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("OLLAMA_API_BASE", "http://localhost:11434")

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agent import root_agent
from .config import OLLAMA_MODEL

APP_NAME = "ediscovery_analysis"
USER_ID = "local_user"


async def run_agent(runner: Runner, session_id: str, user_input: str) -> str:
    """Send a message to the agent and collect the final response."""
    content = types.Content(
        role="user", parts=[types.Part(text=user_input)]
    )

    final_text = ""
    async for event in runner.run_async(
        user_id=USER_ID, session_id=session_id, new_message=content
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        final_text += part.text

    return final_text.strip() if final_text else "[No response from agent]"


def _check_ollama() -> bool:
    """Return True if Ollama is reachable, False otherwise."""
    base = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
    try:
        with urlopen(f"{base}/api/tags", timeout=5) as resp:
            return resp.status == 200
    except (URLError, OSError):
        return False


async def main():
    if not _check_ollama():
        base = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
        print("ERROR: Cannot reach Ollama at", base)
        print("Start Ollama first:  ollama serve  (or launch the desktop app)")
        print(f"Then pull a model:   ollama pull {OLLAMA_MODEL}")
        return

    session_service = InMemorySessionService()
    session_id = f"session_{uuid.uuid4().hex[:8]}"

    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    print("=" * 60)
    print("  eDiscovery Time Entry Analysis System")
    print("  LOCAL ONLY -- Ollama + Google ADK")
    print(f"  Model: {OLLAMA_MODEL}")
    print("=" * 60)
    print()
    print("All inference runs locally. No data leaves this machine.")
    print()
    print("Place CSV, Excel, or Parquet files in the")
    print("ediscovery_agents/data/ directory, then ask questions.")
    print("Type 'exit' or 'quit' to end the session.")
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye.")
            break

        response = await run_agent(runner, session_id, user_input)
        print(f"\nAgent: {response}\n")


if __name__ == "__main__":
    asyncio.run(main())
