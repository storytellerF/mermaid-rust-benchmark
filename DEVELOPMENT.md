# Development

Use stable Rust, Bash, and Python 3. Run the controlled runner tests without
compiling Rust or publishing anything:

```bash
python3 -m unittest discover -s tests -v
```

On Windows, set `BASH` to the Git Bash executable path if Bash is not on `PATH`.
The tests use fake cargo results to exercise the actual runner and report
generator, including failed benchmarks, log writes, missing measurements, report
generation failures, and stale cached results.

Compile every benchmark with the committed dependency graph:

```bash
cargo bench --workspace --locked --no-run
```

Run `bash run_benchmarks.sh` for the complete benchmark and HTML report. The
runner fixes the target directory to the repository's `target/` so measurement
cleanup and report collection use the same location even if `CARGO_TARGET_DIR`
is set. Compiled artifacts remain cached; Criterion measurements, logs, and the
previous report are removed before each run. Every library is attempted, but
any failed benchmark or log write prevents report generation and returns a
nonzero status. The generator also requires all four groups and three cases.

## Dependency compatibility

`merman-render 0.8.0-alpha.3` requires the matching `dugong`, `dugong-graphlib`,
and `manatee 0.8.0-alpha.3` APIs. Cargo's prerelease ranges permitted alpha.6,
which removed APIs used by this renderer. Keep these compatible versions in
`Cargo.lock` and validate upgrades with the compilation command above and a full
run. See [issue #7](https://github.com/storytellerF/mermaid-rust-benchmark/issues/7).
The runner uses `--locked` so normal benchmark runs cannot change this graph.
Keep displayed library versions in `crates.json` and `README.md` consistent with
the lockfile when upgrading.

## CI and deployment

On matching pushes to `main` or manual dispatch, the workflow runs the controlled
tests and then the full benchmark. The Pages artifact is prepared and uploaded
only after these steps succeed. The deploy job requires the benchmark job to
succeed; a nonzero runner status blocks publication of an incomplete report.
Do not add `continue-on-error` to these steps or `always()` to the deploy job.
