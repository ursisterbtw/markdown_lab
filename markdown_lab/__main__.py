#!/usr/bin/env python3
"""
Command line interface for markdown_lab.
"""

import sys

from markdown_lab.core.scraper import main

if __name__ == "__main__":
    # Re-execute main with the same arguments
    main(sys.argv[1:]) if len(sys.argv) > 1 else main([])
