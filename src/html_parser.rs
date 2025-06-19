use once_cell::sync::Lazy;
use scraper::{Html, Selector};
use std::borrow::Cow;
use std::collections::HashMap;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ParserError {
    #[error("Selector error: {0}")]
    SelectorError(String),

    #[error("Element not found: {0}")]
    NotFound(String),

    #[error("URL parsing error: {0}")]
    UrlError(String),

    #[error("Other error: {0}")]
    Other(String),
}

// Cache commonly used selectors for better performance
static SELECTOR_CACHE: Lazy<HashMap<&'static str, Selector>> = Lazy::new(|| {
    let mut cache = HashMap::new();

    // Content container selectors
    if let Ok(selector) = Selector::parse("main, article, #content, .content") {
        cache.insert("main_content", selector);
    }

    // Unwanted element selectors (combined for efficiency)
    if let Ok(selector) = Selector::parse(
        "script, style, iframe, noscript, .advertisement, .ad, .banner, \
         #cookie-notice, header, footer, nav, .sidebar, .menu, .comments, \
         .related, .share, .social",
    ) {
        cache.insert("unwanted_elements", selector);
    }

    // Link selector
    if let Ok(selector) = Selector::parse("a[href]") {
        cache.insert("links", selector);
    }

    // Individual content selectors for fallback
    let selectors_to_cache = [
        ("main", "main"),
        ("article", "article"),
        ("content_id", "#content"),
        ("content_class", ".content"),
        ("body", "body"),
    ];

    for (key, selector_str) in selectors_to_cache {
        if let Ok(selector) = Selector::parse(selector_str) {
            cache.insert(key, selector);
        }
    }

    cache
});

/// Extracts the main content from an HTML document by identifying and
/// Extracts the main content section from an HTML document using cached CSS selectors.
///
/// Attempts to locate the primary content container by first using a combined selector for common main content elements. If not found, falls back to individual selectors in a preferred order. Returns the extracted fragment as an `Html` object, or the entire document if no specific section is found.
///
/// # Examples
///
/// ```
/// use markdown_lab_rs::html_parser::extract_main_content;
/// let html = r#"<html><body><main><p>Hello</p></main></body></html>"#;
/// let main_content = extract_main_content(html).unwrap();
/// assert!(main_content.root_element().html().contains("Hello"));
/// ```
pub fn extract_main_content(html: &str) -> Result<Html, ParserError> {
    let document = Html::parse_document(html);

    // First try the combined selector for efficiency
    if let Some(selector) = SELECTOR_CACHE.get("main_content") {
        if let Some(element) = document.select(selector).next() {
            return Ok(Html::parse_fragment(&element.html()));
        }
    }

    // Fallback to individual selectors in order of preference
    let fallback_selectors = ["main", "article", "content_id", "content_class", "body"];

    for selector_key in fallback_selectors {
        if let Some(selector) = SELECTOR_CACHE.get(selector_key) {
            if let Some(element) = document.select(selector).next() {
                return Ok(Html::parse_fragment(&element.html()));
            }
        }
    }

    // Final fallback: return the whole document
    Ok(document)
}

/// Cleans up HTML by removing unwanted elements like scripts, ads, etc.
/// Removes unwanted elements from the HTML using cached CSS selectors.
///
/// Unwanted elements such as scripts, ads, banners, and navigation are identified using a cached selector and removed from the HTML. If the selector cache is unavailable, returns the original HTML.
///
/// # Returns
/// A cleaned HTML string with unwanted elements removed.
///
/// # Examples
///
/// ```
/// use markdown_lab_rs::html_parser::clean_html;
/// let html = r#"<body><script>bad()</script><main>Content</main></body>"#;
/// let cleaned = clean_html(html).unwrap();
/// assert!(cleaned.contains("Content"));
/// assert!(!cleaned.contains("<script>"));
/// ```
pub fn clean_html(html: &str) -> Result<String, ParserError> {
    let document = Html::parse_document(html);

    // Use cached selector for better performance
    if let Some(unwanted_selector) = SELECTOR_CACHE.get("unwanted_elements") {
        // Collect elements to remove first (to avoid modification during iteration)
        let elements_to_remove: Vec<String> = document
            .select(unwanted_selector)
            .map(|element| element.html())
            .collect();

        // Remove elements by replacing their HTML
        let mut cleaned_html = document.root_element().html();
        for element_html in elements_to_remove {
            cleaned_html = cleaned_html.replace(&element_html, "");
        }

        Ok(cleaned_html)
    } else {
        // Fallback: return original HTML if selector cache failed
        Ok(html.to_string())
    }
}

/// More efficient version that works directly with the DOM structure
/// Cleans HTML content by removing unwanted elements, with a placeholder for future DOM-based optimization.
///
/// Currently delegates to `clean_html`, but intended for future enhancement to perform more efficient DOM manipulation when supported.
///
/// # Examples
///
/// ```
/// use markdown_lab_rs::html_parser::clean_html_advanced;
/// let html = r#"<html><body><script>bad()</script><main>Good Content</main></body></html>"#;
/// let cleaned = clean_html_advanced(html).unwrap();
/// assert!(cleaned.contains("Good Content"));
/// assert!(!cleaned.contains("<script>"));
/// ```
pub fn clean_html_advanced(html: &str) -> Result<String, ParserError> {
    // In a future optimization, we could manipulate the DOM tree directly
    // rather than using string replacement, but scraper crate has limited
    // DOM modification capabilities currently.

    // For now, fall back to the cached selector approach
    clean_html(html)
}

/// Extracts all unique absolute URLs from anchor elements in the HTML document.
///
/// Parses the HTML and uses a cached selector to find all anchor tags with `href` attributes. Filters out JavaScript, fragment-only, and empty links. Resolves relative URLs against the provided base URL, returning a sorted vector of unique absolute URLs.
///
/// # Parameters
/// - `html`: The HTML content to parse.
/// - `base_url`: The base URL used to resolve relative links.
///
/// # Returns
/// A vector of unique absolute URLs found in the document.
///
/// # Errors
/// Returns `ParserError::UrlError` if the base URL is invalid, or `ParserError::SelectorError` if the link selector is missing from the cache.
///
/// # Examples
///
/// ```
/// use markdown_lab_rs::html_parser::extract_links;
/// let html = r#"<a href="/about">About</a><a href="https://example.com/contact">Contact</a>"#;
/// let links = extract_links(html, "https://example.com").unwrap();
/// assert_eq!(links, vec![
///     "https://example.com/about".to_string(),
///     "https://example.com/contact".to_string()
/// ]);
/// ```
pub fn extract_links(html: &str, base_url: &str) -> Result<Vec<String>, ParserError> {
    let document = Html::parse_document(html);
    let base_url = url::Url::parse(base_url).map_err(|e| ParserError::UrlError(e.to_string()))?;

    // Use cached selector for better performance
    let selector = SELECTOR_CACHE.get("links").ok_or_else(|| {
        ParserError::SelectorError("Links selector not found in cache".to_string())
    })?;

    let mut links = Vec::new();

    for element in document.select(selector) {
        if let Some(href) = element.value().attr("href") {
            // Skip javascript and fragment-only links
            if href.starts_with("javascript:") || href.starts_with("#") || href.is_empty() {
                continue;
            }

            let processed_link = if href.starts_with("http://") || href.starts_with("https://") {
                // Absolute URL - use as-is
                href.to_string()
            } else {
                // Relative URL - resolve against base URL
                match base_url.join(href) {
                    Ok(absolute_url) => absolute_url.to_string(),
                    Err(_) => continue, // Skip malformed URLs
                }
            };

            links.push(processed_link);
        }
    }

    // Remove duplicates more efficiently using sort + dedup
    links.sort_unstable(); // unstable sort is faster
    links.dedup();

    Ok(links)
}

/// Resolves a relative URL against a base URL, returning the absolute URL as a string.
///
/// If the relative URL is already absolute, it is returned unchanged. Otherwise, the function parses the base URL and joins it with the relative URL. Returns an error if URL parsing or joining fails.
///
/// # Examples
///
/// ```
/// use markdown_lab_rs::html_parser::resolve_url;
/// let abs = resolve_url("https://example.com/path/", "subpage.html").unwrap();
/// assert_eq!(abs, "https://example.com/path/subpage.html");
///
/// let abs2 = resolve_url("https://example.com", "https://other.com/page").unwrap();
/// assert_eq!(abs2, "https://other.com/page");
/// ```
pub fn resolve_url(base_url: &str, relative_url: &str) -> Result<String, ParserError> {
    if relative_url.starts_with("http://") || relative_url.starts_with("https://") {
        Ok(relative_url.to_string())
    } else {
        let base = url::Url::parse(base_url).map_err(|e| ParserError::UrlError(e.to_string()))?;
        let resolved = base
            .join(relative_url)
            .map_err(|e| ParserError::UrlError(e.to_string()))?;
        Ok(resolved.to_string())
    }
}

/// Extracts and normalizes the text content from an HTML element, collapsing consecutive whitespace into single spaces.
/// Uses Cow<str> for zero-copy optimization when possible.
///
/// # Examples
///
/// ```
/// use scraper::{Html, Selector};
/// use markdown_lab_rs::html_parser::get_element_text;
/// let html = Html::parse_fragment("<div>Hello   <b>world</b>!</div>");
/// let selector = Selector::parse("div").unwrap();
/// let element = html.select(&selector).next().unwrap();
/// let text = get_element_text(&element);
/// assert_eq!(text, "Hello world !");
/// ```
pub fn get_element_text(element: &scraper::ElementRef) -> String {
    let raw_text: String = element.text().collect::<Vec<_>>().join(" ");
    normalize_whitespace(&raw_text).into_owned()
}

/// Normalizes whitespace in text using zero-copy optimization when possible.
/// Only allocates a new string if normalization is actually needed.
///
/// # Examples
///
/// ```
/// use markdown_lab_rs::html_parser::normalize_whitespace;
/// let text = "Hello world";
/// let normalized = normalize_whitespace(text);
/// // No allocation needed - returns Cow::Borrowed
/// assert_eq!(normalized, "Hello world");
///
/// let text_with_spaces = "Hello    world\n\ttest";
/// let normalized = normalize_whitespace(text_with_spaces);
/// // Allocation needed - returns Cow::Owned
/// assert_eq!(normalized, "Hello world test");
/// ```
pub fn normalize_whitespace(input: &str) -> Cow<'_, str> {
    // Check if normalization is needed
    let needs_normalization =
        input.chars().any(|c| c.is_whitespace() && c != ' ') || input.contains("  "); // Multiple consecutive spaces

    if !needs_normalization {
        // No allocation needed
        Cow::Borrowed(input)
    } else {
        // Normalize whitespace - allocation required
        let normalized = input.split_whitespace().collect::<Vec<_>>().join(" ");
        Cow::Owned(normalized)
    }
}

/// Efficiently cleans text by removing extra whitespace and optionally trimming.
/// Uses streaming approach for large texts to minimize memory allocations.
///
/// # Arguments
/// * `input` - Input text to clean
/// * `trim` - Whether to trim leading/trailing whitespace
/// * `max_length` - Optional maximum length (truncates if exceeded)
///
/// # Returns
/// Cleaned text with optimized memory usage
pub fn clean_text_efficient(input: &str, trim: bool, max_length: Option<usize>) -> Cow<'_, str> {
    let mut needs_processing = false;

    // Quick check for processing needs
    if trim && (input.starts_with(char::is_whitespace) || input.ends_with(char::is_whitespace)) {
        needs_processing = true;
    }

    if max_length.map_or(false, |max| input.len() > max) {
        needs_processing = true;
    }

    if input.chars().any(|c| c.is_whitespace() && c != ' ') || input.contains("  ") {
        needs_processing = true;
    }

    if !needs_processing {
        return Cow::Borrowed(input);
    }

    // Process the text
    let result = if trim { input.trim() } else { input };

    // Normalize whitespace
    let normalized = normalize_whitespace(result);
    let mut result_string = normalized.into_owned();

    // Apply length limit if specified
    if let Some(max_len) = max_length {
        if result_string.len() > max_len {
            // Find a good truncation point (word boundary)
            let truncation_point = result_string[..max_len]
                .rfind(char::is_whitespace)
                .unwrap_or(max_len);

            result_string.truncate(truncation_point);
            result_string.push_str("...");
        }
    }

    Cow::Owned(result_string)
}

/// Stream-based HTML content extraction for memory-efficient processing of large documents.
/// Processes HTML in chunks to avoid loading entire DOM into memory when possible.
pub struct StreamingHtmlProcessor {
    chunk_size: usize,
    buffer: String,
}

impl StreamingHtmlProcessor {
    /// Create a new streaming processor with specified chunk size.
    pub fn new(chunk_size: usize) -> Self {
        Self {
            chunk_size,
            buffer: String::with_capacity(chunk_size * 2),
        }
    }

    /// Add HTML content to the processor buffer.
    /// Returns extracted text chunks when buffer is full.
    pub fn add_content(&mut self, html_chunk: &str) -> Vec<String> {
        self.buffer.push_str(html_chunk);

        let mut results = Vec::new();

        // Process complete tags in buffer
        while self.buffer.len() > self.chunk_size {
            if let Some(chunk) = self.extract_next_chunk() {
                results.push(chunk);
            } else {
                break;
            }
        }

        results
    }

    /// Finalize processing and return any remaining content.
    pub fn finalize(&mut self) -> Option<String> {
        if self.buffer.is_empty() {
            None
        } else {
            let remaining = self.buffer.clone();
            self.buffer.clear();
            Some(self.extract_text_from_html(&remaining))
        }
    }

    fn extract_next_chunk(&mut self) -> Option<String> {
        // Find a good break point (complete HTML tag)
        let search_start = self.chunk_size.saturating_sub(100); // Look back a bit

        if let Some(tag_end) = self.buffer[search_start..].find('>') {
            let split_point = search_start + tag_end + 1;

            let chunk = self.buffer[..split_point].to_string();
            self.buffer.drain(..split_point);

            Some(self.extract_text_from_html(&chunk))
        } else {
            None
        }
    }

    fn extract_text_from_html(&self, html: &str) -> String {
        // Simple text extraction - in a full implementation,
        // this would use the scraper crate with streaming
        Html::parse_fragment(html)
            .root_element()
            .text()
            .collect::<String>()
    }
}
