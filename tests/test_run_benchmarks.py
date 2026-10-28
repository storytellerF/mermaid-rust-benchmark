"""Exercise the real runner and report generator with controlled cargo results."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
GROUPS = ("mermaid-rs-renderer", "merman", "rusty-mermaid", "selkie")
BENCHMARKS = ("simple_flowchart", "complex_flowchart", "sequence_diagram")


class BenchmarkRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="benchmark runner ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name in ("run_benchmarks.sh", "generate_report.py", "crates.json"):
            shutil.copyfile(ROOT / name, self.root / name)
        for group in GROUPS:
            for bench in BENCHMARKS:
                estimates = self.root / "fixtures" / group / bench / "new" / "estimates.json"
                estimates.parent.mkdir(parents=True)
                estimates.write_text(json.dumps({
                    "median": {
                        "point_estimate": 1000,
                        "confidence_interval": {"lower_bound": 900, "upper_bound": 1100},
                    },
                }), encoding="utf-8")
        self.write_command("rustc", 'echo "rustc test"\n')
        self.write_command("python3", f'''
if [[ "${{FAIL_REPORT:-}}" == 1 ]]; then exit 23; fi
exec "{Path(sys.executable).as_posix()}" "$@"
''')
        self.write_command("cargo", '''
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
[[ "$1" == bench && "$2" == --locked && "$3" == --target-dir ]]
target="$4"
[[ "$5" == -p && "$7" == --bench && "$8" == bench && "$9" == -- && "${10}" == --noplot ]]
crate="$6"
printf '%s\n' "$crate" >> "$root/calls"
label="${crate#bench-}"
echo "Running $label"
if [[ ",${FAIL_GROUPS:-}," == *",$label,"* ]]; then
    echo "controlled benchmark failure" >&2
    exit 42
fi
mkdir -p "$target/criterion"
cp -R "$root/fixtures/$label" "$target/criterion/"
''')

    def write_command(self, name, body):
        command = self.bin / name
        command.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8")
        command.chmod(0o755)

    def run_benchmarks(self, **overrides):
        env = dict(os.environ, PYTHONUTF8="1", **overrides)
        # Bash uses a POSIX path separator even when driven by Windows Python.
        bin_path = self.bin.as_posix()
        if os.name == "nt":
            drive, rest = bin_path.split(":", 1)
            bin_path = f"/{drive.lower()}{rest}"
            env["PATH"] = bin_path + ":/usr/bin:/bin"
        else:
            env["PATH"] = bin_path + os.pathsep + env["PATH"]
        # Git's bin/bash.exe wrapper prepends /usr/bin; restore the fixture PATH
        # inside Bash so real utilities cannot shadow controlled failures.
        env["BENCHMARK_TEST_PATH"] = env["PATH"]
        bash = os.environ.get("BASH", shutil.which("bash"))
        if not bash:
            self.fail("Bash is required; set BASH to its executable path")
        return subprocess.run(
            [bash, "-c", 'export PATH="$BENCHMARK_TEST_PATH"; exec bash "$1"',
             "--", (self.root / "run_benchmarks.sh").as_posix()],
            cwd=self.root, env=env, capture_output=True, text=True,
            encoding="utf-8", timeout=30,
        )

    def assert_all_benchmarks_attempted(self):
        self.assertEqual(
            (self.root / "calls").read_text().splitlines(),
            [f"bench-{group}" for group in GROUPS],
        )

    def test_complete_success_generates_report(self):
        result = self.run_benchmarks()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_all_benchmarks_attempted()
        self.assertIn("Found 12 benchmark measurements", result.stdout)
        report = (self.root / "report.html").read_text(encoding="utf-8")
        for group in GROUPS:
            self.assertIn(group, report)

    def test_benchmark_failure_returns_nonzero_and_keeps_running_other_groups(self):
        result = self.run_benchmarks(FAIL_GROUPS="merman,rusty-mermaid")
        self.assertNotEqual(result.returncode, 0)
        self.assert_all_benchmarks_attempted()
        self.assertIn("Failed benchmarks: merman rusty-mermaid", result.stderr)
        self.assertFalse((self.root / "report.html").exists())
        self.assertIn("controlled benchmark failure", (self.root / "results/merman.log").read_text())

    def test_failed_run_removes_previous_report_and_measurements(self):
        shutil.copytree(self.root / "fixtures", self.root / "target/criterion")
        results = self.root / "results"
        results.mkdir()
        (results / "obsolete.log").write_text("stale results")
        (self.root / "report.html").write_text("stale report")
        (self.root / "target/build-cache").write_text("keep compiled artifacts")
        result = self.run_benchmarks(FAIL_GROUPS="merman")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "report.html").exists())
        self.assertFalse((self.root / "target/criterion/merman").exists())
        self.assertFalse((results / "obsolete.log").exists())
        self.assertTrue((self.root / "target/build-cache").exists())

    def test_missing_measurement_rejects_report_even_when_cargo_succeeds(self):
        (self.root / "fixtures/merman/sequence_diagram/new/estimates.json").unlink()
        result = self.run_benchmarks()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing: merman/sequence_diagram", result.stderr)
        self.assertFalse((self.root / "report.html").exists())

    def test_logging_failure_returns_nonzero(self):
        self.write_command("tee", 'cat >/dev/null\nexit 1\n')
        result = self.run_benchmarks()
        self.assertNotEqual(result.returncode, 0)
        self.assert_all_benchmarks_attempted()
        self.assertFalse((self.root / "report.html").exists())

    def test_custom_target_directory_does_not_redirect_measurements(self):
        custom_target = self.root / "custom target"
        custom_target.mkdir()
        result = self.run_benchmarks(CARGO_TARGET_DIR=str(custom_target))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(list(custom_target.iterdir()), [])
        self.assertEqual(len(list((self.root / "target/criterion").glob("*/*/new/estimates.json"))), 12)

    def test_report_generation_failure_returns_nonzero(self):
        result = self.run_benchmarks(FAIL_REPORT="1")
        self.assertEqual(result.returncode, 23)
        self.assertFalse((self.root / "report.html").exists())


if __name__ == "__main__":
    unittest.main()
