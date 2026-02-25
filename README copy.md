<div align="center">

  <h1>⚖️ eDiscovery Time Entry Analysis System</h1>
  
  <p>
    <strong>A fully local, privacy-first, hierarchical multi-agent system for analyzing legal billing time entries.</strong>
  </p>

  <p>
    Built with ❤️ by <b>DSAI</b>
  </p>

  <p>
    <a href="https://google.github.io/adk-docs/"><img src="https://img.shields.io/badge/Powered_by-Google_ADK-blue?style=for-the-badge&logo=google" alt="Google ADK"></a>
    <a href="https://ollama.com/"><img src="https://img.shields.io/badge/Inference-Ollama-white?style=for-the-badge&logo=ollama&color=black" alt="Ollama"></a>
    <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+"></a>
  </p>

</div>

<br />

## 📖 Overview

Powered by the [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) and [Ollama](https://ollama.com/), this system provides deep quantitative and qualitative analysis of legal time entries without ever exposing sensitive client data. 

**🔒 Privacy First**: **No data ever leaves your machine.** All Large Language Model (LLM) inference runs completely locally through Ollama. Zero cloud API keys required.

---

## 🏛️ Architecture

The system leverages a sophisticated **Orchestrator-Specialist** pattern. Four distinct agents collaborate seamlessly, all driven by a local Ollama model via the ADK `LiteLlm` connector:

| Agent | Role |
| :--- | :--- |
| 🛡️ **Root Orchestrator** | Intelligent user-facing interface that routes queries to the appropriate specialists. |
| 📥 **Ingestion Agent** | Profiles uploaded `CSV`, `Excel`, and `Parquet` files to understand schemas and data quality. |
| 📊 **Analysis Agent** | Performs deep quantitative analysis utilizing a suite of 8 Pandas-powered tools. |
| 📝 **Reporting Agent** | Synthesizes findings and formats them into polished, professional legal reports. |

---

## 🚀 Getting Started

### Prerequisites

- **Python**: `3.10+`
- **Ollama**: Installed and running locally ([Download Ollama](https://ollama.com/download))

### 1️⃣ Pull an Ollama Model
You need a local model with tool-calling support. We recommend `qwen2.5:7b` for an excellent balance of speed and capability:

```bash
ollama pull qwen2.5:7b
```

<details>
<summary><b>Alternative Models</b></summary>
Run `ollama show <model>` to confirm `tools` appears under Capabilities.

```bash
ollama pull mistral-small3.1    # 24B, excellent but requires more RAM
ollama pull llama3.1:8b         # Popular alternative
ollama pull qwen2.5:14b         # Stronger reasoning capabilities
```
</details>

### 2️⃣ Install Dependencies

Set up your virtual environment and install required packages:

```bash
# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

### 3️⃣ Configuration (Optional)

The system works out of the box with the defaults in `ediscovery_agents/.env`:

```env
OLLAMA_API_BASE=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
PYTHONUTF8=1
```
*Note: Change `OLLAMA_MODEL` if you pulled a different local model in Step 1.*

### 4️⃣ Add Your Data

Place your eDiscovery time entry files (`.csv`, `.xlsx`, or `.parquet`) into the designated data directory:
```text
ediscovery_agents/data/
```

---

## 💻 Usage

Ensure Ollama is actively running in the background (`ollama serve` or via the Ollama desktop application).

### Option A: ADK Web Interface (Recommended)
Provides a rich graphical interface for development and interaction.

```bash
# PowerShell
$env:OLLAMA_API_BASE="http://localhost:11434"
$env:PYTHONUTF8="1"
adk web --port 8000
```
*Open `http://localhost:8000` in your browser and select **ediscovery_agents** from the dropdown.*

### Option B: ADK Command Line Interface
Run directly via the ADK framework.

```bash
# PowerShell
$env:OLLAMA_API_BASE="http://localhost:11434"
$env:PYTHONUTF8="1"
adk run ediscovery_agents
```

### Option C: Standalone CLI
Run the package directly using Python. Environment variables are set automatically by the CLI entrypoint.

```bash
python -m ediscovery_agents
```

---

## 💡 Example Queries

Interact seamlessly with the system using natural language:

- 📂 *"What files are available for analysis?"*
- 🔍 *"Profile the `time_entries.csv` file."*
- 📈 *"Show me summary statistics for `time_entries.csv`."*
- 👯 *"Find duplicate entries based on Date, Timekeeper, and Hours."*
- 🧑‍⚖️ *"Analyze billing by timekeeper using the Attorney and Hours columns."*
- ⚠️ *"Detect billing anomalies in the Hours column."*
- ⏱️ *"Filter entries where Hours is greater than 8."*
- 📑 *"Generate a formal report summarizing the key findings."*

---

## 🛡️ Data Security & Compliance

We take data privacy extremely seriously. By design, this system is suited for highly sensitive legal data:

- 🔒 **100% Local Inference**: All LLM processing is handled by Ollama on your local hardware.
- 🚫 **No Cloud APIs**: Zero external API calls. No API keys are required, stored, or transmitted.
- 📂 **Local Storage Only**: Data files stay on disk and are only read by local Python/Pandas operations.
- 🧹 **Ephemeral State**: Session state is held securely in-memory and completely discarded upon exit.

---

## 📁 Project Structure

```text
ediscovery_agents/
├── __init__.py           # Package initialization
├── .env                  # Local Ollama configuration
├── config.py             # Centralized model configuration
├── agent.py              # Root orchestrator agent definition
├── callbacks.py          # Session-aware context injection callbacks
├── cli.py                # Standalone interactive CLI implementation
├── __main__.py           # Python -m entrypoint
├── sub_agents/           # Specialist agents
│   ├── __init__.py
│   ├── ingestion_agent.py
│   ├── analysis_agent.py
│   └── reporting_agent.py
├── tools/                # Agent capabilities
│   ├── __init__.py
│   ├── ingestion.py      # File profiling and parsing tools
│   ├── analysis.py       # Data analysis and manipulation tools
│   └── loader.py         # Shared safe data-loading utility
└── data/                 # Drop zone for eDiscovery data files
```

---
<div align="center">
  <p><b>Built by DSAI</b> | Privacy-First Legal Tech</p>
</div>
