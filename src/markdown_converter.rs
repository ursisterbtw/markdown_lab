use scraper::{Html, Selector};
use serde::{Deserialize, Serialize};
use thiserror::Error;
use url::Url;

#[derive(Error, Debug)]
pub enum MarkdownError {
    #[error("Selector error: {0}")]
    SelectorError(String),

    #[error("URL parsing error: {0}")]
    UrlError(#[from] url::ParseError),

    #[error("Serialization error: {0}")]
    SerializationError(String),

    #[error("Other error: {0}")]
    Other(String),
}

/// Supported output formats for content conversion
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OutputFormat {
    Markdown,
    Json,
    Xml,
}

/// Data structure for document representation that can be serialized to different formats
#[derive(Debug, Serialize, Deserialize)]
pub struct Document {
    pub title: String,
    pub base_url: String,
    pub headings: Vec<Heading>,
    pub paragraphs: Vec<String>,
    pub links: Vec<Link>,
    pub images: Vec<Image>,
    pub lists: Vec<List>,
    pub code_blocks: Vec<CodeBlock>,
    pub blockquotes: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Heading {
    pub level: u8,
    pub text: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Link {
    pub text: String,
    pub url: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Image {
    pub alt: String,
    pub src: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct List {
    pub ordered: bool,
    pub items: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct CodeBlock {
    pub language: String,
    pub code: String,
}

/// Parse HTML into our document structure
pub fn parse_html_to_document(html: &str, base_url_str: &str) -> Result<Document, MarkdownError> {
    let document_html = Html::parse_document(html);
    let base_url = Url::parse(base_url_str)?;

    let title = extract_document_title(&document_html)?;
    let mut document = create_document_structure(&title, base_url_str);

    populate_document_content(&mut document, &document_html, &base_url)?;

    Ok(document)
}

/// Extract the document title from HTML
fn extract_document_title(document_html: &Html) -> Result<String, MarkdownError> {
    let title_selector =
        Selector::parse("title").map_err(|e| MarkdownError::SelectorError(e.to_string()))?;
    let title = document_html
        .select(&title_selector)
        .next()
        .map(|element| element.text().collect::<String>())
        .unwrap_or_else(|| "No Title".to_string());
    Ok(title.trim().to_string())
}

/// Create the initial document structure
fn create_document_structure(title: &str, base_url: &str) -> Document {
    Document {
        title: title.to_string(),
        base_url: base_url.to_string(),
        headings: Vec::new(),
        paragraphs: Vec::new(),
        links: Vec::new(),
        images: Vec::new(),
        lists: Vec::new(),
        code_blocks: Vec::new(),
        blockquotes: Vec::new(),
    }
}

/// Populate document with content from HTML
fn populate_document_content(
    document: &mut Document,
    document_html: &Html,
    base_url: &Url,
) -> Result<(), MarkdownError> {
    process_headings(document, document_html)?;
    process_paragraphs(document, document_html)?;
    process_links(document, document_html, base_url)?;
    process_images(document, document_html, base_url)?;
    process_lists(document, document_html)?;
    process_code_blocks(document, document_html)?;
    process_blockquotes(document, document_html)?;
    Ok(())
}

/// Process heading elements (h1-h6)
fn process_headings(document: &mut Document, document_html: &Html) -> Result<(), MarkdownError> {
    for i in 1..=6 {
        let heading_selector = Selector::parse(&format!("h{}", i))
            .map_err(|e| MarkdownError::SelectorError(e.to_string()))?;

        for element in document_html.select(&heading_selector) {
            let text = element.text().collect::<String>().trim().to_string();
            if !text.is_empty() {
                document.headings.push(Heading {
                    level: i as u8,
                    text,
                });
            }
        }
    }
    Ok(())
}

/// Process paragraph elements
fn process_paragraphs(document: &mut Document, document_html: &Html) -> Result<(), MarkdownError> {
    let p_selector =
        Selector::parse("p").map_err(|e| MarkdownError::SelectorError(e.to_string()))?;
    for element in document_html.select(&p_selector) {
        let text = element.text().collect::<String>().trim().to_string();
        if !text.is_empty() {
            document.paragraphs.push(text);
        }
    }
    Ok(())
}

/// Process link elements
fn process_links(
    document: &mut Document,
    document_html: &Html,
    base_url: &Url,
) -> Result<(), MarkdownError> {
    let a_selector =
        Selector::parse("a[href]").map_err(|e| MarkdownError::SelectorError(e.to_string()))?;
    for element in document_html.select(&a_selector) {
        if let Some(href) = element.value().attr("href") {
            let text = element.text().collect::<String>().trim().to_string();
            if !text.is_empty() {
                let absolute_url = resolve_url_against_base(base_url, href);
                document.links.push(Link {
                    text,
                    url: absolute_url,
                });
            }
        }
    }
    Ok(())
}

/// Process image elements
fn process_images(
    document: &mut Document,
    document_html: &Html,
    base_url: &Url,
) -> Result<(), MarkdownError> {
    let img_selector =
        Selector::parse("img[src]").map_err(|e| MarkdownError::SelectorError(e.to_string()))?;
    for element in document_html.select(&img_selector) {
        if let Some(src) = element.value().attr("src") {
            let alt = element.value().attr("alt").unwrap_or("image").to_string();
            let absolute_url = resolve_url_against_base(base_url, src);
            document.images.push(Image {
                alt,
                src: absolute_url,
            });
        }
    }
    Ok(())
}

/// Process list elements (both ordered and unordered)
fn process_lists(document: &mut Document, document_html: &Html) -> Result<(), MarkdownError> {
    let li_selector =
        Selector::parse("li").map_err(|e| MarkdownError::SelectorError(e.to_string()))?;

    // Process unordered lists
    let ul_selector =
        Selector::parse("ul").map_err(|e| MarkdownError::SelectorError(e.to_string()))?;
    for ul in document_html.select(&ul_selector) {
        if let Some(list) = extract_list_items(&ul, &li_selector, false) {
            document.lists.push(list);
        }
    }

    // Process ordered lists
    let ol_selector =
        Selector::parse("ol").map_err(|e| MarkdownError::SelectorError(e.to_string()))?;
    for ol in document_html.select(&ol_selector) {
        if let Some(list) = extract_list_items(&ol, &li_selector, true) {
            document.lists.push(list);
        }
    }

    Ok(())
}

/// Process code block elements
fn process_code_blocks(document: &mut Document, document_html: &Html) -> Result<(), MarkdownError> {
    let pre_selector =
        Selector::parse("pre, code").map_err(|e| MarkdownError::SelectorError(e.to_string()))?;
    for element in document_html.select(&pre_selector) {
        let text = element.text().collect::<String>().trim().to_string();
        if !text.is_empty() {
            let lang = element
                .value()
                .classes()
                .find(|c| c.starts_with("language-"))
                .map(|c| c.strip_prefix("language-").unwrap_or(""))
                .unwrap_or("")
                .to_string();

            document.code_blocks.push(CodeBlock {
                language: lang,
                code: text,
            });
        }
    }
    Ok(())
}

/// Process blockquote elements
fn process_blockquotes(document: &mut Document, document_html: &Html) -> Result<(), MarkdownError> {
    let blockquote_selector =
        Selector::parse("blockquote").map_err(|e| MarkdownError::SelectorError(e.to_string()))?;
    for element in document_html.select(&blockquote_selector) {
        let text = element.text().collect::<String>().trim().to_string();
        if !text.is_empty() {
            document.blockquotes.push(text);
        }
    }
    Ok(())
}

/// Helper function to resolve URLs against a base URL
fn resolve_url_against_base(base_url: &Url, href: &str) -> String {
    base_url
        .join(href)
        .unwrap_or_else(|_| Url::parse(href).unwrap_or(base_url.clone()))
        .to_string()
}

/// Helper function to extract list items
fn extract_list_items(
    list_element: &scraper::ElementRef,
    li_selector: &Selector,
    ordered: bool,
) -> Option<List> {
    let mut items = Vec::new();
    for li in list_element.select(li_selector) {
        let text = li.text().collect::<String>().trim().to_string();
        if !text.is_empty() {
            items.push(text);
        }
    }

    if !items.is_empty() {
        Some(List { ordered, items })
    } else {
        None
    }
}

/// Convert document to markdown format
pub fn document_to_markdown(document: &Document) -> String {
    let mut markdown_content = format!("# {}\n\n", document.title);

    // Add headings
    for heading in &document.headings {
        let heading_prefix = "#".repeat(heading.level as usize);
        markdown_content.push_str(&format!("{} {}\n\n", heading_prefix, heading.text));
    }

    // Add paragraphs
    for paragraph in &document.paragraphs {
        markdown_content.push_str(&format!("{}\n\n", paragraph));
    }

    // Add links
    for link in &document.links {
        markdown_content.push_str(&format!("[{}]({})\n\n", link.text, link.url));
    }

    // Add images
    for image in &document.images {
        markdown_content.push_str(&format!("![{}]({})\n\n", image.alt, image.src));
    }

    // Add lists
    for list in &document.lists {
        if list.ordered {
            for (i, item) in list.items.iter().enumerate() {
                markdown_content.push_str(&format!("{}. {}\n", i + 1, item));
            }
        } else {
            for item in &list.items {
                markdown_content.push_str(&format!("- {}\n", item));
            }
        }
        markdown_content.push('\n');
    }

    // Add code blocks
    for code_block in &document.code_blocks {
        markdown_content.push_str(&format!(
            "```{}\n{}\n```\n\n",
            code_block.language, code_block.code
        ));
    }

    // Add blockquotes
    for blockquote in &document.blockquotes {
        let quoted = blockquote
            .lines()
            .map(|line| format!("> {}", line))
            .collect::<Vec<String>>()
            .join("\n");
        markdown_content.push_str(&format!("{}\n\n", quoted));
    }

    // Clean up extra newlines
    markdown_content
        .replace("\n\n\n\n", "\n\n")
        .replace("\n\n\n", "\n\n")
        .trim()
        .to_string()
}

/// Convert document to JSON format
pub fn document_to_json(document: &Document) -> Result<String, MarkdownError> {
    serde_json::to_string_pretty(document).map_err(|e| {
        MarkdownError::SerializationError(format!("Failed to serialize to JSON: {}", e))
    })
}

/// Convert document to XML format
pub fn document_to_xml(document: &Document) -> Result<String, MarkdownError> {
    use quick_xml::se::to_string;

    match to_string(document) {
        Ok(xml) => Ok(xml),
        Err(e) => {
            eprintln!("Error serializing document to XML: {:?}", e);
            Err(MarkdownError::SerializationError(format!(
                "Failed to serialize to XML: {}",
                e
            )))
        }
    }
}

/// Convert HTML to the specified output format
pub fn convert_html(
    html: &str,
    base_url: &str,
    format: OutputFormat,
) -> Result<String, MarkdownError> {
    let document = parse_html_to_document(html, base_url)?;

    match format {
        OutputFormat::Markdown => Ok(document_to_markdown(&document)),
        OutputFormat::Json => document_to_json(&document),
        OutputFormat::Xml => document_to_xml(&document),
    }
}

/// Backward compatibility function for convert_to_markdown
pub fn convert_to_markdown(html: &str, base_url: &str) -> Result<String, MarkdownError> {
    convert_html(html, base_url, OutputFormat::Markdown)
}
