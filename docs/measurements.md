# Evidence and measurements

Run `./bin/dramdpnd verify RUN_ID` to check a recorded run without changing it. Version 2 metadata identifies the source revision, executable, execution environment, exact invocation and copied inputs. The output manifest ties the recorded files to their SHA-256 hashes.

| Evidence status | Meaning |
| --- | --- |
| `VALID` | Successful simulator exit, pinned trace format, usable statistics, nonempty structurally valid trace and matching input and output hashes |
| `UNVERIFIED` | Historical record without a versioned output manifest |
| `INVALID` | A validation check failed |
| `INCOMPLETE` | Execution did not finalize |
| `UNSUPPORTED` | Source revision has no validated parser contract |

A successful simulator exit alone does not establish evidence validity. The copied `config.yaml` or `config.py` is the input supplied to the simulator. The original simulators do not emit a complete resolved runtime configuration for these runs, so `resolved_runtime_config` is null. A source commit identifies source code, while the executable hash identifies the binary. The Docker tag is recorded for reference, but execution uses the resolved immutable image ID. The selected source tree is mounted read-only, only the new run directory is writable, and container networking is disabled.

## Version 2 metadata contract

| Fields | Meaning |
| --- | --- |
| `schema_version`, `run_id`, `artifact` | Integer version `2`, unique directory name and pinned backend |
| `source_repository`, `source_revision`, `nested_dependencies`, `simulator_executable`, `simulator_sha256` | Source and executable provenance |
| `configuration` | Copied input and SHA-256, project source path, byte-for-byte transformation and nullable resolved runtime configuration |
| `workloads` | Copied workload paths and SHA-256 values |
| `command` | Argument vector actually invoked |
| `host`, `environment`, `compiler`, `cmake` | Observed host and runtime identities. `environment.image` is the human reference; `environment.image_id` is the executed immutable ID. |
| `started_at`, `completed_at`, `wall_seconds`, `exit_status` | UTC ISO 8601 timestamps, host monotonic elapsed seconds and simulator process code |
| `execution_status`, `evidence_status` | Execution (`SUCCESS`, `FAILED`, `INTERRUPTED` or `INCOMPLETE`) and evidence validity, independently recorded |
| `native_output_files`, `native_trace_files`, `trace_format`, `statistics_file` | Original outputs and their formats |
| `output_hashes`, `output_manifest_sha256` | SHA-256 per native output path and hash of `outputs.sha256`, which contains the same sorted path/hash pairs |
| `evidence_issues`, `harness_status`, `ramviz_compatible` | Validation failures, finalization and validated upstream RAM2BIN compatibility |

A provisional record may lack final fields after interruption or execution failure. It is not a completed run.

## Native observations

WMB's [text recorder](https://github.com/STAR-Laboratory/PRAC_TC_ISCA25/blob/c4809a89299f47d7f02b7f922453cd8f7647e479/PRACLeak/ramulator2/src/dram_controller/impl/plugin/trace_recorder.cpp) emits the cycle, native command, six address-vector components and a reconstructed address. [QPRAC](https://github.com/sith-lab/qprac/blob/6fd217e102c01e21fd2ba1ff300c3e0460b91c41/perf_analysis/src/dram_controller/impl/plugin/trace_recorder.cpp) and [Chronus](https://github.com/CMU-SAFARI/Chronus/blob/881a097a4c10f58953011c3ecf737e8f66d30bc0/src/dram_controller/impl/plugin/trace_recorder.cpp) emit the first eight fields. The inspected address-vector formats identify logical channel, rank, bank group, bank, row and column. Each recorder advances its controller update clock and records selected commands immediately before device issue. These records are not accepted or completed requests.

The upstream [binary recorder](https://github.com/CMU-SAFARI/ramulator2/blob/7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da/src/ramulator/controller/plugin/impl/bin_trace_recorder.cpp) emits RAM2BIN 1.2 with a 64-byte header, specification names, timing values and chunked command arrays. The inspector checks version, complete flag, specification bounds, chunk structure, event count, command IDs and cycle order. This validates the structure of the pinned format, not the completeness of architectural observation. Native command and resource identifiers are retained. The historical text traces are not RamViz-compatible.

WMB, QPRAC and Chronus write statistics to `stdout.txt`. WMB's `output.txt` is empty in the bounded runs. Upstream writes `stats.json`. The text parser preserves each key, enclosing section, source line and numeric value, so repeated keys in different scopes stay distinct. The JSON parser retains the native hierarchy.

## Measurement definitions

| Measurement | Definition |
| --- | --- |
| `recorded_commands` | Number of parsed issued-command records |
| `recorded_activations` | Number of records whose native command is exactly `ACT` |
| `logical_bank_activity` | Counts grouped by complete logical channel, rank, bank group and bank coordinates |
| `logical_bank_command_share` | 100 times the bank's count divided by `bank_addressed_commands`, the count of all commands with complete bank coordinates |
| `observed_span_cycles` | Last recorded command cycle minus first recorded command cycle |
| `observed_span_ns` | Observed span in cycles multiplied by verified `tCK_ps` and divided by 1,000 |

An observed bank has at least one bank-addressed issued command. Commands lacking complete bank coordinates are excluded from the command-share denominator. Command share measures the distribution of issued commands, not modeled bank-state time. The observed span is not total simulation time or a service outage.

## Clock domains

The inspected timing models define 625 ps for `DDR5_3200AN` and 312 ps for `DDR5_6400B`. See [WMB DDR5-VRR](https://github.com/STAR-Laboratory/PRAC_TC_ISCA25/blob/c4809a89299f47d7f02b7f922453cd8f7647e479/PRACLeak/ramulator2/src/dram/impl/DDR5-VRR.cpp), [Chronus DDR5-VRR](https://github.com/CMU-SAFARI/Chronus/blob/881a097a4c10f58953011c3ecf737e8f66d30bc0/src/dram/impl/DDR5-VRR.cpp) and [QPRAC DDR5-PRAC](https://github.com/sith-lab/qprac/blob/6fd217e102c01e21fd2ba1ff300c3e0460b91c41/perf_analysis/src/dram/impl/DDR5-PRAC.cpp).

For historical text traces, the analyzer reads the hashed configuration copy in the run directory. It converts cycles only when exactly one recognized preset is present without an explicit rate or `tCK_ps` override. It never uses the current mutable experiment file to interpret historical time. Upstream takes `tCK_ps` from the binary specification and rejects recordings with conflicting channel periods. Frontend cycles, controller cycles, host wall seconds and DDR data rate are separate quantities. Review the timing model and clock ratios before interpreting a changed configuration.

## Dependability interpretation

An issued command is an observation. A count or command span is a derived measurement. Assessing a dependability property requires a service requirement, sufficient observation coverage and an appropriate model. The current traces do not establish full request latency distributions, physical fault probabilities, MTTF, FIT, BER, availability, reliability, integrity or confidentiality. Missing measurements remain unavailable rather than zero.

Use `./bin/dramdpnd analyze RUN_ID` for JSON output, including source record locations for a bounded event sample. The original trace and native statistics remain the full evidence for the run.
