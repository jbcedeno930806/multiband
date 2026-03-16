#!/usr/bin/env python3
"""
Ejecuta simulaciones ONDM unificadas (una ruta) para varias topologias.

Ajustes rapidos:
- TRAFFIC_BY_TOPOLOGY: rango de cargas por topologia.
- N_EVALUATIONS: numero de eventos por simulacion.
- PROGRESS_EVERY: frecuencia de logs de progreso (0.05 = 5%).
"""
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from netsim.netSimPy import EventsGenerator, Network
from netsim.netSimPy.common.allocators import (
    Variant,
    alphaBalancing,
    bitrate_partition_allocation,
    least_fragmentation_band_prioritization,
    length_partition_allocation,
    most_available_band_all_routes,
)
from netsim.netSimPy.common.evaluators import NetworkEvaluator


# -----------------------------
# Configuracion
# -----------------------------
N_EVALUATIONS = 10_000
M_LAMBDA = 200_000
PROGRESS_EVERY = 0.05

DEFAULT_TRAFFIC = [50_000, 100_000, 150_000, 200_000, 250_000, 300_000, 350_000, 400_000]

TRAFFIC_BY_TOPOLOGY = {
    "NSFNet": DEFAULT_TRAFFIC,
    # "UKNet": DEFAULT_TRAFFIC,
    # "Eurocore": DEFAULT_TRAFFIC,
    # "USNet": DEFAULT_TRAFFIC,
    # "EONet": DEFAULT_TRAFFIC,
}

TOPOLOGIES = [
    {"name": "NSFNet", "dir": "nsfnet", "bitrate": "bitrates_4_bands.json"},
    # {"name": "UKNet", "dir": "uknet", "bitrate": "bitrates_c_bands.json"},
    # {"name": "Eurocore", "dir": "eurocore", "bitrate": "bitrates_c_bands.json"},
    # {"name": "USNet", "dir": "usnet", "bitrate": "bitrates_c_bands.json"},
    # {"name": "EONet", "dir": "eon", "bitrate": "bitrates_c_bands.json"},
]


# -----------------------------
# Helpers
# -----------------------------
def now_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


class LogManager:
    def __init__(self) -> None:
        self._is_tty = sys.stdout.isatty()
        self._live_active = False
        self._run_line = ""
        self._prog_line = ""
        self._run_ts = ""

    def _format_line(self, level: str, msg: str, ts: Optional[str] = None) -> str:
        stamp = ts if ts is not None else now_ts()
        return f"[{stamp}] {level:<5} | {msg}"

    def _emit(self, level: str, msg: str) -> None:
        if self._live_active and self._is_tty:
            self._clear_live_area()
        print(self._format_line(level, msg), flush=True)

    def info(self, msg: str) -> None:
        self._emit("INFO", msg)

    def warn(self, msg: str) -> None:
        self._emit("WARN", msg)

    def _render_live(self) -> None:
        if not self._is_tty:
            return
        if self._live_active:
            # move cursor up to the RUN line
            sys.stdout.write("\x1b[1A\r\x1b[2K")
        else:
            self._live_active = True
        sys.stdout.write(self._run_line + "\n")
        sys.stdout.write("\r\x1b[2K" + self._prog_line)
        sys.stdout.flush()

    def _clear_live_area(self) -> None:
        if not self._is_tty or not self._live_active:
            return
        # clear PROG line
        sys.stdout.write("\r\x1b[2K")
        # clear RUN line
        sys.stdout.write("\x1b[1A\r\x1b[2K")
        sys.stdout.flush()
        self._live_active = False
        self._run_line = ""
        self._prog_line = ""
        self._run_ts = ""

    def live_run(self, msg: str) -> None:
        if not self._is_tty:
            self.info(msg)
            return
        if not self._live_active:
            self._run_ts = now_ts()
        self._run_line = self._format_line("INFO", msg, ts=self._run_ts)
        if not self._prog_line:
            self._prog_line = self._format_line("PROG", "", ts=now_ts())
        self._render_live()

    def progress(self, msg: str) -> None:
        if not self._is_tty:
            self.info(msg)
            return
        self._prog_line = self._format_line("PROG", msg, ts=now_ts())
        self._render_live()

    def finalize_progress(self) -> None:
        if self._live_active and self._is_tty:
            self._clear_live_area()


def fmt_seconds(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = seconds / 60.0
    if minutes < 60:
        return f"{minutes:.1f}m"
    hours = minutes / 60.0
    return f"{hours:.2f}h"


def progress_bar(ratio: float, width: int = 20) -> str:
    ratio = max(0.0, min(1.0, ratio))
    filled = int(ratio * width)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def section_line(title: str, width: int = 72) -> str:
    label = f" {title} "
    if len(label) >= width:
        return label
    side = (width - len(label)) // 2
    return "-" * side + label + "-" * (width - len(label) - side)


def filter_bands(order: List[str], available: List[str]) -> List[str]:
    filtered = [b for b in order if b in available]
    return filtered if filtered else list(available)


def compute_mean_length(network: Network) -> int:
    if not network.lengths:
        return 0
    total = sum(lengths[0] for lengths in network.lengths.values())
    return math.ceil(total / len(network.lengths))


def compute_mean_bitrate(network: Network) -> float:
    if not network.bitRates:
        return 0.0
    values = [br.getBitRate() for br in network.bitRates]
    return sum(values) / len(values)


# -----------------------------
# Evaluator con progreso
# -----------------------------
class ProgressNetworkEvaluator(NetworkEvaluator):
    def __init__(
        self,
        name: str,
        total_steps: int,
        bands: List[str],
        progress_every: float,
        log_fn: Callable[[str], None],
        context: str,
        header: Optional[Dict[str, str]] = None,
    ):
        super().__init__(name=name, bands=bands, header=header, should_save=True)
        self.total_steps = total_steps
        self.progress_every = progress_every
        self._next_progress = progress_every
        self._log = log_fn
        self._context = context
        self._start = time.perf_counter()

    def _on_update(self, args):
        super()._on_update(args)
        if self.total_steps <= 0:
            return
        steps = self.metrics["steps"]
        ratio = steps / self.total_steps if self.total_steps else 0.0
        if ratio >= self._next_progress:
            bp = self.metrics["blockedEvents"] / steps if steps else 0.0
            elapsed = time.perf_counter() - self._start
            eta = elapsed * (self.total_steps - steps) / steps if steps else 0.0
            bar = progress_bar(ratio)
            self._log(
                f"{self._context} | {bar} {ratio*100:5.1f}% | "
                f"BP~{bp:.6f} | t={fmt_seconds(elapsed)} | ETA={fmt_seconds(eta)}"
            )
            while self._next_progress <= ratio:
                self._next_progress += self.progress_every

    def _on_run_end(self, args):
        block = self.metrics["blockedEvents"]
        steps = self.metrics["steps"]
        if self.results_writer:
            self.results_writer.write_row(self.metrics)
        bp = round(block / steps, 6) if steps else 0.0
        elapsed = time.perf_counter() - self._start
        bar = progress_bar(1.0)
        self._log(
            f"{self._context} | {bar} 100.0% | " f"BP={bp} | t={fmt_seconds(elapsed)}"
        )
        return bp


# -----------------------------
# Plan de ejecucion
# -----------------------------
@dataclass
class TopologyState:
    name: str
    network: Network
    generator: EventsGenerator
    available_bands: List[str]
    mean_length: int
    mean_bitrate: float
    traffic: List[int]


@dataclass
class AlgorithmSpec:
    key: str
    label: str
    factory: Callable[[TopologyState], Callable]


def build_algorithms() -> List[AlgorithmSpec]:
    def lfbp_factory(ctx: TopologyState):
        return least_fragmentation_band_prioritization(
            1, variant=Variant.Least_Fragmentation
        )

    def mabar_factory(ctx: TopologyState):
        return most_available_band_all_routes(1)

    def lpa_factory(ctx: TopologyState):
        orders = [
            filter_bands(["E", "S", "C", "L"], ctx.available_bands),
            filter_bands(["L", "C", "S", "E"], ctx.available_bands),
        ]
        return length_partition_allocation(1, ctx.mean_length, bandsOrders=orders)

    def bpa_factory(ctx: TopologyState):
        orders = [
            filter_bands(["C", "L", "S", "E"], ctx.available_bands),
            filter_bands(["E", "L", "S", "C"], ctx.available_bands),
        ]
        return bitrate_partition_allocation(1, ctx.mean_bitrate, bandsOrders=orders)

    def abpa_clse_factory(ctx: TopologyState):
        order = filter_bands(["C", "L", "S", "E"], ctx.available_bands)
        return alphaBalancing(1, [1], [order])

    def abpa_eslc_factory(ctx: TopologyState):
        order = filter_bands(["E", "S", "L", "C"], ctx.available_bands)
        return alphaBalancing(1, [1], [order])

    return [
        AlgorithmSpec(
            key="lfbp",
            label="least_fragmentation_band_prioritization",
            factory=lfbp_factory,
        ),
        AlgorithmSpec(
            key="mabar",
            label="most_available_band_all_routes",
            factory=mabar_factory,
        ),
        AlgorithmSpec(
            key="lpa",
            label="length_partition_allocation",
            factory=lpa_factory,
        ),
        AlgorithmSpec(
            key="bpa",
            label="bitrate_partition_allocation",
            factory=bpa_factory,
        ),
        AlgorithmSpec(
            key="abpa_clse",
            label='alphaBalancing(1,[1],[["C","L","S","E"]])',
            factory=abpa_clse_factory,
        ),
        AlgorithmSpec(
            key="abpa_eslc",
            label='alphaBalancing(1,[1],[["E","S","L","C"]])',
            factory=abpa_eslc_factory,
        ),
    ]


def build_topologies(logs: LogManager) -> Dict[str, TopologyState]:
    root = Path(__file__).resolve().parents[2]
    networks_dir = root / "networks"
    states: Dict[str, TopologyState] = {}

    for topo in TOPOLOGIES:
        name = topo["name"]
        traffic = TRAFFIC_BY_TOPOLOGY.get(name, [])
        if not traffic:
            logs.warn(f"Omitiendo {name}: no hay trafico definido.")
            continue

        topo_dir = networks_dir / topo["dir"]
        network = Network(
            networkFileName=str(topo_dir / "network.json"),
            pathsFileName=str(topo_dir / "routes.json"),
            bitrateFilename=str(topo_dir / topo["bitrate"]),
        )
        generator = EventsGenerator(mLambda=M_LAMBDA)
        available_bands = network.getBands()
        mean_length = compute_mean_length(network)
        mean_bitrate = compute_mean_bitrate(network)

        states[name] = TopologyState(
            name=name,
            network=network,
            generator=generator,
            available_bands=available_bands,
            mean_length=mean_length,
            mean_bitrate=mean_bitrate,
            traffic=traffic,
        )
        logs.info(
            f"Topologia {name} | bandas={available_bands} | "
            f"mean_len={mean_length} | mean_br={mean_bitrate:.1f}"
        )
    return states


def main() -> None:
    logs = LogManager()
    logs.info("Inicio de simulaciones ONDM unificadas (1 ruta).")
    topologies = build_topologies(logs)
    algorithms = build_algorithms()
    if not topologies:
        logs.info("No hay topologias activas. Revisar TRAFFIC_BY_TOPOLOGY.")
        return

    tasks: List[Tuple[TopologyState, AlgorithmSpec, int]] = []
    for topo in topologies.values():
        for algo in algorithms:
            for traffic in topo.traffic:
                tasks.append((topo, algo, traffic))

    total_tasks = len(tasks)
    if total_tasks == 0:
        logs.info("No hay simulaciones para ejecutar.")
        return

    base_results = Path(__file__).resolve().parent / "results"
    total_start = time.perf_counter()
    logs.info(f"Plan: {total_tasks} simulaciones en cola.")

    current_topology = None
    for idx, (topo, algo, traffic) in enumerate(tasks, start=1):
        if topo.name != current_topology:
            logs.info(section_line(f"TOPOLOGY {topo.name}"))
            current_topology = topo.name
        global_pct = (idx - 1) / total_tasks * 100
        logs.live_run(
            f"RUNNING  | {topo.name} | {algo.key} | "
            f"global={idx}/{total_tasks} ({global_pct:.1f}%)"
        )

        allocator = algo.factory(topo)
        simulator = None
        try:
            from netsim.netSimPy import NetworkSimulator

            simulator = NetworkSimulator(
                network=topo.network,
                eventsGenerator=topo.generator,
                allocator=allocator,
            )
            simulator.reset()
            simulator.setLambda(traffic)

            out_dir = base_results / topo.name
            run_name = str(out_dir / f"{algo.key}_{traffic}")
            header = {
                "topology": topo.name,
                "algorithm": algo.label,
                "lambda": str(traffic),
                "n_evaluations": str(N_EVALUATIONS),
            }
            context = f"{topo.name} | {algo.key} | lambda={traffic}"
            evaluator = ProgressNetworkEvaluator(
                name=run_name,
                total_steps=N_EVALUATIONS,
                bands=topo.available_bands,
                progress_every=PROGRESS_EVERY,
                log_fn=logs.progress,
                context=context,
                header=header,
            )

            run_start = time.perf_counter()
            bp = simulator.run(N_EVALUATIONS, evaluator)
            run_elapsed = time.perf_counter() - run_start
            logs.finalize_progress()

            logs.info(
                f"DONE | {topo.name} | {algo.key} | lambda={traffic} | "
                f"total_time={fmt_seconds(run_elapsed)} | BP={bp}"
            )
        finally:
            if simulator is not None:
                simulator.reset()

    total_elapsed = time.perf_counter() - total_start
    logs.info(f"Fin. Tiempo total: {fmt_seconds(total_elapsed)}")
    logs.info(f"Resultados en: {base_results}")


if __name__ == "__main__":
    main()
