#!/usr/bin/env python3
"""Script to standardize error handling by replacing generic Exception catches."""

import os
import re
from pathlib import Path
from typing import List, Tuple


def find_generic_exceptions(file_path: Path) -> List[Tuple[int, str]]:
    """Find lines with generic Exception catches."""
    issues = []

    with open(file_path, 'r') as f:
        lines = f.readlines()

    for i, line in enumerate(lines, 1):
        # Match "except Exception" patterns
        if re.search(r'except\s+Exception(?:\s+as\s+\w+)?:', line):
            issues.append((i, line.strip()))

    return issues


def suggest_specific_exception(context: str, file_path: Path) -> str:
    """Suggest a more specific exception based on context."""

    # Determine context from file and surrounding code
    if 'network' in str(file_path).lower() or 'client' in str(file_path).lower():
        return "(requests.exceptions.RequestException, OSError, ValueError)"
    if 'rust' in str(file_path).lower():
        return "RustIntegrationError"
    if 'convert' in str(file_path).lower():
        return "ConversionError"
    if 'parse' in str(file_path).lower():
        return "ParsingError"
    if 'config' in str(file_path).lower():
        return "ConfigurationError"
    if 'test' in str(file_path).lower():
        # Tests might legitimately catch all exceptions
        return "Exception  # OK in tests"
    return "MarkdownLabError"


def main():
    """Main function to find and report generic exception handling."""

    project_root = Path(__file__).parent.parent
    python_files = list(project_root.glob("**/*.py"))

    # Exclude venv, build, and other non-source directories
    python_files = [
        f for f in python_files
        if not any(part in f.parts for part in ['.venv', 'build', 'dist', '__pycache__', '.git'])
    ]

    total_issues = 0
    files_with_issues = []

    print("Scanning for generic Exception handling...\n")

    for file_path in python_files:
        issues = find_generic_exceptions(file_path)
        if issues:
            total_issues += len(issues)
            files_with_issues.append((file_path, issues))

    if files_with_issues:
        print(f"Found {total_issues} generic Exception catches in {len(files_with_issues)} files:\n")

        for file_path, issues in files_with_issues:
            rel_path = file_path.relative_to(project_root)
            print(f"\n{rel_path}:")
            for line_num, line_content in issues:
                suggestion = suggest_specific_exception(line_content, file_path)
                print(f"  Line {line_num}: {line_content}")
                print(f"    Suggested: except {suggestion}:")
    else:
        print("No generic Exception catches found! ✓")

    print(f"\n{'='*60}")
    print(f"Summary: {total_issues} issues in {len(files_with_issues)} files")

    if total_issues > 0:
        print("\nRecommendations:")
        print("1. Replace generic 'except Exception' with specific exception types")
        print("2. Use error hierarchy from markdown_lab.core.errors")
        print("3. Tests may keep generic catches if testing error handling")
        print("4. Add proper logging for unexpected exceptions")

    return total_issues


if __name__ == "__main__":
    exit(main())
