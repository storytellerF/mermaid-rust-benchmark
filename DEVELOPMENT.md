# 开发指南

使用 stable Rust、Bash 和 Python 3。以下命令运行受控的执行器测试，不编译 Rust，也不发布任何内容：

```bash
python3 -m unittest discover -s tests -v
```

Windows 上如果 Bash 不在 `PATH` 中，将 `BASH` 设为 Git Bash 可执行文件路径。测试使用模拟 cargo 结果，实际运行执行器和报告生成器，覆盖基准测试失败、日志写入、测量缺失、报告生成失败和过时缓存结果等情况。

使用已提交的依赖图编译全部基准测试：

```bash
cargo bench --workspace --locked --no-run
```

运行 `bash run_benchmarks.sh` 执行完整基准测试并生成 HTML 报告。执行器将目标目录固定为仓库的 `target/`，即使设置了 `CARGO_TARGET_DIR`，测量清理和报告收集也使用同一位置。编译产物保留缓存；每次运行前清除 Criterion 测量值、日志和上一份报告。执行器会尝试所有库，但任意基准测试或日志写入失败都会阻止报告生成，并返回非零状态。生成器还要求四组库和三种用例全部齐备。

## 依赖兼容性

`merman-render 0.8.0-alpha.3` 需要匹配的 `dugong`、`dugong-graphlib` 和 `manatee 0.8.0-alpha.3` API。Cargo 的预发布版本范围允许解析到 alpha.6，而该版本移除了渲染器使用的 API。在 `Cargo.lock` 中保持这些版本兼容，升级时使用上面的编译命令并执行一次完整运行。参见 [issue #7](https://github.com/storytellerF/mermaid-rust-benchmark/issues/7)。执行器使用 `--locked`，因此普通基准测试不能修改依赖图。升级时，让 `crates.json` 和 `README.md` 显示的库版本与锁文件保持一致。

## CI 与部署

涉及匹配路径的 `main` push 或手动触发，会先运行受控测试，再执行完整基准测试。只有这些步骤成功，才准备并上传 Pages 产物。部署作业要求基准测试作业成功；执行器返回非零状态时，不完整报告不能发布。不要为这些步骤添加 `continue-on-error`，也不要给部署作业添加 `always()`。
