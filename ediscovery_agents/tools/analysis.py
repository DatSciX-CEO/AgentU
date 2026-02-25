from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
from google.adk.tools.tool_context import ToolContext

from .loader import safe_load


def _append_analysis_history(
    tool_context: ToolContext, analysis_type: str, result_summary: str
) -> None:
    """Append an analysis result to the session's analysis_history list.

    Keeps the last 10 entries so the reporting agent can reference multiple
    prior analyses instead of only the most recent one.
    """
    history = tool_context.state.get("analysis_history", [])
    history.append({
        "type": analysis_type,
        "result": result_summary[:500],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    tool_context.state["analysis_history"] = history[-10:]


def get_summary_statistics(file_name: str, tool_context: ToolContext) -> dict:
    """Calculates comprehensive summary statistics for an eDiscovery time entry dataset.

    Provides row count, numeric column statistics (mean, median, min, max, sum,
    std dev), and detected date ranges.

    Args:
        file_name: The name of the file in the data directory.

    Returns:
        dict: Summary statistics including counts, totals, averages, and date ranges.
    """
    try:
        df = safe_load(file_name)
        stats: dict = {
            "status": "success",
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "columns": list(df.columns),
        }

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            numeric_stats = {}
            for col in numeric_cols:
                numeric_stats[col] = {
                    "mean": round(float(df[col].mean()), 2),
                    "median": round(float(df[col].median()), 2),
                    "min": round(float(df[col].min()), 2),
                    "max": round(float(df[col].max()), 2),
                    "sum": round(float(df[col].sum()), 2),
                    "std_dev": round(float(df[col].std()), 2),
                }
            stats["numeric_statistics"] = numeric_stats

        date_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()
        for col in df.select_dtypes(include=["object", "str"]).columns:
            try:
                pd.to_datetime(df[col].dropna().head(10), format="mixed")
                date_cols.append(col)
            except (ValueError, TypeError):
                pass

        if date_cols:
            date_info = {}
            for col in date_cols:
                try:
                    dates = pd.to_datetime(df[col], errors="coerce")
                    valid = dates.dropna()
                    if not valid.empty:
                        date_info[col] = {
                            "earliest": str(valid.min()),
                            "latest": str(valid.max()),
                            "range_days": int((valid.max() - valid.min()).days),
                        }
                except Exception:
                    # Skip columns that fail date parsing/range extraction
                    continue
            if date_info:
                stats["date_ranges"] = date_info

        tool_context.state["active_file"] = file_name
        tool_context.state["last_analysis_type"] = "summary_statistics"
        _append_analysis_history(
            tool_context,
            "summary_statistics",
            f"rows={stats['total_rows']} cols={stats['total_columns']} columns={stats['columns']}",
        )

        return stats
    except Exception as e:
        return {"status": "error", "message": str(e)}


def analyze_by_timekeeper(
    file_name: str,
    timekeeper_column: str,
    hours_column: str,
    tool_context: ToolContext,
    rate_column: Optional[str] = None,
) -> dict:
    """Analyzes time entries grouped by timekeeper (attorney/reviewer).

    Groups data by the timekeeper column and calculates total hours, average hours,
    entry count, and optionally billing amounts per timekeeper.

    Args:
        file_name: The name of the file in the data directory.
        timekeeper_column: Column identifying timekeepers (e.g., 'Attorney', 'Reviewer').
        hours_column: Column containing hours worked.
        rate_column: Optional column containing hourly rates for billing calculation.

    Returns:
        dict: Per-timekeeper analysis with hours, counts, and billing breakdowns.
    """
    try:
        df = safe_load(file_name)

        for col in [timekeeper_column, hours_column]:
            if col not in df.columns:
                return {
                    "status": "error",
                    "message": f"Column '{col}' not found. Available: {list(df.columns)}",
                }

        grouped = df.groupby(timekeeper_column)
        result = {}
        for name, group in grouped:
            entry = {
                "total_hours": round(float(group[hours_column].sum()), 2),
                "average_hours_per_entry": round(
                    float(group[hours_column].mean()), 2
                ),
                "entry_count": int(len(group)),
                "min_hours": round(float(group[hours_column].min()), 2),
                "max_hours": round(float(group[hours_column].max()), 2),
            }
            if rate_column and rate_column in df.columns:
                entry["average_rate"] = round(float(group[rate_column].mean()), 2)
                entry["total_billed"] = round(
                    float((group[hours_column] * group[rate_column]).sum()), 2
                )
            result[str(name)] = entry

        tool_context.state["active_file"] = file_name
        tool_context.state["last_analysis_type"] = "timekeeper_analysis"
        _append_analysis_history(
            tool_context,
            "timekeeper_analysis",
            f"timekeepers={len(result)} top={list(result.keys())[:5]}",
        )

        return {
            "status": "success",
            "timekeeper_analysis": result,
            "total_timekeepers": len(result),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def find_duplicate_entries(file_name: str, columns: str, tool_context: ToolContext) -> dict:
    """Finds potential duplicate time entries based on specified columns.

    Identifies rows with identical values across the given columns, which may
    indicate duplicate billing entries requiring review.

    Args:
        file_name: The name of the file in the data directory.
        columns: Comma-separated column names to check for duplicates
                 (e.g., 'Date,Timekeeper,Hours,Description').

    Returns:
        dict: Duplicate entries found, grouped by their duplicate key values.
    """
    try:
        df = safe_load(file_name)
        cols = [c.strip() for c in columns.split(",")]

        missing = [c for c in cols if c not in df.columns]
        if missing:
            return {
                "status": "error",
                "message": f"Columns not found: {missing}. Available: {list(df.columns)}",
            }

        duplicates = df[df.duplicated(subset=cols, keep=False)]

        if duplicates.empty:
            tool_context.state["active_file"] = file_name
            tool_context.state["last_analysis_type"] = "duplicate_detection"
            _append_analysis_history(
                tool_context, "duplicate_detection", "No duplicates found",
            )
            return {
                "status": "success",
                "duplicate_count": 0,
                "message": "No duplicate entries found for the specified columns.",
            }

        dup_groups = []
        for _, group in duplicates.groupby(cols):
            dup_groups.append(
                {
                    "count": len(group),
                    "values": {c: str(group[c].iloc[0]) for c in cols},
                    "row_indices": group.index.tolist()[:20],
                }
            )

        tool_context.state["active_file"] = file_name
        tool_context.state["last_analysis_type"] = "duplicate_detection"
        _append_analysis_history(
            tool_context,
            "duplicate_detection",
            f"duplicates={len(duplicates)} groups={len(dup_groups)}",
        )

        total_groups = len(dup_groups)
        capped_groups = dup_groups[:50]
        result = {
            "status": "success",
            "duplicate_count": len(duplicates),
            "duplicate_groups": total_groups,
            "duplicates": capped_groups,
        }
        if total_groups > 50:
            result["note"] = (
                f"Results capped at 50 duplicate groups. "
                f"Full dataset contains {total_groups} groups."
            )
        else:
            for group in capped_groups:
                if len(group.get("row_indices", [])) < group.get("count", 0):
                    result["note"] = (
                        "Row indices within groups are capped at 20 entries. "
                        "Some groups may contain more rows than shown."
                    )
                    break

        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


def filter_time_entries(
    file_name: str, column: str, operator: str, value: str, tool_context: ToolContext,
) -> dict:
    """Filters time entries based on a condition on a specific column.

    Supports comparison operators for numeric and string filtering.

    Args:
        file_name: The name of the file in the data directory.
        column: The column name to filter on.
        operator: Comparison operator. One of: equals, not_equals, greater_than,
                  less_than, greater_equal, less_equal, contains, startswith,
                  endswith, between. For 'between', pass value as "low,high"
                  (comma-separated) to filter for low <= column_value <= high.
        value: The value to compare against (auto-cast to appropriate type).

    Returns:
        dict: Filtered results with matching rows (up to 100) and total count.
    """
    try:
        df = safe_load(file_name)
        if column not in df.columns:
            return {
                "status": "error",
                "message": f"Column '{column}' not found. Available: {list(df.columns)}",
            }

        typed_value: object = value
        if pd.api.types.is_numeric_dtype(df[column].dtype):
            try:
                typed_value = float(value)
            except ValueError:
                pass

        ops = {
            "equals": lambda s, v: s == v,
            "not_equals": lambda s, v: s != v,
            "greater_than": lambda s, v: s > v,
            "less_than": lambda s, v: s < v,
            "greater_equal": lambda s, v: s >= v,
            "less_equal": lambda s, v: s <= v,
            "contains": lambda s, v: s.astype(str).str.contains(
                str(v), case=False, na=False
            ),
            "startswith": lambda s, v: s.astype(str).str.startswith(
                str(v), na=False
            ),
            "endswith": lambda s, v: s.astype(str).str.endswith(
                str(v), na=False
            ),
        }

        if operator == "between":
            parts = str(value).split(",")
            if len(parts) != 2:
                return {
                    "status": "error",
                    "message": "Operator 'between' requires value as 'low,high' (comma-separated).",
                }
            try:
                low, high = float(parts[0].strip()), float(parts[1].strip())
            except ValueError:
                return {
                    "status": "error",
                    "message": "Operator 'between' requires numeric low and high values.",
                }
            mask = (df[column] >= low) & (df[column] <= high)
            filtered = df[mask]

            tool_context.state["active_file"] = file_name
            tool_context.state["last_analysis_type"] = "filter"
            _append_analysis_history(
                tool_context,
                "filter",
                f"between {column} [{low},{high}] matched={len(filtered)}/{len(df)}",
            )

            sample = filtered.head(100)

            columns_note = None
            if len(sample.columns) > 10:
                key_columns = {"Date", "TimekeeperFullName"}
                projected_cols = {column}
                projected_cols.update(c for c in key_columns if c in sample.columns)
                projected_cols = sorted(projected_cols)
                sample = sample[projected_cols]
                columns_note = (
                    f"Showing {len(projected_cols)} of {len(filtered.columns)} columns: "
                    f"{projected_cols}. Full row data available in the source file."
                )

            result = {
                "status": "success",
                "matching_rows": len(filtered),
                "total_rows": len(df),
                "percentage": round(len(filtered) / max(len(df), 1) * 100, 2),
                "data": sample.to_dict(orient="records"),
            }
            if columns_note:
                result["columns_shown"] = columns_note

            return result

        if operator not in ops:
            return {
                "status": "error",
                "message": f"Invalid operator '{operator}'. Valid: {list(ops.keys())}",
            }

        mask = ops[operator](df[column], typed_value)
        filtered = df[mask]

        tool_context.state["active_file"] = file_name
        tool_context.state["last_analysis_type"] = "filter"
        _append_analysis_history(
            tool_context,
            "filter",
            f"{column} {operator} {value} matched={len(filtered)}/{len(df)}",
        )

        sample = filtered.head(100)

        # Column projection: if wide dataset, return only key columns
        columns_note = None
        if len(sample.columns) > 10:
            key_columns = {"Date", "TimekeeperFullName"}
            projected_cols = {column}  # always include the filtered column
            projected_cols.update(c for c in key_columns if c in sample.columns)
            projected_cols = sorted(projected_cols)
            sample = sample[projected_cols]
            columns_note = (
                f"Showing {len(projected_cols)} of {len(filtered.columns)} columns: "
                f"{projected_cols}. Full row data available in the source file."
            )

        result = {
            "status": "success",
            "matching_rows": len(filtered),
            "total_rows": len(df),
            "percentage": round(len(filtered) / max(len(df), 1) * 100, 2),
            "data": sample.to_dict(orient="records"),
        }
        if columns_note:
            result["columns_shown"] = columns_note

        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


def calculate_totals(
    file_name: str,
    group_by_column: str,
    sum_column: str,
    tool_context: ToolContext,
    secondary_group_by: str = "",
) -> dict:
    """Calculates grouped totals by aggregating a numeric column.

    Groups the data by one column (or two columns when secondary_group_by is
    provided) and computes sum, average, and count for another, useful for
    total hours by task code, total amounts by timekeeper, etc.

    Args:
        file_name: The name of the file in the data directory.
        group_by_column: The column to group by (e.g., 'TaskCode', 'Timekeeper').
        sum_column: The numeric column to aggregate (e.g., 'Hours', 'Amount').
        secondary_group_by: Optional second column for two-level grouping.

    Returns:
        dict: Grouped totals sorted highest to lowest, with grand total.
    """
    try:
        df = safe_load(file_name)

        check_cols = [group_by_column, sum_column]
        if secondary_group_by:
            check_cols.append(secondary_group_by)
        for col in check_cols:
            if col not in df.columns:
                return {
                    "status": "error",
                    "message": f"Column '{col}' not found. Available: {list(df.columns)}",
                }

        group_cols = (
            [group_by_column, secondary_group_by]
            if secondary_group_by
            else group_by_column
        )

        grouped = df.groupby(group_cols)[sum_column].agg(
            ["sum", "mean", "count"]
        )
        grouped = grouped.sort_values("sum", ascending=False)
        grouped.columns = ["total", "average", "count"]

        result = {}
        for idx, row in grouped.iterrows():
            result[str(idx)] = {
                "total": round(float(row["total"]), 2),
                "average": round(float(row["average"]), 2),
                "count": int(row["count"]),
            }

        tool_context.state["active_file"] = file_name
        tool_context.state["last_analysis_type"] = "totals_calculation"
        grand = round(float(grouped["total"].sum()), 2)
        _append_analysis_history(
            tool_context,
            "totals_calculation",
            f"group_by={group_by_column} sum={sum_column} groups={len(result)} grand_total={grand}",
        )

        return {
            "status": "success",
            "grouped_totals": result,
            "grand_total": grand,
            "group_count": len(result),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def detect_billing_anomalies(
    file_name: str,
    hours_column: str,
    tool_context: ToolContext,
    rate_column: Optional[str] = None,
) -> dict:
    """Detects anomalies in billing patterns using IQR statistical analysis.

    Identifies entries with unusually high or low hours, zero-hour entries,
    and rate outliers that may warrant review for billing compliance.

    Args:
        file_name: The name of the file in the data directory.
        hours_column: The column name containing hours worked.
        rate_column: Optional column name containing hourly rates.

    Returns:
        dict: Detected anomalies by category with statistical thresholds.
    """
    try:
        df = safe_load(file_name)
        if hours_column not in df.columns:
            return {
                "status": "error",
                "message": f"Column '{hours_column}' not found. Available: {list(df.columns)}",
            }

        anomalies = []

        hours = df[hours_column].dropna()
        q1 = float(hours.quantile(0.25))
        q3 = float(hours.quantile(0.75))
        iqr = q3 - q1
        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr

        high_hours = df[df[hours_column] > upper_fence]
        if not high_hours.empty:
            anomalies.append(
                {
                    "type": "excessive_hours",
                    "description": f"Entries exceeding {round(upper_fence, 2)} hours (Q3 + 1.5*IQR)",
                    "threshold": round(upper_fence, 2),
                    "count": len(high_hours),
                    "entries": high_hours.head(20).to_dict(orient="records"),
                }
            )

        low_hours = df[(df[hours_column] < lower_fence) & (df[hours_column] > 0)]
        if not low_hours.empty:
            anomalies.append(
                {
                    "type": "unusually_low_hours",
                    "description": f"Entries below {round(lower_fence, 2)} hours (Q1 - 1.5*IQR)",
                    "threshold": round(lower_fence, 2),
                    "count": len(low_hours),
                    "entries": low_hours.head(20).to_dict(orient="records"),
                }
            )

        zero_hours = df[df[hours_column] == 0]
        if not zero_hours.empty:
            anomalies.append(
                {
                    "type": "zero_hour_entries",
                    "description": "Entries with exactly 0 hours billed",
                    "count": len(zero_hours),
                    "entries": zero_hours.head(20).to_dict(orient="records"),
                }
            )

        if rate_column and rate_column in df.columns:
            rates = df[rate_column].dropna()
            r_q1 = float(rates.quantile(0.25))
            r_q3 = float(rates.quantile(0.75))
            r_iqr = r_q3 - r_q1
            rate_outliers = df[
                (df[rate_column] > r_q3 + 1.5 * r_iqr)
                | (df[rate_column] < r_q1 - 1.5 * r_iqr)
            ]
            if not rate_outliers.empty:
                anomalies.append(
                    {
                        "type": "rate_outliers",
                        "description": "Entries with hourly rates outside the IQR fences",
                        "count": len(rate_outliers),
                        "entries": rate_outliers.head(20).to_dict(orient="records"),
                    }
                )

        tool_context.state["last_analysis_type"] = "billing_anomalies"
        total_anomaly_count = sum(a["count"] for a in anomalies)
        _append_analysis_history(
            tool_context,
            "billing_anomalies",
            f"total_anomalies={total_anomaly_count} categories={len(anomalies)} "
            f"upper_fence={round(upper_fence, 2)} lower_fence={round(lower_fence, 2)}",
        )

        return {
            "status": "success",
            "total_anomalies": total_anomaly_count,
            "anomaly_categories": len(anomalies),
            "anomalies": anomalies,
            "hours_statistics": {
                "q1": round(q1, 2),
                "q3": round(q3, 2),
                "iqr": round(iqr, 2),
                "upper_fence": round(upper_fence, 2),
                "lower_fence": round(lower_fence, 2),
            },
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def date_range_analysis(
    file_name: str, date_column: str, start_date: str, end_date: str, tool_context: ToolContext,
) -> dict:
    """Analyzes time entries within a specific date range.

    Filters entries between the start and end dates and provides summary
    statistics for the period, including daily entry counts.

    Args:
        file_name: The name of the file in the data directory.
        date_column: The column name containing dates.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.

    Returns:
        dict: Analysis of entries within the date range with daily breakdown.
    """
    try:
        df = safe_load(file_name)
        if date_column not in df.columns:
            return {
                "status": "error",
                "message": f"Column '{date_column}' not found. Available: {list(df.columns)}",
            }

        df[date_column] = pd.to_datetime(df[date_column], errors="coerce")
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        mask = (df[date_column] >= start) & (df[date_column] <= end)
        filtered = df[mask]

        if filtered.empty:
            return {
                "status": "success",
                "message": "No entries found in the specified date range.",
                "matching_rows": 0,
            }

        numeric_cols = filtered.select_dtypes(include=[np.number]).columns.tolist()
        summary: dict = {
            "status": "success",
            "matching_rows": len(filtered),
            "total_rows": len(df),
        }

        for col in numeric_cols:
            summary[f"{col}_total"] = round(float(filtered[col].sum()), 2)
            summary[f"{col}_average"] = round(float(filtered[col].mean()), 2)

        daily = filtered.groupby(filtered[date_column].dt.date).size()
        summary["entries_per_day"] = {str(k): int(v) for k, v in daily.items()}
        summary["active_days"] = len(daily)

        tool_context.state["last_analysis_type"] = "date_range_analysis"
        _append_analysis_history(
            tool_context,
            "date_range_analysis",
            f"range={start_date}..{end_date} matched={summary['matching_rows']}/{summary['total_rows']} active_days={summary.get('active_days', 0)}",
        )

        return summary
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cross_reference_entries(
    file_name: str, column1: str, column2: str, tool_context: ToolContext,
) -> dict:
    """Cross-references two columns to find relationships and patterns.

    Creates a pivot-style analysis showing how values in one column relate to
    values in another, useful for identifying which timekeepers work on which
    task codes, or which matters have the most billing hours.

    Args:
        file_name: The name of the file in the data directory.
        column1: The first column for cross-reference (row axis).
        column2: The second column for cross-reference (column axis).

    Returns:
        dict: Cross-reference counts showing the relationship between the two columns.
    """
    try:
        df = safe_load(file_name)
        for col in [column1, column2]:
            if col not in df.columns:
                return {
                    "status": "error",
                    "message": f"Column '{col}' not found. Available: {list(df.columns)}",
                }

        cross = pd.crosstab(df[column1], df[column2])

        result = {}
        for idx in cross.index:
            row_data = {}
            for col in cross.columns:
                val = int(cross.loc[idx, col])
                if val > 0:
                    row_data[str(col)] = val
            if row_data:
                result[str(idx)] = row_data

        tool_context.state["active_file"] = file_name
        tool_context.state["last_analysis_type"] = "cross_reference"
        _append_analysis_history(
            tool_context,
            "cross_reference",
            f"{column1} x {column2} unique_rows={len(cross.index)} unique_cols={len(cross.columns)}",
        )

        return {
            "status": "success",
            "cross_reference": result,
            f"{column1}_unique_values": len(cross.index),
            f"{column2}_unique_values": len(cross.columns),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def analyze_utilization_trends(
    file_name: str,
    tool_context: ToolContext,
    group_by: str = "TimekeeperFullName",
    metric: str = "Utilization",
) -> dict:
    """Analyzes utilization trends from time entry data grouped by a specified column.

    Computes mean, min, max, and standard deviation of a utilization metric per
    group, and identifies groups that are below or above target when a
    'Variance Against Utilization Target Hours' column is present.

    Args:
        file_name: The name of the file in the data directory.
        group_by: Column to group by (default: 'TimekeeperFullName').
        metric: Numeric column to analyze (default: 'Utilization').

    Returns:
        dict: Per-group utilization statistics and target performance breakdown.
    """
    try:
        df = safe_load(file_name)

        for col in [group_by, metric]:
            if col not in df.columns:
                return {
                    "status": "error",
                    "message": f"Column '{col}' not found. Available: {list(df.columns)}",
                }

        grouped = df.groupby(group_by)
        per_group = {}
        for name, group in grouped:
            entry = {
                "mean": round(float(group[metric].mean()), 2),
                "min": round(float(group[metric].min()), 2),
                "max": round(float(group[metric].max()), 2),
                "std": round(float(group[metric].std()), 2)
                if len(group) > 1
                else 0.0,
            }
            per_group[str(name)] = entry

        variance_col = "Variance Against Utilization Target Hours"
        below_target = []
        above_target = []

        if variance_col in df.columns:
            for name, group in grouped:
                avg_variance = round(float(group[variance_col].mean()), 2)
                per_group[str(name)]["avg_variance"] = avg_variance
                if avg_variance < 0:
                    below_target.append(str(name))
                else:
                    above_target.append(str(name))

        tool_context.state["active_file"] = file_name
        tool_context.state["last_analysis_type"] = "utilization_trends"
        _append_analysis_history(
            tool_context,
            "utilization_trends",
            f"group_by={group_by} metric={metric} groups={len(per_group)} below_target={len(below_target)} above_target={len(above_target)}",
        )

        result: dict = {
            "status": "success",
            "group_count": len(per_group),
            "per_group_stats": per_group,
        }
        if variance_col in df.columns:
            result["below_target"] = {
                "count": len(below_target),
                "names": below_target,
            }
            result["above_target"] = {
                "count": len(above_target),
                "names": above_target,
            }

        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}
