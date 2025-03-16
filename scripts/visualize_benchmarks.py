#!/usr/bin/env python3
import json
import os
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

def load_benchmark_data():
    """Load benchmark data from Criterion output directory."""
    criterion_dir = Path("target/criterion")
    if not criterion_dir.exists():
        print("No benchmark data found. Run 'cargo bench' first.")
        return None

    data = []
    for bench_dir in criterion_dir.glob("*/new"):
        if bench_dir.is_dir():
            estimates_file = bench_dir.parent / "estimates.json"
            if estimates_file.exists():
                with open(estimates_file) as f:
                    estimates = json.load(f)
                    benchmark_name = bench_dir.parent.name
                    mean_time = estimates["mean"]["point_estimate"] / 1e9  # Convert to seconds
                    std_dev = estimates["mean"]["standard_error"] / 1e9
                    data.append({
                        "benchmark": benchmark_name,
                        "mean_time": mean_time,
                        "std_dev": std_dev
                    })

    return pd.DataFrame(data)

def create_benchmark_plot(df):
    """Create an interactive bar plot of benchmark results."""
    if df is None or df.empty:
        return

    fig = go.Figure()

    # Add bars for mean execution time
    fig.add_trace(go.Bar(
        name="Execution Time",
        x=df["benchmark"],
        y=df["mean_time"],
        error_y=dict(type="data", array=df["std_dev"]),
        marker_color="rgb(55, 83, 109)"
    ))

    # Update layout
    fig.update_layout(
        title="Benchmark Results",
        xaxis_title="Benchmark",
        yaxis_title="Time (seconds)",
        template="plotly_white",
        showlegend=False,
        hovermode="x"
    )

    # Save the plot
    fig.write_html("target/criterion/benchmark_results.html")
    print("Benchmark visualization saved to target/criterion/benchmark_results.html")

def main():
    df = load_benchmark_data()
    create_benchmark_plot(df)

if __name__ == "__main__":
    main()
