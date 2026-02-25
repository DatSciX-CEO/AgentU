"""Shared fixtures for the eDiscovery tools test suite.

The google-adk package may not be installed in the test environment, so we
register lightweight stubs in sys.modules BEFORE any test module triggers an
import of ediscovery_agents (whose __init__.py transitively imports google.adk
agents, callbacks, config, and sub-agents).
"""

import sys
import types

# ---------------------------------------------------------------------------
# Build a minimal fake google.adk module tree so all transitive imports
# resolve without the real SDK.  This block runs at import-time — well before
# pytest collects any test files that import ediscovery_agents.
# ---------------------------------------------------------------------------

def _make_module(name, parent_path=None):
    mod = types.ModuleType(name)
    if parent_path is not None:
        mod.__path__ = []
    return mod


if "google.adk" not in sys.modules:
    # ---- google / google.adk ----
    _google = _make_module("google", parent_path=[])
    _google_adk = _make_module("google.adk", parent_path=[])

    # ---- google.adk.agents / google.adk.agents.callback_context ----
    _agents = _make_module("google.adk.agents", parent_path=[])
    _callback_ctx = _make_module("google.adk.agents.callback_context")

    class _FakeLlmAgent:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class _FakeCallbackContext:
        def __init__(self):
            self.state = {}

    _agents.LlmAgent = _FakeLlmAgent
    _callback_ctx.CallbackContext = _FakeCallbackContext

    # ---- google.adk.tools / google.adk.tools.tool_context ----
    _tools = _make_module("google.adk.tools", parent_path=[])
    _tool_ctx = _make_module("google.adk.tools.tool_context")

    class _FakeToolContext:
        def __init__(self):
            self.state: dict = {}

    _tool_ctx.ToolContext = _FakeToolContext

    # ---- google.adk.models / llm_request / llm_response / lite_llm ----
    _models = _make_module("google.adk.models", parent_path=[])
    _llm_req = _make_module("google.adk.models.llm_request")
    _llm_resp = _make_module("google.adk.models.llm_response")
    _lite_llm = _make_module("google.adk.models.lite_llm")

    class _FakeLlmRequest:
        pass

    class _FakeLlmResponse:
        pass

    class _FakeLiteLlm:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    _llm_req.LlmRequest = _FakeLlmRequest
    _llm_resp.LlmResponse = _FakeLlmResponse
    _lite_llm.LiteLlm = _FakeLiteLlm

    # ---- google.genai / google.genai.types (used conditionally) ----
    _genai = _make_module("google.genai", parent_path=[])
    _genai_types = _make_module("google.genai.types")
    _genai.types = _genai_types

    # Register everything into sys.modules
    _all = {
        "google": _google,
        "google.adk": _google_adk,
        "google.adk.agents": _agents,
        "google.adk.agents.callback_context": _callback_ctx,
        "google.adk.tools": _tools,
        "google.adk.tools.tool_context": _tool_ctx,
        "google.adk.models": _models,
        "google.adk.models.llm_request": _llm_req,
        "google.adk.models.llm_response": _llm_resp,
        "google.adk.models.lite_llm": _lite_llm,
        "google.genai": _genai,
        "google.genai.types": _genai_types,
    }
    for mod_name, mod in _all.items():
        sys.modules.setdefault(mod_name, mod)

# ---------------------------------------------------------------------------
# Now it is safe to import ediscovery_agents modules.
# ---------------------------------------------------------------------------

import os

import pandas as pd
import pytest


class MockToolContext:
    """Minimal stand-in for google.adk.tools.tool_context.ToolContext.

    Only the ``state`` dict attribute is needed by the tools under test.
    """

    def __init__(self):
        self.state: dict = {}


@pytest.fixture
def tool_context():
    """Provide a fresh MockToolContext for each test."""
    return MockToolContext()


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create a temporary data directory and return its path."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_csv(tmp_data_dir):
    """Write a small CSV with realistic eDiscovery columns into the temp data dir."""
    df = pd.DataFrame(
        {
            "Date": [
                "1/6/2025",
                "1/6/2025",
                "1/7/2025",
                "1/7/2025",
                "1/8/2025",
            ],
            "TimekeeperFullName": [
                "Alice Adams",
                "Bob Brown",
                "Alice Adams",
                "Bob Brown",
                "Alice Adams",
            ],
            "JobTitle_UKG": [
                "Review Attorney",
                "Forensics Consultant",
                "Review Attorney",
                "Forensics Consultant",
                "Review Attorney",
            ],
            "Department_UKG": [
                "Managed Review",
                "Forensics",
                "Managed Review",
                "Forensics",
                "Managed Review",
            ],
            "CountryCode_UKG": ["US", "UK", "US", "UK", "US"],
            "Chargeable Hours": [8.0, 6.0, 8.5, 6.5, 7.5],
            "Non Chargeable Hours": [0.5, 2.0, 0.0, 1.5, 1.0],
            "Billable Hours": [8.0, 6.0, 8.5, 6.5, 7.5],
            "Utilization": [1.0625, 1.0, 1.0625, 1.0, 1.0625],
            "Variance Against Utilization Target Hours": [
                1.2,
                0.0,
                1.7,
                0.5,
                0.7,
            ],
        }
    )
    path = tmp_data_dir / "test_data.csv"
    df.to_csv(path, index=False)
    return "test_data.csv"


@pytest.fixture
def wide_csv(tmp_data_dir):
    """Write a CSV with >10 columns so column-projection logic triggers."""
    cols = {f"col_{i}": list(range(5)) for i in range(12)}
    cols["Date"] = ["1/6/2025"] * 5
    cols["TimekeeperFullName"] = ["Alice"] * 5
    cols["Chargeable Hours"] = [1.0, 2.0, 3.0, 4.0, 5.0]
    df = pd.DataFrame(cols)
    path = tmp_data_dir / "wide_data.csv"
    df.to_csv(path, index=False)
    return "wide_data.csv"


@pytest.fixture
def patch_data_dir(monkeypatch, tmp_data_dir):
    """Patch DATA_DIR in loader.py (and re-exports) to point at the temp dir."""
    import ediscovery_agents.tools.loader as loader_mod
    import ediscovery_agents.tools.ingestion as ingestion_mod

    monkeypatch.setattr(loader_mod, "DATA_DIR", str(tmp_data_dir))
    monkeypatch.setattr(ingestion_mod, "DATA_DIR", str(tmp_data_dir))
