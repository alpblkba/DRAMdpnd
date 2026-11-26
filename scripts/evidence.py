"""Read and validate native evidence without changing a simulator run."""

import hashlib
import json
import re
import struct
from collections import Counter
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ("wmb", "qprac", "chronus", "ramulator")
PINS = {"wmb": "c4809a89299f47d7f02b7f922453cd8f7647e479", "qprac": "6fd217e102c01e21fd2ba1ff300c3e0460b91c41", "chronus": "881a097a4c10f58953011c3ecf737e8f66d30bc0", "ramulator": "7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da"}
MEASUREMENTS = {
    "recorded_commands": {"meaning": "Number of parsed command records in the native trace", "unit": "commands", "method": "count every validated native record", "clock_domain": None, "limitation": "Not a request count or full service count"},
    "recorded_activations": {"meaning": "Number of native ACT command records", "unit": "commands", "method": "count records whose native command is exactly ACT", "clock_domain": None, "limitation": "No physical activation or fault probability is inferred"},
    "observed_span_cycles": {"meaning": "Difference between the last and first recorded command clocks", "unit": "controller cycles", "method": "last recorded cycle minus first recorded cycle", "clock_domain": "controller", "limitation": "Not total simulation time or unavailable service time"},
    "observed_span_ns": {"meaning": "Physical-time span between the first and last recorded commands under the validated model clock", "unit": "ns", "method": "observed_span_cycles times model tCK_ps divided by 1000", "clock_domain": "controller/DRAM", "limitation": "Available only for a recognized speed preset in the hashed run input or native RAM2BIN timing"},
    "logical_bank_activity": {"meaning": "Recorded commands with complete logical channel, rank, bank-group, and bank coordinates", "unit": "commands per logical bank", "method": "group validated command records by their first four address components", "clock_domain": None, "limitation": "Not physical die layout; commands without a bank coordinate are excluded"},
    "logical_bank_command_share": {"meaning": "Share of bank-addressed issued commands recorded for each observed logical bank", "unit": "% of bank-addressed commands", "method": "divide each logical bank's command count by the sum of command counts with complete bank coordinates", "clock_domain": None, "limitation": "Not bank-time utilization; observed means at least one bank-addressed command in this trace"},
}


class EvidenceError(ValueError):
    pass


def cycles_to_ns(cycles, tck_ps):
    if cycles < 0 or tck_ps is None or tck_ps <= 0:
        raise EvidenceError("a positive model clock period and nonnegative cycle count are required")
    return float(Decimal(cycles) * Decimal(tck_ps) / Decimal(1000))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_path(run_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise EvidenceError("run ID must contain only letters, digits, underscore, or hyphen")
    if (ROOT / "runs").is_symlink():
        raise EvidenceError("runs directory must not be a symbolic link")
    matches = [ROOT / "runs" / artifact / run_id for artifact in ARTIFACTS if not (ROOT / "runs" / artifact).is_symlink() and (ROOT / "runs" / artifact / run_id).is_dir() and not (ROOT / "runs" / artifact / run_id).is_symlink()]
    if len(matches) != 1:
        raise EvidenceError(f"run ID is {'ambiguous' if matches else 'not found'}: {run_id}")
    return matches[0]


def discover():
    if (ROOT / "runs").is_symlink():
        return []
    return sorted((path for artifact in ARTIFACTS if (ROOT / "runs" / artifact).is_dir() and not (ROOT / "runs" / artifact).is_symlink() for path in (ROOT / "runs" / artifact).iterdir() if path.is_dir() and not path.is_symlink()), key=lambda path: path.stat().st_mtime, reverse=True)


def safe_file(run, relative):
    if not isinstance(relative, str):
        raise EvidenceError("evidence path must be text")
    path = Path(relative)
    if path.is_absolute() or not path.parts or any(part in (".", "..") for part in path.parts):
        raise EvidenceError(f"unsafe evidence path: {relative}")
    target = run / path
    if not target.resolve().is_relative_to(run.resolve()) or not target.is_file():
        raise EvidenceError(f"missing or unsafe evidence file: {relative}")
    return target


def load_metadata(run):
    path = run / "metadata.json"
    if not path.is_file():
        return None, "metadata.json is absent"
    try:
        data = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return None, f"metadata.json is malformed: {error}"
    if not isinstance(data, dict) or data.get("artifact") != run.parent.name:
        return None, "metadata.json has an invalid artifact identity"
    if data.get("schema_version", 1) not in (1, 2):
        return None, "metadata.json has an unsupported schema version"
    if data.get("schema_version") == 2:
        if data.get("run_id") != run.name:
            return None, "metadata.json has an invalid run identity"
        if data.get("execution_status") not in ("SUCCESS", "FAILED", "INTERRUPTED", "INCOMPLETE") or not isinstance(data.get("command"), list) or any(not isinstance(item, str) for item in data["command"]) or not isinstance(data.get("started_at"), str):
            return None, "metadata.json has malformed execution fields"
        status, code = data["execution_status"], data.get("exit_status")
        if (status == "SUCCESS" and code != 0) or (status == "FAILED" and (not isinstance(code, int) or isinstance(code, bool) or code == 0)) or (status in ("INTERRUPTED", "INCOMPLETE") and code is not None):
            return None, "metadata.json has contradictory execution status and exit code"
        environment = data.get("environment")
        if not isinstance(data.get("source_repository"), str) or not data["source_repository"] or not isinstance(data.get("simulator_executable"), str) or not data["simulator_executable"] or not isinstance(data.get("simulator_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", data["simulator_sha256"]) or not isinstance(environment, dict) or not isinstance(environment.get("kind"), str) or not isinstance(environment.get("image"), str) or not isinstance(environment.get("image_id"), str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", environment["image_id"]) or environment["image_id"] not in data["command"] or not isinstance(data.get("host"), dict) or not isinstance(data["host"].get("system"), str) or not isinstance(data["host"].get("architecture"), str):
            return None, "metadata.json lacks required executable or environment identity"
        if status in ("SUCCESS", "FAILED") and (not isinstance(data.get("completed_at"), str) or not isinstance(data.get("wall_seconds"), (int, float)) or isinstance(data.get("wall_seconds"), bool) or data["wall_seconds"] < 0):
            return None, "metadata.json lacks final execution timing"
        records = [data.get("configuration"), *(data.get("workloads") if isinstance(data.get("workloads"), list) else [None])]
        if any(not isinstance(record, dict) or not isinstance(record.get("file"), str) or not isinstance(record.get("sha256"), str) for record in records):
            return None, "metadata.json has malformed input records"
    return data, None


def text_events(run, artifact):
    traces = sorted((run / "commands").glob("trace.ch*"))
    if not traces:
        raise EvidenceError("native text command trace is absent")
    for trace in traces:
        match = re.fullmatch(r"trace\.ch(\d+)", trace.name)
        if not match or trace.is_symlink():
            raise EvidenceError(f"unexpected trace path: {trace.name}")
        trace = safe_file(run, str(trace.relative_to(run)))
        channel = int(match.group(1))
        previous = -1
        seen = 0
        with trace.open(encoding="utf-8") as source:
            for line_number, line in enumerate(source, 1):
                parts = [part.strip() for part in line.rstrip("\r\n").split(",")]
                expected = 9 if artifact == "wmb" else 8
                if len(parts) != expected or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", parts[1]):
                    raise EvidenceError(f"{trace.relative_to(run)}:{line_number}: invalid field count or command")
                try:
                    cycle = int(parts[0])
                    address = tuple(int(item) for item in parts[2:])
                except ValueError as error:
                    raise EvidenceError(f"{trace.relative_to(run)}:{line_number}: invalid integer") from error
                if cycle < 0 or cycle < previous or address[0] != channel:
                    raise EvidenceError(f"{trace.relative_to(run)}:{line_number}: cycle order or channel mismatch")
                previous = cycle
                seen += 1
                yield {"cycle": cycle, "command": parts[1], "address": address[:6], "reconstructed_address": address[6] if artifact == "wmb" else None, "source": str(trace.relative_to(run)), "source_line": line_number}
        if seen == 0:
            raise EvidenceError(f"{trace.relative_to(run)}: empty command trace")


def _cstrings(data, offset, count):
    values = []
    for _ in range(count):
        end = data.find(b"\0", offset)
        if end < 0:
            raise EvidenceError("RAM2BIN spec has an unterminated name")
        try:
            values.append(data[offset:end].decode("ascii"))
        except UnicodeDecodeError as error:
            raise EvidenceError("RAM2BIN spec has a non-ASCII name") from error
        offset = end + 1
    return values, offset


def binary_events(run, relative):
    path = safe_file(run, relative)
    with path.open("rb") as source:
        header = source.read(64)
        if len(header) != 64 or header[:8] != b"RAM2BIN\0" or header[8:10] != b"\x01\x02":
            raise EvidenceError(f"{relative}: invalid or unsupported RAM2BIN header (expected version 1.2)")
        flags, levels, commands, timings = struct.unpack_from("<4H", header, 10)
        count, data_offset = struct.unpack_from("<QQ", header, 32)
        channel = struct.unpack_from("<I", header, 24)[0]
        if not flags & 1 or not 1 <= levels <= 8 or not 1 <= commands <= 255 or timings > 128 or count == 0 or not 64 < data_offset <= min(path.stat().st_size, 1024 * 1024) or data_offset % 8:
            raise EvidenceError(f"{relative}: incomplete or inconsistent RAM2BIN header")
        spec = source.read(data_offset - 64)
        level_names, pos = _cstrings(spec, 0, levels)
        pos += 4 * levels
        command_names, pos = _cstrings(spec, pos, commands)
        pos += commands * 2
        timing_names, pos = _cstrings(spec, pos, timings)
        if pos + 4 * timings > len(spec) or len(set(level_names)) != levels or len(set(command_names)) != commands:
            raise EvidenceError(f"{relative}: invalid RAM2BIN spec section")
        timing_values = struct.unpack_from(f"<{timings}i", spec, pos) if timings else ()
        timing_map = dict(zip(timing_names, timing_values))
        previous = -1
        seen = 0
        while source.tell() < path.stat().st_size:
            chunk_header = source.read(8)
            if len(chunk_header) != 8:
                raise EvidenceError(f"{relative}: truncated RAM2BIN chunk header")
            n, reserved = struct.unpack("<II", chunk_header)
            stride = 28 + 4 * levels
            if not 1 <= n <= 65536 or reserved:
                raise EvidenceError(f"{relative}: invalid RAM2BIN chunk header")
            size = n * stride
            data = source.read(size)
            padding = source.read(-(8 + size) % 8)
            if len(data) != size or len(padding) != (-(8 + size) % 8) or any(padding):
                raise EvidenceError(f"{relative}: truncated RAM2BIN chunk")
            for index in range(n):
                cycle = struct.unpack_from("<q", data, 8 * index)[0]
                command_id = data[24 * n + index]
                if cycle < previous or command_id >= commands:
                    raise EvidenceError(f"{relative}: invalid RAM2BIN event {seen + index + 1}")
                previous = cycle
                address = tuple(struct.unpack_from("<i", data, (28 + 4 * level) * n + 4 * index)[0] for level in range(levels))
                yield {"cycle": cycle, "command": command_names[command_id], "address": address, "levels": level_names, "tCK_ps": timing_map.get("tCK_ps"), "source": relative, "entry_index": seen + index + 1, "channel_id": channel}
            seen += n
        if seen != count:
            raise EvidenceError(f"{relative}: header count {count} differs from {seen} events")


def events(run, artifact):
    if artifact == "ramulator":
        traces = sorted(run.glob("*.ram2bin"))
        if not traces:
            raise EvidenceError("native RAM2BIN trace is absent")
        periods = set()
        for trace in traces:
            for event in binary_events(run, trace.name):
                periods.add(event["tCK_ps"])
                if len(periods) > 1:
                    raise EvidenceError("RAM2BIN traces disagree on tCK_ps")
                yield event
    else:
        yield from text_events(run, artifact)


def native_statistics(run, artifact):
    if artifact == "ramulator":
        path = safe_file(run, "stats.json")
        try:
            data = json.loads(path.read_text())
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise EvidenceError(f"stats.json is malformed: {error}") from error
        if not isinstance(data, dict) or not isinstance(data.get("memory_system"), dict) or not isinstance(data.get("frontend"), dict):
            raise EvidenceError("stats.json lacks required simulator sections")
        return data, "stats.json"
    path = safe_file(run, "stdout.txt")
    text = path.read_text()
    if "Frontend:\n" not in text or "MemorySystem:\n" not in text:
        raise EvidenceError("stdout.txt lacks required simulator statistics sections")
    stats, sections = [], []
    for line_number, line in enumerate(text.splitlines(), 1):
        match = re.fullmatch(r"(\s*)([A-Za-z][A-Za-z0-9_]*):\s*(.*?)\s*", line)
        if not match:
            continue
        indent, key, value = len(match[1]), match[2], match[3]
        while sections and sections[-1][0] >= indent:
            sections.pop()
        if not value:
            sections.append((indent, key))
        elif re.fullmatch(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", value):
            stats.append({"scope": "/".join(name for _, name in sections), "key": key, "value": float(value) if any(char in value for char in ".eE") else int(value), "line": line_number})
    if not any(item["scope"] == "MemorySystem" and item["key"] == "memory_system_cycles" for item in stats):
        raise EvidenceError("stdout.txt lacks memory_system_cycles")
    return stats, "stdout.txt"


def verify(run):
    metadata, problem = load_metadata(run)
    if problem:
        return {"status": "UNVERIFIED" if "absent" in problem else "INVALID", "issues": [problem], "metadata": metadata}
    if metadata.get("source_revision") != PINS[run.parent.name]:
        return {"status": "UNSUPPORTED", "issues": ["source revision is not a validated trace format pin"], "metadata": metadata}
    if metadata.get("execution_status") in ("INCOMPLETE", "INTERRUPTED"):
        return {"status": "INCOMPLETE", "issues": ["execution did not finalize its evidence"], "metadata": metadata}
    if not isinstance(metadata.get("configuration"), dict) or not isinstance(metadata.get("workloads"), list) or not isinstance(metadata.get("native_output_files"), list) or any(not isinstance(item, dict) or not isinstance(item.get("file"), str) for item in metadata["workloads"]) or not isinstance(metadata["configuration"].get("file"), str):
        return {"status": "INVALID", "issues": ["metadata input or output inventory is malformed"], "metadata": metadata}
    issues = []
    for record in [metadata.get("configuration", {}), *metadata.get("workloads", [])]:
        if not isinstance(record, dict):
            issues.append("input record is malformed")
            continue
        try:
            path = safe_file(run, record["file"])
            if sha256(path) != record["sha256"]:
                issues.append(f"input hash mismatch: {record['file']}")
        except (EvidenceError, KeyError, OSError, TypeError) as error:
            issues.append(str(error))
    try:
        native_statistics(run, run.parent.name)
        count = sum(1 for _ in events(run, run.parent.name))
        if count == 0:
            issues.append("native trace contains no commands")
    except (EvidenceError, OSError, UnicodeError, struct.error) as error:
        issues.append(str(error))
    if metadata.get("schema_version") == 2:
        outputs = metadata.get("output_hashes")
        if not isinstance(outputs, dict) or not outputs or any(not isinstance(key, str) or not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for key, value in outputs.items()):
            issues.append("output hash manifest is absent")
        else:
            inventory = metadata["native_output_files"]
            if any(not isinstance(item, str) for item in inventory) or set(inventory) != set(outputs):
                issues.append("native output inventory differs from the output hash manifest")
            for relative, expected in outputs.items():
                try:
                    if sha256(safe_file(run, relative)) != expected:
                        issues.append(f"output hash mismatch: {relative}")
                except (EvidenceError, OSError, TypeError) as error:
                    issues.append(str(error))
            manifest = "".join(f"{digest}  {relative}\n" for relative, digest in sorted(outputs.items()))
            try:
                recorded = safe_file(run, "outputs.sha256")
                if recorded.read_text() != manifest or sha256(recorded) != metadata.get("output_manifest_sha256"):
                    issues.append("output manifest mismatch")
            except (EvidenceError, OSError, TypeError) as error:
                issues.append(str(error))
            inputs = {metadata["configuration"].get("file"), *(item.get("file") for item in metadata["workloads"] if isinstance(item, dict))}
            actual = {str(path.relative_to(run)) for path in run.rglob("*") if path.is_file() and path.name not in ("metadata.json", "outputs.sha256") and not path.name.endswith(".tmp")}
            if actual - set(outputs) - inputs:
                issues.append("unrecorded output files: " + ", ".join(sorted(actual - set(outputs) - inputs)))
    if metadata.get("exit_status") != 0:
        issues.append(f"simulator exited {metadata.get('exit_status')}")
    status = "INVALID" if issues else "VALID" if metadata.get("schema_version") == 2 else "UNVERIFIED"
    return {"status": status, "issues": issues or (["legacy metadata has no output hashes"] if status == "UNVERIFIED" else []), "metadata": metadata}


def analyze(run):
    check = verify(run)
    if check["status"] in ("INVALID", "INCOMPLETE", "UNSUPPORTED") or check["metadata"] is None:
        raise EvidenceError("run evidence is invalid or missing: " + "; ".join(check["issues"]))
    artifact = run.parent.name
    stats, stats_source = native_statistics(run, artifact)
    commands = Counter()
    banks = Counter()
    first = last = None
    count = 0
    sample = []
    tck = None
    for event in events(run, artifact):
        count += 1
        commands[event["command"]] += 1
        address = event["address"]
        if len(address) >= 4 and all(value >= 0 for value in address[:4]):
            banks["/".join(map(str, address[:4]))] += 1
        first = event["cycle"] if first is None else min(first, event["cycle"])
        last = event["cycle"] if last is None else max(last, event["cycle"])
        tck = event.get("tCK_ps", tck)
        if len(sample) < 24:
            sample.append(event)
    if artifact != "ramulator":
        config = safe_file(run, "config.yaml").read_text()
        presets = re.findall(r"^\s+preset:\s+DDR5_(3200AN|6400B)\s*$", config, re.MULTILINE)
        if len(presets) == 1 and not re.search(r"^\s+(?:rate|tCK_ps):", config, re.MULTILINE):
            tck = {"3200AN": 625, "6400B": 312}[presets[0]]
    span = last - first if first is not None else None
    bank_denominator = sum(banks.values())
    bank_shares = {key: 100 * value / bank_denominator for key, value in sorted(banks.items())} if bank_denominator else {}
    measurements = {"recorded_commands": count, "recorded_activations": commands["ACT"], "observed_span_cycles": span, "observed_span_ns": cycles_to_ns(span, tck) if span is not None and tck else None, "logical_bank_activity": dict(sorted(banks.items())), "logical_bank_command_share": bank_shares}
    result = {"run_id": run.name, "artifact": artifact, "evidence_status": check["status"], "trace_format": "RAM2BIN 1.2" if artifact == "ramulator" else "native text", "clock_domain": "controller cycles", "tCK_ps": tck, "event_count": count, "first_cycle": first, "last_cycle": last, "span_cycles": span, "bank_addressed_commands": bank_denominator, "command_counts": dict(sorted(commands.items())), "logical_bank_counts": dict(sorted(banks.items())), "measurements": measurements, "measurement_definitions": MEASUREMENTS, "native_statistics": stats, "statistics_source": stats_source, "sample_events": sample, "limitations": ["Issued commands do not represent every accepted or completed memory request.", "Logical resource identifiers do not establish physical die positions."]}
    return result
