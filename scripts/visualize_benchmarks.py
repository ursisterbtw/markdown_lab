#!/usr/bin/env python3
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go


def load_benchmark_data():
    """
    Loads benchmark results from Criterion's output directory and returns them as a DataFrame.

    Scans the "target/criterion" directory for benchmark result subdirectories, extracts mean execution times and standard errors from "estimates.json" files, and compiles the data into a pandas DataFrame. Returns None if no benchmark data is found.
    """
    criterion_dir = Path("target/criterion")
    if not criterion_dir.exists():
        return None

    data = []
    for bench_dir in criterion_dir.glob("*/new"):
        if bench_dir.is_dir():
            estimates_file = bench_dir.parent / "estimates.json"
            if estimates_file.exists():
                with open(estimates_file) as f:
                    estimates = json.load(f)
                    benchmark_name = bench_dir.parent.name
                    mean_time = (
                        estimates["mean"]["point_estimate"] / 1e9
                    )  # Convert to seconds
                    std_dev = estimates["mean"]["standard_error"] / 1e9
                    data.append(
                        {
                            "benchmark": benchmark_name,
                            "mean_time": mean_time,
                            "std_dev": std_dev,
                        }
                    )

    return pd.DataFrame(data)


def create_benchmark_plot(df):
    """
    Generates and saves an interactive bar chart visualizing benchmark execution times.

    If the provided DataFrame is empty or None, the function returns without creating a plot. The resulting HTML file is saved to "target/criterion/benchmark_results.html".
    """
    if df is None or df.empty:
        return

    fig = go.Figure()

    # Add bars for mean execution time
    fig.add_trace(
        go.Bar(
            name="Execution Time",
            x=df["benchmark"],
            y=df["mean_time"],
            error_y={"type": "data", "array": df["std_dev"]},
            marker_color="rgb(55, 83, 109)",
        )
    )

    # Update layout
    fig.update_layout(
        title="Benchmark Results",
        xaxis_title="Benchmark",
        yaxis_title="Time (seconds)",
        template="plotly_white",
        showlegend=False,
        hovermode="x",
    )

    # Save the plot
    fig.write_html("target/criterion/benchmark_results.html")


def main():
    """
    Loads benchmark data and generates an interactive benchmark results plot.
    """
    df = load_benchmark_data()
    create_benchmark_plot(df)


if __name__ == "__main__":
    main()
