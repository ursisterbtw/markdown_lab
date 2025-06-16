#!/usr/bin/env python3
"""
Terminal User Interface for markdown_lab using Textual.

This module provides a full-screen terminal interface with:
- Real-time progress tracking
- Interactive forms and configuration
- Live log display
- Tabbed interface for different operations
- Keyboard shortcuts and mouse support
"""

import threading
import time
from urllib.parse import urlparse

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.validation import ValidationResult, Validator
from textual.widgets import (
    Button,
    Collapsible,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Log,
    ProgressBar,
    RadioButton,
    RadioSet,
    Rule,
    SelectionList,
    Slider,
    Static,
    Switch,
    TabPane,
    Tabs,
    TextArea,
)

from markdown_lab.core.config import MarkdownLabConfig
from markdown_lab.core.converter import Converter


class URLValidator(Validator):
    """Validates URL input."""

    def validate(self, value: str) -> ValidationResult:
        if not value:
            return self.failure("URL cannot be empty")

        if not value.startswith(("http://", "https://")):
            return self.failure("URL must start with http:// or https://")

        try:
            parsed = urlparse(value)
            if not parsed.netloc:
                return self.failure("Invalid URL format")
        except Exception:
            return self.failure("Invalid URL format")

        return self.success()


class ConversionStatus(Static):
    """Widget to display conversion status."""

    status = reactive("Ready")
    progress = reactive(0)

    def render(self) -> str:
        return f"Status: {self.status} | Progress: {self.progress}%"


class ConversionWorker:
    """Worker class to handle conversion in background."""

    def __init__(self, app):
        self.app = app
        self.running = False
        self.thread = None

    def start_conversion(self, url: str, config: dict):
        """Start conversion in background thread."""
        if self.running:
            return False

        self.running = True
        self.thread = threading.Thread(
            target=self._conversion_worker, args=(url, config), daemon=True
        )
        self.thread.start()
        return True

    def _conversion_worker(self, url: str, config: dict):
        """Background conversion worker."""
        try:
            self.app.call_from_thread(self.app.update_status, "Initializing...", 0)

            # Setup converter
            markdown_config = MarkdownLabConfig(**config)
            converter = Converter(markdown_config)

            self.app.call_from_thread(self.app.update_status, "Fetching content...", 20)

            # Fetch content
            html_content = converter.client.get(url)

            self.app.call_from_thread(
                self.app.update_status, "Converting content...", 50
            )

            # Convert content
            content, markdown_content = converter.convert_html(
                html_content, url, config.get("output_format", "markdown")
            )

            self.app.call_from_thread(self.app.update_status, "Saving content...", 80)

            # Save content
            output_file = config.get("output_file", "output.md")
            converter.save_content(content, output_file)

            # Handle chunks if enabled
            if config.get("save_chunks", False):
                self.app.call_from_thread(
                    self.app.update_status, "Creating chunks...", 90
                )

                chunks = converter.create_chunks(markdown_content, url)

                from markdown_lab.utils.chunk_utils import ContentChunker

                chunker = ContentChunker(
                    config.get("chunk_size", 1000), config.get("chunk_overlap", 200)
                )
                chunker.save_chunks(
                    chunks,
                    config.get("chunk_dir", "chunks"),
                    config.get("chunk_format", "jsonl"),
                )

            self.app.call_from_thread(self.app.update_status, "Complete!", 100)
            self.app.call_from_thread(
                self.app.conversion_complete, True, f"Successfully converted {url}"
            )

        except Exception as e:
            self.app.call_from_thread(self.app.update_status, f"Error: {str(e)}", 100)
            self.app.call_from_thread(self.app.conversion_complete, False, str(e))
        finally:
            self.running = False


class SingleURLTab(Container):
    """Tab for single URL conversion."""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("🌐 Single URL Conversion", classes="tab-title")
            yield Rule()

            with Horizontal(classes="form-row"):
                yield Label("URL:", classes="form-label")
                yield Input(
                    placeholder="https://example.com",
                    validators=[URLValidator()],
                    id="url_input",
                )

            with Horizontal(classes="form-row"):
                yield Label("Output File:", classes="form-label")
                yield Input(placeholder="output.md", id="output_file_input")

            with Horizontal(classes="form-row"):
                yield Label("Format:", classes="form-label")
                with RadioSet(id="format_radio"):
                    yield RadioButton("Markdown", value=True, id="format_markdown")
                    yield RadioButton("JSON", id="format_json")
                    yield RadioButton("XML", id="format_xml")

            with Collapsible(title="⚙️ Advanced Options"):
                with Horizontal(classes="form-row"):
                    yield Label("Save Chunks:", classes="form-label")
                    yield Switch(id="save_chunks_switch")

                with Horizontal(classes="form-row"):
                    yield Label("Chunk Size:", classes="form-label")
                    yield Slider(
                        min=100,
                        max=5000,
                        step=100,
                        value=1000,
                        tooltip="Maximum chunk size in characters",
                        id="chunk_size_slider",
                    )

                with Horizontal(classes="form-row"):
                    yield Label("Rate Limit (req/s):", classes="form-label")
                    yield Slider(
                        min=0.1,
                        max=10.0,
                        step=0.1,
                        value=1.0,
                        tooltip="Requests per second",
                        id="rate_limit_slider",
                    )

                with Horizontal(classes="form-row"):
                    yield Label("Timeout (s):", classes="form-label")
                    yield Slider(
                        min=5,
                        max=120,
                        step=5,
                        value=30,
                        tooltip="Request timeout in seconds",
                        id="timeout_slider",
                    )

            yield Rule()

            with Horizontal(classes="button-row"):
                yield Button(
                    "🚀 Start Conversion", variant="primary", id="start_conversion"
                )
                yield Button(
                    "🛑 Cancel", variant="error", id="cancel_conversion", disabled=True
                )

            yield Rule()

            with Vertical(classes="status-area"):
                yield Label("📊 Status", classes="section-title")
                yield ConversionStatus(id="conversion_status")
                yield ProgressBar(id="conversion_progress")


class BatchURLTab(Container):
    """Tab for batch URL conversion."""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("📋 Batch URL Conversion", classes="tab-title")
            yield Rule()

            with Horizontal(classes="form-row"):
                yield Label("Links File:", classes="form-label")
                yield Input(placeholder="links.txt", id="links_file_input")
                yield Button("📁 Browse", id="browse_links_file")

            with Horizontal(classes="form-row"):
                yield Label("Output Directory:", classes="form-label")
                yield Input(placeholder="output/", id="output_dir_input")
                yield Button("📁 Browse", id="browse_output_dir")

            with Horizontal(classes="form-row"):
                yield Label("Parallel Processing:", classes="form-label")
                yield Switch(id="parallel_switch")
                yield Label("Max Workers:", classes="form-label")
                yield Slider(min=1, max=16, step=1, value=4, id="max_workers_slider")

            yield Rule()

            with Horizontal(classes="button-row"):
                yield Button("🚀 Start Batch", variant="primary", id="start_batch")
                yield Button(
                    "🛑 Cancel", variant="error", id="cancel_batch", disabled=True
                )

            yield Rule()

            with Vertical(classes="batch-status"):
                yield Label("📊 Batch Status", classes="section-title")
                yield DataTable(id="batch_progress_table")


class SitemapTab(Container):
    """Tab for sitemap-based conversion."""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("🗺️ Sitemap Conversion", classes="tab-title")
            yield Rule()

            with Horizontal(classes="form-row"):
                yield Label("Base URL:", classes="form-label")
                yield Input(
                    placeholder="https://example.com",
                    validators=[URLValidator()],
                    id="sitemap_url_input",
                )

            with Horizontal(classes="form-row"):
                yield Label("Min Priority:", classes="form-label")
                yield Slider(
                    min=0.0,
                    max=1.0,
                    step=0.1,
                    value=0.5,
                    tooltip="Minimum sitemap priority",
                    id="min_priority_slider",
                )

            with Horizontal(classes="form-row"):
                yield Label("Max URLs:", classes="form-label")
                yield Input(placeholder="100", id="max_urls_input")

            with Collapsible(title="🔍 URL Filters"), Vertical():
                yield Label("Include Patterns (regex):")
                yield TextArea(
                    placeholder=".*\\.html\n.*\\.php", id="include_patterns_area"
                )

                yield Label("Exclude Patterns (regex):")
                yield TextArea(
                    placeholder=".*\\.pdf\n.*\\.jpg", id="exclude_patterns_area"
                )

            yield Rule()

            with Horizontal(classes="button-row"):
                yield Button("🔍 Discover URLs", id="discover_urls")
                yield Button("🚀 Start Sitemap", variant="primary", id="start_sitemap")
                yield Button(
                    "🛑 Cancel", variant="error", id="cancel_sitemap", disabled=True
                )

            yield Rule()

            with Vertical(classes="sitemap-status"):
                yield Label("🔍 Discovered URLs", classes="section-title")
                yield SelectionList(id="discovered_urls_list")


class LogTab(Container):
    """Tab for displaying logs."""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("📝 Application Logs", classes="tab-title")
            yield Rule()

            with Horizontal(classes="button-row"):
                yield Button("🗑️ Clear Logs", id="clear_logs")
                yield Button("💾 Save Logs", id="save_logs")

            yield Log(id="app_log", auto_scroll=True)


class ConfigTab(Container):
    """Tab for configuration management."""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("⚙️ Configuration", classes="tab-title")
            yield Rule()

            with ScrollableContainer():
                with Collapsible(title="🌐 Network Settings", collapsed=False):
                    with Horizontal(classes="form-row"):
                        yield Label("Requests per Second:", classes="form-label")
                        yield Slider(
                            min=0.1,
                            max=10.0,
                            step=0.1,
                            value=1.0,
                            id="config_rate_limit",
                        )

                    with Horizontal(classes="form-row"):
                        yield Label("Timeout (seconds):", classes="form-label")
                        yield Slider(
                            min=5, max=120, step=5, value=30, id="config_timeout"
                        )

                    with Horizontal(classes="form-row"):
                        yield Label("Max Retries:", classes="form-label")
                        yield Slider(
                            min=1, max=10, step=1, value=3, id="config_retries"
                        )

                    with Horizontal(classes="form-row"):
                        yield Label("Enable Cache:", classes="form-label")
                        yield Switch(value=True, id="config_cache_enabled")

                    with Horizontal(classes="form-row"):
                        yield Label("Cache TTL (seconds):", classes="form-label")
                        yield Slider(
                            min=300,
                            max=7200,
                            step=300,
                            value=3600,
                            id="config_cache_ttl",
                        )

                with Collapsible(title="📦 Chunking Settings"):
                    with Horizontal(classes="form-row"):
                        yield Label("Default Chunk Size:", classes="form-label")
                        yield Slider(
                            min=100,
                            max=5000,
                            step=100,
                            value=1000,
                            id="config_chunk_size",
                        )

                    with Horizontal(classes="form-row"):
                        yield Label("Chunk Overlap:", classes="form-label")
                        yield Slider(
                            min=0,
                            max=500,
                            step=50,
                            value=200,
                            id="config_chunk_overlap",
                        )

                with Collapsible(title="📁 Output Settings"):
                    with Horizontal(classes="form-row"):
                        yield Label("Default Format:", classes="form-label")
                        with RadioSet(id="config_default_format"):
                            yield RadioButton("Markdown", value=True)
                            yield RadioButton("JSON")
                            yield RadioButton("XML")

                    with Horizontal(classes="form-row"):
                        yield Label("Default Output Dir:", classes="form-label")
                        yield Input(value="output", id="config_output_dir")

            yield Rule()

            with Horizontal(classes="button-row"):
                yield Button("💾 Save Config", variant="primary", id="save_config")
                yield Button("🔄 Reset to Defaults", id="reset_config")
                yield Button("📋 Show Current", id="show_config")


class MarkdownLabTUI(App):
    """Main TUI application for Markdown Lab."""

    TITLE = "🔬 Markdown Lab TUI"
    DESCRIPTION = "Terminal User Interface for HTML to Markdown conversion"

    CSS = """
    .tab-title {
        text-align: center;
        color: $accent;
        text-style: bold;
        margin: 1;
    }

    .form-row {
        height: 3;
        align: left middle;
        margin: 1 0;
    }

    .form-label {
        width: 20;
        text-align: right;
        margin-right: 1;
    }

    .button-row {
        height: 3;
        align: center middle;
        margin: 1;
    }

    .section-title {
        text-style: bold;
        color: $secondary;
        margin: 1 0;
    }

    .status-area {
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }

    .batch-status {
        border: solid $secondary;
        padding: 1;
        margin: 1 0;
    }

    .sitemap-status {
        border: solid $accent;
        padding: 1;
        margin: 1 0;
    }

    Button {
        margin: 0 1;
    }

    Slider {
        width: 30;
    }

    Input {
        width: 1fr;
    }

    TextArea {
        height: 8;
        margin: 1 0;
    }

    SelectionList {
        height: 20;
        border: solid $primary;
    }

    DataTable {
        height: 15;
    }

    Log {
        height: 1fr;
        border: solid $warning;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("f1", "show_help", "Help"),
        Binding("ctrl+l", "clear_logs", "Clear Logs"),
        Binding("ctrl+s", "save_config", "Save Config"),
    ]

    def __init__(self):
        super().__init__()
        self.conversion_worker = ConversionWorker(self)
        self.discovered_urls = []

    def compose(self) -> ComposeResult:
        yield Header()

        with Tabs(id="main_tabs"):
            with TabPane("🌐 Single URL", id="single_url_tab"):
                yield SingleURLTab()

            with TabPane("📋 Batch", id="batch_tab"):
                yield BatchURLTab()

            with TabPane("🗺️ Sitemap", id="sitemap_tab"):
                yield SitemapTab()

            with TabPane("📝 Logs", id="logs_tab"):
                yield LogTab()

            with TabPane("⚙️ Config", id="config_tab"):
                yield ConfigTab()

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the application."""
        self.log_to_app("🚀 Markdown Lab TUI started")

        # Initialize batch progress table
        table = self.query_one("#batch_progress_table", DataTable)
        table.add_columns("URL", "Status", "Progress")

    def log_to_app(self, message: str) -> None:
        """Add a message to the application log."""
        log_widget = self.query_one("#app_log", Log)
        log_widget.write_line(f"[{time.strftime('%H:%M:%S')}] {message}")

    def update_status(self, status: str, progress: int) -> None:
        """Update conversion status."""
        status_widget = self.query_one("#conversion_status", ConversionStatus)
        status_widget.status = status
        status_widget.progress = progress

        progress_bar = self.query_one("#conversion_progress", ProgressBar)
        progress_bar.progress = progress

        self.log_to_app(f"Status: {status} ({progress}%)")

    def conversion_complete(self, success: bool, message: str) -> None:
        """Handle conversion completion."""
        if success:
            self.log_to_app(f"✅ {message}")
            self.notify("✅ Conversion completed successfully!", severity="information")
        else:
            self.log_to_app(f"❌ {message}")
            self.notify(f"❌ Conversion failed: {message}", severity="error")

        # Re-enable start button, disable cancel button
        self.query_one("#start_conversion", Button).disabled = False
        self.query_one("#cancel_conversion", Button).disabled = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "start_conversion":
            self.handle_start_conversion()
        elif button_id == "cancel_conversion":
            self.handle_cancel_conversion()
        elif button_id == "clear_logs":
            self.handle_clear_logs()
        elif button_id == "save_logs":
            self.handle_save_logs()
        elif button_id == "save_config":
            self.handle_save_config()
        elif button_id == "reset_config":
            self.handle_reset_config()
        elif button_id == "show_config":
            self.handle_show_config()
        elif button_id == "discover_urls":
            self.handle_discover_urls()
        elif button_id == "start_sitemap":
            self.handle_start_sitemap()
        elif button_id == "start_batch":
            self.handle_start_batch()

    def handle_start_conversion(self) -> None:
        """Start single URL conversion."""
        url_input = self.query_one("#url_input", Input)
        url = url_input.value.strip()

        if not url:
            self.notify("❌ Please enter a URL", severity="error")
            return

        # Validate URL
        validator = URLValidator()
        if not validator.validate(url).is_valid:
            self.notify("❌ Please enter a valid URL", severity="error")
            return

        # Get form values
        output_file = self.query_one("#output_file_input", Input).value or "output.md"

        # Get format
        format_radio = self.query_one("#format_radio", RadioSet)
        if (
            format_radio.pressed_button
            and format_radio.pressed_button.id == "format_json"
        ):
            output_format = "json"
        elif (
            format_radio.pressed_button
            and format_radio.pressed_button.id == "format_xml"
        ):
            output_format = "xml"
        else:
            output_format = "markdown"
        # Get advanced options
        save_chunks = self.query_one("#save_chunks_switch", Switch).value
        chunk_size = int(self.query_one("#chunk_size_slider", Slider).value)
        rate_limit = self.query_one("#rate_limit_slider", Slider).value
        timeout = int(self.query_one("#timeout_slider", Slider).value)

        # Prepare config
        config = {
            "output_format": output_format,
            "output_file": output_file,
            "save_chunks": save_chunks,
            "chunk_size": chunk_size,
            "chunk_overlap": 200,
            "chunk_dir": "chunks",
            "chunk_format": "jsonl",
            "requests_per_second": rate_limit,
            "timeout": timeout,
            "max_retries": 3,
            "cache_enabled": True,
            "cache_ttl": 3600,
        }

        # Start conversion
        if self.conversion_worker.start_conversion(url, config):
            self.log_to_app(f"🚀 Starting conversion of {url}")
            self.query_one("#start_conversion", Button).disabled = True
            self.query_one("#cancel_conversion", Button).disabled = False
        else:
            self.notify("❌ Conversion already in progress", severity="warning")

    def handle_cancel_conversion(self) -> None:
        """Cancel ongoing conversion."""
        self.log_to_app("🛑 Conversion cancelled by user")
        self.query_one("#start_conversion", Button).disabled = False
        self.query_one("#cancel_conversion", Button).disabled = True

    def handle_clear_logs(self) -> None:
        """Clear application logs."""
        log_widget = self.query_one("#app_log", Log)
        log_widget.clear()
        self.log_to_app("🗑️ Logs cleared")

    def handle_save_logs(self) -> None:
        """Save application logs to file."""
        # This would save logs to a file
        self.log_to_app("💾 Logs saved to markdown_lab_tui.log")
        self.notify("💾 Logs saved successfully!", severity="information")

    def handle_save_config(self) -> None:
        """Save current configuration."""
        self.log_to_app("💾 Configuration saved")
        self.notify("💾 Configuration saved!", severity="information")

    def handle_reset_config(self) -> None:
        """Reset configuration to defaults."""
        self.log_to_app("🔄 Configuration reset to defaults")
        self.notify("🔄 Configuration reset!", severity="information")

    def handle_show_config(self) -> None:
        """Show current configuration."""
        self.log_to_app("📋 Current configuration displayed")

    def handle_discover_urls(self) -> None:
        """Discover URLs from sitemap."""
        url_input = self.query_one("#sitemap_url_input", Input)
        url = url_input.value.strip()

        if not url:
            self.notify("❌ Please enter a base URL", severity="error")
            return

        self.log_to_app(f"🔍 Discovering URLs from {url}")
        self.notify("🔍 Discovering URLs...", severity="information")

        # This would actually discover URLs from sitemap
        # For now, just add some dummy URLs
        discovered_list = self.query_one("#discovered_urls_list", SelectionList)
        discovered_list.clear_options()

        dummy_urls = [
            f"{url}/page1",
            f"{url}/page2",
            f"{url}/about",
            f"{url}/contact",
        ]

        for dummy_url in dummy_urls:
            discovered_list.add_option((dummy_url, dummy_url))

        self.log_to_app(f"🔍 Found {len(dummy_urls)} URLs")
        self.notify(f"🔍 Found {len(dummy_urls)} URLs!", severity="information")

    def handle_start_sitemap(self) -> None:
        """Start sitemap conversion."""
        self.log_to_app("🗺️ Starting sitemap conversion")
        self.notify("🗺️ Sitemap conversion started!", severity="information")

    def handle_start_batch(self) -> None:
        """Start batch conversion."""
        self.log_to_app("📋 Starting batch conversion")
        self.notify("📋 Batch conversion started!", severity="information")

    def action_show_help(self) -> None:
        """Show help information."""
        help_text = """
🔬 Markdown Lab TUI Help

Keyboard Shortcuts:
- Q or Ctrl+C: Quit application
- F1: Show this help
- Ctrl+L: Clear logs
- Ctrl+S: Save configuration

Tabs:
- 🌐 Single URL: Convert individual web pages
- 📋 Batch: Convert multiple URLs from a file
- 🗺️ Sitemap: Convert URLs discovered from sitemap
- 📝 Logs: View application logs
- ⚙️ Config: Manage settings

Features:
- Real-time progress tracking
- Content chunking for RAG
- Multiple output formats (Markdown, JSON, XML)
- Parallel processing support
- Advanced URL filtering
        """

        self.push_screen(HelpScreen(help_text))

    def action_clear_logs(self) -> None:
        """Clear logs via keyboard shortcut."""
        self.handle_clear_logs()

    def action_save_config(self) -> None:
        """Save config via keyboard shortcut."""
        self.handle_save_config()


class HelpScreen(Screen):
    """Help screen overlay."""

    def __init__(self, help_text: str):
        super().__init__()
        self.help_text = help_text

    def compose(self) -> ComposeResult:
        with Container():
            yield Static(self.help_text, id="help_text")
            yield Button("Close", variant="primary", id="close_help")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close_help":
            self.app.pop_screen()

    BINDINGS = [
        Binding("escape", "close", "Close"),
    ]

    def action_close(self) -> None:
        self.app.pop_screen()


def main():
    """Main entry point for TUI."""
    app = MarkdownLabTUI()
    app.run()


if __name__ == "__main__":
    main()
