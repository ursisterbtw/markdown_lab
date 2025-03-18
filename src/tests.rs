#[cfg(test)]
mod html_parser_tests {
    use crate::html_parser::{clean_html, extract_links, extract_main_content};

    #[test]
    fn test_extract_main_content() {
        let html = "<html><head><title>Test</title></head><body><main><h1>Main Content</h1><p>Test paragraph</p></main><footer>Footer content</footer></body></html>";

        let result = extract_main_content(html).unwrap();
        let content = result.root_element().html();
        assert!(content.contains("Main Content"));
        assert!(content.contains("Test paragraph"));
        assert!(!content.contains("Footer content"));
    }

    #[test]
    fn test_clean_html() {
        let html = "<div><script>alert('test');</script><p>Keep this content</p><style>.test{color:red;}</style><div class=\"ad\">Remove this ad</div></div>";

        let result = clean_html(html).unwrap();
        assert!(result.contains("Keep this content"));
        assert!(!result.contains("alert('test')"));
        assert!(!result.contains("Remove this ad"));
        assert!(!result.contains(".test{color:red;}"));
    }

    #[test]
    fn test_extract_links() {
        let html = "<div><a href=\"https://example.com\">Example</a><a href=\"/relative/path\">Relative</a><a href=\"javascript:void(0)\">JS Link</a><a href=\"#section\">Hash Link</a></div>";

        let base_url = "https://test.com";
        let links = extract_links(html, base_url).unwrap();

        assert!(links.contains(&"https://example.com".to_string()));
        assert!(links.contains(&"https://test.com/relative/path".to_string()));
        assert_eq!(links.len(), 2); // Only valid URLs should be included
    }
}

#[cfg(test)]
mod markdown_converter_tests {
    use crate::markdown_converter::convert_to_markdown;

    #[test]
    fn test_convert_basic_html() {
        let html = "<html><head><title>Test Page</title></head><body><h1>Main Title</h1><p>This is a test paragraph.</p><ul><li>Item 1</li><li>Item 2</li></ul></body></html>";

        let base_url = "https://example.com";
        let markdown = convert_to_markdown(html, base_url).unwrap();

        assert!(markdown.contains("# Test Page"));
        assert!(markdown.contains("# Main Title"));
        assert!(markdown.contains("This is a test paragraph."));
        assert!(markdown.contains("- Item 1"));
        assert!(markdown.contains("- Item 2"));
    }

    #[test]
    fn test_convert_links_and_images() {
        let html =
            "<div><a href=\"/test\">Test Link</a><img src=\"/image.jpg\" alt=\"Test Image\"></div>";

        let base_url = "https://example.com";
        let markdown = convert_to_markdown(html, base_url).unwrap();

        assert!(markdown.contains("[Test Link](https://example.com/test)"));
        assert!(markdown.contains("![Test Image](https://example.com/image.jpg)"));
    }

    #[test]
    fn test_convert_code_blocks() {
        let html = "<pre><code class=\"language-rust\">fn main() { println!(\"Hello, world!\"); }</code></pre>";

        let base_url = "https://example.com";
        let markdown = convert_to_markdown(html, base_url).unwrap();

        assert!(markdown.contains("```rust"));
        assert!(markdown.contains("fn main()"));
        assert!(markdown.contains("```"));
    }
}

#[cfg(test)]
mod chunker_tests {
    use crate::chunker::create_semantic_chunks;

    #[test]
    fn test_basic_chunking() {
        let markdown = "# Title\n\n## Section 1\n\nThis is a test paragraph.\n\n## Section 2\n\n* List item 1\n* List item 2";

        let chunks = create_semantic_chunks(markdown, 500, 50).unwrap();
        assert!(!chunks.is_empty());
        assert!(chunks[0].contains("# Title"));
    }

    #[test]
    fn test_chunk_overlap() {
        let markdown = "# First\n\nContent 1\n\n# Second\n\nContent 2\n\n# Third\n\nContent 3";

        let chunks = create_semantic_chunks(markdown, 20, 10).unwrap();
        assert!(chunks.len() > 1);

        // Check for overlap
        if chunks.len() >= 2 {
            let first_chunk = &chunks[0];
            let second_chunk = &chunks[1];

            assert!(first_chunk.contains("First"));
            assert!(second_chunk.contains("Second"));
        }
    }
}
