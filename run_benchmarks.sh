#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RESULTS_DIR="$SCRIPT_DIR/results"
mkdir -p "$RESULTS_DIR"

CRATES=(
    "bench-mermaid-rs-renderer"
    "bench-merman"
    "bench-rusty-mermaid"
    "bench-selkie"
)

LABELS=(
    "mermaid-rs-renderer"
    "merman"
    "rusty-mermaid"
    "selkie"
)

echo "============================================"
echo "  Mermaid Rust SVG Libraries Benchmark"
echo "============================================"
echo ""
echo "Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "Rust: $(rustc --version)"
echo "OS:   $(uname -srm)"
echo ""

for i in "${!CRATES[@]}"; do
    crate="${CRATES[$i]}"
    label="${LABELS[$i]}"

    echo "--------------------------------------------"
    echo "  Benchmarking: $label"
    echo "--------------------------------------------"

    if cargo bench -p "$crate" --bench bench -- --noplot 2>&1 | tee "$RESULTS_DIR/${label}.log"; then
        echo "  [OK] $label completed"
    else
        echo "  [WARN] $label benchmarks had errors (partial results may exist)"
    fi
    echo ""
done

echo "============================================"
echo "  Collecting criterion results..."
echo "============================================"

python3 "$SCRIPT_DIR/generate_report.py" \
    --criterion-dir "$SCRIPT_DIR/target/criterion" \
    --results-dir "$RESULTS_DIR" \
    --output "$SCRIPT_DIR/report.html"

echo ""
echo "Report generated: $SCRIPT_DIR/report.html"
echo "Done!"
