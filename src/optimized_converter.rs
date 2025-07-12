use crate::markdown_converter::{Document, MarkdownError};
use once_cell::sync::Lazy;
use scraper::{Html, Selector};
use smallvec::SmallVec;
use std::borrow::Cow;
use url::Url;

// Pre-compiled selectors for better performance
static HEADING_SELECTORS: Lazy<Vec<(u8, Selector)>> = Lazy::new(|| {
    (1..=6)
        .filter_map(|i| {
            Selector::parse(&format!("h{}", i))
                .ok()
                .map(|s| (i as u8, s))
        })
        .collect()
});

static COMMON_SELECTORS: Lazy<std::collections::HashMap<&'static str, Selector>> =
    Lazy::new(|| {
        let mut map = std::collections::HashMap::new();

        if let Ok(s) = Selector::parse("p") {
            map.insert("p", s);
        }
        if let Ok(s) = Selector::parse("a[href]") {
            map.insert("a", s);
        }
        if let Ok(s) = Selector::parse("img[src]") {
            map.insert("img", s);
        }
        if let Ok(s) = Selector::parse("ul") {
            map.insert("ul", s);
        }
        if let Ok(s) = Selector::parse("ol") {
            map.insert("ol", s);
        }
        if let Ok(s) = Selector::parse("li") {
            map.insert("li", s);
        }
        if let Ok(s) = Selector::parse("pre > code") {
            map.insert("pre_code", s);
        }
        if let Ok(s) = Selector::parse("code") {
            map.insert("code", s);
        }
        if let Ok(s) = Selector::parse("blockquote") {
            map.insert("blockquote", s);
        }

        map
    });

/// Extract text with minimal allocations
fn extract_text_optimized(element: scraper::ElementRef) -> String {
    // Pre-allocate with estimated size
    let mut result = String::with_capacity(256);

    // Collect text nodes efficiently
    for text in element.text() {
        result.push_str(text);
    }

    // Trim in-place if possible
    let trimmed_len = result.trim_end().len();
    result.truncate(trimmed_len);

    // Trim start by shifting
    let trim_start = result.len() - result.trim_start().len();
    if trim_start > 0 {
        result.drain(..trim_start);
    }

    result
}

/// Resolve URL with Cow for efficiency
fn resolve_url_optimized<'a>(base_url: &Url, href: &'a str) -> Cow<'a, str> {
    // Check if already absolute
    if href.starts_with("http://") || href.starts_with("https://") {
        Cow::Borrowed(href)
    } else {
        // Must allocate for relative URLs
        match base_url.join(href) {
            Ok(url) => Cow::Owned(url.to_string()),
            Err(_) => Cow::Borrowed(href),
        }
    }
}

/// Optimized HTML parsing with reduced allocations
pub fn parse_html_optimized(html: &str, base_url_str: &str) -> Result<Document, MarkdownError> {
    let document_html = Html::parse_document(html);
    let base_url = Url::parse(base_url_str)?;

    // Extract title
    let title = if let Some(selector) = Selector::parse("title").ok() {
        document_html
            .select(&selector)
            .next()
            .map(extract_text_optimized)
            .unwrap_or_else(|| "No Title".to_string())
    } else {
        "No Title".to_string()
    };

    // Pre-allocate document with estimated capacities
    let mut document = Document {
        title,
        base_url: base_url_str.to_string(),
        headings: Vec::with_capacity(20),
        paragraphs: Vec::with_capacity(50),
        links: Vec::with_capacity(30),
        images: Vec::with_capacity(10),
        lists: Vec::with_capacity(10),
        code_blocks: Vec::with_capacity(5),
        blockquotes: Vec::with_capacity(5),
    };

    // Process headings with pre-compiled selectors
    for (level, selector) in HEADING_SELECTORS.iter() {
        for element in document_html.select(selector) {
            let text = extract_text_optimized(element);
            if !text.is_empty() {
                document.headings.push(crate::markdown_converter::Heading {
                    level: *level,
                    text,
                });
            }
        }
    }

    // Process paragraphs
    if let Some(selector) = COMMON_SELECTORS.get("p") {
        for element in document_html.select(selector) {
            let text = extract_text_optimized(element);
            if !text.is_empty() {
                document.paragraphs.push(text);
            }
        }
    }

    // Process links with Cow optimization
    if let Some(selector) = COMMON_SELECTORS.get("a") {
        for element in document_html.select(selector) {
            if let Some(href) = element.value().attr("href") {
                let text = extract_text_optimized(element);
                if !text.is_empty() {
                    let url = resolve_url_optimized(&base_url, href);
                    document.links.push(crate::markdown_converter::Link {
                        text,
                        url: url.into_owned(),
                    });
                }
            }
        }
    }

    // Process images
    if let Some(selector) = COMMON_SELECTORS.get("img") {
        for element in document_html.select(selector) {
            if let Some(src) = element.value().attr("src") {
                let alt = element.value().attr("alt").unwrap_or("image").to_string();
                let url = resolve_url_optimized(&base_url, src);
                document.images.push(crate::markdown_converter::Image {
                    alt,
                    src: url.into_owned(),
                });
            }
        }
    }

    // Process lists using SmallVec for small lists
    if let Some(ul_selector) = COMMON_SELECTORS.get("ul") {
        if let Some(li_selector) = COMMON_SELECTORS.get("li") {
            for ul in document_html.select(ul_selector) {
                let mut items: SmallVec<[String; 8]> = SmallVec::new();
                for li in ul.select(li_selector) {
                    let text = extract_text_optimized(li);
                    if !text.is_empty() {
                        items.push(text);
                    }
                }
                if !items.is_empty() {
                    document.lists.push(crate::markdown_converter::List {
                        ordered: false,
                        items: items.into_vec(),
                    });
                }
            }
        }
    }

    // Process ordered lists
    if let Some(ol_selector) = COMMON_SELECTORS.get("ol") {
        if let Some(li_selector) = COMMON_SELECTORS.get("li") {
            for ol in document_html.select(ol_selector) {
                let mut items: SmallVec<[String; 8]> = SmallVec::new();
                for li in ol.select(li_selector) {
                    let text = extract_text_optimized(li);
                    if !text.is_empty() {
                        items.push(text);
                    }
                }
                if !items.is_empty() {
                    document.lists.push(crate::markdown_converter::List {
                        ordered: true,
                        items: items.into_vec(),
                    });
                }
            }
        }
    }

    // Process code blocks
    if let Some(selector) = COMMON_SELECTORS.get("pre_code") {
        for element in document_html.select(selector) {
            let code = extract_text_optimized(element);

            // Extract language from class
            let language = element
                .value()
                .classes()
                .find(|c| c.starts_with("language-"))
                .map(|c| c[9..].to_string())
                .unwrap_or_default();

            if !code.is_empty() {
                document
                    .code_blocks
                    .push(crate::markdown_converter::CodeBlock { language, code });
            }
        }
    }

    // Process blockquotes
    if let Some(selector) = COMMON_SELECTORS.get("blockquote") {
        for element in document_html.select(selector) {
            let text = extract_text_optimized(element);
            if !text.is_empty() {
                document.blockquotes.push(text);
            }
        }
    }

    Ok(document)
}

/// Optimized markdown generation with pre-allocated buffer
pub fn document_to_markdown_optimized(doc: &Document) -> String {
    // Estimate output size
    let estimated_size = estimate_markdown_size(doc);
    let mut output = String::with_capacity(estimated_size);

    // Use a reusable buffer for formatting
    let mut fmt_buffer = String::with_capacity(256);

    // Add title
    if !doc.title.is_empty() && doc.title != "No Title" {
        output.push_str("# ");
        output.push_str(&doc.title);
        output.push_str("\n\n");
    }

    // Add headings
    for heading in &doc.headings {
        // Reuse buffer for heading markers
        fmt_buffer.clear();
        for _ in 0..heading.level {
            fmt_buffer.push('#');
        }
        fmt_buffer.push(' ');

        output.push_str(&fmt_buffer);
        output.push_str(&heading.text);
        output.push_str("\n\n");
    }

    // Add paragraphs
    for paragraph in &doc.paragraphs {
        output.push_str(paragraph);
        output.push_str("\n\n");
    }

    // Add lists
    for list in &doc.lists {
        for (i, item) in list.items.iter().enumerate() {
            if list.ordered {
                // Use fmt_buffer for number formatting
                fmt_buffer.clear();
                use std::fmt::Write;
                write!(&mut fmt_buffer, "{}. ", i + 1).unwrap();
                output.push_str(&fmt_buffer);
            } else {
                output.push_str("- ");
            }
            output.push_str(item);
            output.push('\n');
        }
        output.push('\n');
    }

    // Add code blocks
    for code_block in &doc.code_blocks {
        output.push_str("```");
        output.push_str(&code_block.language);
        output.push('\n');
        output.push_str(&code_block.code);
        if !code_block.code.ends_with('\n') {
            output.push('\n');
        }
        output.push_str("```\n\n");
    }

    // Add blockquotes
    for blockquote in &doc.blockquotes {
        output.push_str("> ");
        output.push_str(blockquote);
        output.push_str("\n\n");
    }

    // Add links section
    if !doc.links.is_empty() {
        output.push_str("## Links\n\n");
        for link in &doc.links {
            output.push_str("- [");
            output.push_str(&link.text);
            output.push_str("](");
            output.push_str(&link.url);
            output.push_str(")\n");
        }
        output.push('\n');
    }

    // Add images section
    if !doc.images.is_empty() {
        output.push_str("## Images\n\n");
        for image in &doc.images {
            output.push_str("![");
            output.push_str(&image.alt);
            output.push_str("](");
            output.push_str(&image.src);
            output.push_str(")\n\n");
        }
    }

    output
}

/// Estimate markdown size for pre-allocation
fn estimate_markdown_size(doc: &Document) -> usize {
    let mut size = 0;

    // Title
    size += doc.title.len() + 4;

    // Headings
    for heading in &doc.headings {
        size += heading.text.len() + heading.level as usize + 3;
    }

    // Paragraphs
    for paragraph in &doc.paragraphs {
        size += paragraph.len() + 2;
    }

    // Lists
    for list in &doc.lists {
        size += list.items.iter().map(|i| i.len() + 4).sum::<usize>();
    }

    // Code blocks
    for code_block in &doc.code_blocks {
        size += code_block.code.len() + code_block.language.len() + 10;
    }

    // Blockquotes
    for blockquote in &doc.blockquotes {
        size += blockquote.len() + 4;
    }

    // Links and images
    size += doc.links.len() * 20
        + doc
            .links
            .iter()
            .map(|l| l.text.len() + l.url.len())
            .sum::<usize>();
    size += doc.images.len() * 20
        + doc
            .images
            .iter()
            .map(|i| i.alt.len() + i.src.len())
            .sum::<usize>();

    // Add 20% buffer
    size + (size / 5)
}

/// Optimized conversion function
pub fn convert_to_markdown_optimized(html: &str, base_url: &str) -> Result<String, MarkdownError> {
    let document = parse_html_optimized(html, base_url)?;
    Ok(document_to_markdown_optimized(&document))
}
