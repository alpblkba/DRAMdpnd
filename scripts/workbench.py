"""Generate a self-contained, read-only local research workbench."""

import json
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from evidence import ARTIFACTS, PINS, ROOT, EvidenceError, analyze, discover, safe_file, sha256, verify
from workspace import SOURCES, image_id, readiness, source_clean, source_revision


SOURCE_URLS = {"wmb": "https://github.com/STAR-Laboratory/PRAC_TC_ISCA25", "qprac": "https://github.com/sith-lab/qprac", "chronus": "https://github.com/CMU-SAFARI/Chronus", "ramulator": "https://github.com/CMU-SAFARI/ramulator2"}
PAPERS = {"wmb": ("When Mitigations Backfire: Timing Channel Attacks and Defense for PRAC-Based RowHammer Mitigations", "ISCA 2025"), "qprac": ("QPRAC: Secure and Practical PRAC-based RowHammer Mitigation using Priority Queues", "HPCA 2025"), "chronus": ("Chronus: Understanding and Securing the Cutting-Edge Industry Solutions to DRAM Read Disturbance", "HPCA 2025"), "ramulator": ("Ramulator 2.1: A Composable Memory System Simulator for Modern DRAM Systems", "2026 tutorial")}


def command_output(*args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=3, check=False)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def preview(run, relative):
    try:
        path = safe_file(run, relative)
        if path.suffix in (".ram2bin", ".png", ".pdf", ".svg"):
            return None
        with path.open("rb") as source:
            sample = source.read(4097)
        return {"text": sample[:4096].decode("utf-8", errors="replace"), "truncated": len(sample) > 4096}
    except (EvidenceError, OSError):
        return None


def verified_figures(run, folder):
    try:
        metadata = json.loads(safe_file(folder, "figure_metadata.json").read_text())
        hashes = metadata["file_hashes"]
        if metadata["run_id"] != run.name or metadata["artifact"] != run.parent.name or metadata["source_metadata_sha256"] != sha256(run / "metadata.json") or not isinstance(hashes, dict) or not hashes:
            raise ValueError("figure metadata does not match its source run")
        files = {path.name for path in folder.iterdir() if path.is_file() and path.name != "figure_metadata.json"}
        if files != set(hashes) or any(not isinstance(name, str) or not isinstance(digest, str) or sha256(safe_file(folder, name)) != digest for name, digest in hashes.items()):
            raise ValueError("figure file inventory or SHA-256 differs from its manifest")
        return [str(path.relative_to(ROOT / "runs")) for path in sorted(folder.iterdir()) if path.is_file() and path.suffix in (".svg", ".pdf", ".png", ".csv", ".json")], None
    except (EvidenceError, OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        return [], f"derived figure integrity failed: {error}"


def run_data(run):
    check = verify(run)
    metadata = check["metadata"] or {}
    config = metadata.get("configuration") if isinstance(metadata.get("configuration"), dict) else {}
    workloads = metadata.get("workloads") if isinstance(metadata.get("workloads"), list) else []
    outputs = metadata.get("native_output_files") if isinstance(metadata.get("native_output_files"), list) else []
    hashes = metadata.get("output_hashes") if isinstance(metadata.get("output_hashes"), dict) else {}
    files = []
    for relative in [config.get("file"), *(item.get("file") for item in workloads if isinstance(item, dict)), *outputs]:
        if not isinstance(relative, str):
            continue
        try:
            path = safe_file(run, relative)
            files.append({"name": relative, "size": path.stat().st_size, "sha256": hashes.get(relative) or (config.get("sha256") if relative == config.get("file") else next((item.get("sha256") for item in workloads if isinstance(item, dict) and item.get("file") == relative), None)), "preview": preview(run, relative)})
        except EvidenceError:
            files.append({"name": relative, "size": None, "sha256": None, "preview": None})
    measurement = None
    if check["status"] in ("VALID", "UNVERIFIED") and metadata:
        try:
            measurement = analyze(run)
        except EvidenceError:
            pass
    derived = ROOT / "runs" / "derived" / run.name
    figure_dirs = sorted((path for path in derived.iterdir() if path.is_dir() and not path.is_symlink() and (path / "figure_metadata.json").is_file()), key=lambda path: path.stat().st_mtime, reverse=True) if derived.is_dir() and not derived.is_symlink() else []
    figures, figure_issue = verified_figures(run, figure_dirs[0]) if figure_dirs else ([], None)
    exports = [str(path.relative_to(ROOT / "runs")) for path in sorted(derived.glob("*.perfetto.json")) if not path.is_symlink()] if derived.is_dir() and not derived.is_symlink() else []
    started = metadata.get("started_at")
    wall = metadata.get("wall_seconds")
    return {"id": run.name, "artifact": run.parent.name, "execution": metadata.get("execution_status") or ("SUCCESS" if metadata.get("exit_status") == 0 else "FAILED" if metadata.get("exit_status") is not None else "UNKNOWN"), "evidence": check["status"], "trace": "RAM2BIN" if measurement and run.parent.name == "ramulator" else "text" if measurement else "unavailable", "issues": check["issues"], "figure_issue": figure_issue, "schema": metadata.get("schema_version", 1) if metadata else None, "started": started if isinstance(started, str) else None, "wall_seconds": wall if isinstance(wall, (int, float)) else None, "metadata": metadata, "files": files, "measurement": measurement, "figures": figures, "exports": exports}


def build_data():
    image = image_id()
    sources = []
    for artifact in ARTIFACTS:
        spec = SOURCES[artifact]
        revision = source_revision(spec)
        binary_available = (ROOT / spec["binary"]).is_file()
        experiment = f"experiments/{artifact}.yaml" if artifact != "ramulator" else "experiments/ramulator.py"
        sources.append({"artifact": artifact, "paper": PAPERS[artifact][0], "venue": PAPERS[artifact][1], "repository": SOURCE_URLS[artifact], "pin": PINS[artifact], "revision": revision, "source_clean": source_clean(spec), "binary_available": binary_available, "binary_path": spec["binary"], "execution_ready": not readiness(artifact, image), "experiment": experiment, "command": f"./bin/dramdpnd {artifact}", "trace_format": "RAM2BIN 1.2" if artifact == "ramulator" else "native text"})
    runs = [run_data(run) for run in discover()]
    toolchain = {"python": platform.python_version(), "cmake": (command_output("cmake", "--version") or "unavailable").splitlines()[0], "compiler": (command_output("c++", "--version") or "unavailable").splitlines()[0], "node": command_output("node", "--version") or "unavailable"}
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "host": f"{platform.system()} {platform.machine()}", "disk_free_gib": round(shutil.disk_usage(ROOT).free / 1024 ** 3, 1), "toolchain": toolchain, "docker_image": image, "sources": sources, "runs": runs, "documentation": {"exploration": "../../docs/exploration.md", "measurements": "../../docs/measurements.md", "attribution": "../../THIRD_PARTY.md", "environment": "../../docs/environment.md"}}


def generate(output=None, data=None):
    output = output or ROOT / "runs" / "workbench" / "index.html"
    if (ROOT / "runs").is_symlink() or output.parent.is_symlink() or output.is_symlink():
        raise EvidenceError("workbench output path must not be a symbolic link")
    output.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(data if data is not None else build_data(), separators=(",", ":"), ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")
    template = (ROOT / "scripts" / "workbench-template.html").read_text()
    output.write_text(template.replace("__DRAMDPD_DATA__", data))
    return output


if __name__ == "__main__":
    print(generate())
