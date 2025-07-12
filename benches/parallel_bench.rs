use criterion::{BenchmarkId, Criterion, criterion_group, criterion_main};
use markdown_lab_rs::{
    markdown_converter::convert_to_markdown,
    optimized_converter::convert_to_markdown_optimized,
    parallel_processor::{ParallelConfig, convert_documents_parallel},
};
use std::hint::black_box;

// Generate test documents
fn generate_test_documents(count: usize) -> Vec<(String, String)> {
    (0..count)
        .map(|i| {
            let html = format!(
                r#"<!DOCTYPE html>
                <html>
                <head><title>Document {}</title></head>
                <body>
                    <h1>Document {}</h1>
                    <p>This is paragraph 1 in document {}.</p>
                    <p>This is paragraph 2 with <a href="/link{}">a link</a>.</p>
                    <ul>
                        <li>Item 1</li>
                        <li>Item 2</li>
                        <li>Item 3</li>
                    </ul>
                    <pre><code>function test{} () {{ return {}; }}</code></pre>
                    <blockquote>Quote from document {}</blockquote>
                </body>
                </html>"#,
                i, i, i, i, i, i, i
            );
            (html, format!("https://example.com/doc{}", i))
        })
        .collect()
}

fn benchmark_sequential_processing(c: &mut Criterion) {
    let mut group = c.benchmark_group("sequential_processing");

    for doc_count in [10, 50, 100, 500].iter() {
        let documents = generate_test_documents(*doc_count);

        group.bench_with_input(
            BenchmarkId::new("standard", doc_count),
            &documents,
            |b, docs| {
                b.iter(|| {
                    docs.iter()
                        .map(|(html, base_url)| {
                            convert_to_markdown(black_box(html), black_box(base_url))
                        })
                        .collect::<Vec<_>>()
                });
            },
        );

        group.bench_with_input(
            BenchmarkId::new("optimized", doc_count),
            &documents,
            |b, docs| {
                b.iter(|| {
                    docs.iter()
                        .map(|(html, base_url)| {
                            convert_to_markdown_optimized(black_box(html), black_box(base_url))
                        })
                        .collect::<Vec<_>>()
                });
            },
        );
    }

    group.finish();
}

fn benchmark_parallel_processing(c: &mut Criterion) {
    let mut group = c.benchmark_group("parallel_processing");

    for doc_count in [10, 50, 100, 500].iter() {
        let documents = generate_test_documents(*doc_count);

        // Test with different thread counts
        for threads in [1, 2, 4, 8].iter() {
            let config = ParallelConfig {
                max_threads: Some(*threads),
                chunk_size: 50,
                use_optimized: true,
            };

            group.bench_with_input(
                BenchmarkId::new(format!("threads_{}", threads), doc_count),
                &documents,
                |b, docs| {
                    b.iter(|| {
                        convert_documents_parallel(
                            black_box(docs.clone()),
                            black_box(config.clone()),
                        )
                    });
                },
            );
        }
    }

    group.finish();
}

fn benchmark_speedup_comparison(c: &mut Criterion) {
    let mut group = c.benchmark_group("speedup_comparison");

    let documents = generate_test_documents(100);

    // Sequential optimized
    group.bench_function("sequential_optimized", |b| {
        b.iter(|| {
            documents
                .iter()
                .map(|(html, base_url)| {
                    convert_to_markdown_optimized(black_box(html), black_box(base_url))
                })
                .collect::<Vec<_>>()
        });
    });

    // Parallel with auto thread count
    let config = ParallelConfig {
        max_threads: None, // Use rayon's default
        chunk_size: 25,
        use_optimized: true,
    };

    group.bench_function("parallel_auto", |b| {
        b.iter(|| {
            convert_documents_parallel(black_box(documents.clone()), black_box(config.clone()))
        });
    });

    group.finish();
}

criterion_group!(
    benches,
    benchmark_sequential_processing,
    benchmark_parallel_processing,
    benchmark_speedup_comparison
);
criterion_main!(benches);
