# Code Review Reference

This document provides a comprehensive mapping of files, functions, agents, and critical code elements within the `ediscovery_agents` project to serve as a reference guide for the codebase.

| File Location | Code Object (Function / Agent / Class) | Meaning / Purpose |
|---------------|-----------------------------------------|-------------------|
| `ediscovery_agents/agent.py` | `root_agent` (LlmAgent) | The main orchestrator agent that manages sub-agents and routes user queries to the appropriate specialized agent depending on the workflow stage. |
| `ediscovery_agents/callbacks.py` | `inject_session_context` | A before-model callback function that reads the session state and injects information (e.g., active file, previously discovered columns, recent analysis history) into the system prompt so all agents share context. |
| `ediscovery_agents/cli.py` | `run_agent` | Asynchronous function to send a user message to the `root_agent` and collect the final response parts. |
| `ediscovery_agents/cli.py` | `_check_ollama` | Checks if the local Ollama API server is reachable before initializing. |
| `ediscovery_agents/cli.py` | `main` | Sets up the ADK Runner, InMemorySessionService, handles the chat loop, and configures the environment for the local interactive CLI. |
| `ediscovery_agents/config.py` | `get_model` | Returns the `LiteLlm` model configuration specifically bound to `ollama_chat` for the selected local Ollama model (defaulting to `qwen2.5:7b`). |
| `ediscovery_agents/sub_agents/analysis_agent.py` | `analysis_agent` (LlmAgent) | A sub-agent dedicated to deep quantitative, statistical, and trend analysis on the data. Equipped with specialized data analysis tools. |
| `ediscovery_agents/sub_agents/ingestion_agent.py` | `ingestion_agent` (LlmAgent) | A sub-agent handling file discovery and schema profiling. Used to explore available data files and determine dataset structure. |
| `ediscovery_agents/sub_agents/reporting_agent.py` | `reporting_agent` (LlmAgent) | Formats analysis findings into structured professional reports suitable for legal teams. |
| `ediscovery_agents/sub_agents/reporting_agent.py` | `ReportSection`, `AnalysisReport` (Pydantic Models) | Structured output schemas enforcing a consistent report format (executive summary, sections with findings, recommendations, and quality notes). |
| `ediscovery_agents/tools/analysis.py` | `_append_analysis_history` | Helper to keep a rolling 10-entry log of past analysis results in the tool context so agents can reference historical queries. |
| `ediscovery_agents/tools/analysis.py` | `get_summary_statistics` | Calculates row limits, numeric statistics, and column counts for an eDiscovery time entry dataset. |
| `ediscovery_agents/tools/analysis.py` | `analyze_by_timekeeper` | Analyzes time entries grouped by the timekeeper (attorney/reviewer), computing totals and averages. |
| `ediscovery_agents/tools/analysis.py` | `find_duplicate_entries` | Identifies exact duplicate rows across specified columns to spot repetitive or double-billed time entries. |
| `ediscovery_agents/tools/analysis.py` | `filter_time_entries` | Applies logical and textual comparisons (equals, greater_than, contains) over columns to filter specific entries. |
| `ediscovery_agents/tools/analysis.py` | `calculate_totals` | Groups data by specific columns to calculate counts and summed values, like hours by task code. |
| `ediscovery_agents/tools/analysis.py` | `detect_billing_anomalies` | Detects anomalies in billing patterns using the Interquartile Range (IQR) to find extremely high/low working hours, zero hours, and rate outliers. |
| `ediscovery_agents/tools/analysis.py` | `date_range_analysis` | Filters data entries between start and end dates and summarizes activities within that timeframe. |
| `ediscovery_agents/tools/analysis.py` | `cross_reference_entries` | Creates a cross-tabulation of two columns to analyze their relationships (e.g. Timekeeper vs. Task Code counts). |
| `ediscovery_agents/tools/analysis.py` | `analyze_utilization_trends` | Checks metrics against utilization target limits and target variance to classify below/above target metrics. |
| `ediscovery_agents/tools/ingestion.py` | `list_uploaded_files` | Looks in the local `data` directory for active CSV, Excel, and Parquet data files. |
| `ediscovery_agents/tools/ingestion.py` | `profile_file` | Reads file schemas, extracts standard data types, row counts, memory footprints, and sampling data to determine table structure. |
| `ediscovery_agents/tools/loader.py` | `safe_load` | Centralized utility to restrict file opening strictly to the local `data` subfolder, blocking invalid locations and path traversal attempts. |
