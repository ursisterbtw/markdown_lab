use scraper::{Html, Selector};
use std::collections::HashMap;
use once_cell::sync::Lazy;
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
         .related, .share, .social"
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
/// cleaning up the most relevant section. Uses cached selectors for better performance.
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
/// Uses cached selectors and more efficient element removal.
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
/// (Alternative implementation for future optimization)
pub fn clean_html_advanced(html: &str) -> Result<String, ParserError> {
    // In a future optimization, we could manipulate the DOM tree directly
    // rather than using string replacement, but scraper crate has limited
    // DOM modification capabilities currently.
    
    // For now, fall back to the cached selector approach
    clean_html(html)
}

/// Extracts all unique links from the HTML document using cached selectors
pub fn extract_links(html: &str, base_url: &str) -> Result<Vec<String>, ParserError> {
    let document = Html::parse_document(html);
    let base_url = url::Url::parse(base_url).map_err(|e| ParserError::UrlError(e.to_string()))?;

    // Use cached selector for better performance
    let selector = SELECTOR_CACHE
        .get("links")
        .ok_or_else(|| ParserError::SelectorError("Links selector not found in cache".to_string()))?;

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

/// Fast URL resolution utility with error handling
pub fn resolve_url(base_url: &str, relative_url: &str) -> Result<String, ParserError> {
    if relative_url.starts_with("http://") || relative_url.starts_with("https://") {
        Ok(relative_url.to_string())
    } else {
        let base = url::Url::parse(base_url).map_err(|e| ParserError::UrlError(e.to_string()))?;
        let resolved = base.join(relative_url).map_err(|e| ParserError::UrlError(e.to_string()))?;
        Ok(resolved.to_string())
    }
}

/// Utility function to get text content of an element, cleaning up whitespace
pub fn get_element_text(element: &scraper::ElementRef) -> String {
    element
        .text()
        .collect::<Vec<_>>()
        .join(" ")
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
}
