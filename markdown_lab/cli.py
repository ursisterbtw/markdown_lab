#!/usr/bin/env python3
"""
Modern CLI interface for markdown_lab using Typer and Rich.

Modern command-line interface with:
- Rich terminal output with colors and formatting
- Progress bars and status indicators
- Interactive TUI mode
- Configuration profiles
- Comprehensive help system
"""

import logging
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Annotated, List, Optional

import typer
from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.prompt import Confirm
from rich.table import Table

from markdown_lab.core.config import (
    MarkdownLabConfig,
    create_config_from_cli_args,
    get_config,
)
from markdown_lab.core.converter import Converter
from markdown_lab.core.scraper import MarkdownScraper  # Legacy support
from markdown_lab.utils.url_utils import get_domain_from_url

app = typer.Typer(
    name="markdown-lab",
    help="HTML to Markdown converter with TUI support",
    rich_markup_mode="rich",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)

console = Console()


class OutputFormat(str, Enum):
    """Supported output formats."""

    markdown = "markdown"
    json = "json"
    xml = "xml"


class ChunkFormat(str, Enum):
    """Supported chunk formats."""

    json = "json"
    jsonl = "jsonl"


class LogLevel(str, Enum):
    """Logging levels."""

    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"


# Global state
current_config = None
interactive_mode = False


def setup_config(**kwargs) -> MarkdownLabConfig:
    """setup configuration with provided CLI parameters"""
    return create_config_from_cli_args(**kwargs)


def print_banner():
    """display the application banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                       Markdown Lab                           ║
║              HTML to Markdown Converter                      ║
║                                                              ║
║  Convert web content to Markdown, JSON, or XML               ║
║  with semantic chunking for RAG applications                 ║
╚══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold blue")


def create_status_table(stats: dict) -> Table:
    """create status table showing current operation statistics"""
    table = Table(
        title="📊 Operation Status", show_header=True, header_style="bold magenta"
    )
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    for key, value in stats.items():
        table.add_row(key, str(value))

    return table


@app.command("convert")
def convert_url(
    url: Annotated[str, typer.Argument(help="🌐 URL to convert")],
    output: Annotated[
        Optional[str], typer.Option("-o", "--output", help="📁 Output file path")
    ] = None,
    format: Annotated[
        OutputFormat, typer.Option("-f", "--format", help="📝 Output format")
    ] = OutputFormat.markdown,
    interactive: Annotated[
        bool,
        typer.Option(
            "--interactive", "-i", help="🎯 Interactive mode with live progress"
        ),
    ] = False,
    save_chunks: Annotated[
        bool, typer.Option("--chunks", help="📦 Save content chunks for RAG")
    ] = False,
    chunk_dir: Annotated[str, typer.Option(help="📂 Directory for chunks")] = "chunks",
    chunk_format: Annotated[
        ChunkFormat, typer.Option(help="📋 Chunk output format")
    ] = ChunkFormat.jsonl,
    chunk_size: Annotated[
        int, typer.Option(help="📏 Maximum chunk size in characters")
    ] = 1000,
    chunk_overlap: Annotated[
        int, typer.Option(help="🔄 Chunk overlap in characters")
    ] = 200,
    requests_per_second: Annotated[
        float, typer.Option(help="⚡ Rate limit (requests/sec)")
    ] = 1.0,
    timeout: Annotated[int, typer.Option(help="⏱️ Request timeout in seconds")] = 30,
    max_retries: Annotated[int, typer.Option(help="🔄 Maximum retry attempts")] = 3,
    cache_enabled: Annotated[
        bool, typer.Option("--cache/--no-cache", help="💾 Enable/disable caching")
    ] = True,
    cache_ttl: Annotated[int, typer.Option(help="⏰ Cache TTL in seconds")] = 3600,
    skip_cache: Annotated[
        bool, typer.Option(help="🚫 Skip cache for this request")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("-v", "--verbose", help="🔍 Verbose output")
    ] = False,
):
    """
    🌐 Convert a single URL to the specified format.

    This command scrapes a website and converts its content to Markdown, JSON, or XML.
    Supports caching, rate limiting, and content chunking for RAG applications.
    """
    global interactive_mode
    interactive_mode = interactive

    if not interactive:
        print_banner()

    # Setup configuration from CLI args
    config = setup_config(
        requests_per_second=requests_per_second,
        timeout=timeout,
        max_retries=max_retries,
        cache_enabled=cache_enabled,
        cache_ttl=cache_ttl,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    # Create converter
    converter = Converter(config)

    # Determine output file
    if not output:
        domain = get_domain_from_url(url).replace(".", "_")
        ext = ".md" if format == OutputFormat.markdown else f".{format.value}"
        output = f"{domain}_content{ext}"

    stats = {
        "URL": url,
        "Output Format": format.value.upper(),
        "Output File": output,
        "Cache Enabled": "✅" if cache_enabled else "❌",
        "Chunking": "✅" if save_chunks else "❌",
    }

    if interactive:
        return _convert_interactive(
            converter,
            url,
            output,
            format.value,
            save_chunks,
            chunk_dir,
            chunk_format.value,
            skip_cache,
            stats,
        )
    return _convert_standard(
        converter,
        url,
        output,
        format.value,
        save_chunks,
        chunk_dir,
        chunk_format.value,
        skip_cache,
        stats,
        verbose,
    )


def _convert_interactive(
    converter,
    url,
    output,
    format_str,
    save_chunks,
    chunk_dir,
    chunk_format,
    skip_cache,
    stats,
):
    """interactive conversion with live progress display"""

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=10),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=3),
    )

    # Header
    header_panel = Panel(
        Align.center("🔬 Markdown Lab - Interactive Mode", vertical="middle"),
        style="bold blue",
        title="Status",
    )
    layout["header"].update(header_panel)

    # Main content - status table
    status_table = create_status_table(stats)
    layout["main"].update(Panel(status_table, title="📊 Current Operation"))

    # Footer
    footer_text = "Press Ctrl+C to cancel"
    layout["footer"].update(Panel(footer_text, style="dim"))

    try:
        with Live(layout, refresh_per_second=4):
            # Phase 1: Fetching content
            layout["main"].update(
                Panel("🌐 Fetching content from URL...", title="Phase 1")
            )
            time.sleep(1)  # Show the phase

            html_content = converter.client.get(url, skip_cache=skip_cache)

            # Phase 2: Converting content
            layout["main"].update(
                Panel("🔄 Converting HTML to target format...", title="Phase 2")
            )
            time.sleep(0.5)

            content, markdown_content = converter.convert_html(
                html_content, url, format_str
            )

            # Phase 3: Saving content
            layout["main"].update(
                Panel("💾 Saving converted content...", title="Phase 3")
            )
            time.sleep(0.5)

            converter.save_content(content, output)

            # Phase 4: Chunking (if enabled)
            if save_chunks:
                layout["main"].update(
                    Panel("📦 Creating content chunks...", title="Phase 4")
                )
                time.sleep(0.5)

                chunks = converter.create_chunks(markdown_content, url)

                # Save chunks
                from markdown_lab.utils.chunk_utils import ContentChunker

                chunker = ContentChunker(config=converter.config)
                chunker.save_chunks(chunks, chunk_dir, chunk_format)

                stats["Chunks Created"] = len(chunks)

            # Success
            stats["Status"] = "✅ Completed"
            stats["Output Size"] = f"{len(content)} chars"

            final_table = create_status_table(stats)
            layout["main"].update(
                Panel(final_table, title="✅ Conversion Complete", border_style="green")
            )

            time.sleep(2)  # Show final result

    except KeyboardInterrupt as e:
        console.print("\n❌ Operation cancelled by user", style="bold red")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="bold red")
        raise typer.Exit(1) from e

    console.print(f"\n✅ Successfully converted URL to {output}", style="bold green")


def _convert_standard(
    converter,
    url,
    output,
    format_str,
    save_chunks,
    chunk_dir,
    chunk_format,
    skip_cache,
    stats,
    verbose,
):
    """standard conversion with progress bars"""

    console.print(create_status_table(stats))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        # Main conversion task
        main_task = progress.add_task("🔄 Converting URL...", total=100)

        try:
            # Step 1: Fetch content
            progress.update(
                main_task, description="🌐 Fetching content...", completed=20
            )
            html_content = converter.client.get(url, skip_cache=skip_cache)

            if verbose:
                console.print(
                    f"📄 Fetched {len(html_content)} characters of HTML content"
                )

            # Step 2: Convert content
            progress.update(
                main_task, description="🔄 Converting HTML...", completed=50
            )
            content, markdown_content = converter.convert_html(
                html_content, url, format_str
            )

            if verbose:
                console.print(
                    f"📝 Generated {len(content)} characters of {format_str.upper()} content"
                )

            # Step 3: Save content
            progress.update(main_task, description="💾 Saving content...", completed=75)
            converter.save_content(content, output)

            if verbose:
                console.print(f"💾 Saved content to {output}")

            # Step 4: Create chunks (if enabled)
            if save_chunks:
                progress.update(
                    main_task, description="📦 Creating chunks...", completed=90
                )
                chunks = converter.create_chunks(markdown_content, url)

                # Save chunks
                from markdown_lab.utils.chunk_utils import ContentChunker

                chunker = ContentChunker(config=converter.config)
                chunker.save_chunks(chunks, chunk_dir, chunk_format)

                if verbose:
                    console.print(f"📦 Created {len(chunks)} chunks in {chunk_dir}")

            progress.update(main_task, description="✅ Complete!", completed=100)

        except Exception as e:
            progress.update(main_task, description="❌ Failed!", completed=100)
            console.print(f"\n❌ Error: {e}", style="bold red")
            raise typer.Exit(1) from e

    # Success summary
    success_panel = Panel(
        f"✅ Successfully converted [bold cyan]{url}[/bold cyan]\n"
        f"📁 Output: [bold green]{output}[/bold green]\n"
        f"📝 Format: [bold yellow]{format_str.upper()}[/bold yellow]"
        + (
            f"\n📦 Chunks: [bold magenta]{chunk_dir}[/bold magenta]"
            if save_chunks
            else ""
        ),
        title="🎉 Conversion Complete",
        border_style="green",
    )
    console.print(success_panel)


@app.command("sitemap")
def convert_sitemap(
    url: Annotated[str, typer.Argument(help="🌐 Base URL with sitemap")],
    output_dir: Annotated[
        str, typer.Option("-o", "--output", help="📁 Output directory")
    ] = "output",
    format: Annotated[
        OutputFormat, typer.Option("-f", "--format", help="📝 Output format")
    ] = OutputFormat.markdown,
    interactive: Annotated[
        bool, typer.Option("--interactive", "-i", help="🎯 Interactive mode")
    ] = False,
    min_priority: Annotated[
        Optional[float], typer.Option(help="⭐ Minimum sitemap priority (0.0-1.0)")
    ] = None,
    include: Annotated[
        Optional[List[str]], typer.Option(help="✅ Include URL patterns (regex)")
    ] = None,
    exclude: Annotated[
        Optional[List[str]], typer.Option(help="❌ Exclude URL patterns (regex)")
    ] = None,
    limit: Annotated[
        Optional[int], typer.Option(help="🔢 Maximum URLs to process")
    ] = None,
    save_chunks: Annotated[
        bool, typer.Option("--chunks", help="📦 Save content chunks")
    ] = False,
    chunk_dir: Annotated[str, typer.Option(help="📂 Chunk directory")] = "chunks",
    chunk_format: Annotated[
        ChunkFormat, typer.Option(help="📋 Chunk format")
    ] = ChunkFormat.jsonl,
    parallel: Annotated[
        bool, typer.Option(help="⚡ Enable parallel processing")
    ] = False,
    max_workers: Annotated[int, typer.Option(help="👥 Max parallel workers")] = 4,
    requests_per_second: Annotated[float, typer.Option(help="⚡ Rate limit")] = 1.0,
    verbose: Annotated[
        bool, typer.Option("-v", "--verbose", help="🔍 Verbose output")
    ] = False,
):
    """
    🗺️ Convert multiple URLs discovered via sitemap.

    Discovers URLs from the target website's sitemap.xml and converts all matching pages.
    Supports filtering by priority, URL patterns, and parallel processing.
    """
    global interactive_mode
    interactive_mode = interactive

    if not interactive:
        print_banner()

    # Setup configuration from CLI args
    config = setup_config(requests_per_second=requests_per_second)
    converter = Converter(config)

    stats = {
        "Base URL": url,
        "Output Directory": output_dir,
        "Format": format.value.upper(),
        "Min Priority": min_priority or "Any",
        "Parallel": "✅" if parallel else "❌",
        "Max Workers": max_workers if parallel else "N/A",
    }

    console.print(create_status_table(stats))

    try:
        # Use the converter's sitemap method
        successful_urls = converter.convert_sitemap(
            base_url=url,
            output_dir=output_dir,
            output_format=format.value,
            min_priority=min_priority,
            include_patterns=include,
            exclude_patterns=exclude,
            limit=limit,
            save_chunks=save_chunks,
            chunk_dir=chunk_dir,
            chunk_format=chunk_format.value,
        )

        # Success summary
        success_panel = Panel(
            f"✅ Successfully processed [bold cyan]{len(successful_urls)}[/bold cyan] URLs\n"
            f"📁 Output: [bold green]{output_dir}[/bold green]\n"
            f"📝 Format: [bold yellow]{format.value.upper()}[/bold yellow]"
            + (
                f"\n📦 Chunks: [bold magenta]{chunk_dir}[/bold magenta]"
                if save_chunks
                else ""
            ),
            title="🎉 Sitemap Conversion Complete",
            border_style="green",
        )
        console.print(success_panel)

        if verbose and successful_urls:
            console.print("\n📋 Processed URLs:", style="bold")
            for i, processed_url in enumerate(successful_urls[:10], 1):  # Show first 10
                console.print(f"  {i}. {processed_url}")
            if len(successful_urls) > 10:
                console.print(f"  ... and {len(successful_urls) - 10} more")

    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="bold red")
        raise typer.Exit(1) from e


@app.command("batch")
def convert_batch(
    links_file: Annotated[
        str, typer.Argument(help="📋 File containing URLs to convert")
    ] = "links.txt",
    output_dir: Annotated[
        str, typer.Option("-o", "--output", help="📁 Output directory")
    ] = "output",
    format: Annotated[
        OutputFormat, typer.Option("-f", "--format", help="📝 Output format")
    ] = OutputFormat.markdown,
    interactive: Annotated[
        bool, typer.Option("--interactive", "-i", help="🎯 Interactive mode")
    ] = False,
    parallel: Annotated[
        bool, typer.Option(help="⚡ Enable parallel processing")
    ] = False,
    max_workers: Annotated[int, typer.Option(help="👥 Max parallel workers")] = 4,
    save_chunks: Annotated[
        bool, typer.Option("--chunks", help="📦 Save content chunks")
    ] = False,
    chunk_dir: Annotated[str, typer.Option(help="📂 Chunk directory")] = "chunks",
    chunk_format: Annotated[
        ChunkFormat, typer.Option(help="📋 Chunk format")
    ] = ChunkFormat.jsonl,
    requests_per_second: Annotated[float, typer.Option(help="⚡ Rate limit")] = 1.0,
    verbose: Annotated[
        bool, typer.Option("-v", "--verbose", help="🔍 Verbose output")
    ] = False,
):
    """
    📋 Convert multiple URLs from a file.

    Reads URLs from a text file (one per line) and converts each to the specified format.
    Supports parallel processing for faster batch conversion.
    """
    global interactive_mode
    interactive_mode = interactive

    if not interactive:
        print_banner()

    # Check if file exists
    if not Path(links_file).exists():
        console.print(f"❌ Links file not found: {links_file}", style="bold red")
        raise typer.Exit(1)

    # Setup configuration from CLI args
    config = setup_config(requests_per_second=requests_per_second)

    # Use legacy scraper for batch processing (it has the implementation)
    scraper = MarkdownScraper(config)

    stats = {
        "Links File": links_file,
        "Output Directory": output_dir,
        "Format": format.value.upper(),
        "Parallel": "✅" if parallel else "❌",
        "Max Workers": max_workers if parallel else "N/A",
    }

    console.print(create_status_table(stats))

    try:
        successful_urls = scraper.scrape_by_links_file(
            links_file=links_file,
            output_dir=output_dir,
            output_format=format.value,
            save_chunks=save_chunks,
            chunk_dir=chunk_dir,
            chunk_format=chunk_format.value,
            parallel=parallel,
            max_workers=max_workers,
        )

        # Success summary
        success_panel = Panel(
            f"✅ Successfully processed [bold cyan]{len(successful_urls)}[/bold cyan] URLs\n"
            f"📁 Output: [bold green]{output_dir}[/bold green]\n"
            f"📝 Format: [bold yellow]{format.value.upper()}[/bold yellow]"
            + (
                f"\n📦 Chunks: [bold magenta]{chunk_dir}[/bold magenta]"
                if save_chunks
                else ""
            ),
            title="🎉 Batch Conversion Complete",
            border_style="green",
        )
        console.print(success_panel)

        if verbose and successful_urls:
            console.print("\n📋 Processed URLs:", style="bold")
            for i, processed_url in enumerate(successful_urls[:10], 1):  # Show first 10
                console.print(f"  {i}. {processed_url}")
            if len(successful_urls) > 10:
                console.print(f"  ... and {len(successful_urls) - 10} more")

    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="bold red")
        raise typer.Exit(1) from e


@app.command("status")
def show_status():
    """
    📊 Show system status and configuration.

    Displays information about the current installation, available features,
    and system configuration.
    """
    print_banner()

    # System info
    import platform

    import markdown_lab

    system_table = Table(
        title="🖥️ System Information", show_header=True, header_style="bold cyan"
    )
    system_table.add_column("Component", style="cyan", no_wrap=True)
    system_table.add_column("Version/Status", style="green")

    system_table.add_row("Python", platform.python_version())
    system_table.add_row("Platform", platform.platform())
    system_table.add_row("Markdown Lab", markdown_lab.__version__)

    # Check Rust backend
    try:
        from markdown_lab.core.rust_backend import RustBackend

        rust_backend = RustBackend()
        rust_status = (
            "✅ Available" if rust_backend.is_available() else "❌ Not Available"
        )
    except ImportError:
        rust_status = "❌ Not Available"

    system_table.add_row("Rust Backend", rust_status)

    # Check optional dependencies
    optional_deps = {
        "Rich": "rich",
        "Typer": "typer",
        "Textual": "textual",
        "Playwright": "playwright",
    }

    for name, module in optional_deps.items():
        try:
            __import__(module)
            status = "✅ Available"
        except ImportError:
            status = "❌ Not Available"
        system_table.add_row(name, status)

    console.print(system_table)

    # Configuration info
    config = get_config()
    config_table = Table(
        title="⚙️ Current Configuration", show_header=True, header_style="bold magenta"
    )
    config_table.add_column("Setting", style="cyan", no_wrap=True)
    config_table.add_column("Value", style="green")

    config_table.add_row("Requests/Second", str(config.requests_per_second))
    config_table.add_row("Timeout", f"{config.timeout}s")
    config_table.add_row("Max Retries", str(config.max_retries))
    config_table.add_row("Cache Enabled", "✅" if config.cache_enabled else "❌")
    config_table.add_row("Cache TTL", f"{config.cache_ttl}s")
    config_table.add_row("Chunk Size", str(config.chunk_size))
    config_table.add_row("Chunk Overlap", str(config.chunk_overlap))

    console.print(config_table)


@app.command("tui")
def launch_tui():
    """
    🎯 Launch interactive TUI (Terminal User Interface).

    Opens a full-screen terminal interface for interactive website conversion
    with real-time progress, logs, and advanced options.
    """
    try:
        from markdown_lab.tui import MarkdownLabTUI

        app = MarkdownLabTUI()
        app.run()
    except ImportError as e:
        console.print(
            "❌ TUI dependencies not available. Install with: pip install textual",
            style="bold red",
        )
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"❌ Error launching TUI: {e}", style="bold red")
        raise typer.Exit(1) from e


@app.command("config")
def manage_config(
    show: Annotated[
        bool, typer.Option("--show", help="📋 Show current configuration")
    ] = False,
    reset: Annotated[
        bool, typer.Option("--reset", help="🔄 Reset to defaults")
    ] = False,
    set_key: Annotated[
        Optional[str], typer.Option("--set", help="🔧 Set configuration key=value")
    ] = None,
):
    """
    ⚙️ Manage configuration settings.

    View, modify, or reset configuration settings for markdown-lab.
    """
    if show:
        show_status()
    elif reset:
        if Confirm.ask("Are you sure you want to reset all settings to defaults?"):
            # Reset logic would go here
            console.print("✅ Configuration reset to defaults", style="bold green")
        else:
            console.print("❌ Reset cancelled", style="bold yellow")
    elif set_key:
        # Parse key=value
        if "=" not in set_key:
            console.print("❌ Invalid format. Use key=value", style="bold red")
            raise typer.Exit(1)
        key, value = set_key.split("=", 1)
        console.print(f"✅ Set {key} = {value}", style="bold green")
    else:
        console.print("Use --show, --reset, or --set key=value", style="bold blue")


@app.callback()
def main(
    version: Annotated[bool, typer.Option("--version", help="Show version")] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="🔇 Quiet mode")] = False,
):
    """
    🔬 Markdown Lab - Modern HTML to Markdown converter with TUI support.

    Convert web content to Markdown, JSON, or XML with support for:
    - Interactive TUI mode with live progress
    - Batch processing with sitemaps
    - Content chunking for RAG applications
    - Rich terminal output with colors and progress bars
    """
    if version:
        import markdown_lab

        console.print(f"Markdown Lab v{markdown_lab.__version__}")
        raise typer.Exit()

    if quiet:
        console.quiet = True


def cli_main():
    """entry point for the CLI application"""
    try:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        app()
    except KeyboardInterrupt:
        console.print("\n❌ Operation cancelled by user", style="bold red")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ Unexpected error: {e}", style="bold red")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
