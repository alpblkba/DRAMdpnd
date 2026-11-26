"""Run one bounded upstream Ramulator 2.1 DDR4 example with native RAM2BIN output."""

import json

import ramulator


frontend = ramulator.frontend.SimpleO3(
    clock_ratio=8,
    traces=["ordinary.trace"],
    num_expected_insts=512,
    llc_capacity_per_core="1KB",
    translation=ramulator.translation.NoTranslation(max_addr=2147483648),
)
dram = ramulator.dram.DDR4(org_preset="DDR4_8Gb_x8", timing_preset="DDR4_2400R", rank=1)
controller = ramulator.controller.GenericDDR(
    dram=dram,
    scheduler=ramulator.scheduler.FRFCFS(),
    refresh_manager=ramulator.refresh_manager.AllBank(),
    row_policy=ramulator.row_policy.Open(),
    addr_mapper=ramulator.addr_mapper.RoBaRaCoCh(),
    controller_plugins=[ramulator.controller_plugin.BinTraceRecorder(path="trace")],
)
memory = ramulator.memory_system.GenericDRAM(
    clock_ratio=3,
    controllers=[controller],
    channel_mapper=ramulator.channel_mapper.CacheLineInterleave(),
)
simulation = ramulator.Simulation(frontend, memory)
simulation.run()
with open("stats.json", "w") as output:
    json.dump(simulation.stats, output, indent=2)
    output.write("\n")
