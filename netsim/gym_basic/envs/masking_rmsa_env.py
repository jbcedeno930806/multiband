from ...netSimPy.network import AllocationResult
from ...netSimPy import NetworkSimulator, Connection, Network, Link
from .rmsa_env import RMSA_ENV
from ...netSimPy.common.utils import pairwise, get_available_blocks
import numpy as np

# types:
from typing import Tuple, Union, Callable, List


class MASKING_RMSA_ENV(RMSA_ENV):
    def __init__(
        self,
        simulator: NetworkSimulator,
        episode_length=100,
        j: int = 1,
        n_paths=5,
        allocator: Union[
            Callable[
                [Connection, Network, int],
                Tuple[AllocationResult, Connection],
            ],
            None,
        ] = None,
        use_first_fit_masking=False,
    ):
        super().__init__(simulator, episode_length, j, n_paths, allocator)
        self._mask = None

    def _state(self, connection: Connection):
        network = self.simulator.network
        numberOfNodes = network.getNodesCount()
        self._mask = [0] * self.n_paths * self.j

        # Source state
        src = connection.src
        dst = connection.dst
        srcState = np.zeros(numberOfNodes)
        dstState = np.zeros(numberOfNodes)
        srcState[src] = 1
        dstState[dst] = 1
        lengths = network.lengths
        paths = network.paths[src, dst]

        routesState = np.full((self.n_paths, self.j * 2 + 3), fill_value=-1)
        for idp, path in enumerate(paths[: self.n_paths]):
            linksOfPath: List[Link] = [
                network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
            ]
            bestModulation = connection.bitRate.getBestModulationByBand(
                linksOfPath, lengths[src, dst][idp], "C"
            )
            demand = bestModulation["slots"]
            _indexes, _lengths = get_available_blocks(demand, linksOfPath, "C")

            for i in range(min(self.j, len(_indexes))):
                self._mask[idp * self.j + i] = 1
                routesState[idp, 2 * i] = _indexes[i]
                routesState[idp, 2 * i + 1] = _lengths[i]
            routesState[idp, 2 * self.j] = demand
            routesState[idp, 2 * self.j + 1] = (
                self.simulator.network.getRouteAvailibility(linksOfPath, "C")
            )
            if len(_lengths) > 0:
                routesState[idp, 2 * self.j + 2] = sum(_lengths) / len(_lengths)
        _state = routesState.reshape(self.n_paths * (self.j * 2 + 3))
        return np.concatenate(
            (srcState, dstState, _state),
        )

    def action_masks(self):
        return self._mask
