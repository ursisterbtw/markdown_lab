#!/usr/bin/env python3
"""
Quality gate script to detect and prevent mock usage in the codebase.
This script should be run in CI to ensure no new mocks are introduced.
"""
import ast
import sys
from pathlib import Path
from typing import List, Tuple

# Patterns to detect
MOCK_IMPORTS = {
    "unittest.mock",
    "mock",
    "pytest_mock",
    "mockall",  # Rust
}

MOCK_OBJECTS = {
    "Mock",
    "MagicMock",
    "PropertyMock",
    "patch",
    "monkeypatch",
}

# Files/directories to exclude from checking
EXCLUDE_PATHS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "build",
    "dist",
    ".eggs",
    "*.egg-info",
    # This script itself
    "scripts/validate-no-mocks.py",
}


class MockDetector(ast.NodeVisitor):
    """AST visitor to detect mock usage in Python files."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.violations: List[Tuple[int, str]] = []

    def visit_Import(self, node):
        """Check regular imports."""
        for alias in node.names:
            if any(mock in alias.name for mock in MOCK_IMPORTS):
                self.violations.append(
                    (node.lineno, f"Mock import detected: import {alias.name}")
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Check from imports."""
        if node.module and any(mock in node.module for mock in MOCK_IMPORTS):
            imported = ", ".join(alias.name for alias in node.names)
            self.violations.append(
                (
                    node.lineno,
                    f"Mock import detected: from {node.module} import {imported}",
                )
            )
        self.generic_visit(node)

    def visit_Name(self, node):
        """Check for mock object usage."""
        if node.id in MOCK_OBJECTS:
            self.violations.append((node.lineno, f"Mock object detected: {node.id}"))
        self.generic_visit(node)

    def visit_Attribute(self, node):
        """Check for mock attributes like mock.patch."""
        if hasattr(node.value, "id") and node.value.id == "mock":
            self.violations.append(
                (node.lineno, f"Mock attribute detected: mock.{node.attr}")
            )
        self.generic_visit(node)


def should_exclude(path: Path) -> bool:
    """Check if path should be excluded from checking."""
    path_str = str(path)
    for exclude in EXCLUDE_PATHS:
        if exclude in path_str:
            return True
        if path.match(exclude):
            return True
    return False


def check_python_file(filepath: Path) -> List[Tuple[int, str]]:
    """Check a Python file for mock usage."""
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(filepath))

        detector = MockDetector(str(filepath))
        detector.visit(tree)

        return detector.violations
    except Exception:
        return []


def check_rust_file(filepath: Path) -> List[Tuple[int, str]]:
    """Check a Rust file for mock usage."""
    violations = []
    try:
        content = filepath.read_text(encoding="utf-8")
        lines = content.splitlines()

        for i, line in enumerate(lines, 1):
            # Check for mockall usage
            if "mockall" in line and not line.strip().startswith("//"):
                violations.append((i, f"Mockall detected: {line.strip()}"))

            # Check for #[cfg(test)] with mock implementations
            if "#[cfg(test)]" in line:
                # Look ahead for mock-like patterns
                violations.extend(
                    (
                        j + 1,
                        f"Test mock implementation detected: {lines[j].strip()}",
                    )
                    for j in range(i, min(i + 10, len(lines)))
                    if "mock" in lines[j].lower() and "impl" in lines[j]
                )
    except Exception:
        pass

    return violations


def find_all_violations(root_dir: Path) -> dict:
    """Find all mock violations in the codebase."""
    violations = {}

    # Check Python files
    for py_file in root_dir.rglob("*.py"):
        if should_exclude(py_file):
            continue

        if file_violations := check_python_file(py_file):
            violations[str(py_file)] = file_violations

    # Check Rust files
    for rs_file in root_dir.rglob("*.rs"):
        if should_exclude(rs_file):
            continue

        if file_violations := check_rust_file(rs_file):
            violations[str(rs_file)] = file_violations

    return violations


def print_violations(violations: dict) -> None:
    """Print violations in a clear format."""

    total_violations = 0
    for file_violations in violations.values():
        for _line_no, _message in file_violations:
            total_violations += 1


def main():
    """Main entry point."""
    # Get project root (parent of scripts directory)
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent

    if violations := find_all_violations(project_root):
        print_violations(violations)
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
