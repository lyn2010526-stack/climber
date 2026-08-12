"""Chart and visualization generation tools.

Creates various types of charts and plots from data, including line charts,
bar charts, scatter plots, histograms, pie charts, heatmaps, and more.
Outputs are saved as PNG images.
"""

from __future__ import annotations

import os

import structlog

from app.tools import tool

logger = structlog.get_logger()


def _load_matplotlib():
    """Lazy-load matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        return None


def _load_pandas():
    """Lazy-load pandas."""
    try:
        import pandas as pd
        return pd
    except ImportError:
        return None


def _ensure_output_path(output_path: str) -> str:
    """Ensure output directory exists."""
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    return output_path


@tool(description="Create a line chart from data. Supports multiple series, custom labels, titles, and styles.")
async def chart_line(
    file_path: str,
    x_column: str,
    y_columns: str,
    output_path: str = "/tmp/chart_line.png",
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    file_type: str = "auto",
    figsize: str = "10,6",
    style: str = "",
) -> str:
    """Create a line chart.

    Args:
        file_path: Path to data file.
        x_column: Column for x-axis.
        y_columns: Comma-separated columns for y-axis (multiple lines).
        output_path: Path to save the chart image.
        title: Chart title.
        x_label: X-axis label.
        y_label: Y-axis label.
        file_type: csv, json, xlsx, auto.
        figsize: Figure size as width,height.
        style: Matplotlib style name.
    """
    plt = _load_matplotlib()
    pd = _load_pandas()
    if plt is None:
        return "Error: matplotlib not installed. Install with: pip install matplotlib"
    if pd is None:
        return "Error: pandas not installed."

    try:
        df = _load_df(pd, file_path, file_type)
        if isinstance(df, str):
            return df

        if style:
            plt.style.use(style)

        w, h = (int(x) for x in figsize.split(","))
        fig, ax = plt.subplots(figsize=(w, h))

        cols = [c.strip() for c in y_columns.split(",")]
        for col in cols:
            if col not in df.columns:
                return f"Error: Column '{col}' not found."
            ax.plot(df[x_column], df[col], marker="o", markersize=3, label=col, linewidth=1.5)

        ax.set_xlabel(x_label or x_column)
        ax.set_ylabel(y_label or y_columns)
        ax.set_title(title or f"Line Chart: {y_columns} vs {x_column}")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        _ensure_output_path(output_path)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        size = os.path.getsize(output_path)
        return f"Line chart saved: {output_path} ({size:,} bytes)"
    except Exception as e:
        return f"Error creating line chart: {e!s}"


@tool(description="Create a bar chart from data. Supports grouped and stacked bars.")
async def chart_bar(
    file_path: str,
    x_column: str,
    y_column: str,
    output_path: str = "/tmp/chart_bar.png",
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    file_type: str = "auto",
    horizontal: bool = False,
    color: str = "#4C72B0",
    top_n: int = 0,
) -> str:
    """Create a bar chart.

    Args:
        file_path: Path to data file.
        x_column: Column for categories (x-axis).
        y_column: Column for values (y-axis).
        output_path: Path to save the chart.
        title: Chart title.
        x_label: X-axis label.
        y_label: Y-axis label.
        file_type: csv, json, xlsx, auto.
        horizontal: Create horizontal bar chart.
        color: Bar color (hex or name).
        top_n: Show only top N categories (0 for all).
    """
    plt = _load_matplotlib()
    pd = _load_pandas()
    if plt is None or pd is None:
        return "Error: matplotlib and pandas required."

    try:
        df = _load_df(pd, file_path, file_type)
        if isinstance(df, str):
            return df

        if top_n > 0:
            df = df.nlargest(top_n, y_column)

        fig, ax = plt.subplots(figsize=(10, 6))

        if horizontal:
            ax.barh(df[x_column], df[y_column], color=color)
            ax.set_xlabel(y_label or y_column)
            ax.set_ylabel(x_label or x_column)
        else:
            ax.bar(df[x_column], df[y_column], color=color)
            ax.set_xlabel(x_label or x_column)
            ax.set_ylabel(y_label or y_column)

        ax.set_title(title or f"Bar Chart: {y_column} by {x_column}")

        if not horizontal and len(df) > 5:
            plt.xticks(rotation=45, ha="right")

        plt.tight_layout()
        _ensure_output_path(output_path)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        size = os.path.getsize(output_path)
        return f"Bar chart saved: {output_path} ({size:,} bytes)"
    except Exception as e:
        return f"Error creating bar chart: {e!s}"


@tool(description="Create a scatter plot from numeric data. Supports color coding by category and trend lines.")
async def chart_scatter(
    file_path: str,
    x_column: str,
    y_column: str,
    output_path: str = "/tmp/chart_scatter.png",
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    file_type: str = "auto",
    color_column: str = "",
    trend_line: bool = False,
    alpha: float = 0.6,
) -> str:
    """Create a scatter plot.

    Args:
        file_path: Path to data file.
        x_column: Column for x-axis values.
        y_column: Column for y-axis values.
        output_path: Path to save the chart.
        title: Chart title.
        x_label: X-axis label.
        y_label: Y-axis label.
        file_type: csv, json, xlsx, auto.
        color_column: Column for color coding points.
        trend_line: Add linear regression trend line.
        alpha: Point transparency (0-1).
    """
    plt = _load_matplotlib()
    pd = _load_pandas()
    if plt is None or pd is None:
        return "Error: matplotlib and pandas required."

    try:
        df = _load_df(pd, file_path, file_type)
        if isinstance(df, str):
            return df

        fig, ax = plt.subplots(figsize=(10, 8))

        if color_column and color_column in df.columns:
            categories = df[color_column].unique()
            cmap = plt.get_cmap("tab10").resampled(len(categories))
            for i, cat in enumerate(categories):
                mask = df[color_column] == cat
                ax.scatter(df.loc[mask, x_column], df.loc[mask, y_column],
                          label=cat, alpha=alpha, color=cmap(i), s=30)
            ax.legend(title=color_column)
        else:
            ax.scatter(df[x_column], df[y_column], alpha=alpha, s=30, color="#4C72B0")

        if trend_line:
            from scipy import stats
            mask = df[[x_column, y_column]].notna().all(axis=1)
            x = df.loc[mask, x_column]
            y = df.loc[mask, y_column]
            slope, intercept, r_val, _, _ = stats.linregress(x, y)
            line_x = [x.min(), x.max()]
            line_y = [slope * xi + intercept for xi in line_x]
            ax.plot(line_x, line_y, "r--", alpha=0.8, label=f"trend (R={r_val:.2f})")
            ax.legend()

        ax.set_xlabel(x_label or x_column)
        ax.set_ylabel(y_label or y_column)
        ax.set_title(title or f"Scatter: {y_column} vs {x_column}")
        ax.grid(True, alpha=0.2)

        plt.tight_layout()
        _ensure_output_path(output_path)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        size = os.path.getsize(output_path)
        return f"Scatter plot saved: {output_path} ({size:,} bytes)"
    except Exception as e:
        return f"Error creating scatter plot: {e!s}"


@tool(description="Create a histogram to visualize distribution of a numeric column.")
async def chart_histogram(
    file_path: str,
    column: str,
    output_path: str = "/tmp/chart_histogram.png",
    title: str = "",
    x_label: str = "",
    bins: int = 30,
    file_type: str = "auto",
    kde: bool = True,
    color: str = "#4C72B0",
) -> str:
    """Create a histogram.

    Args:
        file_path: Path to data file.
        column: Numeric column to plot.
        output_path: Path to save the chart.
        title: Chart title.
        x_label: X-axis label.
        bins: Number of bins.
        file_type: csv, json, xlsx, auto.
        kde: Overlay kernel density estimate.
        color: Bar color.
    """
    plt = _load_matplotlib()
    pd = _load_pandas()
    if plt is None or pd is None:
        return "Error: matplotlib and pandas required."

    try:
        df = _load_df(pd, file_path, file_type)
        if isinstance(df, str):
            return df

        data = df[column].dropna()

        fig, ax = plt.subplots(figsize=(10, 6))

        ax.hist(data, bins=bins, color=color, alpha=0.7, edgecolor="white", density=kde)

        if kde:
            try:
                from scipy.stats import gaussian_kde
                kde_est = gaussian_kde(data)
                x_range = [data.min(), data.max()]
                x_vals = [x_range[0] + i * (x_range[1] - x_range[0]) / 200 for i in range(201)]
                ax.plot(x_vals, kde_est(x_vals), "r-", linewidth=2, label="KDE")
                ax.legend()
            except ImportError:
                pass

        ax.set_xlabel(x_label or column)
        ax.set_ylabel("Frequency")
        ax.set_title(title or f"Distribution of {column}")

        # Add statistics text
        stats_text = f"Mean: {data.mean():.2f}\nMedian: {data.median():.2f}\nStd: {data.std():.2f}"
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=9,
                verticalalignment="top", bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.5})

        plt.tight_layout()
        _ensure_output_path(output_path)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        size = os.path.getsize(output_path)
        return f"Histogram saved: {output_path} ({size:,} bytes)"
    except Exception as e:
        return f"Error creating histogram: {e!s}"


@tool(description="Create a pie chart to show proportions of categories.")
async def chart_pie(
    file_path: str,
    label_column: str,
    value_column: str,
    output_path: str = "/tmp/chart_pie.png",
    title: str = "",
    file_type: str = "auto",
    top_n: int = 10,
    explode_largest: bool = False,
) -> str:
    """Create a pie chart.

    Args:
        file_path: Path to data file.
        label_column: Column for category labels.
        value_column: Column for values.
        output_path: Path to save the chart.
        title: Chart title.
        file_type: csv, json, xlsx, auto.
        top_n: Show top N categories (rest as 'Other').
        explode_largest: Explode the largest slice.
    """
    plt = _load_matplotlib()
    pd = _load_pandas()
    if plt is None or pd is None:
        return "Error: matplotlib and pandas required."

    try:
        df = _load_df(pd, file_path, file_type)
        if isinstance(df, str):
            return df

        # Aggregate by label
        agg = df.groupby(label_column)[value_column].sum().sort_values(ascending=False)

        if top_n > 0 and len(agg) > top_n:
            top = agg.head(top_n)
            other = agg.iloc[top_n:].sum()
            top["Other"] = other
            agg = top

        fig, ax = plt.subplots(figsize=(10, 8))

        colors = plt.cm.Set3(range(len(agg)))
        explode = [0.05 if explode_largest and i == 0 else 0 for i in range(len(agg))]

        _, _, autotexts = ax.pie(
            agg.values, labels=agg.index, autopct="%1.1f%%",
            colors=colors, explode=explode, startangle=90,
        )

        for autotext in autotexts:
            autotext.set_fontsize(8)

        ax.set_title(title or f"Pie Chart: {value_column} by {label_column}")

        plt.tight_layout()
        _ensure_output_path(output_path)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        size = os.path.getsize(output_path)
        return f"Pie chart saved: {output_path} ({size:,} bytes)"
    except Exception as e:
        return f"Error creating pie chart: {e!s}"


@tool(description="Create a heatmap visualization, typically for correlation matrices or 2D data.")
async def chart_heatmap(
    file_path: str,
    output_path: str = "/tmp/chart_heatmap.png",
    title: str = "",
    file_type: str = "auto",
    column1: str = "",
    column2: str = "",
    value_column: str = "",
    cmap: str = "YlOrRd",
) -> str:
    """Create a heatmap.

    Args:
        file_path: Path to data file.
        output_path: Path to save the chart.
        title: Chart title.
        file_type: csv, json, xlsx, auto.
        column1: Row dimension for pivot.
        column2: Column dimension for pivot.
        value_column: Values for pivot (empty for correlation matrix).
        cmap: Colormap name.
    """
    plt = _load_matplotlib()
    pd = _load_pandas()
    if plt is None or pd is None:
        return "Error: matplotlib and pandas required."

    try:
        df = _load_df(pd, file_path, file_type)
        if isinstance(df, str):
            return df

        fig, ax = plt.subplots(figsize=(12, 10))

        if column1 and column2 and value_column:
            # Pivot table heatmap
            pivot = df.pivot_table(index=column1, columns=column2, values=value_column, aggfunc="mean")
            im = ax.imshow(pivot.values, cmap=cmap, aspect="auto")
            ax.set_xticks(range(len(pivot.columns)))
            ax.set_xticklabels(pivot.columns, rotation=45, ha="right")
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels(pivot.index)
        else:
            # Correlation heatmap
            numeric_df = df.select_dtypes(include=["number"])
            corr = numeric_df.corr()
            im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1)
            ax.set_xticks(range(len(corr.columns)))
            ax.set_xticklabels(corr.columns, rotation=45, ha="right")
            ax.set_yticks(range(len(corr.index)))
            ax.set_yticklabels(corr.index)

            # Add correlation values
            for i in range(len(corr)):
                for j in range(len(corr)):
                    ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)

        fig.colorbar(im, ax=ax, shrink=0.8)
        ax.set_title(title or "Heatmap")

        plt.tight_layout()
        _ensure_output_path(output_path)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        size = os.path.getsize(output_path)
        return f"Heatmap saved: {output_path} ({size:,} bytes)"
    except Exception as e:
        return f"Error creating heatmap: {e!s}"


@tool(description="Create a box plot to show distribution statistics and outliers across categories.")
async def chart_box(
    file_path: str,
    value_column: str,
    group_column: str = "",
    output_path: str = "/tmp/chart_box.png",
    title: str = "",
    file_type: str = "auto",
    horizontal: bool = False,
) -> str:
    """Create a box plot.

    Args:
        file_path: Path to data file.
        value_column: Numeric column to plot.
        group_column: Column for grouping (one box per group).
        output_path: Path to save the chart.
        title: Chart title.
        file_type: csv, json, xlsx, auto.
        horizontal: Horizontal box plot.
    """
    plt = _load_matplotlib()
    pd = _load_pandas()
    if plt is None or pd is None:
        return "Error: matplotlib and pandas required."

    try:
        df = _load_df(pd, file_path, file_type)
        if isinstance(df, str):
            return df

        fig, ax = plt.subplots(figsize=(10, 6))

        if group_column and group_column in df.columns:
            groups = df[group_column].unique()
            data = [df[df[group_column] == g][value_column].dropna() for g in groups]
            ax.boxplot(data, labels=groups, vert=not horizontal)
        else:
            ax.boxplot(df[value_column].dropna(), vert=not horizontal)

        ax.set_title(title or f"Box Plot: {value_column}")
        if horizontal:
            ax.set_xlabel(value_column)
        else:
            ax.set_ylabel(value_column)

        plt.tight_layout()
        _ensure_output_path(output_path)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        size = os.path.getsize(output_path)
        return f"Box plot saved: {output_path} ({size:,} bytes)"
    except Exception as e:
        return f"Error creating box plot: {e!s}"


@tool(description="Create a time series chart with date axis. Supports multiple series and date formatting.")
async def chart_timeseries(
    file_path: str,
    date_column: str,
    value_columns: str,
    output_path: str = "/tmp/chart_timeseries.png",
    title: str = "",
    y_label: str = "",
    file_type: str = "auto",
    rolling_window: int = 0,
) -> str:
    """Create a time series chart.

    Args:
        file_path: Path to data file.
        date_column: Column containing dates.
        value_columns: Comma-separated columns to plot.
        output_path: Path to save the chart.
        title: Chart title.
        y_label: Y-axis label.
        file_type: csv, json, xlsx, auto.
        rolling_window: Rolling average window size (0 to disable).
    """
    plt = _load_matplotlib()
    pd = _load_pandas()
    if plt is None or pd is None:
        return "Error: matplotlib and pandas required."

    try:
        df = _load_df(pd, file_path, file_type)
        if isinstance(df, str):
            return df

        df[date_column] = pd.to_datetime(df[date_column])
        df = df.sort_values(date_column)

        fig, ax = plt.subplots(figsize=(14, 6))

        cols = [c.strip() for c in value_columns.split(",")]
        for col in cols:
            ax.plot(df[date_column], df[col], label=col, linewidth=1.5, alpha=0.8)
            if rolling_window > 0:
                rolling = df[col].rolling(window=rolling_window).mean()
                ax.plot(df[date_column], rolling, linewidth=2.5, linestyle="--",
                       label=f"{col} ({rolling_window}-period MA)")

        ax.set_xlabel("Date")
        ax.set_ylabel(y_label or value_columns)
        ax.set_title(title or f"Time Series: {value_columns}")
        ax.legend()
        ax.grid(True, alpha=0.3)

        fig.autofmt_xdate()

        plt.tight_layout()
        _ensure_output_path(output_path)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        size = os.path.getsize(output_path)
        return f"Time series chart saved: {output_path} ({size:,} bytes)"
    except Exception as e:
        return f"Error creating time series: {e!s}"


@tool(description="Create a dashboard with multiple subplots combining different chart types.")
async def chart_dashboard(
    file_path: str,
    output_path: str = "/tmp/chart_dashboard.png",
    title: str = "Data Dashboard",
    file_type: str = "auto",
) -> str:
    """Create a multi-panel dashboard with overview charts.

    Args:
        file_path: Path to data file.
        output_path: Path to save the dashboard.
        title: Dashboard title.
        file_type: csv, json, xlsx, auto.
    """
    plt = _load_matplotlib()
    pd = _load_pandas()
    if plt is None or pd is None:
        return "Error: matplotlib and pandas required."

    try:
        df = _load_df(pd, file_path, file_type)
        if isinstance(df, str):
            return df

        numeric_cols = df.select_dtypes(include=["number"]).columns[:4]
        if len(numeric_cols) == 0:
            return "No numeric columns found for dashboard."

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(title, fontsize=16, fontweight="bold")

        # Histogram of first numeric col
        ax = axes[0, 0]
        ax.hist(df[numeric_cols[0]].dropna(), bins=30, color="#4C72B0", alpha=0.7)
        ax.set_title(f"Distribution: {numeric_cols[0]}")

        # Bar chart of means
        ax = axes[0, 1]
        means = df[numeric_cols].mean()
        ax.bar(means.index, means.values, color="#55A868")
        ax.set_title("Mean Values")
        ax.tick_params(axis="x", rotation=45)

        # Box plots
        ax = axes[1, 0]
        df[numeric_cols].boxplot(ax=ax)
        ax.set_title("Box Plots")
        ax.tick_params(axis="x", rotation=45)

        # Correlation heatmap
        ax = axes[1, 1]
        corr = df[numeric_cols].corr()
        im = ax.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
        ax.set_xticks(range(len(corr)))
        ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(len(corr)))
        ax.set_yticklabels(corr.index, fontsize=8)
        ax.set_title("Correlations")
        fig.colorbar(im, ax=ax, shrink=0.8)

        plt.tight_layout()
        _ensure_output_path(output_path)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        size = os.path.getsize(output_path)
        return f"Dashboard saved: {output_path} ({size:,} bytes)"
    except Exception as e:
        return f"Error creating dashboard: {e!s}"


def _load_df(pd, file_path: str, file_type: str = "auto"):
    """Load a file into a DataFrame."""
    if not os.path.exists(file_path):
        return f"Error: File not found: {file_path}"

    if file_type == "auto":
        ext = os.path.splitext(file_path)[1].lower()
        type_map = {".csv": "csv", ".json": "json", ".xlsx": "xlsx", ".xls": "xlsx", ".parquet": "parquet"}
        file_type = type_map.get(ext, "csv")

    if file_type == "csv":
        return pd.read_csv(file_path)
    if file_type == "json":
        return pd.read_json(file_path)
    if file_type == "xlsx":
        return pd.read_excel(file_path)
    if file_type == "parquet":
        return pd.read_parquet(file_path)
    return pd.read_csv(file_path)
