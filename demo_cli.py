#!/usr/bin/env python3
"""
Demo script showcasing the new CLI/TUI features of markdown_lab.
"""

import subprocess
from pathlib import Path


def run_command(cmd, description, timeout=30):
    """Run a command and display the output."""

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)

        if result.stdout:

        if result.stderr:


    except subprocess.TimeoutExpired:
        pass")
    except Exception as e:
        pass")


def main():
    """Run the CLI demo."""

    # Clean up any previous demo files
    demo_files = [
        "demo_test.md",
        "demo_batch_output",
        "demo_links.txt",
        "demo_interactive.md",
        "demo_json.json",
        "demo_xml.xml",
    ]

    for file_path in demo_files:
        path = Path(file_path)
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            import shutil

            shutil.rmtree(path)

    # Test 1: Show help
    run_command(["python", "-m", "markdown_lab", "--help"], "Display main help")

    # Test 2: Show status
    run_command(
        ["python", "-m", "markdown_lab", "status"],
        "Show system status and configuration",
    )

    # Test 3: Convert single URL to Markdown
    run_command(
        [
            "python",
            "-m",
            "markdown_lab",
            "convert",
            "https://httpbin.org/html",
            "--output",
            "demo_test.md",
            "--verbose",
        ],
        "Convert single URL to Markdown",
    )

    # Test 4: Convert to JSON format
    run_command(
        [
            "python",
            "-m",
            "markdown_lab",
            "convert",
            "https://httpbin.org/html",
            "--output",
            "demo_json.json",
            "--format",
            "json",
            "--verbose",
        ],
        "Convert single URL to JSON",
    )

    # Test 5: Convert to XML format
    run_command(
        [
            "python",
            "-m",
            "markdown_lab",
            "convert",
            "https://httpbin.org/html",
            "--output",
            "demo_xml.xml",
            "--format",
            "xml",
            "--verbose",
        ],
        "Convert single URL to XML",
    )

    # Test 6: Create a demo links file and test batch conversion
    with open("demo_links.txt", "w") as f:
        f.write("https://httpbin.org/html\n")
        f.write("https://httpbin.org/json\n")

    run_command(
        [
            "python",
            "-m",
            "markdown_lab",
            "batch",
            "demo_links.txt",
            "--output",
            "demo_batch_output",
            "--verbose",
        ],
        "Batch conversion from links file",
    )

    # Test 7: Show convert command help
    run_command(
        ["python", "-m", "markdown_lab", "convert", "--help"],
        "Show convert command help",
    )

    # Test 8: Show batch command help
    run_command(
        ["python", "-m", "markdown_lab", "batch", "--help"], "Show batch command help"
    )

    # Test 9: Show sitemap command help
    run_command(
        ["python", "-m", "markdown_lab", "sitemap", "--help"],
        "Show sitemap command help",
    )

    # Test 10: Test with chunking enabled
    run_command(
        [
            "python",
            "-m",
            "markdown_lab",
            "convert",
            "https://httpbin.org/html",
            "--output",
            "demo_chunks.md",
            "--chunks",
            "--chunk-dir",
            "demo_chunks",
            "--verbose",
        ],
        "Convert with content chunking enabled",
    )


    # Show created files
    created_files = []
    for pattern in [
        "demo_*.md",
        "demo_*.json",
        "demo_*.xml",
        "demo_batch_output",
        "demo_chunks",
    ]:
        for path in Path(".").glob(pattern):
            created_files.append(str(path))

    if created_files:
        for file_path in sorted(created_files):
            if Path(file_path).is_file():
                size = Path(file_path).stat().st_size
            elif Path(file_path).is_dir():
                count = len(list(Path(file_path).rglob("*")))



if __name__ == "__main__":
    main()
