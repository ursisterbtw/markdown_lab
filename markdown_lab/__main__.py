#!/usr/bin/env python3
"""
Command line interface for markdown_lab.
"""

import os
import sys


def main():
    """Main entry point that routes to appropriate interface."""
    # Check if running in legacy mode
    if os.environ.get("MARKDOWN_LAB_LEGACY", "").lower() in ("1", "true", "yes"):
        # Use legacy CLI
        from markdown_lab.core.scraper import main as legacy_main

        legacy_main(sys.argv[1:]) if len(sys.argv) > 1 else legacy_main([])
    else:
        # Use new CLI
        try:
            from markdown_lab.cli import cli_main

            cli_main()
        except ImportError:
            # Fall back to legacy CLI
            from markdown_lab.core.scraper import main as legacy_main

            legacy_main(sys.argv[1:]) if len(sys.argv) > 1 else legacy_main([])


if __name__ == "__main__":
    main()
