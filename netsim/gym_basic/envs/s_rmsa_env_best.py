import gymnasium as gym
from gymnasium.spaces import MultiBinary

import numpy as np

# local imports:
from ...netSimPy.network import AllocationResult
from ...netSimPy import NetworkSimulator, Connection, Network, Link
from ...netSimPy.common.allocators import sap_ff
from ..envs.s_base_env import S_BASE_ENV
from ...netSimPy.common.utils import pairwise, get_available_blocks, get_shared_link

# types:
from typing import Tuple, Union, Callable, List


class S_RMSA_ENV_BEST(S_BASE_ENV):
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
        self.n_paths = n_paths
        self.j = j
        self.n_paths = n_paths
        self.simulator = simulator
        numberOfNodes = self.simulator.network.getNodesCount()
        self.allDemands = [1, 2, 3, 4, 5, 6, 8, 9, 11, 15, 18, 22, 44]
        self.__shape = (
            2 * numberOfNodes + self.n_paths * 344 + self.n_paths * len(self.allDemands)
        )
        self.observation_space = MultiBinary(self.__shape)
        self.action_space_len = self.n_paths * self.j
        self.action_space = gym.spaces.Discrete(self.action_space_len)

        super().__init__(simulator, episode_length, allocator)
        self.sap_allocator = sap_ff(self.n_paths, ["C"])

    def _state231243123(self, connection: Connection):
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

    def _state(self, connection: Connection, routeIndex: int):
        network = self.simulator.network
        numberOfNodes = network.getNodesCount()
        src = connection.src
        dst = connection.dst

        srcState = np.zeros(numberOfNodes)
        dstState = np.zeros(numberOfNodes)
        srcState[src] = 1
        dstState[dst] = 1

        state = self._state231243123(connection)
        if routeIndex is None:
            return state
        slotsOfBand = network.getCapacityOfBand("C")
        start = 2 * self.simulator.network.getNodesCount()
        state[start : start + routeIndex * slotsOfBand] = [-1] * routeIndex * slotsOfBand
        max_paths = len(network.paths[src, dst])
        if max_paths < self.n_paths:
            state[
                start + (max_paths - 1) * slotsOfBand : start + max_paths * slotsOfBand
            ] = ([-1] * routeIndex * slotsOfBand)
        return state

    # def get_available_routes(
    #     self,
    #     c: Connection,
    #     network: Network,
    # ):
    #     lengths = network.lengths
    #     paths = network.paths
    #     band = "C"
    #     a_routes = []
    #     for idp, path in enumerate(
    #         paths[c.src, c.dst][: min(self.n_paths, len(paths[c.src, c.dst]))]
    #     ):
    #         linksOfPath: List[Link] = [
    #             network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
    #         ]
    #         bestModulation = c.bitRate.getBestModulationByBand(
    #             linksOfPath, lengths[c.src, c.dst][idp], band
    #         )
    #         if bestModulation is None:
    #             continue
    #         numberOfSlots = bestModulation["slots"]
    #         indexes, _ = get_available_blocks(
    #             numberOfSlots,
    #             linksOfPath,
    #             band,
    #         )
    #         if len(indexes) > 0:
    #             a_routes.append(idp)
    #     return a_routes

    def _allocator(
        self,
        c: Connection,
        network: Network,
        action: int,
    ) -> Tuple[AllocationResult, Connection]:
        idx_block = 0
        lengths = network.lengths
        # paths = self.get_available_routes(c, network)

        # if self.routeIndexSelected is None:
        #     return AllocationResult.Not_Allocated, c

        if len(network.paths[c.src, c.dst]) < action:
            return AllocationResult.Not_Allocated, c

        idx_path = action
        selected_path = network.paths[c.src, c.dst][action]
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

    def reward(self, result: AllocationResult, connection: Connection):
        if result == AllocationResult.Allocated:
            return 1
        elif connection.protected:
            return 0
        return -1
