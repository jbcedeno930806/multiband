import numpy as np

# local imports:
from ...netSimPy.network import AllocationResult
from ...netSimPy import NetworkSimulator, Connection, Network, Link, EventType
from ...netSimPy.common.allocators import sap_ff
from ..envs.rmsa_env_large import RMSA_ENV_LARGE
from ...netSimPy.common.utils import pairwise, get_available_blocks

# types:
from typing import Tuple, Union, Callable, List


class S_RMSA_ENV(RMSA_ENV_LARGE):
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
        super().__init__(simulator, episode_length, j, n_paths, allocator)
        self.sap_allocator = sap_ff(self.n_paths, ["C"])
        self.routeIndexSelected = None

    def _state(self, connection: Connection):
        network = self.simulator.network
        numberOfNodes = network.getNodesCount()
        src = connection.src
        dst = connection.dst

        self.routeIndexSelected = None
        # asignar la ruta principal usando sap_ff!!:
        c = Connection(connection.eventID, src, dst, connection.bitRate)
        status, c = self.sap_allocator(c, network, 0)
        if status != AllocationResult.Allocated:
            return super()._state(connection)
        # Se usa esta variable para indicar si alguna conexion fue asignada
        connection.protected = True
        self.simulator.getNetwork().allocate(c)
        self.routeIndexSelected = c.routeIndex
        # Componer el nuevo estado del agente:
        srcState = np.zeros(numberOfNodes)
        dstState = np.zeros(numberOfNodes)
        srcState[src] = 1
        dstState[dst] = 1

        state = super()._state(connection)
        slotsOfBand = network.getCapacityOfBand("C")
        start = 2 * self.simulator.network.getNodesCount()
        state[start : start + c.routeIndex * slotsOfBand] = (
            [-1] * c.routeIndex * slotsOfBand
        )
        max_paths = len(network.paths[src, dst])
        if max_paths < self.n_paths:
            state[
                start + (max_paths - 1) * slotsOfBand : start + max_paths * slotsOfBand
            ] = ([-1] * c.routeIndex * slotsOfBand)
        return state

    def get_available_routes(
        self,
        c: Connection,
        network: Network,
    ):
        lengths = network.lengths
        paths = network.paths
        band = "C"
        a_routes = []
        for idp, path in enumerate(
            paths[c.src, c.dst][: min(self.n_paths, len(paths[c.src, c.dst]))]
        ):
            if self.routeIndexSelected is None:
                return []
            if idp <= self.routeIndexSelected:
                # No se puede usar la misma ruta que la asignada previamente
                continue
            linksOfPath: List[Link] = [
                network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
            ]
            bestModulation = c.bitRate.getBestModulationByBand(
                linksOfPath, lengths[c.src, c.dst][idp], band
            )
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
    ) -> Tuple[AllocationResult, Connection]:
        idx_block = 0
        lengths = network.lengths
        paths = self.get_available_routes(c, network)

        if self.routeIndexSelected is None:
            return AllocationResult.Not_Allocated, c

        if len(paths) <= action or len(paths) == 0:
            self.event.setType(EventType.Departure)
            self.simulator.eventsGenerator.appendEvent(self.event)
            return AllocationResult.Not_Allocated, c

        idx_path = paths[action]
        selected_path = network.paths[c.src, c.dst][idx_path]
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
        self.event.setType(EventType.Departure)
        self.simulator.eventsGenerator.appendEvent(self.event)
        return AllocationResult.Not_Allocated, c

    def reward(self, result: AllocationResult, connection: Connection):
        if result == AllocationResult.Allocated:
            return 1
        elif connection.protected:
            return 0
        return -1
