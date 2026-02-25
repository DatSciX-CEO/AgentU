"""Allow running the CLI via `python -m ediscovery_agents`."""
import os

os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("OLLAMA_API_BASE", "http://localhost:11434")

import asyncio
from .cli import main as _async_main


def main():
    """Synchronous entry point used by the `ediscovery` console script."""
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
