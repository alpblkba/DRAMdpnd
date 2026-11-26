#!/usr/bin/env python3
"""Check project-owned publication candidates without changing historical evidence."""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from evidence import PINS, ROOT, discover
from workbench import verified_figures


def markdown_targets(path):
    for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", path.read_text()):
        target = target.split("#", 1)[0]
        if target and not target.startswith(("https://", "http://", "mailto:")):
            yield path.parent / target


def asset_valid(path):
    limit = 8 if path.name in ("workbench.gif", "ramviz.gif") else 5
    if not path.is_file() or not 0 < path.stat().st_size <= limit * 1024 * 1024:
        return False
    header = path.read_bytes()[:8]
    return header[:6] in (b"GIF87a", b"GIF89a") if path.suffix == ".gif" else header == b"\x89PNG\r\n\x1a\n"


def run(*args):
    result = subprocess.run(args, cwd=ROOT, check=False)
    if result.returncode:
        raise RuntimeError(f"{' '.join(map(str, args))} exited {result.returncode}")


def main():
    parser = argparse.ArgumentParser(description="Check public files and local evidence without rebuilding simulators")
    parser.add_argument("--integration", action="store_true", help="run four bounded Docker integration tests")
    parser.add_argument("--demos", action="store_true", help="regenerate terminal and browser demonstration GIFs")
    args = parser.parse_args()
    problems = []
    run(sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_evidence.py", "-q")
    run(sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_release.py", "-q")
    for command in (("help",), ("doctor",), ("status",)):
        run(ROOT / "bin/dramdpnd", *command)
    invalid = subprocess.run([ROOT / "bin/dramdpnd", "not-a-command"], cwd=ROOT, capture_output=True, text=True, check=False)
    if invalid.returncode == 0 or "Usage:" not in invalid.stdout:
        problems.append("invalid CLI command lacked a nonzero usage diagnostic")
    if shutil.which("node"):
        script = (ROOT / "scripts/workbench-template.html").read_text().split("<script>", 1)[1].split("</script>", 1)[0]
        syntax = subprocess.run(["node", "--check"], input=script, capture_output=True, text=True, check=False)
        if syntax.returncode:
            problems.append("workbench JavaScript syntax failed: " + syntax.stderr.strip())
        browser_syntax = subprocess.run(["node", "--check", str(ROOT / "scripts/record_browser_demos.cjs")], capture_output=True, text=True, check=False)
        if browser_syntax.returncode:
            problems.append("browser recorder JavaScript syntax failed: " + browser_syntax.stderr.strip())
    else:
        print("Workbench JavaScript syntax: NOT_TESTED (Node unavailable)")
    docs = [ROOT / "README.md", ROOT / "THIRD_PARTY.md", *(ROOT / "docs").glob("*.md")]
    docs = [path for path in docs if not path.name.startswith("development-report")]
    readme = (ROOT / "README.md").read_text()
    if not readme.startswith("# DRAMdpnd = DRAM dependability platform\n"):
        problems.append("README does not open with the approved project identity")
    for title in ("When Mitigations Backfire: Timing Channel Attacks and Defense for PRAC-Based RowHammer Mitigations", "QPRAC: Secure and Practical PRAC-based RowHammer Mitigation using Priority Queues", "Chronus: Understanding and Securing the Cutting-Edge Industry Solutions to DRAM Read Disturbance"):
        if f"*{title}*" not in readme or f"*{title}*" not in (ROOT / "THIRD_PARTY.md").read_text():
            problems.append(f"missing full italicized research title: {title}")
    for path in docs:
        for target in markdown_targets(path):
            if not target.is_file():
                problems.append(f"missing Markdown target: {target.relative_to(ROOT)}")
    for name in ("execution.gif", "analysis.gif", "workbench.gif", "ramviz.gif", "workbench.png"):
        path = ROOT / "docs/assets" / name
        if not asset_valid(path):
            problems.append(f"missing, malformed, or oversized asset: {path.relative_to(ROOT)}")
    for pin in PINS.values():
        if pin not in (ROOT / "THIRD_PARTY.md").read_text():
            problems.append(f"missing third-party pin: {pin}")
    ignored = (ROOT / ".gitignore").read_text().splitlines()
    for pattern in ("/external/", "/runs/", "/.venv/", "/STYLE.md", "/project-charter-v1.md", "/claude-coarchitect-report-2026-11-24.md"):
        if pattern not in ignored:
            problems.append(f"missing ignore rule: {pattern}")
    license_file = ROOT / "LICENSE"
    if not license_file.is_file() or not license_file.read_text().startswith("MIT License\n\nCopyright (c) 2026 Alp Bolukbasi\n"):
        problems.append("root MIT license or verified copyright holder is missing")
    public = [ROOT / "README.md", ROOT / "THIRD_PARTY.md", ROOT / "CITATION.cff", license_file, ROOT / ".gitignore", *docs, *(ROOT / "bin").glob("*"), *(ROOT / "scripts").glob("*.py"), *(ROOT / "scripts").glob("*.sh"), *(ROOT / "scripts").glob("*.html"), *(ROOT / "scripts").glob("*.cjs"), *(ROOT / "tests").glob("*.py"), *(ROOT / "demos").glob("*.tape")]
    for path in (item for item in public if item.is_file()):
        if ("/" + "Users/") in path.read_text() or ("/home/" + "alp") in path.read_text():
            problems.append(f"machine-specific path in public candidate: {path.relative_to(ROOT)}")
    checked, legacy = 0, 0
    for source in discover():
        derived = ROOT / "runs/derived" / source.name
        if not derived.is_dir():
            continue
        for folder in derived.iterdir():
            manifest = folder / "figure_metadata.json"
            if not manifest.is_file():
                continue
            try:
                record = json.loads(manifest.read_text())
                hashes = record.get("file_hashes")
                if not hashes:
                    legacy += 1
                    continue
                _, issue = verified_figures(source, folder)
                if issue:
                    problems.append(f"{folder.relative_to(ROOT)}: {issue}")
                checked += 1
            except (OSError, ValueError, TypeError) as error:
                problems.append(f"figure manifest malformed: {folder.relative_to(ROOT)} ({error})")
    print(f"Figure manifests: {checked} checked, {legacy} older records without hashes")
    if args.integration:
        result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_harness.py", "-v"], cwd=ROOT, capture_output=True, text=True, check=False)
        print(result.stdout + result.stderr)
        if result.returncode or "skipped=" in result.stderr:
            problems.append("Docker integration failed or skipped; see test output")
    else:
        print("Docker integration: NOT_TESTED (use --integration)")
    if args.demos:
        run(ROOT / "scripts/render_demos.sh")
        for name in ("execution.gif", "analysis.gif", "workbench.gif", "ramviz.gif"):
            if not asset_valid(ROOT / "docs/assets" / name):
                problems.append(f"regenerated demo failed validation: {name}")
    else:
        print("Demonstration regeneration: NOT_TESTED (use --demos)")
    for problem in problems:
        print("FAIL:", problem, file=sys.stderr)
    print(f"Requested checks: {'FAIL' if problems else 'PASS'}; main Git repository: {'present' if (ROOT / '.git').exists() else 'not initialized'}")
    return 1 if problems else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as error:
        print(f"check_release: {error}", file=sys.stderr)
        sys.exit(1)
