#!/usr/bin/env python3
"""Parse criterion benchmark results and generate a modern HTML report."""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent

def load_crate_meta() -> dict:
    with open(SCRIPT_DIR / "crates.json") as f:
        return json.load(f)


def parse_criterion_dir(criterion_dir: str) -> list[dict]:
    """Walk the criterion output directory and collect benchmark results."""
    results = []
    criterion_path = Path(criterion_dir)
    if not criterion_path.exists():
        print(f"Warning: criterion directory not found: {criterion_dir}", file=sys.stderr)
        return results

    for group_dir in sorted(criterion_path.iterdir()):
        if not group_dir.is_dir() or group_dir.name == "report":
            continue
        group_name = group_dir.name

        for bench_dir in sorted(group_dir.iterdir()):
            if not bench_dir.is_dir() or bench_dir.name == "report":
                continue
            bench_name = bench_dir.name

            estimates_file = bench_dir / "new" / "estimates.json"
            if not estimates_file.exists():
                continue

            with open(estimates_file) as f:
                estimates = json.load(f)

            point_ns = estimates["median"]["point_estimate"]
            ci_lower = estimates["median"]["confidence_interval"]["lower_bound"]
            ci_upper = estimates["median"]["confidence_interval"]["upper_bound"]

            results.append({
                "group": group_name,
                "bench": bench_name,
                "median_ns": point_ns,
                "ci_lower_ns": ci_lower,
                "ci_upper_ns": ci_upper,
            })

    return results


def parse_log_files(results_dir: str) -> list[dict]:
    """Fallback: parse criterion text output from log files."""
    results = []
    results_path = Path(results_dir)
    if not results_path.exists():
        return results

    pattern = re.compile(
        r"^([^\s].*?)/([^\s].*?)\s+"
        r"time:\s+\[(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\]"
    )

    for log_file in sorted(results_path.glob("*.log")):
        with open(log_file) as f:
            for line in f:
                m = pattern.search(line)
                if not m:
                    continue
                group = m.group(1)
                bench = m.group(2)
                low_val = float(m.group(3))
                low_unit = m.group(4)
                mid_val = float(m.group(5))
                mid_unit = m.group(6)
                high_val = float(m.group(7))
                high_unit = m.group(8)

                results.append({
                    "group": group,
                    "bench": bench,
                    "median_ns": to_ns(mid_val, mid_unit),
                    "ci_lower_ns": to_ns(low_val, low_unit),
                    "ci_upper_ns": to_ns(high_val, high_unit),
                })

    return results


def to_ns(value: float, unit: str) -> float:
    multipliers = {"ps": 0.001, "ns": 1.0, "µs": 1_000, "us": 1_000, "ms": 1_000_000, "s": 1_000_000_000}
    if unit not in multipliers:
        raise ValueError(f"Unknown time unit: {unit!r}")
    return value * multipliers[unit]


def format_time(ns: float) -> str:
    if ns < 1_000:
        return f"{ns:.1f} ns"
    elif ns < 1_000_000:
        return f"{ns / 1_000:.2f} µs"
    elif ns < 1_000_000_000:
        return f"{ns / 1_000_000:.2f} ms"
    else:
        return f"{ns / 1_000_000_000:.3f} s"


def _chart_id(bench: str, index: int) -> str:
    return f"chart_{index}"


def generate_html(results: list[dict], output_path: str):
    """Generate a modern HTML report from benchmark results."""
    crate_meta = load_crate_meta()
    bench_names = sorted(set(r["bench"] for r in results))
    groups = sorted(set(r["group"] for r in results))

    group_data = {}
    for r in results:
        key = (r["group"], r["bench"])
        group_data[key] = r

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    chart_datasets = {}
    for bench in bench_names:
        chart_datasets[bench] = {"labels": [], "values": [], "errors": []}
        for group in groups:
            key = (group, bench)
            if key in group_data:
                d = group_data[key]
                us = d["median_ns"] / 1_000
                err_low = (d["median_ns"] - d["ci_lower_ns"]) / 1_000
                err_high = (d["ci_upper_ns"] - d["median_ns"]) / 1_000
                chart_datasets[bench]["labels"].append(group)
                chart_datasets[bench]["values"].append(round(us, 3))
                chart_datasets[bench]["errors"].append([round(err_low, 3), round(err_high, 3)])

    colors = [
        "#6366f1", "#ec4899", "#14b8a6", "#f59e0b",
        "#8b5cf6", "#ef4444", "#06b6d4", "#84cc16",
        "#f97316", "#a855f7",
    ]

    table_rows = ""
    for group in groups:
        meta = crate_meta.get(group, {})
        version = meta.get("version", "?")
        desc = meta.get("description", "")
        url = meta.get("url", "#")
        output_type = meta.get("output_type", "?")

        cells = ""
        for bench in bench_names:
            key = (group, bench)
            if key in group_data:
                d = group_data[key]
                median = format_time(d["median_ns"])
                ci_low = format_time(d["ci_lower_ns"])
                ci_high = format_time(d["ci_upper_ns"])
                cells += f'<td class="bench-cell" data-ns="{d["median_ns"]:.0f}">{median}<span class="ci">[{ci_low} .. {ci_high}]</span></td>'
            else:
                cells += '<td class="bench-cell na">N/A</td>'

        table_rows += f"""
        <tr>
            <td class="lib-name"><a href="{url}" target="_blank">{group}</a><span class="version">v{version}</span></td>
            <td class="lib-type">{output_type}</td>
            <td class="lib-desc">{desc}</td>
            {cells}
        </tr>"""

    bench_headers = "".join(f'<th class="bench-header">{b}</th>' for b in bench_names)

    chart_js_blocks = ""
    for i, bench in enumerate(bench_names):
        ds = chart_datasets[bench]
        if not ds["values"]:
            continue
        color = colors[i % len(colors)]
        chart_id = _chart_id(bench, i)
        bench_js = json.dumps(bench)
        bench_label_js = json.dumps(f"{bench} (µs)")
        chart_js_blocks += f"""
    {{
        const ctx = document.getElementById('{chart_id}').getContext('2d');
        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(ds['labels'])},
                datasets: [{{
                    label: {bench_label_js},
                    data: {json.dumps(ds['values'])},
                    backgroundColor: '{color}44',
                    borderColor: '{color}',
                    borderWidth: 2,
                    borderRadius: 6,
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {{
                    legend: {{ display: false }},
                    title: {{
                        display: true,
                        text: {bench_js},
                        font: {{ size: 16, weight: '600' }},
                        color: '#1e293b',
                        padding: {{ bottom: 16 }}
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(ctx) {{
                                return ctx.parsed.x.toFixed(2) + ' µs';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        title: {{ display: true, text: 'Time (µs)', font: {{ size: 13 }} }},
                        grid: {{ color: '#e2e8f0' }},
                        ticks: {{ font: {{ size: 12 }} }}
                    }},
                    y: {{
                        grid: {{ display: false }},
                        ticks: {{ font: {{ size: 13, weight: '500' }} }}
                    }}
                }}
            }}
        }});
    }}
"""

    canvas_blocks = ""
    for i, bench in enumerate(bench_names):
        ds = chart_datasets[bench]
        if not ds["values"]:
            continue
        chart_id = _chart_id(bench, i)
        canvas_blocks += f"""
        <div class="chart-card">
            <canvas id="{chart_id}"></canvas>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mermaid Rust Libraries Benchmark Report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #667eea11 0%, #764ba211 100%);
    min-height: 100vh; color: #1e293b; line-height: 1.6;
}}
.container {{ max-width: 1400px; margin: 0 auto; padding: 2rem; }}
header {{
    text-align: center; margin-bottom: 3rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 3rem 2rem; border-radius: 20px; color: white;
    box-shadow: 0 20px 60px rgba(102, 126, 234, 0.3);
}}
header h1 {{ font-size: 2.5rem; font-weight: 800; letter-spacing: -0.02em; }}
header p {{ font-size: 1.1rem; opacity: 0.9; margin-top: 0.5rem; }}
.meta {{ display: flex; gap: 2rem; justify-content: center; margin-top: 1.5rem; flex-wrap: wrap; }}
.meta-item {{
    background: rgba(255,255,255,0.15); padding: 0.5rem 1.2rem;
    border-radius: 30px; font-size: 0.9rem; backdrop-filter: blur(10px);
}}
.section {{ margin-bottom: 3rem; }}
.section h2 {{
    font-size: 1.6rem; font-weight: 700; margin-bottom: 1.5rem;
    color: #334155; display: flex; align-items: center; gap: 0.5rem;
}}
.section h2::before {{
    content: ''; display: inline-block; width: 4px; height: 28px;
    background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 2px;
}}
.table-wrap {{
    overflow-x: auto; border-radius: 16px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    background: white;
}}
table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
thead th {{
    background: #f8fafc; padding: 1rem; text-align: left; font-weight: 600;
    color: #475569; border-bottom: 2px solid #e2e8f0; white-space: nowrap;
    position: sticky; top: 0; z-index: 1;
}}
tbody td {{ padding: 0.85rem 1rem; border-bottom: 1px solid #f1f5f9; }}
tbody tr:hover {{ background: #f8fafc; }}
tbody tr:last-child td {{ border-bottom: none; }}
.lib-name {{
    font-weight: 600; white-space: nowrap;
}}
.lib-name a {{
    color: #4f46e5; text-decoration: none;
    transition: color 0.2s;
}}
.lib-name a:hover {{ color: #7c3aed; text-decoration: underline; }}
.version {{
    display: inline-block; font-size: 0.75rem; font-weight: 500;
    color: #64748b; background: #f1f5f9; padding: 0.1rem 0.5rem;
    border-radius: 10px; margin-left: 0.5rem;
}}
.lib-type {{
    font-size: 0.8rem; font-weight: 500; text-align: center;
}}
.lib-desc {{ color: #64748b; font-size: 0.85rem; max-width: 320px; }}
.bench-cell {{
    font-variant-numeric: tabular-nums; white-space: nowrap; font-weight: 500;
}}
.bench-cell .ci {{
    display: block; font-size: 0.72rem; color: #94a3b8; font-weight: 400;
}}
.bench-cell.na {{ color: #cbd5e1; font-style: italic; font-weight: 400; }}
.bench-cell.fastest {{
    color: #059669; background: #ecfdf5;
}}
.bench-header {{ text-align: center; }}
.charts-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
    gap: 1.5rem;
}}
.chart-card {{
    background: white; border-radius: 16px; padding: 1.5rem;
    box-shadow: 0 4px 24px rgba(0,0,0,0.06);
    height: 340px;
}}
footer {{
    text-align: center; padding: 2rem; color: #94a3b8; font-size: 0.85rem;
}}
footer a {{ color: #6366f1; text-decoration: none; }}
@media (max-width: 768px) {{
    .container {{ padding: 1rem; }}
    header {{ padding: 2rem 1rem; }}
    header h1 {{ font-size: 1.6rem; }}
    .charts-grid {{ grid-template-columns: 1fr; }}
    .chart-card {{ height: 280px; }}
}}
</style>
</head>
<body>
<div class="container">
    <header>
        <h1>Mermaid Rust Libraries Benchmark</h1>
        <p>Performance comparison of pure Rust Mermaid diagram implementations</p>
        <div class="meta">
            <span class="meta-item">{now}</span>
            <span class="meta-item">{len(groups)} libraries</span>
            <span class="meta-item">{len(bench_names)} test cases</span>
            <span class="meta-item">{len(results)} measurements</span>
        </div>
    </header>

    <div class="section">
        <h2>Results Table</h2>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Library</th>
                        <th>Output</th>
                        <th>Description</th>
                        {bench_headers}
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
    </div>

    <div class="section">
        <h2>Visual Comparison</h2>
        <div class="charts-grid">
            {canvas_blocks}
        </div>
    </div>

    <footer>
        Benchmarks powered by <a href="https://github.com/bheisler/criterion.rs">Criterion.rs</a>.
        Lower is better.
    </footer>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {{
    // Highlight fastest per column
    const table = document.querySelector('table');
    const rows = table.querySelectorAll('tbody tr');
    const headerCells = table.querySelectorAll('thead th');
    const benchStartIdx = 3;

    for (let col = benchStartIdx; col < headerCells.length; col++) {{
        let minNs = Infinity;
        let minCell = null;
        rows.forEach(row => {{
            const cell = row.children[col];
            if (cell && cell.dataset.ns) {{
                const ns = parseFloat(cell.dataset.ns);
                if (ns < minNs) {{
                    minNs = ns;
                    minCell = cell;
                }}
            }}
        }});
        if (minCell) minCell.classList.add('fastest');
    }}

    // Charts
    {chart_js_blocks}
}});
</script>
</body>
</html>
"""

    with open(output_path, "w") as f:
        f.write(html)
    print(f"HTML report written to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate benchmark HTML report")
    parser.add_argument("--criterion-dir", default="target/criterion")
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--output", default="report.html")
    args = parser.parse_args()

    results = parse_criterion_dir(args.criterion_dir)

    if not results:
        print("No criterion JSON found, trying log file parsing...", file=sys.stderr)
        results = parse_log_files(args.results_dir)

    if not results:
        print("ERROR: No benchmark results found!", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(results)} benchmark measurements")
    generate_html(results, args.output)


if __name__ == "__main__":
    main()
