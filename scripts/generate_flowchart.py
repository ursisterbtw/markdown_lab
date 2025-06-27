import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Set

import pydot  # type: ignore

# --- Configuration ---

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# Default directories/files to exclude from scanning
DEFAULT_EXCLUDE_DIRS: Set[str] = {
    ".request_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".git",
    "__pycache__",
    ".DS_Store",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
    "target",
    "*.egg-info",  # Common pattern for Python package build artifacts
    "cache",
    ".cache",
    "secrets",
    ".idea",  # IDE specific
    ".vscode",  # IDE specific
    "*cache*",
}

# Styling constants
NEON_COLORS: List[str] = [
    "#00ff99",
    "#00ffcc",
    "#33ccff",
    "#ff00cc",
    "#ff3366",
    "#ffff00",
]
BG_COLOR = "#121212"
NODE_FILL_COLOR = "#1a1a1a"
DEFAULT_NODE_COLOR = "#00ff99"
DEFAULT_NODE_FONT_COLOR = "#00ffcc"
DEFAULT_EDGE_COLOR = "#39ff14"

# --- Core Logic ---


def scan_directory(
    path: Path,
    max_depth: int = 5,
    current_depth: int = 0,
    exclude_dirs: Optional[Set[str]] = None,
) -> Dict[str, Optional[Dict]]:
    """
    Recursively scans a directory using os.scandir() for better performance
    and returns its structure as a dictionary.

    Args:
        path: The directory path (Path object) to scan.
        max_depth: Maximum recursion depth.
        current_depth: Current recursion depth (used internally).
        exclude_dirs: A set of directory/file names to exclude.

    Returns:
        A dictionary representing the directory structure. Files are keys
        with None values, directories are keys with nested dictionaries.
        Special entries like '...' indicate depth limit reached, or
        permission/error messages.
    """
    if exclude_dirs is None:
        exclude_dirs = DEFAULT_EXCLUDE_DIRS

    if current_depth >= max_depth:
        return {"... (max depth reached)": None}

    structure: Dict[str, Optional[Dict]] = {}
    try:
        # Use os.scandir for better performance
        for entry in os.scandir(path):
            if entry.name in exclude_dirs:
                continue

            # Skip symlinks gracefully to avoid cycles and potential errors
            if entry.is_symlink():
                structure[f"{entry.name} (symlink)"] = None
                continue

            try:
                if entry.is_dir(follow_symlinks=False):
                    # Recurse into subdirectory
                    structure[entry.name] = scan_directory(
                        Path(entry.path), max_depth, current_depth + 1, exclude_dirs
                    )
                elif entry.is_file(follow_symlinks=False):
                    structure[entry.name] = None
                # Silently ignore other types like block devices, sockets etc.
                # Or add specific handling if needed:
                # else:
                #     structure[f"{entry.name} (type: unknown)"] = None

            except OSError as e:
                log.warning(f"Could not access metadata for {entry.path}: {e}")
                structure[f"{entry.name} (access error)"] = None

    except PermissionError:
        log.warning(f"Permission denied accessing directory: {path}")
        return {"Permission denied": None}
    except FileNotFoundError:
        log.error(f"Directory not found: {path}")
        return {"Not found": None}
    except OSError as e:
        log.error(f"OS error scanning directory {path}: {e}")
        return {f"Error: {e}": None}

    return structure


def create_graph(
    structure: Dict[str, Optional[Dict]],
    parent_id: Optional[str] = None,
    graph: Optional[pydot.Dot] = None,
) -> pydot.Dot:
    """
    Recursively creates a pydot graph from the directory structure dictionary.

    Args:
        structure: The directory structure dictionary from scan_directory.
        parent_id: The UUID of the parent node in the graph (used internally).
        graph: The pydot graph instance (used internally).

    Returns:
        The completed pydot graph.
    """
    if graph is None:
        # Initialize the graph with defaults
        graph = pydot.Dot(
            graph_type="digraph",
            rankdir="LR",  # Left-to-right layout
            bgcolor=BG_COLOR,
            fontname="Arial",  # Default font for labels if not overridden
            fontsize="12",  # Default font size
        )
        graph.set_node_defaults(
            style="filled, rounded",
            fillcolor=NODE_FILL_COLOR,
            fontcolor=DEFAULT_NODE_FONT_COLOR,
            fontname="Arial",
            fontsize="12",
            penwidth="1.5",
            color=DEFAULT_NODE_COLOR,  # Default border color
        )
        graph.set_edge_defaults(
            color=DEFAULT_EDGE_COLOR,
            penwidth="1.2",
        )

    # Sort items for consistent graph layout (optional but nice)
    sorted_items = sorted(structure.items())

    for key, value in sorted_items:
        # Generate a unique and safe ID for each node
        # Using UUID ensures valid DOT identifiers regardless of the key content
        node_id = f"node_{uuid.uuid4().hex[:10]}"  # Use slightly longer UUID part

        # Escape double quotes and backslashes in labels for DOT compatibility
        # pydot usually handles this, but explicit escaping is safer
        escaped_label = key.replace("\\", "\\\\").replace('"', '\\"')

        # Determine node shape and potentially color
        is_dir = isinstance(value, dict)
        shape = "box" if is_dir else "ellipse"

        # Vary node border color slightly based on name hash
        color_index = hash(key) % len(NEON_COLORS)
        node_color = NEON_COLORS[color_index]

        node = pydot.Node(
            node_id,
            label=f'"{escaped_label}"',  # Ensure label is quoted
            shape=shape,
            color=node_color,  # Border color
            # other attributes inherit from graph defaults (fillcolor, fontcolor etc.)
        )
        graph.add_node(node)

        if parent_id:
            edge = pydot.Edge(parent_id, node_id)
            graph.add_edge(edge)

        # Recurse if it's a directory (value is a dictionary)
        if is_dir and value:  # Check if value is a non-empty dict
            create_graph(value, node_id, graph)

    return graph


SVG_ANIMATION_CSS = f"""
    <style type="text/css">
    <![CDATA[
      /* Overall SVG background */
      svg {{
        background-color: {BG_COLOR};
      }}

      /* Node styling and animation */
      .node {{
        transition: transform 0.3s ease-in-out, filter 0.4s ease-in-out;
        animation: fadeIn 0.5s ease-out forwards, pulseGlow 4s infinite alternate;
        opacity: 0; /* Start transparent for fadeIn */
        filter: drop-shadow(0 0 4px rgba(0, 255, 153, 0.6));
      }}

      .node:hover {{
        transform: scale(1.1);
        filter: drop-shadow(0 0 10px rgba(0, 255, 153, 1));
        cursor: pointer;
      }}

      /* Edge styling and animation */
      .edge {{
        stroke-dasharray: 8, 4; /* Dashed line pattern */
        animation: dash 10s linear infinite, glow 3s infinite alternate;
      }}

      .edge path {{
         stroke: {DEFAULT_EDGE_COLOR}; /* Ensure path color is set */
      }}
      .edge polygon {{
         fill: {DEFAULT_EDGE_COLOR}; /* Ensure arrowhead color is set */
         stroke: {DEFAULT_EDGE_COLOR};
      }}

      /* Text styling within nodes */
      .node text {{
        fill: {DEFAULT_NODE_FONT_COLOR} !important; /* Ensure high specificity */
        font-weight: bold;
        pointer-events: none; /* Prevent text from blocking node hover */
      }}

      /* Keyframe animations */
      @keyframes fadeIn {{
        to {{ opacity: 1; }}
      }}

      @keyframes pulseGlow {{
        0% {{ filter: drop-shadow(0 0 4px rgba(0, 255, 153, 0.6)); opacity: 0.9; }}
        50% {{ filter: drop-shadow(0 0 8px rgba(0, 255, 153, 0.8)); }}
        100% {{ filter: drop-shadow(0 0 6px rgba(0, 255, 204, 0.9)); opacity: 1; }}
      }}

      @keyframes glow {{
        from {{ stroke-opacity: 0.7; filter: drop-shadow(0 0 2px {DEFAULT_EDGE_COLOR}); }}
        to {{ stroke-opacity: 1; filter: drop-shadow(0 0 4px {DEFAULT_EDGE_COLOR}); }}
      }}

      @keyframes dash {{
        to {{ stroke-dashoffset: -100; }} /* Adjust value based on dasharray */
      }}
    ]]>
    </style>
"""


def add_svg_animation(svg_content: str) -> str:
    """
    Injects CSS animation styles and node/edge classes into SVG content.

    Adds CSS animation rules and assigns `class="node"` and `class="edge"` to corresponding SVG group elements. If the `<svg>` tag is found, the animation CSS is inserted immediately after it; otherwise, the original SVG content is returned unchanged.
    """
    # Improved regex that properly preserves whitespace between attributes
    # Check if class already exists first
    svg_content = re.sub(
        r'(<g\s+id="node\d+")(?!\s+class=")',  # Match node without class
        r'\1 class="node"',  # Add class with proper space
        svg_content,
        flags=re.IGNORECASE,
    )

    # Same fix for edge groups
    svg_content = re.sub(
        r'(<g\s+id="edge\d+")(?!\s+class=")',  # Match edge without class
        r'\1 class="edge"',  # Add class with proper space
        svg_content,
        flags=re.IGNORECASE,
    )

    if svg_tag_match := re.search(r"<svg[^>]*>", svg_content, re.IGNORECASE):
        insert_pos = svg_tag_match.end()
        # Inject the CSS styles right after the opening <svg> tag
        return svg_content[:insert_pos] + SVG_ANIMATION_CSS + svg_content[insert_pos:]
    log.warning("Could not find <svg> tag to inject CSS animations.")
    return svg_content  # Return unmodified content if tag not found


def check_dependencies() -> bool:
    """
    Checks for the presence of the Graphviz 'dot' executable in the system PATH.

    Returns:
        True if 'dot' is found, False otherwise.
    """
    dot_path = shutil.which("dot")
    if not dot_path:
        log.error("Graphviz 'dot' command not found in PATH.")
        log.error("Please install Graphviz: https://graphviz.org/download/")
        return False
    log.info(f"Found 'dot' executable at: {dot_path}")
    return True


def run_dot(dot_file: Path, svg_file: Path) -> bool:
    """Runs the Graphviz 'dot' command to convert DOT to SVG."""
    command = [
        "dot",
        "-Tsvg",
        str(dot_file),
        "-o",
        str(svg_file),
    ]
    log.info(f"Running command: {' '.join(command)}")
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception on non-zero exit code immediately
            encoding="utf-8",
        )
        if result.returncode != 0:
            log.error(f"'dot' command failed with exit code {result.returncode}")
            log.error(f"Stderr:\n{result.stderr}")
            log.error(f"Stdout:\n{result.stdout}")
            return False
        log.info(f"'dot' command completed successfully. SVG saved to {svg_file}")
        return True
    except FileNotFoundError:
        log.error("Failed to run 'dot' command. Is Graphviz installed and in PATH?")
        return False
    except Exception as e:
        log.exception(f"An unexpected error occurred while running 'dot': {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate an animated SVG flowchart of a directory structure.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "repo_path",
        nargs="?",
        default=".",
        help="Path to the directory (repository root) to scan.",
        type=Path,
    )
    parser.add_argument(
        "-o",
        "--output",
        default="flowchart.svg",
        help="Output SVG file name.",
        type=Path,
    )
    parser.add_argument(
        "--dot-output",
        default="flowchart.dot",
        help="Intermediate DOT file name.",
        type=Path,
    )
    parser.add_argument(
        "-d",
        "--max-depth",
        type=int,
        default=4,
        help="Maximum depth to scan directories.",
    )
    parser.add_argument(
        "-e",
        "--exclude",
        nargs="*",
        default=list(DEFAULT_EXCLUDE_DIRS),
        help="Directory or file names to exclude.",
    )
    parser.add_argument(
        "--no-animation",
        action="store_true",
        help="Generate a static SVG without animations.",
    )

    args = parser.parse_args()

    # Convert exclude list to set for efficient lookup
    exclude_set = set(args.exclude)

    # --- Dependency Check ---
    if not check_dependencies():
        sys.exit(1)

    # --- Directory Scanning ---
    if not args.repo_path.is_dir():
        log.error(f"Input path is not a valid directory: {args.repo_path}")
        sys.exit(1)

    log.info(
        f"Scanning directory: {args.repo_path.resolve()} up to depth {args.max_depth}"
    )
    log.info(f"Excluding: {', '.join(sorted(exclude_set))}")
    directory_structure = scan_directory(
        args.repo_path, max_depth=args.max_depth, exclude_dirs=exclude_set
    )

    if not directory_structure:
        log.warning("Scan returned an empty structure. No graph will be generated.")
        sys.exit(0)

    # --- Graph Creation ---
    log.info("Generating flowchart graph...")
    try:
        graph = create_graph(directory_structure)
    except Exception as e:
        log.exception(f"Failed to create graph structure: {e}")
        sys.exit(1)

    # --- DOT File Generation ---
    log.info(f"Saving DOT representation to {args.dot_output}...")
    try:
        # Use write_raw for potentially better compatibility, ensure encoding
        with open(args.dot_output, "w", encoding="utf-8") as f:
            # pydot's to_string() can sometimes be more reliable than write() methods
            dot_string = graph.to_string()
            f.write(dot_string)
        log.info(f"DOT file saved successfully to {args.dot_output}")
    except IOError as e:
        log.error(f"Failed to write DOT file {args.dot_output}: {e}")
        sys.exit(1)
    except Exception as e:
        # Catch potential pydot errors during string conversion/writing
        log.exception(f"An error occurred writing the DOT file: {e}")
        sys.exit(1)

    # --- SVG Generation ---
    log.info("Generating SVG flowchart using 'dot'...")
    if not run_dot(args.dot_output, args.output):
        log.error(
            "Failed to generate SVG file. Check Graphviz installation and DOT file validity."
        )
        sys.exit(1)

    # --- SVG Animation ---
    if not args.no_animation:
        log.info("Adding animations to SVG...")
        try:
            with open(args.output, "r", encoding="utf-8") as f:
                svg_content = f.read()

            animated_svg = add_svg_animation(svg_content)

            with open(args.output, "w", encoding="utf-8") as f:
                f.write(animated_svg)
            log.info(f"Animated flowchart saved as {args.output.resolve()}")

        except FileNotFoundError:
            # This shouldn't happen if run_dot succeeded, but check anyway
            log.error(f"SVG file {args.output} not found after generation step.")
            sys.exit(1)
        except IOError as e:
            log.error(
                f"Failed to read or write SVG file {args.output} for animation: {e}"
            )
            sys.exit(1)
        except Exception as e:
            log.exception(
                f"An unexpected error occurred during SVG animation processing: {e}"
            )
            sys.exit(1)
    else:
        log.info(f"Static flowchart saved as {args.output.resolve()}")

    log.info("Process completed successfully.")


if __name__ == "__main__":
    main()
