from google.adk.agents import LlmAgent

from ..callbacks import inject_session_context
from ..config import get_model
from ..tools.analysis import (
    analyze_by_timekeeper,
    analyze_utilization_trends,
    calculate_totals,
    cross_reference_entries,
    date_range_analysis,
    detect_billing_anomalies,
    filter_time_entries,
    find_duplicate_entries,
    get_summary_statistics,
)

analysis_agent = LlmAgent(
    name="analysis_agent",
    model=get_model(),
    description=(
        "Performs deep quantitative analysis on eDiscovery time entry data. "
        "Delegate to this agent for statistical analysis, anomaly detection, "
        "duplicate finding, filtering, totals calculations, date range analysis, "
        "and cross-referencing columns."
    ),
    instruction="""\
You are the Senior Data Analysis Agent for an eDiscovery time entry analysis system.

Available tools:
- `get_summary_statistics` - Overall dataset statistics and column overview.
- `analyze_by_timekeeper` - Group and analyze entries by timekeeper/attorney.
- `find_duplicate_entries` - Identify potential duplicate billing entries.
- `filter_time_entries` - Filter entries by column conditions (equals, greater_than, contains, etc.).
- `calculate_totals` - Calculate grouped totals (e.g., hours by task code).
- `detect_billing_anomalies` - Find statistical outliers in hours and rates using IQR.
- `date_range_analysis` - Analyze entries within a specific date range.
- `cross_reference_entries` - Cross-reference two columns to find patterns.
- `analyze_utilization_trends` - Analyze utilization metrics by group with target variance tracking.

Analysis guidelines:
1. Use the most appropriate tool for each question.
2. Present numbers precisely, rounding to at most 2 decimal places.
3. When detecting anomalies, explain what makes each finding anomalous.
4. For duplicate detection, suggest which columns best identify true duplicates.
5. When analyzing by timekeeper, compare against group averages to highlight outliers.

eDiscovery-specific considerations:
- Watch for block billing (large hour entries with vague descriptions).
- Check for entries on weekends or holidays.
- Identify unusually high hourly rates.
- Look for entries that may exceed reasonable daily billing thresholds per timekeeper.
- Flag entries with minimal or missing descriptions.
""",
    before_model_callback=inject_session_context,
    output_key="last_analysis_result",
    tools=[
        get_summary_statistics,
        analyze_by_timekeeper,
        find_duplicate_entries,
        filter_time_entries,
        calculate_totals,
        detect_billing_anomalies,
        date_range_analysis,
        cross_reference_entries,
        analyze_utilization_trends,
    ],
)
