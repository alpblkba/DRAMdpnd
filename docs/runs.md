# Local run records

The included workloads are small architectural examples. `experiments/ordinary.trace` contains 32 ordinary cache-line-aligned reads, repeated to reach the frontend's 512-instruction bound. WMB also uses `experiments/idle.trace` as a flush-only second core because its BHO3 implementation treats the last listed core specially. These choices do not reproduce the papers' benchmark workloads. Each CLI run uses a 60-second Linux `timeout`, disabled container networking and its own directory for inputs, native output, stdout, stderr and metadata.

## Initial verified executions

| Command | Local run directory | Native evidence |
| --- | --- | --- |
| `./bin/dramdpnd wmb` | `runs/wmb/20261124T231349Z-1848bd/` | `output.txt`, `stdout.txt`, `commands/trace.ch0` |
| `./bin/dramdpnd qprac` | `runs/qprac/20261124T231349Z-3c14ab/` | `stdout.txt`, `commands/trace.ch0` |
| `./bin/dramdpnd chronus` | `runs/chronus/20261124T231349Z-6dbf82/` | `stdout.txt`, `commands/trace.ch0` |
| `./bin/dramdpnd ramulator` | `runs/ramulator/20261124T232033Z-2a1085/` | `stats.json`, `trace.ch0.ram2bin` |

All four executions exited 0 using their original simulators. These paths are local records, not files included in a public checkout. Run the corresponding command to generate your own evidence. The first upstream binary trace has RAM2BIN magic, a version 1.2 header, complete flag, DDR4 device type and 516 recorded entries. Its size is 27,216 bytes.

## RamViz checks

On 2026-11-26, the upstream viewer discovered a validated `trace.ch0.ram2bin` and opened its timing setup, Commands and Bank state panels in Firefox. The server emitted two Vue Router warnings for `/examples/index.json`. The pinned [examples loader](https://github.com/CMU-SAFARI/ramulator2/blob/7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da/visualizer/app/composables/useExamples.ts) requests that file, which is absent from the local build's `public/examples/` directory. The missing optional example listing did not prevent trace discovery or the tested timeline views.

A subsequent headless Chromium recording also loaded a validated upstream trace, inspected the model clock and selected a logical bank. See [trace visualization](visualization.md). Requests and Throughput interactions remain unverified.

## Earlier feasibility runs

| Directory | Observation |
| --- | --- |
| `runs/wmb/first-smoke/` | Incompatible SimpleO3 frontend with the BHO3-oriented controller. Exit 0 did not make this a valid result. |
| `runs/wmb/bho3-smoke-001/` | Corrected manual run. |
| `runs/qprac/first-smoke/` | Exit 139 with missing power fields. The ordinary configuration now supplies the required default voltage and current settings. |
| `runs/qprac/power-smoke-001/` | Successful corrected manual run. |
| `runs/chronus/first-smoke/`, `runs/ramulator/first-smoke/` | Successful manual checks before CLI execution. |

The earlier E1 feasibility report came from a separate Linux x86-64 environment. DRAMdpnd has not reproduced that report here. Keep the historical records separate from later validated evidence.

## Local repeatability

The reviewed successful upstream bounded runs, including `20261126T043446Z-2cc03f`, produced identical SHA-256 values for the two native outputs:

| File | SHA-256 |
| --- | --- |
| `trace.ch0.ram2bin` | `180b43c124624b2286be043477c0baf2f1eb30a64bb4f77d72114d32cfea6e9c` |
| `stats.json` | `0d66cad0af024710cc6020c9aa26ff4365645a6e09858b59e8c140a6e3a0f6e4` |

This establishes byte-level repeatability for the tested ordinary workload, executable and local environment. It does not establish cross-platform reproducibility or observer transparency. Run metadata and host wall durations differ and remain part of the original evidence.

The recorded traces contain issued commands, not the complete request lifecycle. Historical artifact traces are native text, not RAM2BIN. Perfetto export preserves issued-command instants when a model clock is known. See [measurements](measurements.md) for the observation and interpretation limits.
