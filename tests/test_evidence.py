"""Synthetic format fixtures test inspection code, not simulator behavior."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import evidence


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.run = Path(self.temp.name) / "wmb" / "synthetic"
        (self.run / "commands").mkdir(parents=True)
        (self.run / "config.yaml").write_text("synthetic: true\n")
        (self.run / "ordinary.trace").write_text("4 4096\n")
        (self.run / "stdout.txt").write_text("Frontend:\nMemorySystem:\n  memory_system_cycles: 3\n")
        (self.run / "commands/trace.ch0").write_text("1, ACT, 0, 0, 0, 0, 0, 1, 4096\n")
        self.outputs = {name: evidence.sha256(self.run / name) for name in ("stdout.txt", "commands/trace.ch0")}
        manifest = "".join(f"{digest}  {name}\n" for name, digest in sorted(self.outputs.items()))
        (self.run / "outputs.sha256").write_text(manifest)
        self.metadata = {"schema_version": 2, "run_id": "synthetic", "artifact": "wmb", "source_revision": evidence.PINS["wmb"], "execution_status": "SUCCESS", "started_at": "2026-11-25T00:00:00Z", "command": ["synthetic-simulator", "sha256:" + "b" * 64], "exit_status": 0, "completed_at": "2026-11-25T00:00:01Z", "wall_seconds": 1.0, "source_repository": "https://example.invalid/wmb", "simulator_executable": "synthetic-simulator", "simulator_sha256": "a" * 64, "environment": {"kind": "test", "image": "synthetic", "image_id": "sha256:" + "b" * 64}, "host": {"system": "synthetic", "architecture": "synthetic"}, "configuration": {"file": "config.yaml", "sha256": evidence.sha256(self.run / "config.yaml")}, "workloads": [{"file": "ordinary.trace", "sha256": evidence.sha256(self.run / "ordinary.trace")}], "native_output_files": list(self.outputs), "output_hashes": self.outputs, "output_manifest_sha256": evidence.sha256(self.run / "outputs.sha256")}
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        (self.run / "metadata.json").write_text(json.dumps(self.metadata))

    def test_valid_counts_and_clock_unknown(self):
        self.assertEqual(evidence.verify(self.run)["status"], "VALID")
        result = evidence.analyze(self.run)
        self.assertEqual(result["command_counts"], {"ACT": 1})
        self.assertIsNone(result["tCK_ps"])
        self.assertEqual(result["bank_addressed_commands"], 1)
        self.assertEqual(result["measurements"]["logical_bank_command_share"], {"0/0/0/0": 100.0})

    def test_bank_share_is_unavailable_without_bank_coordinates(self):
        event = {"cycle": 1, "command": "REF", "address": (-1, -1, -1, -1), "source": "commands/trace.ch0"}
        with patch.object(evidence, "events", side_effect=lambda *_: iter([event])):
            result = evidence.analyze(self.run)
        self.assertEqual(result["bank_addressed_commands"], 0)
        self.assertEqual(result["measurements"]["logical_bank_command_share"], {})

    def test_corrupted_output_and_input(self):
        (self.run / "commands/trace.ch0").write_text("1, RD, 0, 0, 0, 0, 0, 1, 4096\n")
        self.assertIn("output hash mismatch", str(evidence.verify(self.run)["issues"]))
        (self.run / "config.yaml").write_text("changed\n")
        self.assertIn("input hash mismatch", str(evidence.verify(self.run)["issues"]))

    def test_empty_trace_and_missing_statistics(self):
        (self.run / "commands/trace.ch0").write_text("")
        self.assertEqual(evidence.verify(self.run)["status"], "INVALID")
        (self.run / "stdout.txt").unlink()
        self.assertIn("stdout.txt", str(evidence.verify(self.run)["issues"]))

    def test_legacy_and_malformed_metadata(self):
        self.metadata.pop("schema_version")
        self.save()
        self.assertEqual(evidence.verify(self.run)["status"], "UNVERIFIED")
        (self.run / "metadata.json").write_text("{")
        self.assertEqual(evidence.verify(self.run)["status"], "INVALID")

    def test_invalid_binary_header_and_safe_path(self):
        (self.run / "bad.ram2bin").write_bytes(b"RAM2BIN\0" + bytes(56))
        with self.assertRaisesRegex(evidence.EvidenceError, "unsupported RAM2BIN header"):
            list(evidence.binary_events(self.run, "bad.ram2bin"))
        with self.assertRaisesRegex(evidence.EvidenceError, "unsafe evidence path"):
            evidence.safe_file(self.run, "../private.txt")

    def test_cli_rejects_unsupported_visualization_and_bad_id(self):
        for args in (("chronus", "ramviz"), ("verify", "../private"), ("unknown",)):
            result = subprocess.run([str(ROOT / "bin/dramdpnd"), *args], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_versioned_identity_and_units(self):
        self.metadata["run_id"] = "another-run"
        self.save()
        self.assertEqual(evidence.verify(self.run)["status"], "INVALID")
        self.assertEqual(evidence.cycles_to_ns(750, 625), 468.75)
        with self.assertRaises(evidence.EvidenceError):
            evidence.cycles_to_ns(-1, 625)

    def test_failed_and_interrupted_executions(self):
        self.metadata["execution_status"] = "FAILED"
        self.metadata["exit_status"] = 124
        self.save()
        self.assertEqual(evidence.verify(self.run)["status"], "INVALID")
        self.assertIn("exited 124", str(evidence.verify(self.run)["issues"]))
        self.metadata["execution_status"] = "INTERRUPTED"
        self.metadata["exit_status"] = None
        self.save()
        self.assertEqual(evidence.verify(self.run)["status"], "INCOMPLETE")

    def test_recorded_clock_is_independent_of_current_experiment(self):
        (self.run / "config.yaml").write_text("    preset: DDR5_3200AN\n")
        self.metadata["configuration"]["sha256"] = evidence.sha256(self.run / "config.yaml")
        self.save()
        with patch.object(evidence, "ROOT", Path(self.temp.name)):
            self.assertEqual(evidence.analyze(self.run)["tCK_ps"], 625)

    def test_binary_traces_reject_disagreeing_clocks(self):
        other = self.run / "a.ram2bin"
        another = self.run / "b.ram2bin"
        other.touch()
        another.touch()
        def fake_events(_, name):
            yield {"tCK_ps": 625 if name == "a.ram2bin" else 833}
        with patch.object(evidence, "binary_events", side_effect=fake_events):
            with self.assertRaisesRegex(evidence.EvidenceError, "disagree"):
                list(evidence.events(self.run, "ramulator"))

    def test_contradictory_execution_and_missing_identity(self):
        self.metadata["execution_status"] = "FAILED"
        self.save()
        self.assertIn("contradictory", str(evidence.verify(self.run)["issues"]))
        self.metadata["execution_status"] = "SUCCESS"
        self.metadata.pop("simulator_sha256")
        self.save()
        self.assertEqual(evidence.verify(self.run)["status"], "INVALID")

    def test_malformed_input_path_type(self):
        self.metadata["configuration"]["file"] = ["config.yaml"]
        self.save()
        self.assertEqual(evidence.verify(self.run)["status"], "INVALID")

    def test_native_statistics_keep_scope_and_repeated_names(self):
        (self.run / "stdout.txt").write_text("Frontend:\n  repeated: 1\nMemorySystem:\n  memory_system_cycles: 3\n  repeated: 2\n")
        stats, _ = evidence.native_statistics(self.run, "wmb")
        self.assertEqual([(item["scope"], item["key"], item["value"]) for item in stats if item["key"] == "repeated"], [("Frontend", "repeated", 1), ("MemorySystem", "repeated", 2)])

    def test_malformed_execution_fields(self):
        self.metadata["command"] = "synthetic-simulator"
        self.save()
        self.assertEqual(evidence.verify(self.run)["status"], "INVALID")
        self.metadata["command"] = ["synthetic-simulator", "sha256:" + "b" * 64]
        self.metadata["started_at"] = 123
        self.save()
        self.assertEqual(evidence.verify(self.run)["status"], "INVALID")

    def test_missing_output_manifest_and_unsafe_input(self):
        (self.run / "outputs.sha256").unlink()
        self.assertIn("outputs.sha256", str(evidence.verify(self.run)["issues"]))
        self.metadata["configuration"]["file"] = "../outside"
        self.save()
        self.assertIn("unsafe evidence path", str(evidence.verify(self.run)["issues"]))

    def test_workbench_generation_is_isolated(self):
        from workbench import generate
        output = generate(Path(self.temp.name) / "index.html", data={"runs": [], "sources": []})
        page = output.read_text()
        self.assertIn('id="workbench-data"', page)
        self.assertNotIn("__DRAMDPD_DATA__", page)
        self.assertIn("Run history", page)

    def test_figure_links_require_matching_manifest(self):
        import workbench
        folder = Path(self.temp.name) / "runs/derived/synthetic/figures"
        folder.mkdir(parents=True)
        (folder / "command.svg").write_text("<svg></svg>")
        (folder / "figure_metadata.json").write_text(json.dumps({"run_id": "synthetic", "artifact": "wmb", "source_metadata_sha256": evidence.sha256(self.run / "metadata.json"), "file_hashes": {"command.svg": evidence.sha256(folder / "command.svg")}}))
        with patch.object(workbench, "ROOT", Path(self.temp.name)):
            files, issue = workbench.verified_figures(self.run, folder)
            self.assertIsNone(issue)
            self.assertTrue(files)
            (folder / "command.svg").write_text("corrupted")
            files, issue = workbench.verified_figures(self.run, folder)
            self.assertFalse(files)
            self.assertIn("integrity failed", issue)

    def test_run_discovery_and_missing_metadata(self):
        discovered = Path(self.temp.name) / "runs" / "wmb" / "discovered"
        discovered.mkdir(parents=True)
        with patch.object(evidence, "ROOT", Path(self.temp.name)):
            self.assertEqual(evidence.discover(), [discovered])
            self.assertEqual(evidence.run_path("discovered"), discovered)
            (self.run / "metadata.json").unlink()
            self.assertEqual(evidence.verify(self.run)["status"], "UNVERIFIED")
        alias = Path(self.temp.name) / "alias"
        alias.mkdir()
        (alias / "runs").symlink_to(Path(self.temp.name) / "runs", target_is_directory=True)
        with patch.object(evidence, "ROOT", alias):
            with self.assertRaisesRegex(evidence.EvidenceError, "symbolic link"):
                evidence.run_path("discovered")

    def test_perfetto_keeps_native_identity_and_names_logical_track(self):
        import perfetto_export
        (self.run / "config.yaml").write_text("    preset: DDR5_3200AN\n")
        self.metadata["configuration"]["sha256"] = evidence.sha256(self.run / "config.yaml")
        self.save()
        with patch.object(perfetto_export, "ROOT", Path(self.temp.name)):
            output = perfetto_export.export(self.run)
        trace = json.loads(output.read_text())
        self.assertEqual(trace["traceEvents"][0]["args"]["name"], "Channel 0 / Rank 0 / Bank group 0 / Bank 0")
        self.assertEqual(trace["traceEvents"][1]["name"], "ACT")
        self.assertEqual(trace["traceEvents"][1]["cat"], "activation")
        self.assertEqual(trace["traceEvents"][1]["args"]["source_file"], "commands/trace.ch0")
        event = {"cycle": 2, "command": "REFab", "address": (0, 0, -1, -1, -1, -1), "source": "commands/trace.ch0", "source_line": 2}
        with patch.object(perfetto_export, "ROOT", Path(self.temp.name)), patch.object(perfetto_export, "events", side_effect=lambda *_: iter([event])):
            alternate = json.loads(perfetto_export.export(self.run).read_text())
        self.assertIn("Bank group unspecified / Bank unspecified", alternate["traceEvents"][0]["args"]["name"])
        self.assertEqual(alternate["traceEvents"][1]["cat"], "refresh command")


if __name__ == "__main__":
    unittest.main()
