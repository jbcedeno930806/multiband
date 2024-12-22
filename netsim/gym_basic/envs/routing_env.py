import gymnasium as gym
from gymnasium.spaces import MultiBinary
import numpy as np

# local imports:
from ...netSimPy.network import AllocationResult
from ...netSimPy import NetworkSimulator, Connection, Network, Link
from ...netSimPy.common.utils import get_shared_link, pairwise, get_available_blocks
from ..envs.base_env import BASE_ENV

# types:
from typing import List, Tuple, Union, Callable


class ROUTING_ENV(BASE_ENV):
    __shape = None

    def __init__(
        self,
        simulator: NetworkSimulator,
        episode_length=100,
        j=5,
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

        paths = network.paths[src, dst]
        slotsOfBand = network.getCapacityOfBand("C")
        linksState = np.zeros((self.n_paths, slotsOfBand))
        # allDemands = np.array([1, 2, 3, 4, 6, 7, 8, 11, 14, 16, 20, 27, 32, 40, 80])
        demandState = np.full((self.n_paths, len(self.allDemands)), fill_value=0)
        for idp, path in enumerate(paths[: self.n_paths]):
            linksOfPath: List[Link] = [
                network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
            ]
            linksState[idp] = [
                1 if slot is True else 0
                for slot in get_shared_link(linksOfPath, band="C")
            ]
            bestModulation = connection.bitRate.getBestModulationByBand(linksOfPath, "C")
            demand = bestModulation["slots"]
            demandPos = -1
            try:
                demandPos = self.allDemands.index(demand)
            except ValueError:
                raise ValueError("Invalid demand used for connection request")
            demandState[idp, demandPos] = 1

        linksState = linksState.reshape(self.n_paths * 344)
        demandState = demandState.reshape(self.n_paths * len(self.allDemands))
        return np.concatenate(
            (
                srcState,
                dstState,
                linksState,
                demandState,
            ),
        )

    def get_available_routes(
        self,
        c: Connection,
        network: Network,
    ):
        paths = network.paths
        band = "C"
        a_routes = []
        for idp, path in enumerate(paths[c.src, c.dst][:3]):
            linksOfPath: List[Link] = [
                network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
            ]
            bestModulation = c.bitRate.getBestModulationByBand(linksOfPath, band)
            if bestModulation is None:
                continue
            numberOfSlots = bestModulation["slots"]
            indexes, _ = get_available_blocks(
                numberOfSlots,
                linksOfPath,
                band,
            )
            if len(indexes) > 0:
                a_routes.append(idp)
        return a_routes

    def _allocator(
        self,
        c: Connection,
        network: Network,
        action: int,
    ):
        idx_block = 0
        paths = self.get_available_routes(c, network)
        if len(paths) <= action or len(paths) == 0:
            return AllocationResult.Not_Allocated, c
        selected_path = network.paths[c.src, c.dst][paths[action]]
        linksOfPath: List[Link] = [
            network.links[f"{src}-{dst}"] for src, dst in pairwise(selected_path)
        ]
        bestModulation = c.bitRate.getBestModulationByBand(linksOfPath, "C")
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
