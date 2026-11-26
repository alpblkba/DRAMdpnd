#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
for tool in vhs ttyd ffmpeg ffprobe python3 node; do
  command -v "$tool" >/dev/null || { echo "render_demos: missing $tool" >&2; exit 2; }
done
python3 - <<'PY'
import shutil
from pathlib import Path
if shutil.disk_usage(Path.cwd()).free < 1024 ** 3:
    raise SystemExit("render_demos: less than 1 GiB free")
PY
[[ -x .venv/bin/python ]] && .venv/bin/python -c 'import matplotlib' || { echo "render_demos: project-local Matplotlib is unavailable" >&2; exit 2; }
[[ -f .venv/playwright/node_modules/playwright/package.json ]] || { echo "render_demos: project-local Playwright is unavailable; see docs/development.md" >&2; exit 2; }
./bin/dramdpnd doctor | grep -q '^wmb: ready$' || { echo "render_demos: WMB execution is not ready" >&2; exit 2; }
started="$(date +%s)"
stage="$(mktemp -d "${TMPDIR:-/tmp}/dramdpnd-demos.XXXXXX")"
trap 'rm -rf "$stage"' EXIT
python3 - "$stage" <<'PY'
import sys
from pathlib import Path
stage = Path(sys.argv[1])
source = Path("demos/execution.tape").read_text()
(stage / "execution.tape").write_text(source.replace("docs/assets/execution.gif", f'"{stage / "execution.gif"}"'))
PY
vhs validate "$stage/execution.tape"
vhs "$stage/execution.tape"
run_id="$(python3 - "$started" <<'PY'
import sys
sys.path.insert(0, "scripts")
from evidence import discover, verify
for run in discover():
    if run.parent.name == "wmb" and run.stat().st_mtime >= int(sys.argv[1]) and verify(run)["status"] == "VALID":
        print(run.name)
        break
else:
    raise SystemExit("render_demos: no validated WMB run")
PY
)"
python3 - "$stage" "$run_id" <<'PY'
import sys
from pathlib import Path
stage, run_id = Path(sys.argv[1]), sys.argv[2]
source = Path("demos/analysis.tape").read_text()
(stage / "analysis.tape").write_text(source.replace("docs/assets/analysis.gif", f'"{stage / "analysis.gif"}"').replace("__RUN_ID__", run_id))
PY
vhs validate "$stage/analysis.tape"
vhs "$stage/analysis.tape"
python3 - "$run_id" "$started" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, "scripts")
from evidence import ROOT, run_path
from workbench import verified_figures
run, started = run_path(sys.argv[1]), int(sys.argv[2])
folders = sorted((ROOT / "runs/derived" / run.name).glob("*/figure_metadata.json"))
if not folders or folders[-1].stat().st_mtime < started or verified_figures(run, folders[-1].parent)[1]:
    raise SystemExit("render_demos: analysis did not produce verified figures")
page = ROOT / "runs/workbench/index.html"
if not page.is_file() or page.stat().st_mtime < started:
    raise SystemExit("render_demos: analysis did not generate the workbench")
PY
node scripts/record_browser_demos.cjs "$stage"
for name in workbench ramviz; do
  width=1360
  [[ "$name" == ramviz ]] && width=1440
  ffmpeg -hide_banner -loglevel error -y -i "$stage/$name.webm" -vf "fps=8,scale=$width:-1:flags=lanczos,palettegen=stats_mode=diff" "$stage/$name-palette.png"
  ffmpeg -hide_banner -loglevel error -y -i "$stage/$name.webm" -i "$stage/$name-palette.png" -filter_complex "fps=8,scale=$width:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" "$stage/$name.gif"
done
python3 - "$stage" <<'PY'
import sys
import struct
import subprocess
from pathlib import Path
stage = Path(sys.argv[1])
for name in ("execution", "analysis"):
    file = stage / f"{name}.gif"
    size = file.stat().st_size
    header = file.read_bytes()[:10]
    duration = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(file)], text=True))
    if header[:6] not in (b"GIF87a", b"GIF89a") or struct.unpack_from("<HH", header, 6) != (1100, 640) or not 5 <= duration <= 30 or not 0 < size <= 5 * 1024 * 1024:
        raise SystemExit(f"render_demos: {name}.gif is invalid or exceeds 5 MiB")
for name, width in (("workbench", 1360), ("ramviz", 1440)):
    file = stage / f"{name}.gif"
    header = file.read_bytes()[:10]
    duration = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(file)], text=True))
    if header[:6] not in (b"GIF87a", b"GIF89a") or struct.unpack_from("<HH", header, 6) != (width, width * 900 // 1440) or not 6 <= duration <= 30 or file.stat().st_size > 8 * 1024 * 1024:
        raise SystemExit(f"render_demos: {name}.gif is invalid or exceeds 8 MiB")
target = Path("docs/assets")
target.mkdir(parents=True, exist_ok=True)
preview = target / "workbench.png"
if not preview.is_file() or preview.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n" or min(struct.unpack(">II", preview.read_bytes()[16:24])) < 800:
    raise SystemExit("render_demos: existing workbench browser capture is missing or invalid")
for name in ("execution", "analysis", "workbench", "ramviz"):
    (stage / f"{name}.gif").replace(target / f"{name}.gif")
    print(f"{target / f'{name}.gif'}: {(target / f'{name}.gif').stat().st_size} bytes")
print("Browser interactions: genuine validated run evidence and upstream RAM2BIN; local recording clips were staged before publication assets changed")
PY
