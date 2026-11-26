# Environment and source setup

I tested the four simulator backends on an Apple M4 Max (ARM64, 36 GiB) running macOS 26.5.1. The host used Apple Clang 17, CMake 4.3.2, Python 3.14.6, Node 26.3.0 and npm 12.1. Simulator execution uses a Linux ARM64 Docker image with Ubuntu 24.04, GCC 13.3, CMake 3.28.3 and Python 3.12.3.

The native WMB build needed `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` for an old yaml-cpp dependency, then Apple Clang failed at `src/base/param.h:91` on a dependent-template `as<T>()` call. All four simulators built and ran inside Linux ARM64. No separate Podman VM or x86-64 emulation was needed. These are bounded local tests, not a clean-host installation test or a reproduction of the papers' results.

## Acquire the pinned sources

Run the following from the DRAMdpnd root for a new workspace. Each detached checkout applies only to its own external source tree. See [third-party sources](../THIRD_PARTY.md) for attribution and licensing.

```bash
git clone --filter=blob:none --sparse https://github.com/sith-lab/qprac.git external/qprac
git -C external/qprac checkout --detach 6fd217e102c01e21fd2ba1ff300c3e0460b91c41
git -C external/qprac sparse-checkout set perf_analysis/src perf_analysis/config perf_analysis/sim_scripts security_analysis
git clone --filter=blob:none --sparse https://github.com/STAR-Laboratory/PRAC_TC_ISCA25.git external/wmb
git -C external/wmb checkout --detach c4809a89299f47d7f02b7f922453cd8f7647e479
git -C external/wmb sparse-checkout set PRACLeak/ramulator2 PRACLeak/results/configs
git clone --filter=blob:none --sparse https://github.com/CMU-SAFARI/Chronus.git external/chronus
git -C external/chronus checkout --detach 881a097a4c10f58953011c3ecf737e8f66d30bc0
git -C external/chronus sparse-checkout set src scripts
git clone --filter=blob:none --sparse https://github.com/CMU-SAFARI/ramulator2.git external/ramulator2
git -C external/ramulator2 checkout --detach 7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da
git -C external/ramulator2 sparse-checkout set .devcontainer examples ext python src tests visualizer
```

## Build the container image

The image recipe comes from the pinned upstream [Dockerfile](https://github.com/CMU-SAFARI/ramulator2/blob/7bead6cb7c4b03e095c6d4769ae3181a8e0bf6da/.devcontainer/Dockerfile). The tested image was `ramulator2-ramulator2:latest`, with ID `sha256:b2477dc25de0367f104ecc9c98c848cf83ac4a5850362c69105568b04ad4624b`. Reuse it if available. On a new ARM64 host, build and inspect the image:

```bash
docker build --platform linux/arm64 -t ramulator2-ramulator2:latest -f external/ramulator2/.devcontainer/Dockerfile external/ramulator2
docker image inspect ramulator2-ramulator2:latest --format '{{.Id}} {{.Architecture}}'
docker run --rm ramulator2-ramulator2:latest g++ -dumpfullversion
```

The Ubuntu base tag, apt packages and Node repository are not digest-pinned, so a newly built image may differ. Each run records the actual immutable image ID and compiler identity. Simulation does not download sources, images or workloads as a side effect.

## Build the simulators

The tested builds use CMake and GCC inside the image. Each source directory has its own `build-linux/` directory.

| Backend | Source directory |
| --- | --- |
| WMB | `external/wmb/PRACLeak/ramulator2` |
| QPRAC | `external/qprac/perf_analysis` |
| Chronus | `external/chronus` |
| Upstream | `external/ramulator2` |

From the project root, a representative WMB build is:

```bash
docker run --rm --platform linux/arm64 --user "$(id -u):$(id -g)" \
  --mount "type=bind,src=$PWD,dst=/workspace" \
  -w /workspace/external/wmb/PRACLeak/ramulator2 \
  ramulator2-ramulator2:latest \
  sh -lc 'cmake -S . -B build-linux -DCMAKE_BUILD_TYPE=Release && cmake --build build-linux -j 4'
```

Substitute the source directory for each remaining backend. The first configure may acquire nested dependencies, so it needs network access and free disk space. Upstream CMake needs the `tests/` sparse path for its default target. Its Python binding and `libramulator.so` are required for `dramdpnd ramulator`.

WMB's local configure used an in-process Git `safe.directory` override for the nested yaml-cpp checkout because Docker's user ID differed from the host. No global Git setting was changed. The local build logs are under `runs/builds/{wmb,qprac,chronus,ramulator2}/`. The build instructions reflect successful local builds rather than a verified fresh-host procedure. Resolve any compiler or nested dependency error before executing the simulator.

## Build RamViz

RamViz is part of the same upstream checkout. The following commands succeeded with the host Node version:

```bash
cd external/ramulator2/visualizer
npm ci --no-audit --no-fund
npm run build
cd ../../..
```

The logs are `runs/builds/ramulator2/ramviz-npm.log` and `ramviz-build.log`. Run `./bin/dramdpnd ramulator ramviz` to start the viewer at `127.0.0.1:3000` with an access token and open the available validated upstream trace. This does not start a simulation. If the port is occupied, stop the existing local viewer first.

## Check the environment

```bash
./bin/dramdpnd doctor
./bin/dramdpnd status
```

New executions use the resolved image ID, a read-only mount of the selected source tree and a writable mount of the new run directory. Container networking is disabled during simulation. The external checkouts and generated runs are ignored by Git and remain available locally. Check free disk space before larger experiments.

The plotting and recording environments are optional. See [figures](figures.md) for Matplotlib and [development](development.md) for terminal and browser recording dependencies.
