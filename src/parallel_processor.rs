use crate::markdown_converter::convert_to_markdown;
use crate::optimized_converter::convert_to_markdown_optimized;
use pyo3::prelude::*;
use rayon::prelude::*;
use std::sync::Arc;

/// Result type for batch processing
#[derive(Debug)]
pub struct BatchResult {
    pub url: String,
    pub content: Result<String, String>,
}

/// Configuration for parallel processing
#[derive(Clone)]
pub struct ParallelConfig {
    pub max_threads: Option<usize>,
    pub chunk_size: usize,
    pub use_optimized: bool,
}

impl Default for ParallelConfig {
    fn default() -> Self {
        Self {
            max_threads: None, // Use rayon's default
            chunk_size: 100,
            use_optimized: true,
        }
    }
}

/// Process multiple HTML documents in parallel
pub fn convert_documents_parallel(
    documents: Vec<(String, String)>, // (html, base_url) pairs
    config: ParallelConfig,
) -> Vec<(String, Result<String, String>)> {
    // Configure thread pool if specified
    let pool = if let Some(threads) = config.max_threads {
        rayon::ThreadPoolBuilder::new().num_threads(threads).build()
    } else {
        rayon::ThreadPoolBuilder::new().build()
    };

    match pool {
        Ok(pool) => pool.install(|| {
            documents
                .into_par_iter()
                .chunks(config.chunk_size)
                .flat_map(|chunk| {
                    chunk
                        .into_par_iter()
                        .map(|(html, base_url)| {
                            let result = if config.use_optimized {
                                convert_to_markdown_optimized(&html, &base_url)
                            } else {
                                convert_to_markdown(&html, &base_url)
                            };

                            let content = match result {
                                Ok(md) => Ok(md),
                                Err(e) => Err(e.to_string()),
                            };

                            (base_url, content)
                        })
                        .collect::<Vec<_>>()
                })
                .collect()
        }),
        Err(_) => {
            // Fallback to default thread pool
            documents
                .into_par_iter()
                .map(|(html, base_url)| {
                    let result = if config.use_optimized {
                        convert_to_markdown_optimized(&html, &base_url)
                    } else {
                        convert_to_markdown(&html, &base_url)
                    };

                    let content = match result {
                        Ok(md) => Ok(md),
                        Err(e) => Err(e.to_string()),
                    };

                    (base_url, content)
                })
                .collect()
        }
    }
}

/// Process multiple URLs with different base URLs in parallel
pub fn convert_urls_parallel(
    url_pairs: Vec<(String, String, String)>, // (html, base_url, identifier) tuples
    config: ParallelConfig,
) -> Vec<BatchResult> {
    url_pairs
        .into_par_iter()
        .map(|(html, base_url, identifier)| {
            let result = if config.use_optimized {
                convert_to_markdown_optimized(&html, &base_url)
            } else {
                convert_to_markdown(&html, &base_url)
            };

            BatchResult {
                url: identifier,
                content: result.map_err(|e| e.to_string()),
            }
        })
        .collect()
}

/// Parallel HTML parsing and analysis
pub fn analyze_documents_parallel(documents: Vec<String>) -> Vec<DocumentStats> {
    use scraper::Html;

    documents
        .into_par_iter()
        .map(|html| {
            let doc = Html::parse_document(&html);

            // Count various elements
            let heading_count = count_elements(&doc, "h1, h2, h3, h4, h5, h6");
            let paragraph_count = count_elements(&doc, "p");
            let link_count = count_elements(&doc, "a[href]");
            let image_count = count_elements(&doc, "img[src]");

            DocumentStats {
                total_size: html.len(),
                heading_count,
                paragraph_count,
                link_count,
                image_count,
            }
        })
        .collect()
}

#[derive(Debug, Clone)]
pub struct DocumentStats {
    pub total_size: usize,
    pub heading_count: usize,
    pub paragraph_count: usize,
    pub link_count: usize,
    pub image_count: usize,
}

fn count_elements(doc: &scraper::Html, selector: &str) -> usize {
    scraper::Selector::parse(selector)
        .map(|s| doc.select(&s).count())
        .unwrap_or(0)
}

/// Parallel text chunking for large documents
pub fn chunk_documents_parallel(
    documents: Vec<(String, usize, usize)>, // (text, chunk_size, overlap)
) -> Vec<Vec<String>> {
    documents
        .into_par_iter()
        .map(|(text, chunk_size, overlap)| {
            // Use the chunker module's semantic chunks function
            crate::chunker::create_semantic_chunks(&text, chunk_size, overlap)
                .unwrap_or_else(|_| vec![text])
        })
        .collect()
}

/// Find and process all HTML files in parallel
pub fn process_html_files_parallel(
    file_paths: Vec<String>,
    base_url: &str,
    config: ParallelConfig,
) -> Vec<(String, Result<String, String>)> {
    let base_url = Arc::new(base_url.to_string());

    file_paths
        .into_par_iter()
        .filter_map(|path| std::fs::read_to_string(&path).ok().map(|html| (path, html)))
        .map(|(path, html)| {
            let base = base_url.clone();
            let result = if config.use_optimized {
                convert_to_markdown_optimized(&html, &base)
            } else {
                convert_to_markdown(&html, &base)
            };

            (path, result.map_err(|e| e.to_string()))
        })
        .collect()
}

// Python bindings for parallel processing
#[pyfunction]
pub fn convert_documents_parallel_py(
    py: Python<'_>,
    documents: Vec<(String, String)>,
    max_threads: Option<usize>,
    use_optimized: bool,
) -> PyResult<Vec<(String, String)>> {
    let config = ParallelConfig {
        max_threads,
        chunk_size: 100,
        use_optimized,
    };

    // Release the GIL for parallel processing
    py.allow_threads(|| {
        let results = convert_documents_parallel(documents, config);

        // Convert results, skipping errors
        let converted: Vec<(String, String)> = results
            .into_iter()
            .filter_map(|(url, result)| result.ok().map(|content| (url, content)))
            .collect();

        Ok(converted)
    })
}

#[pyfunction]
pub fn analyze_documents_parallel_py(
    py: Python<'_>,
    documents: Vec<String>,
) -> PyResult<Vec<(usize, usize, usize, usize, usize)>> {
    py.allow_threads(|| {
        let stats = analyze_documents_parallel(documents);

        Ok(stats
            .into_iter()
            .map(|s| {
                (
                    s.total_size,
                    s.heading_count,
                    s.paragraph_count,
                    s.link_count,
                    s.image_count,
                )
            })
            .collect())
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parallel_conversion() {
        let documents = vec![
            (
                "<html><body><h1>Test 1</h1></body></html>".to_string(),
                "https://example.com".to_string(),
            ),
            (
                "<html><body><h1>Test 2</h1></body></html>".to_string(),
                "https://example.com".to_string(),
            ),
            (
                "<html><body><h1>Test 3</h1></body></html>".to_string(),
                "https://example.com".to_string(),
            ),
        ];

        let config = ParallelConfig::default();
        let results = convert_documents_parallel(documents, config);

        assert_eq!(results.len(), 3);
        for (_, result) in results {
            assert!(result.is_ok());
        }
    }

    #[test]
    fn test_document_analysis() {
        let documents = vec![
            r#"<html><body>
                <h1>Title</h1>
                <p>Paragraph 1</p>
                <p>Paragraph 2</p>
                <a href="/link">Link</a>
                <img src="/image.jpg">
            </body></html>"#
                .to_string(),
        ];

        let stats = analyze_documents_parallel(documents);
        assert_eq!(stats.len(), 1);

        let stat = &stats[0];
        assert_eq!(stat.heading_count, 1);
        assert_eq!(stat.paragraph_count, 2);
        assert_eq!(stat.link_count, 1);
        assert_eq!(stat.image_count, 1);
    }
}
