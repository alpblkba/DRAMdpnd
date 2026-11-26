# Third-party sources

DRAMdpnd runs the original research implementations from pinned checkouts under `external/`. I keep their source, builds, dependencies and raw run outputs outside the public repository. The license information below reflects the inspected tracked files at those revisions. It does not establish redistribution permission for the entire artifact.

## Research artifacts

### *When Mitigations Backfire: Timing Channel Attacks and Defense for PRAC-Based RowHammer Mitigations* (ISCA 2025)

Jeonghyun Woo, Joyce Qu, Gururaj Saileshwar and Prashant J. Nair.

Source: [STAR-Laboratory/PRAC_TC_ISCA25 at `c4809a89299f47d7f02b7f922453cd8f7647e479`](https://github.com/STAR-Laboratory/PRAC_TC_ISCA25/tree/c4809a89299f47d7f02b7f922453cd8f7647e479), checked out as `external/wmb`. DRAMdpnd uses the standalone [PRACLeak simulator](https://github.com/STAR-Laboratory/PRAC_TC_ISCA25/tree/c4809a89299f47d7f02b7f922453cd8f7647e479/PRACLeak/ramulator2). The separate `TPRAC/` workflow is not integrated.

No license file was found at the repository root or in PRACLeak. Two licenses were found under `TPRAC/champsim-ramulator2/`; I do not assume that they cover PRACLeak.

### *QPRAC: Secure and Practical PRAC-based RowHammer Mitigation using Priority Queues* (HPCA 2025)

Jeonghyun Woo, Shaopeng (Chris) Lin, Prashant J. Nair, Aamer Jaleel and Gururaj Saileshwar.

Source: [sith-lab/qprac at `6fd217e102c01e21fd2ba1ff300c3e0460b91c41`](https://github.com/sith-lab/qprac/tree/6fd217e102c01e21fd2ba1ff300c3e0460b91c41), checked out as `external/qprac`. DRAMdpnd uses the simulator in [`perf_analysis/`](https://github.com/sith-lab/qprac/tree/6fd217e102c01e21fd2ba1ff300c3e0460b91c41/perf_analysis), not the separate `security_analysis/` code.

No tracked LICENSE, COPYING or NOTICE file was found at this revision. Redistribution permission remains unresolved.

### *Chronus: Understanding and Securing the Cutting-Edge Industry Solutions to DRAM Read Disturbance* (HPCA 2025)

Oğuzhan Canpolat, A. Giray Yağlıkçı, Geraldo F. Oliveira, Ataberk Olgun, Nisa Bostancı, İsmail Emir Yüksel, Haocong Luo, Oğuz Ergin and Onur Mutlu ([paper record](https://arxiv.org/abs/2502.12650)).

Source: [CMU-SAFARI/Chronus at `881a097a4c10f58953011c3ecf737e8f66d30bc0`](https://github.com/CMU-SAFARI/Chronus/tree/881a097a4c10f58953011c3ecf737e8f66d30bc0), checked out as `external/chronus`. The simulator is in [`src/`](https://github.com/CMU-SAFARI/Chronus/tree/881a097a4c10f58953011c3ecf737e8f66d30bc0/src).

No tracked LICENSE, COPYING or NOTICE file was found at this revision. Redistribution permission remains unresolved.

### Ramulator 2.1 and RamViz

Source: [CMU-SAFARI/ramulator2 at `7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da`](https://github.com/CMU-SAFARI/ramulator2/tree/7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da), checked out as `external/ramulator2`.

The upstream [citation section](https://github.com/CMU-SAFARI/ramulator2/blob/7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da/README.md) lists *Ramulator 2.1: A Composable Memory System Simulator for Modern DRAM Systems* (2026 tutorial) and *Ramulator 2.0: A Modern, Modular, and Extensible DRAM Simulator* (IEEE Computer Architecture Letters 2024). The upstream attribution lists Haocong Luo, F. Nisa Bostancı, Ataberk Olgun, Maria Makeenkova, Ziad Malik, Ipek Akdeniz and Onur Mutlu. See the pinned README for the individual citation records.

The upstream [root license](https://github.com/CMU-SAFARI/ramulator2/blob/7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da/LICENSE) is MIT. Nested components may carry separate notices. This license does not establish rights to independently modified research implementations.

The three historical research artifacts retain the Ramulator 2.0-derived architecture and native text `TraceRecorder` implementations. The separate 2.1 checkout provides `BinTraceRecorder` and [RamViz](https://github.com/CMU-SAFARI/ramulator2/tree/7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da/visualizer). DRAMdpnd reads both trace formats in its own code. No upstream binary recorder has been backported into the research simulators. The RamViz recording in the README shows the original upstream viewer, not a DRAMdpnd visualization engine.

## Visualization and development tools

| Tool | Use in DRAMdpnd |
| --- | --- |
| [Perfetto](https://perfetto.dev/) | External viewer for exported Chrome JSON command instants. Export checked; interactive import unverified. No Perfetto source is cloned or bundled. |
| [Matplotlib](https://matplotlib.org/) 3.11.2 | Optional scientific figure generation. The installed distribution includes the Matplotlib license and separate bundled-font notices. Package versions are recorded in `requirements-figures.txt`. |
| [VHS](https://github.com/charmbracelet/vhs) 0.12.1 | Terminal recordings. The upstream project uses MIT; rendering also requires ttyd and FFmpeg. |
| [Playwright](https://github.com/microsoft/playwright) 1.64.0 | Browser recordings. The inspected `playwright` and `playwright-core` packages identify Apache-2.0 and include LICENSE and NOTICE files. Chromium is a separate browser dependency. |
| ttyd 1.7.7-unknown, FFmpeg 9.0.2, Node 26.3.0 | Local recording and browser tooling. The installed FFmpeg build converts recordings to GIF. |

The optional plotting and recording dependencies are installed locally. Their packages, executables, browser binaries, and caches are not redistributed. The recorded versions describe the tested setup, not a universal compatibility guarantee.

## License scope

I license my original DRAMdpnd contributions under the [MIT License](LICENSE). The license does not extend to the referenced papers, external simulators, their binaries, workloads or raw traces. Where I have not identified an applicable artifact license, I do not claim redistribution rights. A citation or a commit pin is not a license. Retain the original copyright notices and attribution when using the external trees.
