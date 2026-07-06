#!/usr/bin/env python3
"""
Ejecuta simulaciones alphaBalancing para NSFNet.

Se recorren todos los valores de alpha y todas las combinaciones de ordenes
de banda (permutaciones) para bands1 y bands2. Para cada combinacion se
simulan todos los valores de trafico definidos.
"""
import itertools
import shutil
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from netsim.netSimPy import EventsGenerator, Network, NetworkSimulator
from netsim.netSimPy.common.allocators import alphaBalancing
from netsim.netSimPy.common.evaluators import NetworkEvaluator


# -----------------------------
# Configuracion
# -----------------------------
N_EVALUATIONS = 2_000_000
M_LAMBDA = 10_000
PROGRESS_EVERY = 0.00005

AVAILABLE_BANDS = ["C", "S", "L", "E"]
TRAFFICS = [50_000, 75_000, 100_000, 125_000, 150_000, 175_000, 200_000]
ALPHAS = [i / 10 for i in range(3, 11)]  # 0.3 .. 1.0
# Reanuda desde el punto que correspondia a global=11679/29187
# del plan anterior. Eso cae en alpha=0.6, run interno 2652
# (orden1=LSEC, orden2=ECSL, trafico=175000).
#
# Para omitir un alpha completo, usa un start_run mayor a runs_per_alpha (4032).
ALPHA_START_RUNS = {
    "0.3": 4033,
    "0.4": 4033,
    "0.5": 4033,
    "0.6": 2652,
}

# Para pruebas rapidas puedes limitar combinaciones:
MAX_COMBINATIONS = None  # e.g. 10


# -----------------------------
# Logging
# -----------------------------
def now_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


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


class LogManager:
    def __init__(self) -> None:
        self._is_tty = sys.stdout.isatty()
        self._live_active = False
        self._run_line = ""
        self._prog_line = ""
        self._run_ts = ""

    def _format_line(self, level: str, msg: str, ts: Optional[str] = None) -> str:
        stamp = ts if ts is not None else now_ts()
        line = f"[{stamp}] {level:<5} | {msg}"
        if self._is_tty:
            width = shutil.get_terminal_size((120, 20)).columns
            if len(line) > width:
                line = line[: max(0, width - 3)] + "..."
        return line

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
            sys.stdout.write("\x1b[1A\r\x1b[2K")
        else:
            self._live_active = True
        sys.stdout.write(self._run_line + "\n")
        sys.stdout.write("\r\x1b[2K" + self._prog_line)
        sys.stdout.flush()

    def _clear_live_area(self) -> None:
        if not self._is_tty or not self._live_active:
            return
        sys.stdout.write("\r\x1b[2K")
        sys.stdout.write("\x1b[1A\r\x1b[2K")
        sys.stdout.flush()
        self._live_active = False
        self._run_line = ""
        self._prog_line = ""
        self._run_ts = ""

    def live_run(self, msg: str) -> None:
        if not self._is_tty:
            return
        if not self._live_active:
            self._run_ts = now_ts()
        self._run_line = self._format_line("INFO", msg, ts=self._run_ts)
        if not self._prog_line:
            self._prog_line = self._format_line("PROG", "", ts=now_ts())
        self._render_live()

    def progress(self, msg: str) -> None:
        if not self._is_tty:
            return
        self._prog_line = self._format_line("PROG", msg, ts=now_ts())
        self._render_live()

    def finalize_progress(self) -> None:
        if self._live_active and self._is_tty:
            self._clear_live_area()


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
# Main
# -----------------------------
def build_orders() -> List[Tuple[str, ...]]:
    return list(itertools.permutations(AVAILABLE_BANDS))


def order_label(order: Tuple[str, ...]) -> str:
    return "".join(order)


def alpha_start_run(alpha: float) -> int:
    return ALPHA_START_RUNS.get(f"{alpha:.1f}", 1)


def main() -> None:
    logs = LogManager()
    logs.info("Inicio de simulaciones alphaBalancing (NSFNet).")

    orders = build_orders()
    if MAX_COMBINATIONS is not None:
        orders = orders[:MAX_COMBINATIONS]

    order_pairs = list(itertools.product(orders, repeat=2))
    combos_per_alpha = len(order_pairs)
    runs_per_alpha = combos_per_alpha * len(TRAFFICS)

    total_combos = 0
    total_runs = 0
    for alpha in ALPHAS:
        start_run = alpha_start_run(alpha)
        if start_run > runs_per_alpha:
            continue
        total_combos += combos_per_alpha - ((start_run - 1) // len(TRAFFICS))
        total_runs += runs_per_alpha - (start_run - 1)

    logs.info(
        f"Plan: alphas={len(ALPHAS)}, ordenes={len(orders)}, "
        f"combos={total_combos}, runs={total_runs}."
    )

    root = Path(__file__).resolve().parents[2]
    networks_dir = root / "networks" / "nsfnet"
    results_dir = Path(__file__).resolve().parent / "results"

    run_idx = 0
    total_start = time.perf_counter()

    for alpha in ALPHAS:
        alpha_id = f"{alpha:.1f}"
        start_run = alpha_start_run(alpha)
        if start_run > runs_per_alpha:
            logs.warn(
                f"ALPHA {alpha_id} omitido: start_run={start_run} excede "
                f"las {runs_per_alpha} ejecuciones disponibles."
            )
            continue

        start_combo_idx = ((start_run - 1) // len(TRAFFICS)) + 1
        start_traffic_idx = (start_run - 1) % len(TRAFFICS)

        logs.info(section_line(f"ALPHA {alpha_id}"))
        if start_run > 1:
            logs.info(
                f"Reanudando alpha={alpha_id} desde run {start_run}/{runs_per_alpha} "
                f"(combo {start_combo_idx}/{combos_per_alpha}, trafico #{start_traffic_idx + 1})."
            )

        for combo_number, (bands1, bands2) in enumerate(order_pairs, start=1):
            if combo_number < start_combo_idx:
                continue

            traffic_start = start_traffic_idx if combo_number == start_combo_idx else 0
            traffic_values = TRAFFICS[traffic_start:]

            allocator = alphaBalancing(1, [alpha, 1], [list(bands1), list(bands2)])
            network = Network(
                networkFileName=str(networks_dir / "network.json"),
                pathsFileName=str(networks_dir / "routes.json"),
                bitrateFilename=str(networks_dir / "bitrates_4_bands.json"),
            )
            generator = EventsGenerator(M_LAMBDA)
            simulator = NetworkSimulator(
                eventsGenerator=generator,
                network=network,
                allocator=allocator,
            )

            order1 = order_label(bands1)
            order2 = order_label(bands2)
            for traffic in traffic_values:
                run_idx += 1
                global_pct = (run_idx - 1) / total_runs * 100
                logs.live_run(
                    f"RUN  | a={alpha:.1f} | {order1}-{order2} | "
                    f"lam={traffic} | global={run_idx}/{total_runs} ({global_pct:.1f}%)"
                )

                out_dir = results_dir / f"alpha_{alpha:.1f}"
                run_name = str(out_dir / f"{order1}_{order2}_{traffic}")
                header = {
                    "alpha": f"{alpha:.1f}",
                    "order1": order1,
                    "order2": order2,
                    "lambda": str(traffic),
                    "n_evaluations": str(N_EVALUATIONS),
                }
                context = f"a={alpha:.1f} | {order1}-{order2} | lam={traffic}"
                evaluator = ProgressNetworkEvaluator(
                    name=run_name,
                    total_steps=N_EVALUATIONS,
                    bands=AVAILABLE_BANDS,
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
                    f"DONE | a={alpha:.1f} | {order1}-{order2} | "
                    f"lam={traffic} | t={fmt_seconds(run_elapsed)} | BP={bp}"
                )

    total_elapsed = time.perf_counter() - total_start
    logs.info(f"Fin. Tiempo total: {fmt_seconds(total_elapsed)}")
    logs.info(f"Resultados en: {results_dir}")


if __name__ == "__main__":
    main()
