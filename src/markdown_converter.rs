use scraper::{Html, Selector};
use thiserror::Error;
use url::Url;

#[derive(Error, Debug)]
pub enum MarkdownError {
    #[error("Selector error: {0}")]
    SelectorError(String),

    #[error("URL parsing error: {0}")]
    UrlError(#[from] url::ParseError),

    #[error("Other error: {0}")]
    Other(String),
}

pub fn convert_to_markdown(html: &str, base_url: &str) -> Result<String, MarkdownError> {
    let document = Html::parse_document(html);
    let base_url = Url::parse(base_url)?;

    // Get title
    let title_selector =
        Selector::parse("title").map_err(|e| MarkdownError::SelectorError(e.to_string()))?;
    let title = document
        .select(&title_selector)
        .next()
        .map(|element| element.text().collect::<String>())
        .unwrap_or_else(|| "No Title".to_string());

    // Initialize markdown content with title
    let mut markdown_content = format!("# {}\n\n", title);

    // Process headings
    for i in 1..=6 {
        let heading_selector = Selector::parse(&format!("h{}", i))
            .map_err(|e| MarkdownError::SelectorError(e.to_string()))?;

        for element in document.select(&heading_selector) {
            let text = element.text().collect::<String>().trim().to_string();
            if !text.is_empty() {
                let heading = "#".repeat(i);
                markdown_content.push_str(&format!("{} {}\n\n", heading, text));
            }
        }
    }

    // Process paragraphs
    let p_selector =
        Selector::parse("p").map_err(|e| MarkdownError::SelectorError(e.to_string()))?;
    for element in document.select(&p_selector) {
        let text = element.text().collect::<String>().trim().to_string();
        if !text.is_empty() {
            markdown_content.push_str(&format!("{}\n\n", text));
        }
    }

    // Process links
    let a_selector =
        Selector::parse("a[href]").map_err(|e| MarkdownError::SelectorError(e.to_string()))?;
    for element in document.select(&a_selector) {
        if let Some(href) = element.value().attr("href") {
            let text = element.text().collect::<String>().trim().to_string();
            if !text.is_empty() {
                // Resolve relative URLs
                let absolute_url = base_url
                    .join(href)
                    .unwrap_or_else(|_| Url::parse(href).unwrap_or(base_url.clone()))
                    .to_string();

                markdown_content.push_str(&format!("[{}]({})\n\n", text, absolute_url));
            }
        }
    }

    // Process images
    let img_selector =
        Selector::parse("img[src]").map_err(|e| MarkdownError::SelectorError(e.to_string()))?;
    for element in document.select(&img_selector) {
        if let Some(src) = element.value().attr("src") {
            let alt = element.value().attr("alt").unwrap_or("image");

            // Resolve relative URLs
            let absolute_url = base_url
                .join(src)
                .unwrap_or_else(|_| Url::parse(src).unwrap_or(base_url.clone()))
                .to_string();

            markdown_content.push_str(&format!("![{}]({})\n\n", alt, absolute_url));
        }
    }

    // Process lists
    let ul_selector =
        Selector::parse("ul").map_err(|e| MarkdownError::SelectorError(e.to_string()))?;
    let li_selector =
        Selector::parse("li").map_err(|e| MarkdownError::SelectorError(e.to_string()))?;

    for ul in document.select(&ul_selector) {
        for li in ul.select(&li_selector) {
            let text = li.text().collect::<String>().trim().to_string();
            if !text.is_empty() {
                markdown_content.push_str(&format!("- {}\n", text));
            }
        }
        markdown_content.push('\n');
    }

    // Process ordered lists
    let ol_selector =
        Selector::parse("ol").map_err(|e| MarkdownError::SelectorError(e.to_string()))?;

    for ol in document.select(&ol_selector) {
        let mut i = 1;
        for li in ol.select(&li_selector) {
            let text = li.text().collect::<String>().trim().to_string();
            if !text.is_empty() {
                markdown_content.push_str(&format!("{}. {}\n", i, text));
                i += 1;
            }
        }
        markdown_content.push('\n');
    }

    // Process code blocks
    let pre_selector =
        Selector::parse("pre, code").map_err(|e| MarkdownError::SelectorError(e.to_string()))?;
    for element in document.select(&pre_selector) {
        let text = element.text().collect::<String>().trim().to_string();
        if !text.is_empty() {
            let lang = element
                .value()
                .classes()
                .find(|c| c.starts_with("language-"))
                .map(|c| c.strip_prefix("language-").unwrap_or(""))
                .unwrap_or("");

            markdown_content.push_str(&format!("```{}\n{}\n```\n\n", lang, text));
        }
    }

    // Process blockquotes
    let blockquote_selector =
        Selector::parse("blockquote").map_err(|e| MarkdownError::SelectorError(e.to_string()))?;
    for element in document.select(&blockquote_selector) {
        let text = element.text().collect::<String>().trim().to_string();
        if !text.is_empty() {
            let quoted = text
                .lines()
                .map(|line| format!("> {}", line))
                .collect::<Vec<String>>()
                .join("\n");

            markdown_content.push_str(&format!("{}\n\n", quoted));
        }
    }

    // Clean up extra newlines
    let result = markdown_content
        .replace("\n\n\n\n", "\n\n")
        .replace("\n\n\n", "\n\n")
        .trim()
        .to_string();

    Ok(result)
}
