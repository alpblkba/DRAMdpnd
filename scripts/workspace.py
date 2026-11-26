"""Shared current simulator readiness checks for CLI and workbench."""

import shutil
import subprocess

from evidence import ROOT


IMAGE = "ramulator2-ramulator2:latest"
SOURCES = {
    "ramulator": {
        "repo": "https://github.com/CMU-SAFARI/ramulator2",
        "revision": "7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da",
        "checkout": "external/ramulator2",
        "binary": "external/ramulator2/libramulator.so",
        "config": "experiments/ramulator.py",
        "workloads": ["ordinary.trace"],
    },
    "chronus": {
        "repo": "https://github.com/CMU-SAFARI/Chronus",
        "revision": "881a097a4c10f58953011c3ecf737e8f66d30bc0",
        "checkout": "external/chronus",
        "binary": "external/chronus/build-linux/ramulator2",
        "config": "experiments/chronus.yaml",
        "workloads": ["ordinary.trace"],
    },
    "qprac": {
        "repo": "https://github.com/sith-lab/qprac",
        "revision": "6fd217e102c01e21fd2ba1ff300c3e0460b91c41",
        "checkout": "external/qprac",
        "binary": "external/qprac/perf_analysis/build-linux/ramulator2",
        "config": "experiments/qprac.yaml",
        "workloads": ["ordinary.trace"],
    },
    "wmb": {
        "repo": "https://github.com/STAR-Laboratory/PRAC_TC_ISCA25",
        "revision": "c4809a89299f47d7f02b7f922453cd8f7647e479",
        "checkout": "external/wmb",
        "binary": "external/wmb/PRACLeak/ramulator2/build-linux/ramulator2",
        "config": "experiments/wmb.yaml",
        "workloads": ["ordinary.trace", "idle.trace"],
    },
}


def call(*args):
    return subprocess.run(args, capture_output=True, text=True, check=False)


def source_revision(spec):
    checkout = ROOT / spec["checkout"]
    if not checkout.is_dir() or not shutil.which("git"):
        return None
    result = call("git", "-C", str(checkout), "rev-parse", "HEAD")
    return result.stdout.strip() if result.returncode == 0 else None


def image_id():
    if not shutil.which("docker"):
        return None
    if call("docker", "info", "--format", "{{.OSType}}").stdout.strip() != "linux":
        return None
    result = call("docker", "image", "inspect", IMAGE, "--format", "{{.Id}} {{.Architecture}}")
    parts = result.stdout.strip().split()
    return parts[0] if result.returncode == 0 and len(parts) == 2 and parts[1] == "arm64" else None


def source_clean(spec):
    checkout = ROOT / spec["checkout"]
    return source_revision(spec) == spec["revision"] and call("git", "-C", str(checkout), "diff", "--quiet", "HEAD", "--").returncode == 0


def readiness(name, image):
    spec = SOURCES[name]
    revision = source_revision(spec)
    if revision != spec["revision"]:
        return f"source unavailable or wrong revision (expected {spec['revision']}, found {revision or 'none'})"
    checkout = ROOT / spec["checkout"]
    if not source_clean(spec):
        return "tracked source files differ from the pinned revision"
    if not (ROOT / spec["binary"]).is_file():
        return f"build unavailable ({spec['binary']})"
    if name == "ramulator" and not list((ROOT / "external/ramulator2/python/ramulator").glob("_ramulator*.so")):
        return "upstream Python extension unavailable"
    if not (ROOT / spec["config"]).is_file():
        return f"configuration unavailable ({spec['config']})"
    for workload in spec["workloads"]:
        if not (ROOT / "experiments" / workload).is_file():
            return f"workload unavailable (experiments/{workload})"
    if not image:
        return f"Linux ARM64 Docker image unavailable ({IMAGE}); run dramdpnd doctor"
    return None


