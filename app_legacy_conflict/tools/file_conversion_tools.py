"""File format conversion tools.

Provides tools for converting files between various formats:
CSV, JSON, XML, Excel, Markdown, HTML, YAML, TOML, and plain text.
"""

from __future__ import annotations

import csv
import json
import os
import xml.etree.ElementTree as ET
from typing import Any

import structlog

from app.tools import tool

logger = structlog.get_logger()


def _load_pandas():
    """Lazy-load pandas."""
    try:
        import pandas as pd
        return pd
    except ImportError:
        return None


@tool(description="Convert data between formats: CSV, JSON, XML, Excel, Markdown, YAML, TOML, HTML table, and plain text.")
async def convert_file(
    input_path: str,
    output_path: str,
    input_format: str = "auto",
    output_format: str = "auto",
    **kwargs: Any,
) -> str:
    """Convert a file from one format to another.

    Args:
        input_path: Source file path.
        output_path: Target file path.
        input_format: Source format (auto-detect from extension).
        output_format: Target format (auto-detect from extension).
        **kwargs: Additional options (sheet_name, delimiter, encoding, etc.).
    """
    try:
        if not os.path.exists(input_path):
            return f"Error: Input file not found: {input_path}"

        # Detect formats from extensions
        if input_format == "auto":
            input_format = _detect_format(input_path)
        if output_format == "auto":
            output_format = _detect_format(output_path)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        # Route to appropriate converter
        converter_key = f"{input_format}_to_{output_format}"

        # Direct conversions
        if converter_key in _DIRECT_CONVERTERS:
            return _DIRECT_CONVERTERS[converter_key](input_path, output_path, **kwargs)

        # Convert via intermediate JSON if no direct path
        if input_format != "json" and output_format != "json":
            # Two-step: input -> JSON -> output
            intermediate = input_path + ".tmp.json"
            try:
                # Step 1: to JSON
                to_json_key = f"{input_format}_to_json"
                if to_json_key in _DIRECT_CONVERTERS:
                    _DIRECT_CONVERTERS[to_json_key](input_path, intermediate, **kwargs)
                else:
                    return f"Error: Cannot convert {input_format} to intermediate format"

                # Step 2: JSON to output
                from_json_key = f"json_to_{output_format}"
                if from_json_key in _DIRECT_CONVERTERS:
                    result = _DIRECT_CONVERTERS[from_json_key](intermediate, output_path, **kwargs)
                    return result
                else:
                    return f"Error: Cannot convert intermediate to {output_format}"
            finally:
                if os.path.exists(intermediate):
                    os.remove(intermediate)

        return f"Error: Conversion from {input_format} to {output_format} not supported"

    except Exception as e:
        return f"Error converting file: {str(e)}"


def _detect_format(file_path: str) -> str:
    """Detect file format from extension."""
    ext = os.path.splitext(file_path)[1].lower()
    format_map = {
        ".csv": "csv",
        ".tsv": "tsv",
        ".json": "json",
        ".xml": "xml",
        ".xlsx": "xlsx",
        ".xls": "xlsx",
        ".md": "markdown",
        ".markdown": "markdown",
        ".html": "html",
        ".htm": "html",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".txt": "text",
        ".parquet": "parquet",
    }
    return format_map.get(ext, "text")


@tool(description="Convert CSV or Excel data to JSON format. Preserves data types and structure.")
async def csv_to_json(
    input_path: str,
    output_path: str,
    delimiter: str = "",
    encoding: str = "utf-8",
    orient: str = "records",
) -> str:
    """Convert CSV/TSV to JSON.

    Args:
        input_path: Path to CSV file.
        output_path: Path to save JSON.
        delimiter: Column delimiter (auto-detect if empty).
        encoding: File encoding.
        orient: JSON structure - records, index, columns, values.
    """
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas not installed."

    try:
        if not os.path.exists(input_path):
            return f"Error: File not found: {input_path}"

        sep = delimiter if delimiter else ("\t" if input_path.endswith(".tsv") else ",")
        df = pd.read_csv(input_path, sep=sep, encoding=encoding)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        df.to_json(output_path, orient=orient, indent=2, force_ascii=False)

        size = os.path.getsize(output_path)
        return f"Converted CSV to JSON: {output_path} ({len(df)} rows, {size:,} bytes)"
    except Exception as e:
        return f"Error converting CSV to JSON: {str(e)}"


@tool(description="Convert JSON data to CSV or Excel format. Flattens nested structures if needed.")
async def json_to_csv(
    input_path: str,
    output_path: str,
    encoding: str = "utf-8",
    flatten: bool = True,
) -> str:
    """Convert JSON to CSV.

    Args:
        input_path: Path to JSON file.
        output_path: Path to save CSV.
        encoding: File encoding.
        flatten: Flatten nested JSON structures.
    """
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas not installed."

    try:
        if not os.path.exists(input_path):
            return f"Error: File not found: {input_path}"

        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            data = [data]

        if flatten:
            df = pd.json_normalize(data)
        else:
            df = pd.DataFrame(data)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        ext = os.path.splitext(output_path)[1].lower()
        if ext in (".xlsx", ".xls"):
            df.to_excel(output_path, index=False)
        else:
            df.to_csv(output_path, index=False, encoding=encoding)

        size = os.path.getsize(output_path)
        return f"Converted JSON to CSV: {output_path} ({len(df)} rows, {size:,} bytes)"
    except Exception as e:
        return f"Error converting JSON to CSV: {str(e)}"


@tool(description="Convert Markdown to HTML. Supports tables, code blocks, lists, and common extensions.")
async def markdown_to_html(
    input_path: str,
    output_path: str,
    css_style: str = "",
) -> str:
    """Convert Markdown to HTML.

    Args:
        input_path: Path to Markdown file.
        output_path: Path to save HTML.
        css_style: Optional CSS to embed.
    """
    try:
        if not os.path.exists(input_path):
            return f"Error: File not found: {input_path}"

        with open(input_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        try:
            import markdown
            html_body = markdown.markdown(md_content, extensions=["tables", "fenced_code", "codehilite", "toc"])
        except ImportError:
            # Fallback: basic conversion
            html_body = _basic_md_to_html(md_content)

        css = css_style or _default_css()

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{os.path.basename(input_path)}</title>
    <style>{css}</style>
</head>
<body>
{html_body}
</body>
</html>"""

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        size = os.path.getsize(output_path)
        return f"Converted Markdown to HTML: {output_path} ({size:,} bytes)"
    except Exception as e:
        return f"Error converting Markdown to HTML: {str(e)}"


@tool(description="Convert HTML to plain text or Markdown. Strips tags and preserves structure.")
async def html_to_markdown(
    input_path: str,
    output_path: str,
    output_format: str = "markdown",
) -> str:
    """Convert HTML to Markdown or plain text.

    Args:
        input_path: Path to HTML file.
        output_path: Path to save output.
        output_format: markdown or text.
    """
    try:
        if not os.path.exists(input_path):
            return f"Error: File not found: {input_path}"

        with open(input_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        try:
            from markdownify import markdownify
            if output_format == "text":
                result = markdownify(html_content, heading_style="ATX", strip=["img", "script", "style"])
                # Further strip remaining tags
                import re
                result = re.sub(r'<[^>]+>', '', result)
            else:
                result = markdownify(html_content, heading_style="ATX")
        except ImportError:
            # Fallback: strip tags
            import re
            result = re.sub(r'<[^>]+>', '', html_content)
            result = re.sub(r'\n{3,}', '\n\n', result)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)

        size = os.path.getsize(output_path)
        return f"Converted HTML to {output_format}: {output_path} ({size:,} bytes)"
    except Exception as e:
        return f"Error converting HTML: {str(e)}"


@tool(description="Convert XML data to JSON. Preserves attributes and nested elements.")
async def xml_to_json(
    input_path: str,
    output_path: str,
) -> str:
    """Convert XML to JSON.

    Args:
        input_path: Path to XML file.
        output_path: Path to save JSON.
    """
    try:
        if not os.path.exists(input_path):
            return f"Error: File not found: {input_path}"

        tree = ET.parse(input_path)
        root = tree.getroot()

        def element_to_dict(element):
            result = {}
            if element.attrib:
                result["@attributes"] = dict(element.attrib)
            children = list(element)
            if children:
                child_dict = {}
                for child in children:
                    child_data = element_to_dict(child)
                    if child.tag in child_dict:
                        if not isinstance(child_dict[child.tag], list):
                            child_dict[child.tag] = [child_dict[child.tag]]
                        child_dict[child.tag].append(child_data)
                    else:
                        child_dict[child.tag] = child_data
                result.update(child_dict)
            if element.text and element.text.strip():
                if result:
                    result["#text"] = element.text.strip()
                else:
                    return element.text.strip()
            return result

        data = {root.tag: element_to_dict(root)}

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        size = os.path.getsize(output_path)
        return f"Converted XML to JSON: {output_path} ({size:,} bytes)"
    except Exception as e:
        return f"Error converting XML to JSON: {str(e)}"


@tool(description="Convert JSON data to XML format.")
async def json_to_xml(
    input_path: str,
    output_path: str,
    root_element: str = "root",
) -> str:
    """Convert JSON to XML.

    Args:
        input_path: Path to JSON file.
        output_path: Path to save XML.
        root_element: Root element name.
    """
    try:
        if not os.path.exists(input_path):
            return f"Error: File not found: {input_path}"

        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        def dict_to_xml(parent, data):
            if isinstance(data, dict):
                for key, value in data.items():
                    if key.startswith("@"):
                        parent.set(key[1:], str(value))
                    elif key == "#text":
                        parent.text = str(value)
                    else:
                        child = ET.SubElement(parent, str(key))
                        dict_to_xml(child, value)
            elif isinstance(data, list):
                for item in data:
                    child = ET.SubElement(parent, "item")
                    dict_to_xml(child, item)
            else:
                parent.text = str(data)

        root = ET.Element(root_element)
        dict_to_xml(root, data)

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        tree.write(output_path, encoding="unicode", xml_declaration=True)

        size = os.path.getsize(output_path)
        return f"Converted JSON to XML: {output_path} ({size:,} bytes)"
    except Exception as e:
        return f"Error converting JSON to XML: {str(e)}"


@tool(description="Convert between YAML and JSON formats.")
async def convert_yaml_json(
    input_path: str,
    output_path: str,
) -> str:
    """Convert YAML to JSON or vice versa.

    Args:
        input_path: Source file path.
        output_path: Target file path.
    """
    try:
        import yaml

        if not os.path.exists(input_path):
            return f"Error: File not found: {input_path}"

        with open(input_path, "r", encoding="utf-8") as f:
            input_content = f.read()

        input_ext = os.path.splitext(input_path)[1].lower()
        output_ext = os.path.splitext(output_path)[1].lower()

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        if input_ext in (".yaml", ".yml"):
            data = yaml.safe_load(input_content)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        elif input_ext == ".json":
            data = json.loads(input_content)
            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        else:
            return f"Error: Unsupported input format: {input_ext}"

        size = os.path.getsize(output_path)
        return f"Converted {input_ext} to {output_ext}: {output_path} ({size:,} bytes)"
    except ImportError:
        return "Error: PyYAML not installed. Install with: pip install pyyaml"
    except Exception as e:
        return f"Error converting: {str(e)}"


@tool(description="Convert Excel file to CSV, or CSV to Excel. Supports multiple sheets.")
async def convert_excel(
    input_path: str,
    output_path: str,
    sheet_name: str = "",
) -> str:
    """Convert between Excel and CSV.

    Args:
        input_path: Source file path.
        output_path: Target file path.
        sheet_name: Specific sheet name (for Excel input).
    """
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas not installed."

    try:
        if not os.path.exists(input_path):
            return f"Error: File not found: {input_path}"

        input_ext = os.path.splitext(input_path)[1].lower()
        output_ext = os.path.splitext(output_path)[1].lower()

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        if input_ext in (".xlsx", ".xls"):
            df = pd.read_excel(input_path, sheet_name=sheet_name or 0)
            if output_ext == ".json":
                df.to_json(output_path, orient="records", indent=2)
            else:
                df.to_csv(output_path, index=False)
        elif input_ext == ".csv":
            df = pd.read_csv(input_path)
            if output_ext in (".xlsx", ".xls"):
                df.to_excel(output_path, index=False)
            elif output_ext == ".json":
                df.to_json(output_path, orient="records", indent=2)
            else:
                return f"Error: Unsupported output format: {output_ext}"
        else:
            return f"Error: Unsupported input format: {input_ext}"

        size = os.path.getsize(output_path)
        return f"Converted {input_ext} to {output_ext}: {output_path} ({size:,} bytes)"
    except Exception as e:
        return f"Error converting Excel: {str(e)}"


@tool(description="Convert a data file to a formatted Markdown table.")
async def to_markdown_table(
    input_path: str,
    output_path: str = "",
    file_type: str = "auto",
    max_rows: int = 100,
    max_col_width: int = 50,
) -> str:
    """Convert data to a Markdown table.

    Args:
        input_path: Path to data file.
        output_path: Path to save Markdown (empty for inline return).
        file_type: csv, json, xlsx, auto.
        max_rows: Maximum rows to include.
        max_col_width: Maximum column width.
    """
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas not installed."

    try:
        if file_type == "auto":
            ext = os.path.splitext(input_path)[1].lower()
            file_type = "json" if ext == ".json" else "xlsx" if ext in (".xlsx", ".xls") else "csv"

        if file_type == "json":
            df = pd.read_json(input_path)
        elif file_type == "xlsx":
            df = pd.read_excel(input_path)
        else:
            df = pd.read_csv(input_path)

        df = df.head(max_rows)

        # Truncate long values
        for col in df.columns:
            df[col] = df[col].astype(str).str[:max_col_width]

        md_table = df.to_markdown(index=False)

        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(md_table)
            return f"Markdown table saved: {output_path}"

        return md_table
    except Exception as e:
        return f"Error creating Markdown table: {str(e)}"


@tool(description="Convert a data file to an HTML table with styling.")
async def to_html_table(
    input_path: str,
    output_path: str,
    file_type: str = "auto",
    max_rows: int = 500,
    striped: bool = True,
    bordered: bool = True,
) -> str:
    """Convert data to a styled HTML table.

    Args:
        input_path: Path to data file.
        output_path: Path to save HTML.
        file_type: csv, json, xlsx, auto.
        max_rows: Maximum rows.
        striped: Add alternating row colors.
        bordered: Add borders.
    """
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas not installed."

    try:
        if file_type == "auto":
            ext = os.path.splitext(input_path)[1].lower()
            file_type = "json" if ext == ".json" else "xlsx" if ext in (".xlsx", ".xls") else "csv"

        if file_type == "json":
            df = pd.read_json(input_path)
        elif file_type == "xlsx":
            df = pd.read_excel(input_path)
        else:
            df = pd.read_csv(input_path)

        df = df.head(max_rows)

        table_html = df.to_html(index=False, classes="table table-striped" if striped else "table", border=1 if bordered else 0)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Data Table</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; }}
        .table {{ border-collapse: collapse; width: 100%; }}
        .table th, .table td {{ padding: 8px 12px; text-align: left; border: 1px solid #ddd; }}
        .table th {{ background-color: #4C72B0; color: white; }}
        .table-striped tbody tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .table tbody tr:hover {{ background-color: #e8e8e8; }}
    </style>
</head>
<body>
    {table_html}
</body>
</html>"""

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        size = os.path.getsize(output_path)
        return f"HTML table saved: {output_path} ({size:,} bytes)"
    except Exception as e:
        return f"Error creating HTML table: {str(e)}"


@tool(description="Merge multiple CSV/JSON files into a single file. Supports concatenation and joining on a key column.")
async def merge_files(
    input_files: str,
    output_path: str,
    merge_type: str = "concat",
    join_key: str = "",
    file_type: str = "auto",
) -> str:
    """Merge multiple data files.

    Args:
        input_files: Comma-separated file paths.
        output_path: Path to save merged file.
        merge_type: concat (stack rows) or join (merge on key).
        join_key: Column to join on (for join type).
        file_type: csv, json, auto.
    """
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas not installed."

    try:
        files = [f.strip() for f in input_files.split(",")]
        if len(files) < 2:
            return "Error: Need at least 2 files to merge"

        if file_type == "auto":
            ext = os.path.splitext(files[0])[1].lower()
            file_type = "json" if ext == ".json" else "csv"

        # Load all files
        dfs = []
        for f in files:
            if file_type == "json":
                dfs.append(pd.read_json(f))
            else:
                dfs.append(pd.read_csv(f))

        if merge_type == "join" and join_key:
            result = dfs[0]
            for df in dfs[1:]:
                result = result.merge(df, on=join_key, how="outer")
        else:
            result = pd.concat(dfs, ignore_index=True)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        out_ext = os.path.splitext(output_path)[1].lower()
        if out_ext == ".json":
            result.to_json(output_path, orient="records", indent=2)
        elif out_ext in (".xlsx", ".xls"):
            result.to_excel(output_path, index=False)
        else:
            result.to_csv(output_path, index=False)

        size = os.path.getsize(output_path)
        return f"Merged {len(files)} files: {output_path} ({len(result)} rows, {size:,} bytes)"
    except Exception as e:
        return f"Error merging files: {str(e)}"


@tool(description="Split a data file into multiple files based on a column value or row count.")
async def split_file(
    input_path: str,
    output_dir: str,
    split_by: str = "",
    rows_per_file: int = 0,
    file_type: str = "auto",
) -> str:
    """Split a data file into multiple files.

    Args:
        input_path: Path to source file.
        output_dir: Directory for output files.
        split_by: Column to group by (creates one file per unique value).
        rows_per_file: Maximum rows per file (used if split_by is empty).
        file_type: csv, json, auto.
    """
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas not installed."

    try:
        if file_type == "auto":
            ext = os.path.splitext(input_path)[1].lower()
            file_type = "json" if ext == ".json" else "csv"

        if file_type == "json":
            df = pd.read_json(input_path)
        else:
            df = pd.read_csv(input_path)

        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(input_path))[0]

        output_files = []

        if split_by and split_by in df.columns:
            for value, group in df.groupby(split_by):
                safe_value = str(value).replace("/", "_").replace(" ", "_")
                out_path = os.path.join(output_dir, f"{base_name}_{safe_value}.csv")
                group.to_csv(out_path, index=False)
                output_files.append(out_path)
        elif rows_per_file > 0:
            for i, start in enumerate(range(0, len(df), rows_per_file)):
                chunk = df.iloc[start:start + rows_per_file]
                out_path = os.path.join(output_dir, f"{base_name}_part{i+1:03d}.csv")
                chunk.to_csv(out_path, index=False)
                output_files.append(out_path)
        else:
            return "Error: Specify split_by column or rows_per_file"

        return f"Split into {len(output_files)} files in {output_dir}:\n" + "\n".join(f"  {os.path.basename(f)}" for f in output_files)
    except Exception as e:
        return f"Error splitting file: {str(e)}"


# ─── Internal converters ──────────────────────────────────────────────────

def _csv_to_json_converter(input_path: str, output_path: str, **kwargs) -> str:
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas not installed."
    df = pd.read_csv(input_path)
    df.to_json(output_path, orient="records", indent=2, force_ascii=False)
    return f"Converted CSV to JSON: {output_path} ({len(df)} rows)"


def _json_to_csv_converter(input_path: str, output_path: str, **kwargs) -> str:
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas not installed."
    with open(input_path, "r") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = [data]
    df = pd.json_normalize(data) if any(isinstance(v, dict) for v in data[0].values()) else pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    return f"Converted JSON to CSV: {output_path} ({len(df)} rows)"


def _xlsx_to_json_converter(input_path: str, output_path: str, **kwargs) -> str:
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas not installed."
    df = pd.read_excel(input_path, sheet_name=kwargs.get("sheet_name", 0))
    df.to_json(output_path, orient="records", indent=2, force_ascii=False)
    return f"Converted XLSX to JSON: {output_path} ({len(df)} rows)"


def _json_to_xlsx_converter(input_path: str, output_path: str, **kwargs) -> str:
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas not installed."
    with open(input_path, "r") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = [data]
    df = pd.DataFrame(data)
    df.to_excel(output_path, index=False)
    return f"Converted JSON to XLSX: {output_path} ({len(df)} rows)"


def _csv_to_xlsx_converter(input_path: str, output_path: str, **kwargs) -> str:
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas not installed."
    df = pd.read_csv(input_path)
    df.to_excel(output_path, index=False)
    return f"Converted CSV to XLSX: {output_path} ({len(df)} rows)"


def _xlsx_to_csv_converter(input_path: str, output_path: str, **kwargs) -> str:
    pd = _load_pandas()
    if pd is None:
        return "Error: pandas not installed."
    df = pd.read_excel(input_path, sheet_name=kwargs.get("sheet_name", 0))
    df.to_csv(output_path, index=False)
    return f"Converted XLSX to CSV: {output_path} ({len(df)} rows)"


def _md_to_html_converter(input_path: str, output_path: str, **kwargs) -> str:
    return markdown_to_html(input_path, output_path, **kwargs)


def _html_to_md_converter(input_path: str, output_path: str, **kwargs) -> str:
    return html_to_markdown(input_path, output_path, **kwargs)


def _xml_to_json_converter(input_path: str, output_path: str, **kwargs) -> str:
    return xml_to_json(input_path, output_path)


def _json_to_xml_converter(input_path: str, output_path: str, **kwargs) -> str:
    return json_to_xml(input_path, output_path, **kwargs)


_DIRECT_CONVERTERS = {
    "csv_to_json": _csv_to_json_converter,
    "json_to_csv": _json_to_csv_converter,
    "xlsx_to_json": _xlsx_to_json_converter,
    "json_to_xlsx": _json_to_xlsx_converter,
    "csv_to_xlsx": _csv_to_xlsx_converter,
    "xlsx_to_csv": _xlsx_to_csv_converter,
    "markdown_to_html": _md_to_html_converter,
    "html_to_markdown": _html_to_md_converter,
    "xml_to_json": _xml_to_json_converter,
    "json_to_xml": _json_to_xml_converter,
}


def _basic_md_to_html(md: str) -> str:
    """Basic Markdown to HTML conversion without external libraries."""
    import re

    lines = md.split("\n")
    html_lines = []
    in_list = False

    for line in lines:
        # Headers
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            text = line[level:].strip()
            html_lines.append(f"<h{level}>{text}</h{level}>")
            continue

        # Bold and italic
        line = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', line)
        line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
        line = re.sub(r'\*(.+?)\*', r'<em>\1</em>', line)

        # Code blocks
        if line.startswith("```"):
            lang = line[3:].strip()
            html_lines.append(f'<pre><code class="language-{lang}">' if lang else "<pre><code>")
            continue

        # List items
        if line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{line[2:]}</li>")
            continue
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False

        # Paragraphs
        if line.strip():
            html_lines.append(f"<p>{line}</p>")
        else:
            html_lines.append("")

    return "\n".join(html_lines)


def _default_css() -> str:
    """Default CSS for HTML output."""
    return """
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; color: #333; }
    h1, h2, h3 { color: #2c3e50; }
    code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }
    pre { background: #f8f8f8; padding: 16px; border-radius: 6px; overflow-x: auto; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
    th { background: #f0f0f0; }
    """
