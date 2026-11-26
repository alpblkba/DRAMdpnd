# Trace visualization

## Trace formats

WMB, QPRAC and Chronus retain their original Ramulator 2.0-derived source trees. Each uses a native text `TraceRecorder`: [WMB PRACLeak](https://github.com/STAR-Laboratory/PRAC_TC_ISCA25/blob/c4809a89299f47d7f02b7f922453cd8f7647e479/PRACLeak/ramulator2/src/dram_controller/impl/plugin/trace_recorder.cpp), [QPRAC performance analysis](https://github.com/sith-lab/qprac/blob/6fd217e102c01e21fd2ba1ff300c3e0460b91c41/perf_analysis/src/dram_controller/impl/plugin/trace_recorder.cpp) and [Chronus](https://github.com/CMU-SAFARI/Chronus/blob/881a097a4c10f58953011c3ecf737e8f66d30bc0/src/dram_controller/impl/plugin/trace_recorder.cpp). Their `src/main.cpp` files identify the Ramulator 2.0 component architecture.

The separate upstream [Ramulator 2.1 reference](https://github.com/CMU-SAFARI/ramulator2/blob/7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da/README.md) provides [BinTraceRecorder](https://github.com/CMU-SAFARI/ramulator2/blob/7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da/src/ramulator/controller/plugin/impl/bin_trace_recorder.cpp), selected through the Python plugin interface in `experiments/ramulator.py`. No 2.1 binary recorder or other 2.1 component was found in the inspected historical artifact `src/` trees. `scripts/evidence.py` parses both native formats without changing the simulators.

## RamViz

```bash
./bin/dramdpnd ramulator
./bin/dramdpnd ramulator ramviz
```

The first command produces an upstream run. The second opens the newest validated compatible trace in the original [RamViz viewer](https://github.com/CMU-SAFARI/ramulator2/tree/7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da/visualizer). It does not execute another simulation. The viewer reconstructs bank states from issued commands and the trace timing table, rather than reading internal simulator state.

![RamViz command and bank-state inspection](assets/ramviz.gif)

The recording shows a validated DDR4 trace with an 833 ps model clock, its Commands and Bank state panels, logical hierarchy, bank selection and timing legend. Requests and Throughput interactions have not been verified.

## Reading the bank-state statistics

The visible-window bank-state percentages use accumulated state time divided by the number of visible bank lanes multiplied by the window length in clock cycles. See [useRenderer.ts](https://github.com/CMU-SAFARI/ramulator2/blob/7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da/visualizer/app/composables/useRenderer.ts) and the [bank-window accumulator](https://github.com/CMU-SAFARI/ramulator2/blob/7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da/visualizer/app/engine/stats.ts). If one of sixteen counted banks spends the entire window in a state, that bank contributes 6.25% of total bank-time. Header summaries use their descendant banks. Check the inspector's `Banks counted` field before interpreting a percentage.

Selecting a bank displays its state information but does not change the aggregate denominator. Selecting a time range changes the interval. The inspected viewer has no explicit toggle between all configured banks, observed banks and a selected bank.

Channel data-bus utilization has a different denominator. The [coverage calculation](https://github.com/CMU-SAFARI/ramulator2/blob/7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da/visualizer/app/engine/stats.ts) divides busy cycles by the window length for each data-bus domain. The inspector averages those fractions for the visible banks' domains. It does not divide bus busy time by bank count. RamViz may estimate values while edge tiles load, and reconstructed bank states have modeling limits.

The DRAMdpnd workbench provides a different measurement: the share of bank-addressed issued commands attributed to a selected logical bank. A bank is observed if at least one command has its complete logical bank coordinates. The interface displays the denominator and command-span interval. This count-based measurement does not establish bank-state duration or utilization.

## Perfetto

```bash
./bin/dramdpnd perfetto RUN_ID
```

The exporter writes Chrome JSON instant events from `VALID` version 2 runs with a verified model clock. Timestamps are in microseconds. The export is limited to 100,000 command records. Tracks identify logical channels, ranks, bank groups and banks. Each event retains its native command name, cycle, numeric address and source record. Negative native resource placeholders appear as `unspecified` in track names.

Recognized commands are grouped under activation, read, write, refresh or mitigation. Other commands retain the generic issued-command category. The exporter does not invent request lifetimes, bank-state durations or service interruption intervals. A genuine WMB export passed structural checks. Interactive import into a Perfetto viewer remains unverified, and no research trace was uploaded to a remote viewer.
