import gymnasium as gym
from gymnasium.spaces import MultiBinary
import numpy as np

# local imports:
from ...netSimPy.network import AllocationResult
from ...netSimPy import NetworkSimulator, Connection, Network, Link
from ...netSimPy.common.utils import pairwise, get_available_blocks
from ..envs.rmsa_env import RMSA_ENV

# types:
from typing import List, Tuple, Union, Callable


class SMSA_ENV(RMSA_ENV):
    __shape = None

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
    ):
        super().__init__(simulator, episode_length, allocator)
        self.j = j
        self.n_paths = n_paths
        numberOfNodes = self.simulator.network.getNodesCount()
        self.__shape = 2 * numberOfNodes + self.n_paths * (self.j * 2 + 3)
        self.observation_space = MultiBinary(self.__shape)
        self.action_space_len = self.n_paths * self.j
        self.action_space = gym.spaces.Discrete(self.action_space_len)

    def _state(self, connection: Connection):
        network = self.simulator.network
        numberOfNodes = network.getNodesCount()

        # asignar antes que todo la ruta principal calculada con first fit:

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
