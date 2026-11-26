"""Export validated issued-command observations as instant Chrome JSON events."""

import json
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from evidence import ROOT, EvidenceError, analyze, events, run_path, sha256, verify


COMMAND_CATEGORIES = {"ACT": "activation", "RD": "read command", "RDA": "read command", "WR": "write command", "WRA": "write command", "REFab": "refresh command", "REFsb": "refresh command", "RFMab": "mitigation command", "RFMsb": "mitigation command", "DRFMab": "mitigation command", "DRFMsb": "mitigation command", "VRR": "mitigation command"}


def export(run):
    check = verify(run)
    if check["status"] != "VALID":
        raise EvidenceError("Perfetto export requires a version 2 run with valid evidence")
    if (ROOT / "runs" / "derived").is_symlink() or (ROOT / "runs" / "derived" / run.name).is_symlink():
        raise EvidenceError("derived output directory must not be a symbolic link")
    measurement = analyze(run)
    period = measurement["tCK_ps"]
    if period is None or period <= 0:
        raise EvidenceError("model clock period is unverified; no timestamp conversion is possible")
    tracks = {}
    records = []
    for event in events(run, run.parent.name):
        if len(records) >= 100000:
            raise EvidenceError("trace exceeds the bounded 100000-command export limit")
        key = tuple(event["address"][:4])
        if key not in tracks:
            tracks[key] = len(tracks) + 1
        records.append({"name": event["command"], "cat": COMMAND_CATEGORIES.get(event["command"], "issued DRAM command"), "ph": "I", "s": "t", "pid": 1, "tid": tracks[key], "ts": float(Decimal(event["cycle"]) * Decimal(period) / Decimal(1000000)), "args": {"native_cycle": event["cycle"], "clock_period_ps": period, "logical_address": list(event["address"]), "source_file": event["source"], "source_record": event.get("source_line", event.get("entry_index"))}})
    names = [{"name": "thread_name", "ph": "M", "pid": 1, "tid": track, "args": {"name": " / ".join(f"{level} {value if value >= 0 else 'unspecified'}" for level, value in zip(("Channel", "Rank", "Bank group", "Bank"), key))}} for key, track in tracks.items()]
    output_dir = ROOT / "runs" / "derived" / run.name
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = output_dir / f"commands-{stamp}-{uuid.uuid4().hex[:6]}.perfetto.json"
    output.write_text(json.dumps({"traceEvents": names + records, "metadata": {"source_run": f"{run.parent.name}/{run.name}", "source_metadata_sha256": sha256(run / "metadata.json"), "event_semantics": "issued command instant", "timestamp_unit": "microseconds", "native_clock_domain": "controller cycles", "model_clock_period_ps": period}}, separators=(",", ":")) + "\n")
    return output


if __name__ == "__main__":
    try:
        print(export(run_path(sys.argv[1])))
    except (EvidenceError, IndexError) as error:
        print(f"perfetto: {error}", file=sys.stderr)
        sys.exit(2)
