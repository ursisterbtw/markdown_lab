use scraper::{Html, Selector};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ParserError {
    #[error("Selector error: {0}")]
    SelectorError(String),

    #[error("Element not found: {0}")]
    NotFound(String),

    #[error("Other error: {0}")]
    Other(String),
}

/// Extracts the main content from an HTML document by identifying and
/// cleaning up the most relevant section.
pub fn extract_main_content(html: &str) -> Result<Html, ParserError> {
    let document = Html::parse_document(html);

    // Try common content container selectors in order of preference
    let container_selectors = ["main", "article", "#content", ".content", "body"];

    for selector_str in container_selectors {
        let selector =
            Selector::parse(selector_str).map_err(|e| ParserError::SelectorError(e.to_string()))?;

        if let Some(element) = document.select(&selector).next() {
            // Found a main content container
            return Ok(Html::parse_fragment(&element.html()));
        }
    }

    // Fallback: If no specific content container is found, return the whole document.
    // Note: Downstream consumers should handle processing of large documents gracefully.
    Ok(document)
}

/// Cleans up HTML by removing unwanted elements like scripts, ads, etc.
pub fn clean_html(html: &str) -> Result<String, ParserError> {
    let document = Html::parse_document(html);

    // Create a cleaned document by removing unwanted elements
    let mut cleaned_html = document.root_element().html();

    // Elements to remove
    let unwanted_selectors = [
        "script",
        "style",
        "iframe",
        "noscript",
        ".advertisement",
        ".ad",
        ".banner",
        "#cookie-notice",
        "header",
        "footer",
        "nav",
        ".sidebar",
        ".menu",
        ".comments",
        ".related",
        ".share",
        ".social",
    ];

    for selector_str in unwanted_selectors {
        if let Ok(selector) = Selector::parse(selector_str) {
            for element in document.select(&selector) {
                let element_html = element.html();
                cleaned_html = cleaned_html.replace(&element_html, "");
            }
        }
    }

    Ok(cleaned_html)
}

/// Extracts all unique links from the HTML document
pub fn extract_links(html: &str, base_url: &str) -> Result<Vec<String>, ParserError> {
    let document = Html::parse_document(html);
    let base_url = url::Url::parse(base_url).map_err(|e| ParserError::Other(e.to_string()))?;

    let selector =
        Selector::parse("a[href]").map_err(|e| ParserError::SelectorError(e.to_string()))?;

    let mut links = Vec::new();

    for element in document.select(&selector) {
        if let Some(href) = element.value().attr("href") {
            if !href.starts_with("javascript:") && !href.starts_with("#") {
                // For absolute URLs, preserve them exactly as they appear
                if href.starts_with("http://") || href.starts_with("https://") {
                    links.push(href.to_string());
                } else {
                    // For relative URLs, resolve them against the base URL
                    if let Ok(absolute_url) = base_url.join(href) {
                        links.push(absolute_url.to_string());
                    }
                }
            }
        }
    }

    // Remove duplicates
    links.sort();
    links.dedup();

    Ok(links)
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
