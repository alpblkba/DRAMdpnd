# Local workbench

Run `./bin/dramdpnd ui` to generate and open `runs/workbench/index.html`. The page is self-contained and runs locally without a server or external assets. It contains a snapshot of the discovered run records, so regenerate it after a simulation or figure export. The generated page and embedded evidence stay in the ignored `runs/` directory.

| View | Contents |
| --- | --- |
| Overview | Available source trees and executables, separately from historical evidence counts |
| Run history | Filters by artifact, execution status, evidence status, format and search text |
| Evidence | Selected run provenance, integrity findings, file inventory and up to 4 KiB per text file |
| Observations | Command counts, logical bank activity, native statistics and the first 24 parsed events |
| Dependability laboratory | Reliability and security questions, service observations and evaluation evidence |
| Figures | Local SVG, PDF, PNG, CSV and JSON outputs |
| Research sources and environment | Paper references, source pins, executables and toolchain checks |

All scientific measurements come from `scripts/evidence.py`; JavaScript only presents them. A bank's command share uses the number of bank-addressed issued commands as its denominator. It is not a bank-time percentage. See [measurements](measurements.md) for definitions.

Figure links appear only when the source metadata hash, file inventory and SHA-256 manifest match. Failed checks are displayed without modifying the files. Older records remain accessible with an explicit `UNVERIFIED` notice.

Only upstream RAM2BIN recordings open in RamViz. For a validated run with a known model clock, `./bin/dramdpnd perfetto RUN_ID` exports command instants as Chrome JSON. Interactive import is unverified. Keep unpublished trace data local.
