"""Local integration smoke test; requires the prepared ARM64 Docker workbench."""

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import evidence


class HarnessSmoke(unittest.TestCase):
    def run_artifact(self, artifact):
        try:
            image = subprocess.run(["docker", "image", "inspect", "ramulator2-ramulator2:latest"], capture_output=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            self.skipTest("local Linux ARM64 Docker image unavailable")
        if image.returncode:
            self.skipTest("local Linux ARM64 Docker image unavailable")
        result = subprocess.run([str(ROOT / "bin/dramdpnd"), artifact], cwd=ROOT, capture_output=True, text=True, timeout=75)
        self.assertEqual(result.returncode, 0, result.stderr)
        run = Path(result.stdout.strip().split("output: ")[-1])
        metadata = json.loads((run / "metadata.json").read_text())
        self.assertEqual(metadata["schema_version"], 2)
        self.assertEqual(metadata["execution_status"], "SUCCESS")
        self.assertEqual(metadata["evidence_status"], "VALID")
        self.assertEqual(metadata["harness_status"], "complete")
        self.assertEqual(metadata["exit_status"], 0)
        self.assertEqual(metadata["source_revision"], evidence.PINS[artifact])
        self.assertEqual(evidence.verify(run)["status"], "VALID")
        self.assertTrue(metadata["native_trace_files"])
        return run, metadata

    def test_upstream_native_trace_and_provenance(self):
        run, metadata = self.run_artifact("ramulator")
        self.assertTrue(metadata["ramviz_compatible"])
        trace = run / metadata["native_trace_files"][0]
        self.assertEqual(trace.read_bytes()[:8], b"RAM2BIN\0")

    def test_wmb_native_trace(self):
        run, metadata = self.run_artifact("wmb")
        self.assertEqual(evidence.analyze(run)["command_counts"]["ACT"], 32)
        self.assertEqual(metadata["statistics_file"], "stdout.txt")

    def test_qprac_native_trace(self):
        run, _ = self.run_artifact("qprac")
        self.assertGreater(evidence.analyze(run)["command_counts"]["RD"], 0)

    def test_chronus_native_trace(self):
        run, _ = self.run_artifact("chronus")
        self.assertGreater(evidence.analyze(run)["command_counts"]["RD"], 0)


if __name__ == "__main__":
    unittest.main()
