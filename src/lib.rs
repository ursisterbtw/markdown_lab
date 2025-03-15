use pyo3::prelude::*;

mod chunker;
mod html_parser;
mod js_renderer;
mod markdown_converter;

/// A Python module implemented in Rust.
#[pymodule]
fn markdown_lab_rs(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(convert_html_to_markdown, py)?)?;
    m.add_function(wrap_pyfunction!(chunk_markdown, py)?)?;
    m.add_function(wrap_pyfunction!(render_js_page, py)?)?;
    Ok(())
}

/// Converts HTML content to markdown
#[pyfunction]
fn convert_html_to_markdown(html: &str, base_url: &str) -> PyResult<String> {
    let result = markdown_converter::convert_to_markdown(html, base_url)
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
    // Reuse a global runtime or a lazily initialized one for better performance.
    // For example, you could define a static RUNTIME: Lazy<Runtime> ...
    let runtime = get_global_tokio_runtime()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    let html = runtime
        .block_on(async { js_renderer::render_page(url, wait_time.unwrap_or(2000)).await })
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
    Ok(html)
}
