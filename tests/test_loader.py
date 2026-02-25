"""Tests for ediscovery_agents.tools.loader.safe_load."""

import pandas as pd
import pytest

from ediscovery_agents.tools.loader import safe_load


class TestSafeLoadHappyPath:
    """Verify that safe_load returns a DataFrame for supported formats."""

    def test_load_csv(self, patch_data_dir, sample_csv):
        df = safe_load(sample_csv)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5
        assert "Date" in df.columns

    def test_load_parquet(self, patch_data_dir, tmp_data_dir):
        df_orig = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        df_orig.to_parquet(tmp_data_dir / "data.parquet", index=False)
        df = safe_load("data.parquet")
        assert list(df.columns) == ["a", "b"]
        assert len(df) == 2

    def test_load_excel(self, patch_data_dir, tmp_data_dir):
        df_orig = pd.DataFrame({"x": [10], "y": [20]})
        df_orig.to_excel(tmp_data_dir / "data.xlsx", index=False)
        df = safe_load("data.xlsx")
        assert list(df.columns) == ["x", "y"]

    def test_column_names_stripped(self, patch_data_dir, tmp_data_dir):
        """Whitespace in column headers should be stripped."""
        path = tmp_data_dir / "spaces.csv"
        path.write_text(" Col A , Col B \n1,2\n")
        df = safe_load("spaces.csv")
        assert list(df.columns) == ["Col A", "Col B"]


class TestSafeLoadErrors:
    """Verify that safe_load raises on bad inputs."""

    def test_path_traversal_rejected(self, patch_data_dir):
        with pytest.raises(ValueError, match="not a path"):
            safe_load("../evil.csv")

    def test_path_traversal_subdir(self, patch_data_dir):
        with pytest.raises(ValueError, match="not a path"):
            safe_load("subdir/evil.csv")

    def test_unsupported_extension(self, patch_data_dir, tmp_data_dir):
        (tmp_data_dir / "notes.txt").write_text("hello")
        with pytest.raises(ValueError, match="Unsupported file format"):
            safe_load("notes.txt")

    def test_missing_file(self, patch_data_dir):
        with pytest.raises(FileNotFoundError, match="File not found"):
            safe_load("nonexistent.csv")
