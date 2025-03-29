use pyo3::prelude::*;

#[cfg(test)]
mod tests;

pub mod chunker;
pub mod html_parser;
pub mod js_renderer;
pub mod markdown_converter;

/// Python-friendly enumeration of output formats
#[pyclass]
#[derive(Clone, Copy)]
pub enum OutputFormat {
    Markdown = 0,
    Json = 1,
    Xml = 2,
}

#[pymethods]
impl OutputFormat {
    #[staticmethod]
    fn from_str(format_str: &str) -> Self {
        match format_str.to_lowercase().as_str() {
            "json" => OutputFormat::Json,
            "xml" => OutputFormat::Xml,
            _ => OutputFormat::Markdown,
        }
    }
}

impl From<OutputFormat> for markdown_converter::OutputFormat {
    fn from(py_format: OutputFormat) -> Self {
        match py_format {
            OutputFormat::Markdown => markdown_converter::OutputFormat::Markdown,
            OutputFormat::Json => markdown_converter::OutputFormat::Json,
            OutputFormat::Xml => markdown_converter::OutputFormat::Xml,
        }
    }
}

/// A Python module implemented in Rust.
#[pymodule]
fn markdown_lab_rs(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<OutputFormat>()?;
    m.add_function(wrap_pyfunction!(convert_html_to_markdown, py)?)?;
    m.add_function(wrap_pyfunction!(convert_html_to_format, py)?)?;
    m.add_function(wrap_pyfunction!(chunk_markdown, py)?)?;
    m.add_function(wrap_pyfunction!(render_js_page, py)?)?;
    Ok(())
}

/// Converts HTML content to markdown (legacy method)
#[pyfunction]
fn convert_html_to_markdown(html: &str, base_url: &str) -> PyResult<String> {
    let result = markdown_converter::convert_to_markdown(html, base_url)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
    Ok(result)
}

/// Converts HTML content to the specified format
#[pyfunction]
fn convert_html_to_format(html: &str, base_url: &str, format: Option<String>) -> PyResult<String> {
    let output_format = match format.as_deref() {
        Some("json") => markdown_converter::OutputFormat::Json,
        Some("xml") => markdown_converter::OutputFormat::Xml,
        _ => markdown_converter::OutputFormat::Markdown,
    };

    let result = markdown_converter::convert_html(html, base_url, output_format)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
    Ok(result)
}

/// Chunks markdown content for RAG
#[pyfunction]
fn chunk_markdown(
    markdown: &str,
    chunk_size: usize,
    chunk_overlap: usize,
) -> PyResult<Vec<String>> {
    let chunks = chunker::create_semantic_chunks(markdown, chunk_size, chunk_overlap)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
    Ok(chunks)
}

/// Renders a JavaScript-enabled page and returns the HTML content
#[pyfunction]
fn render_js_page(url: &str, wait_time: Option<u64>) -> PyResult<String> {
    let runtime = tokio::runtime::Runtime::new()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    let html = runtime
        .block_on(async { js_renderer::render_page(url, wait_time.unwrap_or(2000)).await })
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    Ok(html)
}
