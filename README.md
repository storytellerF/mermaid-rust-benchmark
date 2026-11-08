# mermaid-rust-benchmark

用于比较纯 Rust Mermaid 图表库性能的基准测试。

**在线报告：** https://storytellerf.github.io/mermaid-rust-benchmark/

## 参与比较的库

| Crate | 版本 | 输出 | 说明 |
|-------|---------|--------|-------------|
| [mermaid-rs-renderer](https://crates.io/crates/mermaid-rs-renderer) | 0.3.1 | SVG | 高速原生 Mermaid 渲染器，支持 23 种图表 |
| [merman](https://crates.io/crates/merman) | 0.8.0-alpha.3 | SVG | 注重与 Mermaid 行为一致的无界面实现 |
| [rusty-mermaid](https://crates.io/crates/rusty-mermaid) | 0.2.0 | SVG | 纯 Rust Mermaid 实现，包含解析、布局和渲染 |
| [selkie](https://crates.io/crates/selkie-rs) | 0.3.0 | SVG | 完整的 Rust Mermaid 解析器与渲染器 |

## 测试用例

每个库都使用三份图表输入进行测量：

- **simple_flowchart**：4 个节点的 LR 流程图。
- **complex_flowchart**：包含子图和循环的 11 节点 TD 流程图。
- **sequence_diagram**：3 个参与者、8 条消息的时序图。

使用 [Criterion.rs](https://github.com/bheisler/criterion.rs) 测量端到端 SVG 渲染耗时。

## 本地运行

```bash
# Prerequisites: Rust stable, Python 3
bash run_benchmarks.sh
# Writes report.html in the project root
```

也可以只运行一个 crate：

```bash
cargo bench --locked -p bench-merman
```

每次完整运行会替换已有日志、Criterion 测量数据和 `report.html`。只有全部库都成功且 12 项测量全部齐备时，才生成报告。运行失败时返回非零状态，日志保留在 `results/` 中。

验证与 CI 细节见 [DEVELOPMENT.md](DEVELOPMENT.md)。
