# Development verification

Run these checks from the repository root after changing execution, evidence processing, measurements, the workbench or its documentation:

```bash
./scripts/check_release.py
```

The offline check runs the evidence and release tests, CLI diagnostics, Markdown link checks, figure manifest checks, asset checks and ignore-boundary checks. It does not build simulators or require recording tools. Docker integration and demo regeneration are reported as `NOT_TESTED` unless requested.

With the local simulator and recording environments prepared, run:

```bash
./scripts/check_release.py --integration --demos
```

Integration executes one bounded ordinary workload per backend. Demo regeneration executes an additional WMB run and produces the terminal and browser GIFs. Check the affected measurements, inspect the workbench and recorded frames, and update the documentation before completing a development cycle. A skipped check is not a pass.

## Recording dependencies

The tested host uses VHS 0.12.1, ttyd 1.7.7-unknown, FFmpeg 9.0.2, Node 26.3.0 and Playwright 1.64.0, with cached Chromium revision 1248 and Playwright FFmpeg revision 1013. A fresh Playwright installation has not been verified end to end. These dependencies are only needed for recording, not ordinary simulation or offline tests.

On macOS, install VHS using the [upstream instructions](https://github.com/charmbracelet/vhs#installation). Ensure ttyd, FFmpeg, ffprobe, Python 3 and Node are available. Install the [plotting environment](figures.md) and the project-local browser recorder:

```bash
brew install vhs
npm install --prefix .venv/playwright playwright@1.64.0 --no-audit --no-fund --ignore-scripts
./.venv/playwright/node_modules/.bin/playwright install chromium
```

The Playwright package stays under ignored `.venv/`. The recording script needs a working WMB backend, a validated QPRAC run and a validated upstream RAM2BIN trace with a built RamViz viewer. Generate the missing runs first using the corresponding simulator commands.

## Regenerating the demonstrations

```bash
./scripts/render_demos.sh
```

The terminal tapes in `demos/` use a fixed Bash prompt and relative paths. The first runs `doctor`, `wmb --relative` and `runs`; the second runs `verify`, `analyze --summary`, `figures` and `ui --no-open` for the newly validated WMB run.

`scripts/record_browser_demos.cjs` uses headless Chromium to navigate the actual workbench and RamViz. It records WMB and QPRAC run selection, observations and measurement definitions, then opens a genuine RAM2BIN trace. FFmpeg converts the 1440 × 900 recordings to GIF; the workbench GIF is scaled to 1360 × 850. The recorder omits the workbench execution-command panel because it may contain private mount paths. The temporary RamViz access token stays inside the recorder process.

The renderer checks all four staged GIFs before replacing the public files in `docs/assets/`. A recording or validation failure preserves the previous assets. Inspect the resulting GIFs for readable text, unintended private information and accurate interaction. The older `workbench.png` remains a separate historical capture. Run regeneration after relevant development changes, not during ordinary experiments.
