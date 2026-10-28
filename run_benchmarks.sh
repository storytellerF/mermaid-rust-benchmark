#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RESULTS_DIR="$SCRIPT_DIR/results"
# Keep build artifacts cached, but never reuse measurements from an earlier run.
rm -rf -- "$RESULTS_DIR" "$SCRIPT_DIR/target/criterion"
rm -f -- "$SCRIPT_DIR/report.html"
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

failed=()
for i in "${!CRATES[@]}"; do
    crate="${CRATES[$i]}"
    label="${LABELS[$i]}"

    echo "--------------------------------------------"
    echo "  Benchmarking: $label"
    echo "--------------------------------------------"

    if cargo bench --locked --target-dir "$SCRIPT_DIR/target" -p "$crate" --bench bench -- --noplot 2>&1 | tee "$RESULTS_DIR/${label}.log"; then
        echo "  [OK] $label completed"
    else
        echo "  [ERROR] $label benchmarks failed" >&2
        failed+=("$label")
    fi
    echo ""
done

if ((${#failed[@]})); then
    echo "[ERROR] Failed benchmarks: ${failed[*]}. Report generation skipped." >&2
    exit 1
fi

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
