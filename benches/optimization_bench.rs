use criterion::{Criterion, black_box, criterion_group, criterion_main};
use markdown_lab_rs::{
    markdown_converter::{convert_to_markdown, document_to_markdown, parse_html_to_document},
    optimized_converter::{
        convert_to_markdown_optimized, document_to_markdown_optimized, parse_html_optimized,
    },
};

const SAMPLE_HTML: &str = r#"
<!DOCTYPE html>
<html>
<head>
    <title>Sample Document</title>
</head>
<body>
    <h1>Main Title</h1>
    <p>This is a paragraph with some text content.</p>
    
    <h2>Section 1</h2>
    <p>Another paragraph with <a href="/page1">a link</a> and <a href="https://example.com">another link</a>.</p>
    
    <ul>
        <li>First item</li>
        <li>Second item</li>
        <li>Third item</li>
    </ul>
    
    <h2>Section 2</h2>
    <blockquote>This is a quote from someone.</blockquote>
    
    <pre><code class="language-python">
def hello_world():
    print("Hello, World!")
    </code></pre>
    
    <p>Final paragraph with an <img src="/image.jpg" alt="test image"> embedded.</p>
</body>
</html>
"#;

fn benchmark_standard_parsing(c: &mut Criterion) {
    c.bench_function("standard_parse_html", |b| {
        b.iter(|| {
            let _ =
                parse_html_to_document(black_box(SAMPLE_HTML), black_box("https://example.com"));
        });
    });
}

fn benchmark_optimized_parsing(c: &mut Criterion) {
    c.bench_function("optimized_parse_html", |b| {
        b.iter(|| {
            let _ = parse_html_optimized(black_box(SAMPLE_HTML), black_box("https://example.com"));
        });
    });
}

fn benchmark_standard_to_markdown(c: &mut Criterion) {
    let document = parse_html_to_document(SAMPLE_HTML, "https://example.com").unwrap();

    c.bench_function("standard_to_markdown", |b| {
        b.iter(|| {
            let _ = document_to_markdown(black_box(&document));
        });
    });
}

fn benchmark_optimized_to_markdown(c: &mut Criterion) {
    let document = parse_html_optimized(SAMPLE_HTML, "https://example.com").unwrap();

    c.bench_function("optimized_to_markdown", |b| {
        b.iter(|| {
            let _ = document_to_markdown_optimized(black_box(&document));
        });
    });
}

fn benchmark_full_conversion_comparison(c: &mut Criterion) {
    let mut group = c.benchmark_group("full_conversion");

    group.bench_function("standard", |b| {
        b.iter(|| {
            let _ = convert_to_markdown(black_box(SAMPLE_HTML), black_box("https://example.com"));
        });
    });

    group.bench_function("optimized", |b| {
        b.iter(|| {
            let _ = convert_to_markdown_optimized(
                black_box(SAMPLE_HTML),
                black_box("https://example.com"),
            );
        });
    });

    group.finish();
}

// Benchmark with large document
fn benchmark_large_document_comparison(c: &mut Criterion) {
    // Create a larger HTML document
    let mut large_html =
        String::from(r#"<!DOCTYPE html><html><head><title>Large Document</title></head><body>"#);

    // Add many headings and paragraphs
    for i in 0..100 {
        large_html.push_str(&format!(r#"<h2>Section {}</h2>"#, i));
        large_html.push_str(&format!(
            r#"<p>This is paragraph {} with some content and <a href="/link{}">a link</a>.</p>"#,
            i, i
        ));

        if i % 10 == 0 {
            large_html.push_str(r#"<ul><li>Item 1</li><li>Item 2</li><li>Item 3</li></ul>"#);
        }

        if i % 20 == 0 {
            large_html.push_str(r#"<pre><code>function example() { return "code"; }</code></pre>"#);
        }
    }

    large_html.push_str("</body></html>");

    let mut group = c.benchmark_group("large_document");

    group.bench_function("standard", |b| {
        b.iter(|| {
            let _ = convert_to_markdown(black_box(&large_html), black_box("https://example.com"));
        });
    });

    group.bench_function("optimized", |b| {
        b.iter(|| {
            let _ = convert_to_markdown_optimized(
                black_box(&large_html),
                black_box("https://example.com"),
            );
        });
    });

    group.finish();
}

criterion_group!(
    benches,
    benchmark_standard_parsing,
    benchmark_optimized_parsing,
    benchmark_standard_to_markdown,
    benchmark_optimized_to_markdown,
    benchmark_full_conversion_comparison,
    benchmark_large_document_comparison
);

criterion_main!(benches);
