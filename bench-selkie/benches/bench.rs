use criterion::{criterion_group, criterion_main, Criterion};

const SIMPLE: &str = include_str!("../../test-data/simple_flowchart.mmd");
const COMPLEX: &str = include_str!("../../test-data/complex_flowchart.mmd");
const SEQUENCE: &str = include_str!("../../test-data/sequence_diagram.mmd");

fn bench_render_svg(c: &mut Criterion) {
    let simple = selkie::parse(SIMPLE).unwrap();
    let complex = selkie::parse(COMPLEX).unwrap();
    let sequence = selkie::parse(SEQUENCE).unwrap();

    let mut g = c.benchmark_group("selkie");
    g.bench_function("simple_flowchart", |b| {
        b.iter(|| selkie::render::render(&simple).unwrap());
    });
    g.bench_function("complex_flowchart", |b| {
        b.iter(|| selkie::render::render(&complex).unwrap());
    });
    g.bench_function("sequence_diagram", |b| {
        b.iter(|| selkie::render::render(&sequence).unwrap());
    });
    g.finish();
}

criterion_group!(benches, bench_render_svg);
criterion_main!(benches);
