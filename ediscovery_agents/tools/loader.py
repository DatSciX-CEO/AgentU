"""Shared data-loading utility with path traversal protection.

All tool modules import from here instead of duplicating loader logic.
"""

import os

import pandas as pd

_PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(_PACKAGE_DIR, "data")


def safe_load(file_name: str) -> pd.DataFrame:
    """Load a DataFrame from the data directory after validating the path.

    Raises ValueError on unsupported formats or path traversal attempts.
    """
    basename = os.path.basename(file_name)
    if basename != file_name:
        raise ValueError(
            f"Invalid file name '{file_name}'. "
            "Provide just the filename, not a path."
        )

    file_path = os.path.join(DATA_DIR, basename)
    resolved = os.path.realpath(file_path)
    if not resolved.startswith(os.path.realpath(DATA_DIR)):
        raise ValueError("Access denied: path resolves outside the data directory.")

    if not os.path.exists(resolved):
        raise FileNotFoundError(
            f"File not found: {basename}. Check the data directory: {DATA_DIR}"
        )

    if resolved.endswith(".parquet"):
        df = pd.read_parquet(resolved)
    elif resolved.endswith(".csv"):
        df = pd.read_csv(resolved)
    elif resolved.endswith((".xlsx", ".xls")):
        df = pd.read_excel(resolved)
    else:
        raise ValueError(f"Unsupported file format: {basename}")

    # Strip leading/trailing whitespace from column names so that tools can
    # match columns reliably regardless of extra spaces in the source file.
    df.columns = df.columns.str.strip()

    return df
