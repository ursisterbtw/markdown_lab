use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use markdown_lab_rs::{
    chunker::create_semantic_chunks,
    html_parser::{clean_html, extract_links, extract_main_content},
    markdown_converter::convert_to_markdown,
};
use std::time::Duration;

fn bench_html_processing(c: &mut Criterion) {
    let mut group = c.benchmark_group("HTML Processing");
    group.measurement_time(Duration::from_secs(10));
    group.sample_size(100);

    // Test data
    let html_samples = [
        (
            "small",
            "<html><body><main><h1>Test</h1><p>Small content</p></main></body></html>",
        ),
        (
            "medium",
            include_str!("../test_data/medium.html"),
        ),
        (
            "large",
            include_str!("../test_data/large.html"),
        ),
    ];

    for (size, html) in html_samples.iter() {
        // Benchmark main content extraction
        group.bench_with_input(
            BenchmarkId::new("extract_main_content", size),
            html,
            |b, html| {
                b.iter(|| extract_main_content(black_box(html)))
            },
        );

        // Benchmark HTML cleaning
        group.bench_with_input(
            BenchmarkId::new("clean_html", size),
            html,
            |b, html| {
                b.iter(|| clean_html(black_box(html)))
            },
        );

        // Benchmark link extraction
        group.bench_with_input(
            BenchmarkId::new("extract_links", size),
            html,
            |b, html| {
                b.iter(|| extract_links(black_box(html), "https://example.com"))
            },
        );

        // Benchmark markdown conversion
        group.bench_with_input(
            BenchmarkId::new("convert_to_markdown", size),
            html,
            |b, html| {
                b.iter(|| convert_to_markdown(black_box(html), "https://example.com"))
            },
        );
    }

    group.finish();
}

fn bench_chunking(c: &mut Criterion) {
    let mut group = c.benchmark_group("Text Chunking");
    group.measurement_time(Duration::from_secs(10));
    group.sample_size(100);

    let chunk_sizes = [100, 500, 1000];
    let overlap_sizes = [10, 50, 100];

    let markdown = include_str!("../test_data/sample.md");

    for &chunk_size in chunk_sizes.iter() {
        for &overlap in overlap_sizes.iter() {
            group.bench_with_input(
                BenchmarkId::new(
                    format!("chunk_size_{}_overlap_{}", chunk_size, overlap),
                    chunk_size,
                ),
                &(chunk_size, overlap),
                |b, &(chunk_size, overlap)| {
                    b.iter(|| {
                        create_semantic_chunks(
                            black_box(markdown),
                            black_box(chunk_size),
                            black_box(overlap),
                        )
                    })
                },
            );
        }
    }

    group.finish();
}

criterion_group!(benches, bench_html_processing, bench_chunking);
criterion_main!(benches);
