"""Generate publication-oriented plots from validated run measurements."""

import csv
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from evidence import ROOT, EvidenceError, analyze, run_path, sha256, verify


os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "runs" / "matplotlib-cache"))
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


def write_csv(path, values, unit):
    with path.open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(("native_name_or_logical_bank", unit))
        writer.writerows(values.items())


def plot_bars(path, values, title, x_label, color, run_label):
    pairs = sorted(values.items(), key=lambda item: (-item[1], item[0]))
    shown = pairs[:20]
    labels = [item[0] for item in shown][::-1]
    counts = [item[1] for item in shown][::-1]
    height = max(3.8, 0.29 * len(shown) + 1.8)
    fig, ax = plt.subplots(figsize=(9, height))
    fig.subplots_adjust(left=0.19, right=0.98, top=1 - 0.55 / height, bottom=0.85 / height)
    bars = ax.barh(labels, counts, color=color, height=0.72)
    ax.bar_label(bars, padding=4, fontsize=9)
    ax.set_xlim(0, max(counts) * 1.1)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlabel(x_label)
    ax.set_title(title, loc="left", fontsize=14, weight="bold")
    ax.grid(axis="x", alpha=0.22)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="both", labelsize=9)
    fig.text(0.01, 0.01, f"DRAMdpnd · {run_label} · {len(shown)} of {len(pairs)} categories shown", fontsize=8, color="#4b5563")
    for extension in ("svg", "pdf", "png"):
        fig.savefig(path.with_suffix(f".{extension}"), dpi=220, facecolor="white", metadata={"Creator": "DRAMdpnd"})
    plt.close(fig)


def generate(run):
    check = verify(run)
    if check["status"] != "VALID":
        raise EvidenceError("figures require a version 2 run with valid evidence: " + "; ".join(check["issues"]))
    if (ROOT / "runs" / "derived").is_symlink() or (ROOT / "runs" / "derived" / run.name).is_symlink():
        raise EvidenceError("derived output directory must not be a symbolic link")
    result = analyze(run)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "runs" / "derived" / run.name / f"{stamp}-{uuid.uuid4().hex[:6]}"
    output.mkdir(parents=True)
    write_csv(output / "command_counts.csv", result["command_counts"], "recorded_commands")
    write_csv(output / "logical_bank_counts.csv", result["logical_bank_counts"], "recorded_commands")
    (output / "measurements.json").write_text(json.dumps(result, indent=2) + "\n")
    label = f"{run.parent.name}/{run.name}"
    plot_bars(output / "command-distribution", result["command_counts"], "Recorded native commands", "Issued command records", "#3478a8", label)
    figure_types = ["command-distribution"]
    if result["logical_bank_counts"]:
        plot_bars(output / "logical-bank-activity", result["logical_bank_counts"], "Recorded activity by logical bank", "Command records with a bank coordinate", "#b5653d", label)
        figure_types.append("logical-bank-activity")
    products = sorted(path.name for path in output.iterdir() if path.is_file())
    (output / "figure_metadata.json").write_text(json.dumps({"run_id": run.name, "artifact": run.parent.name, "source_metadata_sha256": sha256(run / "metadata.json"), "measurement_file": "measurements.json", "figure_types": figure_types, "formats": ["svg", "pdf", "png"], "created_at": datetime.now(timezone.utc).isoformat(), "file_hashes": {name: sha256(output / name) for name in products}}, indent=2) + "\n")
    return output


if __name__ == "__main__":
    try:
        print(generate(run_path(sys.argv[1])).relative_to(ROOT))
    except (EvidenceError, IndexError) as error:
        print(f"figures: {error}", file=sys.stderr)
        sys.exit(2)
