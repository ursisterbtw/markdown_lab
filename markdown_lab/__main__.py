"""
Command-line interface for markdown_lab.
"""

from .main import main

if __name__ == "__main__":
    import sys

    try:
        from .markdown_lab_rs import _rs_chunk_markdown
        print("Rust extension is available!")
    except ImportError:
        print("WARNING: Rust extension not available. Using Python fallback implementation.")

    # Extract command line arguments
    args = sys.argv[1:]

    if not args:
        print("Usage: python -m markdown_lab [URL] [OUTPUT_FILE]")
        print("Example: python -m markdown_lab https://example.com output.md")
        sys.exit(1)

    # Simple CLI wrapper around the main function
    url = args[0]
    output_file = args[1] if len(args) > 1 else f"output_{url.replace('://', '_').replace('/', '_')}.md"

    # Run the main function with default parameters
    main(
        url=url,
        output_file=output_file,
        output_format="markdown",
        save_chunks=True,
        chunk_dir="chunks",
        chunk_format="jsonl",
        requests_per_second=1.0,
    )
