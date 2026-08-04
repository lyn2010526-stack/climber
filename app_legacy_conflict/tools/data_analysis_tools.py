"""Data analysis tools for processing, analyzing, and visualizing structured data.

Provides tools for loading, cleaning, transforming, and analyzing data in various
formats (CSV, JSON, Excel, Parquet). Includes statistical analysis, aggregation,
and data profiling capabilities.
"""

from __future__ import annotations

import json
import os
import statistics
from typing import Any

import structlog

from app.tools import tool

logger = structlog.get_logger()


def _load_pandas():
    """Lazy-load pandas to avoid import errors if not installed."""
    try:
        import pandas as pd
        return pd
    except ImportError:
        return None


def _load_numpy():
    """Lazy-load numpy."""
    try:
        import numpy as np
        return np
    except ImportError:
        return None


@tool(description="Load a data file (CSV, JSON, Excel) and return basic info: row count, column names, data types, and a sample of the first rows.")
async def load_data(
    file_path: str,
    file_type: str = "auto",
    sheet_name: str = "",
    max_rows: int = 10000,
) -> str:
    """Load and inspect a data file.

    Args:
        file_path: Path to the data file.
        file_type: File type - csv, json, xlsx, parquet, auto (detect from extension).
        sheet_name: For Excel files, specific sheet name.
        max_rows: Maximum rows to load.
    """
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas is not installed. Install with: pip install pandas openpyxl"

    try:
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        if file_type == "auto":
            ext = os.path.splitext(file_path)[1].lower()
            type_map = {".csv": "csv", ".json": "json", ".xlsx": "xlsx", ".xls": "xlsx", ".parquet": "parquet", ".tsv": "tsv"}
            file_type = type_map.get(ext, "csv")

        if file_type == "csv":
            df = pd.read_csv(file_path, nrows=max_rows)
        elif file_type == "tsv":
            df = pd.read_csv(file_path, sep="\t", nrows=max_rows)
        elif file_type == "json":
            df = pd.read_json(file_path)
        elif file_type == "xlsx":
            df = pd.read_excel(file_path, sheet_name=sheet_name or 0, nrows=max_rows)
        elif file_type == "parquet":
            df = pd.read_parquet(file_path)
        else:
            return f"Error: Unsupported file type: {file_type}"

        # Build summary
        lines = [
            f"Dataset: {file_path}",
            f"Shape: {df.shape[0]} rows x {df.shape[1]} columns",
            f"",
            f"Column Types:",
        ]
        for col in df.columns:
            dtype = str(df[col].dtype)
            non_null = df[col].notna().sum()
            lines.append(f"  {col}: {dtype} ({non_null} non-null, {df.shape[0] - non_null} missing)")

        lines.append(f"\nSample (first 5 rows):")
        sample = df.head(5).to_string(index=False)
        lines.append(sample)

        return "\n".join(lines)
    except Exception as e:
        return f"Error loading data: {str(e)}"


@tool(description="Compute summary statistics for numeric columns: count, mean, std, min, max, quartiles.")
async def data_summary(
    file_path: str,
    file_type: str = "auto",
    columns: str = "",
) -> str:
    """Compute summary statistics for a dataset.

    Args:
        file_path: Path to the data file.
        file_type: csv, json, xlsx, auto.
        columns: Comma-separated column names to analyze (empty for all numeric).
    """
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas is not installed."

    try:
        df = _load_dataframe(pd, file_path, file_type)
        if isinstance(df, str):
            return df

        if columns:
            col_list = [c.strip() for c in columns.split(",")]
            df = df[col_list]

        numeric_df = df.select_dtypes(include=["number"])
        if numeric_df.empty:
            return "No numeric columns found in dataset."

        stats = numeric_df.describe().transpose()
        stats["median"] = numeric_df.median()
        stats["skew"] = numeric_df.skew()
        stats["kurtosis"] = numeric_df.kurtosis()

        return f"Summary Statistics:\n\n{stats.to_string()}"
    except Exception as e:
        return f"Error computing summary: {str(e)}"


@tool(description="Filter and query data with conditions. Supports column selection, row filtering, sorting, and grouping.")
async def query_data(
    file_path: str,
    file_type: str = "auto",
    select_columns: str = "",
    filter_condition: str = "",
    sort_by: str = "",
    sort_descending: bool = True,
    group_by: str = "",
    aggregate: str = "",
    limit: int = 100,
) -> str:
    """Query and filter data.

    Args:
        file_path: Path to the data file.
        file_type: csv, json, xlsx, auto.
        select_columns: Comma-separated columns to select.
        filter_condition: Filter expression (e.g., 'age > 30').
        sort_by: Column to sort by.
        sort_descending: Sort order.
        group_by: Column to group by.
        aggregate: Aggregation function - sum, mean, count, min, max.
        limit: Maximum rows to return.
    """
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas is not installed."

    try:
        df = _load_dataframe(pd, file_path, file_type)
        if isinstance(df, str):
            return df

        if select_columns:
            cols = [c.strip() for c in select_columns.split(",")]
            df = df[cols]

        if filter_condition:
            df = df.query(filter_condition)

        if group_by and aggregate:
            agg_col = select_columns.split(",")[0] if select_columns else df.columns[-1]
            agg_map = {
                "sum": lambda x: x.sum(),
                "mean": lambda x: x.mean(),
                "count": lambda x: x.count(),
                "min": lambda x: x.min(),
                "max": lambda x: x.max(),
            }
            if aggregate in agg_map:
                df = df.groupby(group_by)[agg_col].agg(agg_map[aggregate]).reset_index()
                df = df.rename(columns={agg_col: f"{aggregate}_{agg_col}"})

        if sort_by:
            df = df.sort_values(by=sort_by, ascending=not sort_descending)

        df = df.head(limit)

        return f"Query Result ({len(df)} rows):\n\n{df.to_string(index=False)}"
    except Exception as e:
        return f"Error querying data: {str(e)}"


@tool(description="Find and analyze missing values in a dataset. Returns count and percentage of missing values per column.")
async def analyze_missing(
    file_path: str,
    file_type: str = "auto",
) -> str:
    """Analyze missing values in a dataset.

    Args:
        file_path: Path to the data file.
        file_type: csv, json, xlsx, auto.
    """
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas is not installed."

    try:
        df = _load_dataframe(pd, file_path, file_type)
        if isinstance(df, str):
            return df

        missing = df.isnull().sum()
        total = len(df)

        lines = [f"Missing Value Analysis ({total} total rows):\n"]
        lines.append(f"{'Column':<30} {'Missing':>10} {'Percent':>10}")
        lines.append("-" * 52)

        for col in df.columns:
            count = missing[col]
            pct = (count / total) * 100
            lines.append(f"{col:<30} {count:>10} {pct:>9.1f}%")

        total_missing = missing.sum()
        lines.append("-" * 52)
        lines.append(f"{'TOTAL':<30} {total_missing:>10} {(total_missing / (total * len(df.columns))) * 100:>9.1f}%")

        return "\n".join(lines)
    except Exception as e:
        return f"Error analyzing missing values: {str(e)}"


@tool(description="Compute correlation matrix for numeric columns. Returns Pearson correlation coefficients.")
async def correlation_analysis(
    file_path: str,
    file_type: str = "auto",
    method: str = "pearson",
) -> str:
    """Compute correlation matrix.

    Args:
        file_path: Path to the data file.
        file_type: csv, json, xlsx, auto.
        method: Correlation method - pearson, spearman, kendall.
    """
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas is not installed."

    try:
        df = _load_dataframe(pd, file_path, file_type)
        if isinstance(df, str):
            return df

        numeric_df = df.select_dtypes(include=["number"])
        if numeric_df.empty:
            return "No numeric columns found."

        corr = numeric_df.corr(method=method)

        # Find highly correlated pairs
        lines = [f"Correlation Matrix ({method}):\n"]
        lines.append(corr.to_string())

        high_corr = []
        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                val = corr.iloc[i, j]
                if abs(val) > 0.7:
                    high_corr.append((corr.columns[i], corr.columns[j], val))

        if high_corr:
            lines.append(f"\n\nHighly Correlated Pairs (|r| > 0.7):")
            for col1, col2, val in high_corr:
                direction = "positive" if val > 0 else "negative"
                lines.append(f"  {col1} <-> {col2}: {val:.3f} ({direction})")

        return "\n".join(lines)
    except Exception as e:
        return f"Error computing correlation: {str(e)}"


@tool(description="Create pivot table from data. Summarize data by grouping and aggregating across multiple dimensions.")
async def pivot_table(
    file_path: str,
    file_type: str = "auto",
    rows: str = "",
    columns: str = "",
    values: str = "",
    agg_func: str = "mean",
) -> str:
    """Create a pivot table.

    Args:
        file_path: Path to the data file.
        file_type: csv, json, xlsx, auto.
        rows: Column for row grouping.
        columns: Column for column grouping.
        values: Column to aggregate.
        agg_func: Aggregation function - sum, mean, count, min, max, std.
    """
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas is not installed."

    try:
        df = _load_dataframe(pd, file_path, file_type)
        if isinstance(df, str):
            return df

        agg_map = {
            "sum": "sum", "mean": "mean", "count": "count",
            "min": "min", "max": "max", "std": "std",
        }
        func = agg_map.get(agg_func, "mean")

        pivot = pd.pivot_table(
            df,
            index=rows or None,
            columns=columns or None,
            values=values or None,
            aggfunc=func,
            fill_value=0,
        )

        return f"Pivot Table ({agg_func}):\n\n{pivot.to_string()}"
    except Exception as e:
        return f"Error creating pivot table: {str(e)}"


@tool(description="Export data to a different file format (CSV, JSON, Excel, Parquet, Markdown table).")
async def export_data(
    file_path: str,
    output_path: str,
    input_type: str = "auto",
    output_format: str = "auto",
) -> str:
    """Export data to a different format.

    Args:
        file_path: Path to the source data file.
        output_path: Path for the output file.
        input_type: Source format - csv, json, xlsx, auto.
        output_format: Target format - csv, json, xlsx, parquet, md, auto.
    """
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas is not installed."

    try:
        df = _load_dataframe(pd, file_path, input_type)
        if isinstance(df, str):
            return df

        if output_format == "auto":
            ext = os.path.splitext(output_path)[1].lower()
            fmt_map = {".csv": "csv", ".json": "json", ".xlsx": "xlsx", ".parquet": "parquet", ".md": "md"}
            output_format = fmt_map.get(ext, "csv")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        if output_format == "csv":
            df.to_csv(output_path, index=False)
        elif output_format == "json":
            df.to_json(output_path, orient="records", indent=2)
        elif output_format == "xlsx":
            df.to_excel(output_path, index=False)
        elif output_format == "parquet":
            df.to_parquet(output_path, index=False)
        elif output_format == "md":
            with open(output_path, "w") as f:
                f.write(df.to_markdown(index=False))
        else:
            return f"Error: Unsupported output format: {output_format}"

        size = os.path.getsize(output_path)
        return f"Exported {len(df)} rows to {output_path} ({size:,} bytes)"
    except Exception as e:
        return f"Error exporting data: {str(e)}"


@tool(description="Clean data: remove duplicates, handle missing values, normalize strings, and fix data types.")
async def clean_data(
    file_path: str,
    file_type: str = "auto",
    output_path: str = "",
    remove_duplicates: bool = True,
    fill_missing: str = "",
    strip_strings: bool = True,
    drop_empty_rows: bool = True,
) -> str:
    """Clean and preprocess data.

    Args:
        file_path: Path to the data file.
        file_type: csv, json, xlsx, auto.
        output_path: Path to save cleaned data (empty for no save).
        remove_duplicates: Remove duplicate rows.
        fill_missing: Fill missing values with this strategy - mean, median, mode, drop.
        strip_strings: Strip whitespace from string columns.
        drop_empty_rows: Drop rows where all values are missing.
    """
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas is not installed."

    try:
        df = _load_dataframe(pd, file_path, file_type)
        if isinstance(df, str):
            return df

        original_shape = df.shape

        if drop_empty_rows:
            df = df.dropna(how="all")

        if remove_duplicates:
            df = df.drop_duplicates()

        if fill_missing == "drop":
            df = df.dropna()
        elif fill_missing in ("mean", "median"):
            numeric_cols = df.select_dtypes(include=["number"]).columns
            for col in numeric_cols:
                if fill_missing == "mean":
                    df[col] = df[col].fillna(df[col].mean())
                else:
                    df[col] = df[col].fillna(df[col].median())
        elif fill_missing == "mode":
            for col in df.columns:
                if df[col].isnull().any():
                    mode_val = df[col].mode()
                    if not mode_val.empty:
                        df[col] = df[col].fillna(mode_val[0])

        if strip_strings:
            str_cols = df.select_dtypes(include=["object"]).columns
            for col in str_cols:
                df[col] = df[col].str.strip()

        result = f"Data Cleaning Report:\n"
        result += f"  Original: {original_shape[0]} rows x {original_shape[1]} columns\n"
        result += f"  Cleaned:  {df.shape[0]} rows x {df.shape[1]} columns\n"
        result += f"  Removed:  {original_shape[0] - df.shape[0]} rows\n"

        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            ext = os.path.splitext(output_path)[1].lower()
            if ext == ".csv":
                df.to_csv(output_path, index=False)
            elif ext == ".json":
                df.to_json(output_path, orient="records", indent=2)
            elif ext == ".xlsx":
                df.to_excel(output_path, index=False)
            else:
                df.to_csv(output_path, index=False)
            result += f"\nSaved to: {output_path}"

        return result
    except Exception as e:
        return f"Error cleaning data: {str(e)}"


@tool(description="Perform statistical analysis: t-test, chi-square, ANOVA, regression, and distribution fitting.")
async def statistical_analysis(
    file_path: str,
    file_type: str = "auto",
    test_type: str = "ttest",
    column1: str = "",
    column2: str = "",
    group_column: str = "",
) -> str:
    """Perform statistical tests on data.

    Args:
        file_path: Path to the data file.
        file_type: csv, json, xlsx, auto.
        test_type: Test type - ttest, chi2, anova, regression, normality.
        column1: First numeric column.
        column2: Second numeric column or target variable.
        group_column: Column defining groups for ANOVA.
    """
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas is not installed."

    try:
        df = _load_dataframe(pd, file_path, file_type)
        if isinstance(df, str):
            return df

        if column1 and column1 not in df.columns:
            return f"Error: Column '{column1}' not found. Available: {', '.join(df.columns)}"

        if test_type == "ttest":
            from scipy import stats
            data1 = df[column1].dropna()
            if column2:
                data2 = df[column2].dropna()
                t_stat, p_val = stats.ttest_ind(data1, data2)
                return (
                    f"Independent t-test: {column1} vs {column2}\n"
                    f"  t-statistic: {t_stat:.4f}\n"
                    f"  p-value: {p_val:.6f}\n"
                    f"  Significant: {'Yes' if p_val < 0.05 else 'No'} (alpha=0.05)\n"
                    f"  Mean({column1}): {data1.mean():.4f}\n"
                    f"  Mean({column2}): {data2.mean():.4f}"
                )
            else:
                t_stat, p_val = stats.ttest_1samp(data1, 0)
                return f"One-sample t-test: {column1}\n  t={t_stat:.4f}, p={p_val:.6f}"

        elif test_type == "anova":
            from scipy import stats
            groups = [g[column1].dropna().values for _, g in df.groupby(group_column)]
            f_stat, p_val = stats.f_oneway(*groups)
            return (
                f"One-way ANOVA: {column1} by {group_column}\n"
                f"  F-statistic: {f_stat:.4f}\n"
                f"  p-value: {p_val:.6f}\n"
                f"  Significant: {'Yes' if p_val < 0.05 else 'No'} (alpha=0.05)\n"
                f"  Groups: {len(groups)}"
            )

        elif test_type == "chi2":
            from scipy import stats
            contingency = pd.crosstab(df[column1], df[column2])
            chi2, p_val, dof, expected = stats.chi2_contingency(contingency)
            return (
                f"Chi-square test: {column1} vs {column2}\n"
                f"  Chi2: {chi2:.4f}\n"
                f"  p-value: {p_val:.6f}\n"
                f"  Degrees of freedom: {dof}\n"
                f"  Significant: {'Yes' if p_val < 0.05 else 'No'}"
            )

        elif test_type == "regression":
            from scipy import stats
            x = df[column2].dropna()
            y = df[column1].loc[x.index]
            slope, intercept, r_val, p_val, std_err = stats.linregress(x, y)
            return (
                f"Linear Regression: {column1} ~ {column2}\n"
                f"  Slope: {slope:.4f}\n"
                f"  Intercept: {intercept:.4f}\n"
                f"  R-squared: {r_val**2:.4f}\n"
                f"  p-value: {p_val:.6f}\n"
                f"  Std Error: {std_err:.4f}\n"
                f"  Equation: {column1} = {slope:.4f} * {column2} + {intercept:.4f}"
            )

        elif test_type == "normality":
            from scipy import stats
            data = df[column1].dropna()
            stat, p_val = stats.shapiro(data[:5000])
            return (
                f"Shapiro-Wilk Normality Test: {column1}\n"
                f"  W-statistic: {stat:.4f}\n"
                f"  p-value: {p_val:.6f}\n"
                f"  Normal: {'Yes' if p_val > 0.05 else 'No'} (alpha=0.05)\n"
                f"  Skewness: {data.skew():.4f}\n"
                f"  Kurtosis: {data.kurtosis():.4f}"
            )

        else:
            return f"Unknown test type: {test_type}"
    except ImportError:
        return "Error: scipy is not installed. Install with: pip install scipy"
    except Exception as e:
        return f"Error in statistical analysis: {str(e)}"


@tool(description="Generate a comprehensive data profile report with distributions, outliers, and data quality metrics.")
async def data_profile(
    file_path: str,
    file_type: str = "auto",
) -> str:
    """Generate a comprehensive data profile report.

    Args:
        file_path: Path to the data file.
        file_type: csv, json, xlsx, auto.
    """
    pd = _load_pandas()
    np = _load_numpy()
    if pd is None:
        return "Error: pandas is not installed."

    try:
        df = _load_dataframe(pd, file_path, file_type)
        if isinstance(df, str):
            return df

        lines = [
            f"Data Profile Report: {file_path}",
            f"{'='*60}",
            f"Rows: {df.shape[0]}",
            f"Columns: {df.shape[1]}",
            f"Memory Usage: {df.memory_usage(deep=True).sum() / 1024:.1f} KB",
            f"Duplicate Rows: {df.duplicated().sum()}",
            f"",
            f"Column Details:",
            f"{'-'*60}",
        ]

        for col in df.columns:
            dtype = str(df[col].dtype)
            unique = df[col].nunique()
            missing = df[col].isnull().sum()
            missing_pct = (missing / len(df)) * 100

            info = f"  {col} ({dtype}): {unique} unique, {missing} missing ({missing_pct:.1f}%)"

            if pd.api.types.is_numeric_dtype(df[col]):
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                outliers = ((df[col] < q1 - 1.5 * iqr) | (df[col] > q3 + 1.5 * iqr)).sum()
                info += f"\n    Range: [{df[col].min()}, {df[col].max()}], Outliers: {outliers}"

            lines.append(info)

        return "\n".join(lines)
    except Exception as e:
        return f"Error profiling data: {str(e)}"


def _load_dataframe(pd, file_path: str, file_type: str = "auto"):
    """Load a file into a pandas DataFrame."""
    if not os.path.exists(file_path):
        return f"Error: File not found: {file_path}"

    if file_type == "auto":
        ext = os.path.splitext(file_path)[1].lower()
        type_map = {".csv": "csv", ".json": "json", ".xlsx": "xlsx", ".xls": "xlsx", ".parquet": "parquet", ".tsv": "tsv"}
        file_type = type_map.get(ext, "csv")

    if file_type == "csv":
        return pd.read_csv(file_path)
    elif file_type == "tsv":
        return pd.read_csv(file_path, sep="\t")
    elif file_type == "json":
        return pd.read_json(file_path)
    elif file_type == "xlsx":
        return pd.read_excel(file_path)
    elif file_type == "parquet":
        return pd.read_parquet(file_path)
    else:
        return pd.read_csv(file_path)
