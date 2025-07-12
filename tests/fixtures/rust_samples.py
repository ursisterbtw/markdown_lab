"""Real Rust code samples for testing compilation without mocks."""

VALID_HELLO_WORLD = """
fn main() {
    println!("Hello from markdown_lab test suite!");
    let version = env!("CARGO_PKG_VERSION");
    println!("Running test with Rust stdlib version: {}", version);
}
"""

VALID_WITH_STRUCTS = """
use std::collections::HashMap;
use std::env;

#[derive(Debug)]
struct WebPage {
    url: String,
    title: String,
    content_length: usize,
}

impl WebPage {
    fn new(url: &str, title: &str, content: &str) -> Self {
        WebPage {
            url: url.to_string(),
            title: title.to_string(),
            content_length: content.len(),
        }
    }

    fn display_info(&self) {
        println!("URL: {}", self.url);
        println!("Title: {}", self.title);
        println!("Content Length: {} bytes", self.content_length);
    }
}

fn main() {
    let mut pages = HashMap::new();

    let page1 = WebPage::new(
        "https://docs.rs/markdown_lab",
        "Markdown Lab Documentation",
        "Full documentation for the markdown_lab crate..."
    );

    let page2 = WebPage::new(
        "https://crates.io/crates/markdown_lab",
        "markdown_lab - crates.io",
        "A powerful markdown conversion library..."
    );

    pages.insert("docs", page1);
    pages.insert("crates", page2);

    for (key, page) in &pages {
        println!("\\n=== {} ===", key);
        page.display_info();
    }
}
"""

COMPILE_ERROR_MISSING_SEMICOLON = """
fn main() {
    println!("This line is missing a semicolon")
    let x = 42;
}
"""

COMPILE_ERROR_TYPE_MISMATCH = """
fn main() {
    let number: i32 = "not a number";
    println!("This won't compile: {}", number);
}
"""

COMPILE_ERROR_UNDEFINED_VARIABLE = """
fn main() {
    println!("The value is: {}", undefined_var);
}
"""

RUNTIME_PANIC_EXPLICIT = """
fn main() {
    println!("About to panic...");
    panic!("Intentional panic for testing error handling");
}
"""

RUNTIME_PANIC_DIVISION_BY_ZERO = """
fn main() {
    let numerator = 100;
    let denominator = 0;
    let result = numerator / denominator;
    println!("This line will never execute: {}", result);
}
"""

INFINITE_LOOP_BUSY = """
fn main() {
    println!("Starting infinite loop test...");
    let mut counter = 0u64;
    loop {
        counter = counter.wrapping_add(1);
        if counter % 1_000_000_000 == 0 {
            println!("Still running... counter: {}", counter);
        }
    }
}
"""

LARGE_OUTPUT_GENERATOR = """
fn main() {
    println!("=== Large Output Test ===");
    for i in 0..5000 {
        println!("Line {}: The quick brown fox jumps over the lazy dog. Lorem ipsum dolor sit amet, consectetur adipiscing elit.", i);
    }
    println!("=== End of Large Output ===");
}
"""

UNICODE_CONTENT = """
fn main() {
    // Testing Unicode support in Rust
    println!("Hello, 世界! 🦀");
    println!("Здравствуй, мир! 🚀");
    println!("مرحبا بالعالم! 🌍");

    let emoji_string = "Rust with emojis: 🔥💻🎯";
    println!("{}", emoji_string);

    let special_chars = "Spëcîál çhârãctérs: ñ, ü, ß, æ, ø";
    println!("{}", special_chars);
}
"""

MEMORY_INTENSIVE = """
fn main() {
    println!("Starting memory-intensive test...");
    let mut big_vec: Vec<Vec<u8>> = Vec::new();

    // Allocate 100 MB of memory
    for i in 0..100 {
        let mb = vec![0u8; 1024 * 1024];
        big_vec.push(mb);
        println!("Allocated {} MB", i + 1);
    }

    println!("Total allocated: {} MB", big_vec.len());
    println!("Memory test completed.");
}
"""
