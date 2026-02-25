import os

from google.adk.tools.tool_context import ToolContext

from .loader import DATA_DIR, safe_load


def list_uploaded_files(tool_context: ToolContext) -> dict:
    """Lists all uploaded data files available for analysis in the data directory.

    Scans the data directory for CSV, Excel, and Parquet files that can be
    profiled and analyzed by the system.

    Returns:
        dict: A dictionary with status and a list of available file names.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    files = [
        f
        for f in os.listdir(DATA_DIR)
        if f.endswith((".csv", ".xlsx", ".xls", ".parquet"))
    ]

    if not files:
        return {
            "status": "success",
            "files": [],
            "message": (
                "No data files found. Please place CSV, Excel, or Parquet files "
                f"in the data directory: {DATA_DIR}"
            ),
        }

    tool_context.state["available_files"] = files

    return {
        "status": "success",
        "files": files,
        "file_count": len(files),
        "data_directory": DATA_DIR,
    }


def profile_file(file_name: str, tool_context: ToolContext) -> dict:
    """Reads and profiles an uploaded eDiscovery time entry file.

    Extracts column names, data types, row count, sample values, and null counts
    to understand the dataset structure. Supports CSV, Excel, and Parquet formats.

    Args:
        file_name: The name of the file in the data directory to profile
                   (e.g., 'time_entries.csv').

    Returns:
        dict: Schema info including columns, data types, row count, and sample data.
    """
    try:
        df = safe_load(file_name)
        file_path = os.path.join(DATA_DIR, file_name)

        column_details = {}
        for col in df.columns:
            column_details[col] = {
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isnull().sum()),
                "non_null_count": int(df[col].notnull().sum()),
                "unique_count": int(df[col].nunique()),
                "sample_values": [
                    str(v) for v in df[col].dropna().head(3).tolist()
                ],
            }

        tool_context.state["active_file"] = file_name
        tool_context.state["active_schema"] = list(df.columns)
        tool_context.state["active_column_types"] = {
            col: str(df[col].dtype) for col in df.columns
        }

        return {
            "status": "success",
            "file_name": file_name,
            "file_path": file_path,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "column_details": column_details,
            "memory_usage_mb": round(
                df.memory_usage(deep=True).sum() / 1024 / 1024, 2
            ),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
