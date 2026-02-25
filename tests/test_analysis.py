"""Tests for ediscovery_agents.tools.analysis — all 9 analysis tools."""

import pandas as pd
import pytest

from ediscovery_agents.tools.analysis import (
    get_summary_statistics,
    analyze_by_timekeeper,
    find_duplicate_entries,
    filter_time_entries,
    calculate_totals,
    detect_billing_anomalies,
    date_range_analysis,
    cross_reference_entries,
    analyze_utilization_trends,
)


# ===================================================================
# Helpers — small DataFrames written to the temp data dir on demand
# ===================================================================


@pytest.fixture
def anomaly_csv(tmp_data_dir):
    """CSV with a clear outlier (50h) and a zero-hour entry for anomaly tests."""
    df = pd.DataFrame(
        {
            "Date": ["1/6/2025"] * 6,
            "TimekeeperFullName": ["A", "B", "C", "D", "E", "F"],
            "Hours": [8.0, 7.5, 7.0, 6.5, 0.0, 50.0],
            "Rate": [100, 100, 100, 100, 100, 100],
        }
    )
    df.to_csv(tmp_data_dir / "anomaly.csv", index=False)
    return "anomaly.csv"


@pytest.fixture
def no_anomaly_csv(tmp_data_dir):
    """CSV where all values are within a tight range — no anomalies expected."""
    df = pd.DataFrame(
        {
            "Hours": [7.0, 7.5, 7.0, 7.5, 7.0],
        }
    )
    df.to_csv(tmp_data_dir / "no_anomaly.csv", index=False)
    return "no_anomaly.csv"


@pytest.fixture
def dup_csv(tmp_data_dir):
    """CSV with intentional duplicates for find_duplicate_entries tests."""
    df = pd.DataFrame(
        {
            "Date": ["1/6/2025", "1/6/2025", "1/7/2025", "1/6/2025"],
            "Name": ["Alice", "Alice", "Bob", "Alice"],
            "Hours": [8.0, 8.0, 6.0, 8.0],
        }
    )
    df.to_csv(tmp_data_dir / "dup.csv", index=False)
    return "dup.csv"


@pytest.fixture
def many_dup_groups_csv(tmp_data_dir):
    """CSV with > 50 duplicate groups to test the cap/note logic."""
    rows = []
    for i in range(60):
        rows.append({"Key": f"group_{i}", "Val": 1})
        rows.append({"Key": f"group_{i}", "Val": 1})
    df = pd.DataFrame(rows)
    df.to_csv(tmp_data_dir / "many_dup.csv", index=False)
    return "many_dup.csv"


@pytest.fixture
def utilization_csv(tmp_data_dir):
    """CSV with Utilization and Variance columns for utilization_trends tests."""
    df = pd.DataFrame(
        {
            "TimekeeperFullName": ["Alice", "Alice", "Bob", "Bob"],
            "Utilization": [1.0, 0.9, 0.5, 0.6],
            "Variance Against Utilization Target Hours": [1.2, 0.7, -0.5, -0.3],
        }
    )
    df.to_csv(tmp_data_dir / "util.csv", index=False)
    return "util.csv"


@pytest.fixture
def utilization_no_variance_csv(tmp_data_dir):
    """CSV with Utilization but NO Variance column."""
    df = pd.DataFrame(
        {
            "TimekeeperFullName": ["Alice", "Bob"],
            "Utilization": [1.0, 0.6],
        }
    )
    df.to_csv(tmp_data_dir / "util_novar.csv", index=False)
    return "util_novar.csv"


# ===================================================================
# get_summary_statistics
# ===================================================================


class TestGetSummaryStatistics:
    def test_success(self, patch_data_dir, sample_csv, tool_context):
        result = get_summary_statistics(sample_csv, tool_context)
        assert result["status"] == "success"
        assert result["total_rows"] == 5
        assert result["total_columns"] > 0
        assert "columns" in result

    def test_numeric_statistics(self, patch_data_dir, sample_csv, tool_context):
        result = get_summary_statistics(sample_csv, tool_context)
        assert "numeric_statistics" in result
        stats = result["numeric_statistics"]
        assert "Chargeable Hours" in stats
        for key in ("mean", "median", "min", "max", "sum", "std_dev"):
            assert key in stats["Chargeable Hours"]

    def test_date_ranges_detected(self, patch_data_dir, sample_csv, tool_context):
        result = get_summary_statistics(sample_csv, tool_context)
        assert "date_ranges" in result
        assert "Date" in result["date_ranges"]

    def test_state_written(self, patch_data_dir, sample_csv, tool_context):
        get_summary_statistics(sample_csv, tool_context)
        assert tool_context.state["active_file"] == sample_csv
        assert tool_context.state["last_analysis_type"] == "summary_statistics"

    def test_missing_file_error(self, patch_data_dir, tool_context):
        result = get_summary_statistics("nope.csv", tool_context)
        assert result["status"] == "error"


# ===================================================================
# analyze_by_timekeeper
# ===================================================================


class TestAnalyzeByTimekeeper:
    def test_success(self, patch_data_dir, sample_csv, tool_context):
        result = analyze_by_timekeeper(
            sample_csv, "TimekeeperFullName", "Chargeable Hours", tool_context
        )
        assert result["status"] == "success"
        assert result["total_timekeepers"] == 2
        assert "Alice Adams" in result["timekeeper_analysis"]
        entry = result["timekeeper_analysis"]["Alice Adams"]
        for key in ("total_hours", "average_hours_per_entry", "entry_count", "min_hours", "max_hours"):
            assert key in entry

    def test_with_rate_column(self, patch_data_dir, tmp_data_dir, tool_context):
        df = pd.DataFrame(
            {
                "Name": ["A", "A", "B"],
                "Hours": [8.0, 7.0, 6.0],
                "Rate": [100, 100, 150],
            }
        )
        df.to_csv(tmp_data_dir / "rated.csv", index=False)
        result = analyze_by_timekeeper(
            "rated.csv", "Name", "Hours", tool_context, rate_column="Rate"
        )
        assert result["status"] == "success"
        assert "average_rate" in result["timekeeper_analysis"]["A"]
        assert "total_billed" in result["timekeeper_analysis"]["A"]

    def test_missing_column_error(self, patch_data_dir, sample_csv, tool_context):
        result = analyze_by_timekeeper(
            sample_csv, "NonExistent", "Chargeable Hours", tool_context
        )
        assert result["status"] == "error"
        assert "NonExistent" in result["message"]

    def test_state_written(self, patch_data_dir, sample_csv, tool_context):
        analyze_by_timekeeper(
            sample_csv, "TimekeeperFullName", "Chargeable Hours", tool_context
        )
        assert tool_context.state["active_file"] == sample_csv
        assert tool_context.state["last_analysis_type"] == "timekeeper_analysis"


# ===================================================================
# find_duplicate_entries
# ===================================================================


class TestFindDuplicateEntries:
    def test_duplicates_found(self, patch_data_dir, dup_csv, tool_context):
        result = find_duplicate_entries(dup_csv, "Date,Name,Hours", tool_context)
        assert result["status"] == "success"
        assert result["duplicate_count"] == 3  # three rows share the same key
        assert result["duplicate_groups"] >= 1

    def test_no_duplicates(self, patch_data_dir, sample_csv, tool_context):
        # sample_csv rows are unique on Date+TimekeeperFullName
        result = find_duplicate_entries(
            sample_csv, "Date,TimekeeperFullName", tool_context
        )
        assert result["status"] == "success"
        assert result["duplicate_count"] == 0

    def test_missing_column_error(self, patch_data_dir, sample_csv, tool_context):
        result = find_duplicate_entries(sample_csv, "FakeCol", tool_context)
        assert result["status"] == "error"

    def test_note_on_group_cap(self, patch_data_dir, many_dup_groups_csv, tool_context):
        result = find_duplicate_entries(many_dup_groups_csv, "Key,Val", tool_context)
        assert result["status"] == "success"
        assert "note" in result
        assert len(result["duplicates"]) <= 50

    def test_state_written(self, patch_data_dir, dup_csv, tool_context):
        find_duplicate_entries(dup_csv, "Date,Name,Hours", tool_context)
        assert tool_context.state["active_file"] == dup_csv
        assert tool_context.state["last_analysis_type"] == "duplicate_detection"

    def test_state_written_no_dups(self, patch_data_dir, sample_csv, tool_context):
        find_duplicate_entries(sample_csv, "Date,TimekeeperFullName", tool_context)
        assert tool_context.state["active_file"] == sample_csv
        assert tool_context.state["last_analysis_type"] == "duplicate_detection"

    def test_note_on_row_indices_cap(self, patch_data_dir, tmp_data_dir, tool_context):
        """When a single duplicate group has > 20 rows, row_indices is capped."""
        rows = [{"Key": "same", "Val": 1}] * 25
        df = pd.DataFrame(rows)
        df.to_csv(tmp_data_dir / "big_group.csv", index=False)
        result = find_duplicate_entries("big_group.csv", "Key,Val", tool_context)
        assert result["status"] == "success"
        group = result["duplicates"][0]
        assert len(group["row_indices"]) <= 20
        assert "note" in result


# ===================================================================
# filter_time_entries
# ===================================================================


class TestFilterTimeEntries:
    # --- standard operators ---

    def test_equals(self, patch_data_dir, sample_csv, tool_context):
        result = filter_time_entries(
            sample_csv, "TimekeeperFullName", "equals", "Alice Adams", tool_context
        )
        assert result["status"] == "success"
        assert result["matching_rows"] == 3

    def test_not_equals(self, patch_data_dir, sample_csv, tool_context):
        result = filter_time_entries(
            sample_csv, "TimekeeperFullName", "not_equals", "Alice Adams", tool_context
        )
        assert result["status"] == "success"
        assert result["matching_rows"] == 2

    def test_greater_than(self, patch_data_dir, sample_csv, tool_context):
        result = filter_time_entries(
            sample_csv, "Chargeable Hours", "greater_than", "8", tool_context
        )
        assert result["status"] == "success"
        assert result["matching_rows"] >= 1

    def test_less_than(self, patch_data_dir, sample_csv, tool_context):
        result = filter_time_entries(
            sample_csv, "Chargeable Hours", "less_than", "7", tool_context
        )
        assert result["status"] == "success"
        assert result["matching_rows"] >= 1

    def test_greater_equal(self, patch_data_dir, sample_csv, tool_context):
        result = filter_time_entries(
            sample_csv, "Chargeable Hours", "greater_equal", "8", tool_context
        )
        assert result["status"] == "success"
        assert result["matching_rows"] >= 2

    def test_less_equal(self, patch_data_dir, sample_csv, tool_context):
        result = filter_time_entries(
            sample_csv, "Chargeable Hours", "less_equal", "6.5", tool_context
        )
        assert result["status"] == "success"
        assert result["matching_rows"] >= 1

    def test_contains(self, patch_data_dir, sample_csv, tool_context):
        result = filter_time_entries(
            sample_csv, "TimekeeperFullName", "contains", "alice", tool_context
        )
        assert result["status"] == "success"
        assert result["matching_rows"] == 3  # case-insensitive

    def test_startswith(self, patch_data_dir, sample_csv, tool_context):
        result = filter_time_entries(
            sample_csv, "TimekeeperFullName", "startswith", "Bob", tool_context
        )
        assert result["status"] == "success"
        assert result["matching_rows"] == 2

    def test_endswith(self, patch_data_dir, sample_csv, tool_context):
        result = filter_time_entries(
            sample_csv, "TimekeeperFullName", "endswith", "Adams", tool_context
        )
        assert result["status"] == "success"
        assert result["matching_rows"] == 3

    # --- between ---

    def test_between(self, patch_data_dir, sample_csv, tool_context):
        result = filter_time_entries(
            sample_csv, "Chargeable Hours", "between", "7,8", tool_context
        )
        assert result["status"] == "success"
        assert result["matching_rows"] >= 1
        for rec in result["data"]:
            assert 7.0 <= rec["Chargeable Hours"] <= 8.0

    def test_between_bad_format(self, patch_data_dir, sample_csv, tool_context):
        result = filter_time_entries(
            sample_csv, "Chargeable Hours", "between", "7", tool_context
        )
        assert result["status"] == "error"
        assert "low,high" in result["message"]

    def test_between_non_numeric(self, patch_data_dir, sample_csv, tool_context):
        result = filter_time_entries(
            sample_csv, "Chargeable Hours", "between", "a,b", tool_context
        )
        assert result["status"] == "error"
        assert "numeric" in result["message"]

    # --- error paths ---

    def test_invalid_operator(self, patch_data_dir, sample_csv, tool_context):
        result = filter_time_entries(
            sample_csv, "Chargeable Hours", "like", "8", tool_context
        )
        assert result["status"] == "error"
        assert "Invalid operator" in result["message"]

    def test_missing_column(self, patch_data_dir, sample_csv, tool_context):
        result = filter_time_entries(
            sample_csv, "NoSuchCol", "equals", "x", tool_context
        )
        assert result["status"] == "error"

    # --- column projection / columns_shown ---

    def test_wide_dataset_columns_shown(self, patch_data_dir, wide_csv, tool_context):
        result = filter_time_entries(
            wide_csv, "Chargeable Hours", "greater_than", "0", tool_context
        )
        assert result["status"] == "success"
        assert "columns_shown" in result

    def test_between_wide_dataset_columns_shown(
        self, patch_data_dir, wide_csv, tool_context
    ):
        result = filter_time_entries(
            wide_csv, "Chargeable Hours", "between", "1,5", tool_context
        )
        assert result["status"] == "success"
        assert "columns_shown" in result

    # --- state ---

    def test_state_written(self, patch_data_dir, sample_csv, tool_context):
        filter_time_entries(
            sample_csv, "Chargeable Hours", "equals", "8", tool_context
        )
        assert tool_context.state["active_file"] == sample_csv
        assert tool_context.state["last_analysis_type"] == "filter"

    def test_percentage_key(self, patch_data_dir, sample_csv, tool_context):
        result = filter_time_entries(
            sample_csv, "Chargeable Hours", "equals", "8", tool_context
        )
        assert "percentage" in result


# ===================================================================
# calculate_totals
# ===================================================================


class TestCalculateTotals:
    def test_single_group_by(self, patch_data_dir, sample_csv, tool_context):
        result = calculate_totals(
            sample_csv, "TimekeeperFullName", "Chargeable Hours", tool_context
        )
        assert result["status"] == "success"
        assert result["group_count"] == 2
        assert "grand_total" in result
        for entry in result["grouped_totals"].values():
            assert "total" in entry
            assert "average" in entry
            assert "count" in entry

    def test_secondary_group_by(self, patch_data_dir, sample_csv, tool_context):
        result = calculate_totals(
            sample_csv,
            "TimekeeperFullName",
            "Chargeable Hours",
            tool_context,
            secondary_group_by="CountryCode_UKG",
        )
        assert result["status"] == "success"
        assert result["group_count"] >= 2

    def test_missing_column_error(self, patch_data_dir, sample_csv, tool_context):
        result = calculate_totals(
            sample_csv, "Fake", "Chargeable Hours", tool_context
        )
        assert result["status"] == "error"

    def test_missing_secondary_column_error(
        self, patch_data_dir, sample_csv, tool_context
    ):
        result = calculate_totals(
            sample_csv,
            "TimekeeperFullName",
            "Chargeable Hours",
            tool_context,
            secondary_group_by="Fake",
        )
        assert result["status"] == "error"

    def test_state_written(self, patch_data_dir, sample_csv, tool_context):
        calculate_totals(
            sample_csv, "TimekeeperFullName", "Chargeable Hours", tool_context
        )
        assert tool_context.state["active_file"] == sample_csv
        assert tool_context.state["last_analysis_type"] == "totals_calculation"


# ===================================================================
# detect_billing_anomalies
# ===================================================================


class TestDetectBillingAnomalies:
    def test_with_anomalies(self, patch_data_dir, anomaly_csv, tool_context):
        result = detect_billing_anomalies(anomaly_csv, "Hours", tool_context)
        assert result["status"] == "success"
        assert result["total_anomalies"] > 0
        types = {a["type"] for a in result["anomalies"]}
        assert "excessive_hours" in types or "zero_hour_entries" in types
        # Verify IQR stats present
        for key in ("q1", "q3", "iqr", "upper_fence", "lower_fence"):
            assert key in result["hours_statistics"]

    def test_zero_hour_detected(self, patch_data_dir, anomaly_csv, tool_context):
        result = detect_billing_anomalies(anomaly_csv, "Hours", tool_context)
        types = {a["type"] for a in result["anomalies"]}
        assert "zero_hour_entries" in types

    def test_no_anomalies(self, patch_data_dir, no_anomaly_csv, tool_context):
        result = detect_billing_anomalies(no_anomaly_csv, "Hours", tool_context)
        assert result["status"] == "success"
        assert result["total_anomalies"] == 0

    def test_with_rate_column(self, patch_data_dir, tmp_data_dir, tool_context):
        df = pd.DataFrame(
            {
                "Hours": [8, 7, 7.5, 7, 7.5],
                "Rate": [100, 100, 100, 100, 500],  # 500 is an outlier
            }
        )
        df.to_csv(tmp_data_dir / "rate_outlier.csv", index=False)
        result = detect_billing_anomalies(
            "rate_outlier.csv", "Hours", tool_context, rate_column="Rate"
        )
        assert result["status"] == "success"
        types = {a["type"] for a in result["anomalies"]}
        assert "rate_outliers" in types

    def test_missing_column_error(self, patch_data_dir, sample_csv, tool_context):
        result = detect_billing_anomalies(sample_csv, "FakeHours", tool_context)
        assert result["status"] == "error"

    def test_state_written(self, patch_data_dir, anomaly_csv, tool_context):
        detect_billing_anomalies(anomaly_csv, "Hours", tool_context)
        assert tool_context.state["last_analysis_type"] == "billing_anomalies"


# ===================================================================
# date_range_analysis
# ===================================================================


class TestDateRangeAnalysis:
    def test_success(self, patch_data_dir, sample_csv, tool_context):
        result = date_range_analysis(
            sample_csv, "Date", "2025-01-06", "2025-01-07", tool_context
        )
        assert result["status"] == "success"
        assert result["matching_rows"] == 4
        assert "entries_per_day" in result
        assert "active_days" in result

    def test_no_matches(self, patch_data_dir, sample_csv, tool_context):
        result = date_range_analysis(
            sample_csv, "Date", "2024-01-01", "2024-01-02", tool_context
        )
        assert result["status"] == "success"
        assert result["matching_rows"] == 0

    def test_numeric_aggregates(self, patch_data_dir, sample_csv, tool_context):
        result = date_range_analysis(
            sample_csv, "Date", "2025-01-06", "2025-01-08", tool_context
        )
        assert result["status"] == "success"
        # At least one numeric total key should exist
        assert any(k.endswith("_total") for k in result)

    def test_missing_column_error(self, patch_data_dir, sample_csv, tool_context):
        result = date_range_analysis(
            sample_csv, "FakeDate", "2025-01-06", "2025-01-07", tool_context
        )
        assert result["status"] == "error"

    def test_state_written(self, patch_data_dir, sample_csv, tool_context):
        date_range_analysis(
            sample_csv, "Date", "2025-01-06", "2025-01-07", tool_context
        )
        assert tool_context.state["last_analysis_type"] == "date_range_analysis"


# ===================================================================
# cross_reference_entries
# ===================================================================


class TestCrossReferenceEntries:
    def test_success(self, patch_data_dir, sample_csv, tool_context):
        result = cross_reference_entries(
            sample_csv, "TimekeeperFullName", "CountryCode_UKG", tool_context
        )
        assert result["status"] == "success"
        assert "cross_reference" in result
        assert "Alice Adams" in result["cross_reference"]
        assert result["TimekeeperFullName_unique_values"] == 2
        assert result["CountryCode_UKG_unique_values"] == 2

    def test_missing_column_error(self, patch_data_dir, sample_csv, tool_context):
        result = cross_reference_entries(
            sample_csv, "FakeCol", "CountryCode_UKG", tool_context
        )
        assert result["status"] == "error"

    def test_state_written(self, patch_data_dir, sample_csv, tool_context):
        cross_reference_entries(
            sample_csv, "TimekeeperFullName", "CountryCode_UKG", tool_context
        )
        assert tool_context.state["active_file"] == sample_csv
        assert tool_context.state["last_analysis_type"] == "cross_reference"


# ===================================================================
# analyze_utilization_trends
# ===================================================================


class TestAnalyzeUtilizationTrends:
    def test_with_variance_column(
        self, patch_data_dir, utilization_csv, tool_context
    ):
        result = analyze_utilization_trends(utilization_csv, tool_context)
        assert result["status"] == "success"
        assert result["group_count"] == 2
        # below / above target splits
        assert "below_target" in result
        assert "above_target" in result
        assert "Bob" in result["below_target"]["names"]
        assert "Alice" in result["above_target"]["names"]
        # per-group stats
        for stats in result["per_group_stats"].values():
            for key in ("mean", "min", "max", "std"):
                assert key in stats
            assert "avg_variance" in stats

    def test_without_variance_column(
        self, patch_data_dir, utilization_no_variance_csv, tool_context
    ):
        result = analyze_utilization_trends(
            utilization_no_variance_csv, tool_context
        )
        assert result["status"] == "success"
        assert "below_target" not in result
        assert "above_target" not in result

    def test_custom_group_by(self, patch_data_dir, tmp_data_dir, tool_context):
        df = pd.DataFrame(
            {
                "Department": ["Eng", "Eng", "Sales"],
                "Score": [80, 90, 70],
            }
        )
        df.to_csv(tmp_data_dir / "dept.csv", index=False)
        result = analyze_utilization_trends(
            "dept.csv", tool_context, group_by="Department", metric="Score"
        )
        assert result["status"] == "success"
        assert result["group_count"] == 2

    def test_missing_group_column_error(
        self, patch_data_dir, utilization_csv, tool_context
    ):
        result = analyze_utilization_trends(
            utilization_csv, tool_context, group_by="FakeCol"
        )
        assert result["status"] == "error"

    def test_missing_metric_column_error(
        self, patch_data_dir, utilization_csv, tool_context
    ):
        result = analyze_utilization_trends(
            utilization_csv, tool_context, metric="FakeMetric"
        )
        assert result["status"] == "error"

    def test_state_written(self, patch_data_dir, utilization_csv, tool_context):
        analyze_utilization_trends(utilization_csv, tool_context)
        assert tool_context.state["active_file"] == utilization_csv
        assert tool_context.state["last_analysis_type"] == "utilization_trends"

    def test_std_zero_for_single_entry_group(
        self, patch_data_dir, tmp_data_dir, tool_context
    ):
        df = pd.DataFrame(
            {
                "TimekeeperFullName": ["Solo"],
                "Utilization": [0.85],
            }
        )
        df.to_csv(tmp_data_dir / "solo.csv", index=False)
        result = analyze_utilization_trends("solo.csv", tool_context)
        assert result["status"] == "success"
        assert result["per_group_stats"]["Solo"]["std"] == 0.0
