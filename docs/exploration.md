# Exploring DRAM behavior

Start with an ordinary run and read the simulator source beside its output. Keep the configuration, metadata, native statistics and trace together. Record the source revision, command, observation and any assumptions behind your interpretation.

## Start with a run

```bash
./bin/dramdpnd status
./bin/dramdpnd wmb
./bin/dramdpnd verify RUN_ID
./bin/dramdpnd analyze RUN_ID --summary
./bin/dramdpnd figures RUN_ID
./bin/dramdpnd ui
```

Replace `RUN_ID` with the new run identifier. In the workbench, filter Run history to WMB and `VALID`. Open the copied configuration, `stdout.txt` and command distribution. Follow one ACT record in `commands/trace.ch0` back to its device-model definition. Compare logical bank counts with the raw lines. Check the `clock_ratio` settings and the 625 ps model period before interpreting `observed_span_ns`. Keep host wall time separate.

## 1. Build and execution

Compare `config.yaml`, `stdout.txt`, `output.txt` and `commands/trace.ch0`. Read the pinned [PRACLeak entry point](https://github.com/STAR-Laboratory/PRAC_TC_ISCA25/blob/c4809a89299f47d7f02b7f922453cd8f7647e479/PRACLeak/ramulator2/src/main.cpp) alongside [environment setup](environment.md). Identify the configuration inputs, native statistics and per-command observations. A successful 512-instruction run does not reproduce the paper's workloads or results.

## 2. DRAM state machine

Read WMB's [DDR5-VRR device model](https://github.com/STAR-Laboratory/PRAC_TC_ISCA25/blob/c4809a89299f47d7f02b7f922453cd8f7647e479/PRACLeak/ramulator2/src/dram/impl/DDR5-VRR.cpp). Look at the hierarchy, command scopes, prerequisites, timing constraints and state transitions. Locate ordinary ACT, RD, PRE/PREA and refresh-related commands when present in the trace. Follow one command to its model definition. A memory request is an input to the memory system. An issued command is a device-level operation. Check the `DDR5_3200AN` timing preset before converting cycles to nanoseconds.

## 3. Request lifecycle

Follow an ordinary read through the [BHO3 frontend](https://github.com/STAR-Laboratory/PRAC_TC_ISCA25/blob/c4809a89299f47d7f02b7f922453cd8f7647e479/PRACLeak/ramulator2/src/frontend/impl/processor/bhO3/bhO3.cpp), [memory system](https://github.com/STAR-Laboratory/PRAC_TC_ISCA25/blob/c4809a89299f47d7f02b7f922453cd8f7647e479/PRACLeak/ramulator2/src/memory_system/impl/bh_DRAM_system.cpp), [PRAC controller](https://github.com/STAR-Laboratory/PRAC_TC_ISCA25/blob/c4809a89299f47d7f02b7f922453cd8f7647e479/PRACLeak/ramulator2/src/dram_controller/impl/prac_dram_controller.cpp) and [text recorder](https://github.com/STAR-Laboratory/PRAC_TC_ISCA25/blob/c4809a89299f47d7f02b7f922453cd8f7647e479/PRACLeak/ramulator2/src/dram_controller/impl/plugin/trace_recorder.cpp). Identify admission, buffers, scheduling, issue and completion. Note which stages are visible in the output. Controller-internal behavior can complete a request without a device command, so the trace alone cannot provide full request latency.

## 4. Address mapping

Read `AddrMapper` in each effective YAML. Compare WMB's [linear mappers](https://github.com/STAR-Laboratory/PRAC_TC_ISCA25/blob/c4809a89299f47d7f02b7f922453cd8f7647e479/PRACLeak/ramulator2/src/addr_mapper/impl/linear_mappers.cpp), QPRAC's `external/qprac/perf_analysis/src/addr_mapper/` and upstream's [ro_ba_ra_co_ch.cpp](https://github.com/CMU-SAFARI/ramulator2/blob/7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da/src/ramulator/controller/addr_mapper/impl/ro_ba_ra_co_ch.cpp). Use the first few ordinary addresses in `experiments/ordinary.trace` to examine the modeled logical coordinates. The same address need not identify the same location across artifacts.

## 5. Clock domains

Compare `Frontend.clock_ratio` and `MemorySystem.clock_ratio` with the simulator tick loop and DRAM timing table. Keep the configured DDR data rate, DRAM cycle period, frontend-to-memory clock relationship, simulated cycles and host wall time separate. Changing the DRAM speed without adjusting clock ratios may change modeled processor frequency. Check that relationship rather than treating it as a finding from the current runs.

## 6. Protection and maintenance observations

Inspect the [WMB plugin directory](https://github.com/STAR-Laboratory/PRAC_TC_ISCA25/tree/c4809a89299f47d7f02b7f922453cd8f7647e479/PRACLeak/ramulator2/src/dram_controller/impl/plugin), QPRAC's performance controller and [Chronus plugin](https://github.com/CMU-SAFARI/Chronus/blob/881a097a4c10f58953011c3ecf737e8f66d30bc0/src/dram_controller/impl/plugin/chronus.cpp). Identify the source of the available maintenance and protection statistics, and compare them with the recorded ordinary workload. A native counter or issued command is evidence of a modeled observation within that run. It is not a security guarantee or a physical fault probability.

## 7. Upstream Ramulator 2.1 and RamViz

```bash
./bin/dramdpnd ramulator
./bin/dramdpnd ramulator ramviz
```

Inspect [bin_trace_recorder.cpp](https://github.com/CMU-SAFARI/ramulator2/blob/7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da/src/ramulator/controller/plugin/impl/bin_trace_recorder.cpp), the run's `stats.json` and native `.ram2bin`. The second command opens the viewer without running another simulation. Inspect commands, bus activity, bank-state reconstruction, timing parameters and resource labels. Distinguish recorded data from states reconstructed by RamViz. The older native text traces cannot be opened as RAM2BIN. Requests and Throughput views remain unverified in the current demonstrations. See the [upstream viewer instructions](https://github.com/CMU-SAFARI/ramulator2/blob/7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da/README.md#10-trace-visualizer).

## 8. Perfetto

`experiments/perfetto-example.json` is a synthetic format example with request slices, an instant and counters. It is useful for reading the [Chrome JSON format guide](https://perfetto.dev/docs/getting-started/other-formats), not for architectural measurements.

For actual observations, run `./bin/dramdpnd perfetto RUN_ID` using a `VALID` run with a known `tCK_ps`. Inspect the exported command instants and native cycle fields. The export has passed local structural checks. Interactive import remains unverified. Keep unpublished research traces local.
