import gymnasium as gym
from gymnasium.spaces import MultiBinary
import numpy as np

# local imports:
from ...netSimPy.network import AllocationResult
from ...netSimPy import NetworkSimulator, Connection, Network, Link
from ...netSimPy.common.utils import get_shared_link, pairwise, get_available_blocks
from .base_env import BASE_ENV

# types:
from typing import List, Tuple, Union, Callable


class RMSA_ENV_LARGE(BASE_ENV):
    __shape = None

    def __init__(
        self,
        simulator: NetworkSimulator,
        episode_length=100,
        j: int = 5,
        n_paths=3,
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
        self.allDemands = [1, 2, 3, 4, 5, 6, 8, 9, 11, 15, 18, 22, 44]
        self.__shape = (
            2 * numberOfNodes + self.n_paths * 344 + self.n_paths * len(self.allDemands)
        )
        self.observation_space = MultiBinary(self.__shape)
        self.action_space_len = self.n_paths * self.j
        self.action_space = gym.spaces.Discrete(self.action_space_len)

    def _state(self, connection: Connection):
        network = self.simulator.network
        numberOfNodes = network.getNodesCount()

        # Source state
        src = connection.src
        dst = connection.dst
        srcState = np.zeros(numberOfNodes)
        dstState = np.zeros(numberOfNodes)
        srcState[src] = 1
        dstState[dst] = 1
        lengths = network.lengths

        paths = network.paths[src, dst]
        slotsOfBand = network.getCapacityOfBand("C")
        linksState = np.full((self.n_paths, slotsOfBand), fill_value=-1)
        # allDemands = np.array([1, 2, 3, 4, 6, 7, 8, 11, 14, 16, 20, 27, 32, 40, 80])
        demandState = np.full((self.n_paths, len(self.allDemands)), fill_value=0)
        for idp, path in enumerate(paths[: self.n_paths]):
            linksOfPath: List[Link] = [
                network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
            ]
            linksState[idp] = [
                1 if slot is True else -1
                for slot in get_shared_link(linksOfPath, band="C")
            ]
            bestModulation = connection.bitRate.getBestModulationByBand(
                linksOfPath, lengths[src, dst][idp], "C"
            )
            demand = bestModulation["slots"]
            demandPos = -1
            try:
                demandPos = self.allDemands.index(demand)
            except ValueError:
                raise ValueError("Invalid demand used for connection request")
            demandState[idp, demandPos] = 1

        linksState = linksState.reshape(self.n_paths * slotsOfBand)
        demandState = demandState.reshape(self.n_paths * len(self.allDemands))
        return np.concatenate(
            (srcState, dstState, linksState, demandState),
        )

    def _allocator(
        self,
        c: Connection,
        network: Network,
        action: int,
    ) -> Tuple[AllocationResult, Connection]:
        lengths = network.lengths
        if action == self.n_paths * self.j:
            return AllocationResult.Not_Allocated, c
        else:
            # get the route and block
            idx_path, idx_block = self.decode_action(action)
            paths = self.simulator.network.paths[c.src, c.dst]
            selected_path = paths[idx_path]

            linksOfPath: List[Link] = [
                network.links[f"{src}-{dst}"] for src, dst in pairwise(selected_path)
            ]
            bestModulation = c.bitRate.getBestModulationByBand(
                linksOfPath, lengths[c.src, c.dst][idx_path], "C"
            )
            numberOfSlots = bestModulation["slots"]
            initial_indices, _lengths = get_available_blocks(
                numberOfSlots,
                linksOfPath,
                "C",
            )
            if len(initial_indices) > idx_block:
                ff_index = initial_indices[idx_block]
                for link in linksOfPath:
                    c.addLinkInfo(
                        link.id,
                        fromSlot=ff_index,
                        toSlot=ff_index + numberOfSlots,
                        band="C",
                        modulation=bestModulation,
                    )
                return AllocationResult.Allocated, c
        return AllocationResult.Not_Allocated, c

    def decode_action(self, act: int) -> tuple[int, int]:
        idx_path: int = act // self.j
        idx_block: int = act % self.j
        return idx_path, idx_block
