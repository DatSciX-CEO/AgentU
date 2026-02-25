"""Tests for ediscovery_agents.tools.ingestion (list_uploaded_files, profile_file)."""

import pytest

from ediscovery_agents.tools.ingestion import list_uploaded_files, profile_file


# ---------------------------------------------------------------------------
# list_uploaded_files
# ---------------------------------------------------------------------------


class TestListUploadedFiles:
    def test_returns_files(self, patch_data_dir, sample_csv, tool_context):
        result = list_uploaded_files(tool_context)
        assert result["status"] == "success"
        assert "test_data.csv" in result["files"]
        assert result["file_count"] >= 1
        assert "data_directory" in result
        # state side-effect
        assert "test_data.csv" in tool_context.state["available_files"]

    def test_empty_directory(self, patch_data_dir, tool_context):
        result = list_uploaded_files(tool_context)
        assert result["status"] == "success"
        assert result["files"] == []
        assert "message" in result

    def test_filters_unsupported_extensions(
        self, patch_data_dir, tmp_data_dir, tool_context
    ):
        (tmp_data_dir / "readme.txt").write_text("hi")
        (tmp_data_dir / "good.csv").write_text("a\n1\n")
        result = list_uploaded_files(tool_context)
        assert "readme.txt" not in result["files"]
        assert "good.csv" in result["files"]


# ---------------------------------------------------------------------------
# profile_file
# ---------------------------------------------------------------------------


class TestProfileFile:
    def test_happy_path(self, patch_data_dir, sample_csv, tool_context):
        result = profile_file(sample_csv, tool_context)
        assert result["status"] == "success"
        assert result["row_count"] == 5
        assert "Date" in result["columns"]
        assert result["column_count"] == len(result["columns"])
        # column_details structure
        for col_name, detail in result["column_details"].items():
            assert "dtype" in detail
            assert "null_count" in detail
            assert "non_null_count" in detail
            assert "unique_count" in detail
            assert "sample_values" in detail

    def test_state_keys_written(self, patch_data_dir, sample_csv, tool_context):
        profile_file(sample_csv, tool_context)
        assert tool_context.state["active_file"] == sample_csv
        assert isinstance(tool_context.state["active_schema"], list)
        assert "Date" in tool_context.state["active_schema"]
        assert isinstance(tool_context.state["active_column_types"], dict)

    def test_missing_file_returns_error(self, patch_data_dir, tool_context):
        result = profile_file("no_such_file.csv", tool_context)
        assert result["status"] == "error"
        assert "message" in result

    def test_memory_usage_present(self, patch_data_dir, sample_csv, tool_context):
        result = profile_file(sample_csv, tool_context)
        assert "memory_usage_mb" in result
        assert isinstance(result["memory_usage_mb"], float)
