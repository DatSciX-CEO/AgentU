from typing import List

from google.adk.agents import LlmAgent
from pydantic import BaseModel

from ..callbacks import inject_session_context
from ..config import get_model


class ReportSection(BaseModel):
    """A single themed section within an analysis report."""

    title: str
    findings: List[str]


class AnalysisReport(BaseModel):
    """Structured output schema for the reporting agent."""

    executive_summary: str
    sections: List[ReportSection]
    recommendations: List[str]
    data_quality_notes: List[str]


reporting_agent = LlmAgent(
    name="reporting_agent",
    model=get_model(),
    description=(
        "Formats analysis results into structured professional reports suitable "
        "for legal teams. Delegate to this agent when the user needs a formal "
        "report, executive summary, or well-formatted output from analysis results."
    ),
    instruction="""\
You are the Reporting Agent for an eDiscovery time entry analysis system.

Your role is to synthesize analysis results into clear, professional reports
suitable for legal teams and litigation support professionals.

You MUST produce output that conforms to the AnalysisReport schema with these
fields:
  - executive_summary: A concise paragraph summarizing the most important
    findings across ALL analyses performed in this session (not just the most
    recent one). Reference analysis_history in the session context to cover
    prior results.
  - sections: A list of ReportSection objects, each with a descriptive title
    and a list of finding strings. Create one section per analysis type or
    logical grouping. Each finding should be a complete, self-contained
    statement with quantified data.
  - recommendations: Actionable next steps based on the findings. Be specific
    and reference the data supporting each recommendation.
  - data_quality_notes: Any caveats, limitations, missing data, or quality
    issues observed during the analyses.

Report content guidelines:
1. Summarize the most important findings first (inverted pyramid style).
2. Quantify all findings with exact numbers and percentages.
3. Compare against common legal billing benchmarks where applicable
   (e.g., reasonable daily billing hours typically 6-10 hours).
4. Recommend specific follow-up actions for flagged entries.
5. Format currency values and time values consistently.
6. Use professional legal industry terminology.

Maintain objectivity and clearly distinguish between:
- Findings: facts derived directly from the data
- Recommendations: your analytical suggestions based on findings
""",
    before_model_callback=inject_session_context,
    output_key="last_report",
    output_schema=AnalysisReport,
    tools=[],
)
