# mermaid-rust-benchmark

Performance benchmark comparing pure-Rust Mermaid diagram libraries.

**Live report:** https://storytellerf.github.io/mermaid-rust-benchmark/

## Libraries

| Crate | Version | Output | Description |
|-------|---------|--------|-------------|
| [mermaid-rs-renderer](https://crates.io/crates/mermaid-rs-renderer) | 0.2.2 | SVG | Fast native Mermaid renderer, 23 diagram types |
| [merman](https://crates.io/crates/merman) | 0.8.0-alpha.1 | SVG | Parity-focused headless Mermaid |
| [rusty-mermaid](https://crates.io/crates/rusty-mermaid) | 0.2.0 | SVG | Pure Rust Mermaid, parse + layout + render |
| [selkie](https://crates.io/crates/selkie-rs) | 0.3.0 | SVG | Full Rust Mermaid parser & renderer |

## Test Cases

Each library is benchmarked against three diagram inputs:

- **simple_flowchart** — 4-node LR flowchart
- **complex_flowchart** — 11-node TD flowchart with subgraphs and a loop
- **sequence_diagram** — 3-participant, 8-message sequence diagram

Benchmarks measure end-to-end SVG rendering time using [Criterion.rs](https://github.com/bheisler/criterion.rs).

## Run Locally

```bash
# Prerequisites: Rust stable, Python 3
bash run_benchmarks.sh
# Opens report.html in the project root
```

Or run a single crate:

```bash
cargo bench -p bench-merman
```

## CI

On every push to `main`, GitHub Actions runs all benchmarks and deploys the HTML report to GitHub Pages automatically.
