"""
Test configuration and fixtures for markdown_lab.
"""

import sys
from pathlib import Path

# Add the repository root to the Python path to ensure imports work correctly
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))