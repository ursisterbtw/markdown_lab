use once_cell::sync::Lazy;
use scraper::{Html, Selector};
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
///
/// # Examples
///
/// ```
/// use markdown_lab_rs::html_parser::get_element_text;
/// use scraper::{Html, Selector};
/// let html = Html::parse_fragment("<div>Hello   <b>world</b>!</div>");
/// let selector = Selector::parse("div").unwrap();
/// let element = html.select(&selector).next().unwrap();
/// let text = get_element_text(&element);
/// assert_eq!(text, "Hello world !");
/// ```
pub fn get_element_text(element: &scraper::ElementRef) -> String {
    element
        .text()
        .collect::<Vec<_>>()
        .join(" ")
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
}
