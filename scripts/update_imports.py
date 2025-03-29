#!/usr/bin/env python
"""
Utility script to update imports in existing code to use the new package structure.
"""

import argparse
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Update imports to use new markdown_lab package structure")
    parser.add_argument("files", nargs="+", help="Python files to update")
    parser.add_argument("--dry-run", action="store_true", help="Don't modify files, just print what would change")
    args = parser.parse_args()

    # Patterns to replace
    patterns = [
        (r"from\s+main\s+import", "from markdown_lab.main import"),
        (r"from\s+chunk_utils\s+import", "from markdown_lab.chunk_utils import"),
        (r"from\s+sitemap_utils\s+import", "from markdown_lab.sitemap_utils import"),
        (r"from\s+throttle\s+import", "from markdown_lab.throttle import"),
        (r"from\s+markdown_lab_rs\s+import", "from markdown_lab.markdown_lab_rs import"),
        (r"import\s+main", "import markdown_lab.main"),
        (r"import\s+chunk_utils", "import markdown_lab.chunk_utils"),
        (r"import\s+sitemap_utils", "import markdown_lab.sitemap_utils"),
        (r"import\s+throttle", "import markdown_lab.throttle"),
        (r"import\s+markdown_lab_rs", "import markdown_lab.markdown_lab_rs"),
        # Also patch patch statements or references to the old paths
        (r'@patch\("main\.', '@patch("markdown_lab.main.'),
        (r'@patch\("chunk_utils\.', '@patch("markdown_lab.chunk_utils.'),
        (r'@patch\("sitemap_utils\.', '@patch("markdown_lab.sitemap_utils.'),
        (r'@patch\("throttle\.', '@patch("markdown_lab.throttle.'),
        (r'@patch\("markdown_lab_rs\.', '@patch("markdown_lab.markdown_lab_rs.'),
    ]

    for file_path in args.files:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            print(f"Warning: {file_path} does not exist or is not a file, skipping.")
            continue

        if not file_path.endswith(".py"):
            print(f"Warning: {file_path} is not a Python file, skipping.")
            continue

        content = path.read_text()
        original_content = content

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)

        if content != original_content:
            if args.dry_run:
                print(f"Would update imports in {file_path}")
            else:
                path.write_text(content)
                print(f"Updated imports in {file_path}")
        else:
            print(f"No changes needed in {file_path}")


if __name__ == "__main__":
    main()
