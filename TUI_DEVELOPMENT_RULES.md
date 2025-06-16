# 🖥️ Comprehensive TUI Development Rules for LLMs

## 🎯 Core Philosophy

**Golden Rule**: A TUI should feel as responsive and intuitive as a modern GUI while respecting terminal constraints and leveraging terminal strengths.

**Performance First**: Every frame matters. 60 FPS should be achievable on modern terminals.

**Accessibility**: Support screen readers, different terminal capabilities, and various input methods.

---

## 🎨 Visual Design Principles

### Color Strategy

- **Use semantic colors**: Error (red), success (green), warning (yellow), info (blue)
- **Respect terminal themes**: Provide light/dark mode support
- **Gradual color introduction**: Start with 16 colors, gracefully upgrade to 256/truecolor
- **Contrast ratios**: Ensure 4.5:1 minimum contrast for text readability
- **Color blindness**: Use symbols/patterns alongside colors for critical information

### Layout Principles

- **Golden ratio**: Use 1.618 ratio for main content areas
- **Breathing room**: Minimum 1-2 char padding around interactive elements
- **Consistent spacing**: Use modular scale (8pt, 12pt, 16pt, 24pt equivalent)
- **Z-index layers**: Background → Content → Overlays → Modals → Tooltips
- **Responsive design**: Handle terminal resize gracefully with minimum viable layouts

### Typography

- **Hierarchy**: Use bold, dim, underline, and color to create visual hierarchy
- **Monospace awareness**: Every character is same width - design accordingly
- **Unicode support**: Test with emoji, accented characters, and CJK text
- **Box drawing**: Prefer Unicode box characters over ASCII for borders

---

## ⚡ Performance Guidelines

### Rendering Optimization

- **Dirty region tracking**: Only redraw changed areas
- **Double buffering**: Render to buffer, then swap atomically
- **Batch updates**: Collect multiple changes before rendering
- **Viewport culling**: Don't render off-screen content
- **Lazy evaluation**: Defer expensive calculations until needed

### Memory Management

- **Component pooling**: Reuse UI components instead of allocating new ones
- **String interning**: Cache frequently used strings
- **Weak references**: Avoid circular references in event systems
- **Structured data**: Use efficient data structures for large lists/trees

### Input Handling

- **Non-blocking input**: Never block the main thread on input
- **Input debouncing**: Handle rapid key repetition gracefully
- **Command queuing**: Queue commands for batch processing
- **Event coalescing**: Merge similar events to reduce processing load

---

## 🦀 Rust TUI Specifics

### Framework Selection

- **ratatui**: Modern, performant, well-maintained (recommended)
- **tui-rs**: Legacy but stable (consider migrating to ratatui)
- **cursive**: High-level, widget-focused for rapid development
- **crossterm**: Cross-platform terminal manipulation

### Rust Best Practices

```rust
// ✅ Good: Efficient state management
#[derive(Debug, Clone)]
pub struct AppState {
    pub items: Vec<ListItem>,
    pub selected: Option<usize>,
    pub scroll_offset: usize,
}

impl AppState {
    pub fn select_next(&mut self) {
        self.selected = match self.selected {
            Some(i) => Some((i + 1).min(self.items.len() - 1)),
            None => Some(0),
        };
        self.adjust_scroll();
    }
}

// ✅ Good: Component-based architecture
pub trait Component {
    type Event;

    fn handle_event(&mut self, event: Self::Event) -> Option<Action>;
    fn render(&self, frame: &mut Frame, area: Rect);
    fn should_redraw(&self) -> bool;
}

// ✅ Good: Error handling
#[derive(Debug, thiserror::Error)]
pub enum TuiError {
    #[error("Terminal error: {0}")]
    Terminal(#[from] crossterm::ErrorKind),
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}

// ✅ Good: Efficient rendering
fn render_list(frame: &mut Frame, area: Rect, items: &[ListItem], selected: Option<usize>) {
    let items: Vec<ratatui::widgets::ListItem> = items
        .iter()
        .enumerate()
        .map(|(i, item)| {
            let style = if Some(i) == selected {
                Style::default().bg(Color::Blue).fg(Color::White)
            } else {
                Style::default()
            };
            ratatui::widgets::ListItem::new(item.title.clone()).style(style)
        })
        .collect();

    let list = List::new(items)
        .block(Block::default().borders(Borders::ALL).title("Items"))
        .highlight_style(Style::default().add_modifier(Modifier::BOLD));

    frame.render_widget(list, area);
}
```

### Performance Patterns

- **Arc<Mutex<T>>**: For shared state across threads
- **mpsc channels**: For event communication
- **rayon**: For parallel data processing
- **Once/LazyStatic**: For expensive initialization

---

## 🐍 Python TUI Specifics

### Framework Selection

- **Textual**: Modern, async, CSS-inspired (highly recommended)
- **Rich**: Excellent for static content and progress bars
- **urwid**: Mature, event-driven, good for complex layouts
- **prompt_toolkit**: Best for REPL-style applications
- **py-cui**: Simple, lightweight option

### Python Best Practices

```python
# ✅ Good: Textual modern approach
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Header, Footer, Static
from textual.reactive import reactive

class CounterApp(App):
    """A simple counter app."""

    CSS = """
    .counter {
        width: 100%;
        height: 100%;
        content-align: center middle;
    }

    Button {
        margin: 1;
        min-width: 16;
    }

    #counter {
        color: $accent;
        text-style: bold;
        font-size: 2;
    }
    """

    count = reactive(0)

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="counter"):
            with Vertical():
                yield Static(str(self.count), id="counter")
                with Horizontal():
                    yield Button("Increment", id="inc", variant="primary")
                    yield Button("Decrement", id="dec", variant="default")
        yield Footer()

    def watch_count(self, count: int) -> None:
        """Update counter display when count changes."""
        self.query_one("#counter", Static).update(str(count))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "inc":
            self.count += 1
        elif event.button.id == "dec":
            self.count -= 1

# ✅ Good: Rich for beautiful output
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live
from rich.table import Table

def create_status_table(stats: dict) -> Table:
    table = Table(title="System Status")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")

    for key, value in stats.items():
        table.add_row(key, str(value))

    return table

# ✅ Good: Async event handling
import asyncio
from textual import events

class AsyncApp(App):
    async def on_mount(self) -> None:
        """Set up background tasks."""
        self.set_interval(1.0, self.update_stats)

    async def update_stats(self) -> None:
        """Update statistics periodically."""
        # Fetch stats asynchronously
        stats = await self.fetch_stats()
        self.refresh_display(stats)
```

### Performance Patterns

- **asyncio**: For non-blocking operations
- **Rich caching**: Cache expensive renderings
- **Generator expressions**: For memory-efficient iterations
- **dataclasses**: For efficient data structures

---

## 🟨 JavaScript/Bun TUI Specifics

### Framework Selection

- **Ink**: React-like components for terminal (recommended)
- **Blessed**: jQuery-like terminal manipulation
- **neo-blessed**: Modern fork of blessed
- **Enquirer**: Beautiful prompts and forms
- **Cliffy**: Deno command-line framework

### JavaScript/Bun Best Practices

```javascript
// ✅ Good: Ink React-style components
import React, { useState, useEffect } from "react";
import { render, Text, Box, useInput, useApp } from "ink";
import Spinner from "ink-spinner";

const CounterApp = () => {
    const [count, setCount] = useState(0);
    const [isLoading, setIsLoading] = useState(false);
    const { exit } = useApp();

    useInput((input, key) => {
        if (input === "q") {
            exit();
        }
        if (key.upArrow) {
            setCount((c) => c + 1);
        }
        if (key.downArrow) {
            setCount((c) => Math.max(0, c - 1));
        }
    });

    return (
        <Box flexDirection="column" padding={2}>
            <Text color="cyan" bold>
                🎯 Counter App
            </Text>
            <Box marginTop={1}>
                <Text>Count: </Text>
                <Text color="green" bold>
                    {count}
                </Text>
            </Box>
            {isLoading && (
                <Box marginTop={1}>
                    <Spinner type="dots" />
                    <Text> Loading...</Text>
                </Box>
            )}
            <Box marginTop={2}>
                <Text dimColor>↑/↓ to change count, 'q' to quit</Text>
            </Box>
        </Box>
    );
};

render(<CounterApp />);

// ✅ Good: Custom hooks for state management
import { useState, useEffect } from "react";

const useAsyncData = (fetchFn) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchFn()
            .then(setData)
            .catch(setError)
            .finally(() => setLoading(false));
    }, [fetchFn]);

    return { data, loading, error };
};

// ✅ Good: Blessed for complex layouts
const blessed = require("blessed");

const screen = blessed.screen({
    smartCSR: true,
    title: "My TUI App",
});

const form = blessed.form({
    parent: screen,
    keys: true,
    left: "center",
    top: "center",
    width: 60,
    height: 20,
    border: { type: "line" },
    style: {
        border: { fg: "cyan" },
        focus: { border: { fg: "green" } },
    },
});

// Performance: Use object pooling for frequently created elements
const elementPool = {
    boxes: [],
    texts: [],

    getBox() {
        return this.boxes.pop() || blessed.box();
    },

    returnBox(box) {
        box.detach();
        this.boxes.push(box);
    },
};
```

### Performance Patterns

- **Virtual scrolling**: For large lists
- **Event debouncing**: Use lodash.debounce for rapid events
- **Worker threads**: For CPU-intensive tasks
- **Memory pools**: Reuse UI elements

---

## 🎯 Universal Best Practices

### State Management

- **Single source of truth**: Centralize application state
- **Immutable updates**: Use immutable patterns for state changes
- **Event sourcing**: Consider event-driven architecture for complex apps
- **State machines**: Use finite state machines for complex UI flows

### Error Handling

```rust
// Rust example
pub enum TuiResult<T> {
    Success(T),
    Recoverable(T, Vec<Warning>),
    Fatal(TuiError),
}

impl<T> TuiResult<T> {
    pub fn with_fallback(self, fallback: T) -> T {
        match self {
            TuiResult::Success(val) | TuiResult::Recoverable(val, _) => val,
            TuiResult::Fatal(_) => fallback,
        }
    }
}
```

### Testing Strategies

- **Snapshot testing**: Capture UI output for regression testing
- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test user workflows end-to-end
- **Property-based testing**: Test with random inputs
- **Performance benchmarks**: Automated performance regression detection

### Accessibility

- **Screen reader support**: Provide aria-labels and descriptions
- **Keyboard navigation**: Full app usable with keyboard only
- **High contrast mode**: Support for accessibility themes
- **Text scaling**: Respect terminal font size settings
- **Focus indicators**: Clear visual focus indicators

### Deployment & Distribution

- **Cross-platform**: Test on Windows, macOS, Linux
- **Terminal compatibility**: Test on different terminal emulators
- **Minimal dependencies**: Reduce binary size and startup time
- **Graceful degradation**: Handle limited terminal capabilities
- **Auto-updates**: Consider automatic update mechanisms

---

## 🧪 Testing & Quality Assurance

### Visual Testing

```bash
# Create visual regression tests
cargo test --test visual_tests
python -m pytest tests/visual/
npm test -- --visual

# Terminal recording for demos
asciinema rec demo.cast
terminalizer record demo
```

### Performance Profiling

```rust
// Rust profiling
use std::time::Instant;

fn measure_render_time<F>(render_fn: F) -> std::time::Duration
where F: FnOnce() {
    let start = Instant::now();
    render_fn();
    start.elapsed()
}
```

### Load Testing

- **Stress test with large datasets**: 10k+ items in lists
- **Memory leak detection**: Long-running apps
- **Input flood testing**: Rapid keypress sequences
- **Terminal resize stress**: Rapid resize events

---

## 📚 Framework-Specific Resources

### Rust

- **Documentation**: docs.rs/ratatui, docs.rs/crossterm
- **Examples**: github.com/ratatui-org/ratatui/tree/main/examples
- **Performance**: Use `cargo flamegraph` for profiling

### Python

- **Documentation**: textual.textualize.io, rich.readthedocs.io
- **Examples**: github.com/Textualize/textual/tree/main/examples
- **Performance**: Use `py-spy` for profiling

### JavaScript/Bun

- **Documentation**: github.com/vadimdemedes/ink
- **Examples**: github.com/vadimdemedes/ink/tree/master/examples
- **Performance**: Use `clinic.js` for profiling

---

## 🎨 Advanced Visual Techniques

### Animations

- **Easing functions**: Use smooth transitions for state changes
- **Frame interpolation**: Smooth animations between discrete states
- **Loading indicators**: Spinners, progress bars, pulsing effects
- **Micro-interactions**: Subtle feedback for user actions

### Data Visualization

- **ASCII charts**: Use Unicode block characters for charts
- **Sparklines**: Inline mini-charts for trends
- **Tables**: Sortable, filterable, paginated tables
- **Trees**: Expandable/collapsible hierarchical data

### Advanced Layouts

- **Flexbox-style**: Flexible layouts that adapt to content
- **Grid systems**: Complex multi-column layouts
- **Overlays**: Modal dialogs, tooltips, dropdowns
- **Split panes**: Resizable panels with drag handles

---

This comprehensive guide provides LLMs with the knowledge needed to create exceptional TUI applications across different programming languages and frameworks, emphasizing both visual appeal and high performance.
