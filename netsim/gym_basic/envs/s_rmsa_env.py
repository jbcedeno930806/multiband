import numpy as np

# local imports:
from ...netSimPy.network import AllocationResult
from ...netSimPy import NetworkSimulator, Connection, Network, Link
from ...netSimPy.common.allocators import sap_ff
from ..envs.rmsa_env_large import RMSA_ENV_LARGE
from ...netSimPy.common.utils import get_shared_link, pairwise, get_available_blocks

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

        # asignar la ruta principal usando sap_ff!!:
        route_con = Connection(connection.eventID, src, dst, connection.bitRate)
        status, c = self.sap_allocator(route_con, network, 0)
        if status != AllocationResult.Allocated:
            return super()._state(connection)
        c.protected = True  # Se usa esta variable para indicar que fue asignada
        self.simulator.getNetwork().addConnection(c)
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
        for idp, path in enumerate(paths[c.src, c.dst][:3]):
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

    # def _allocator(
    #     self,
    #     c: Connection,
    #     network: Network,
    #     action: int,
    # ) -> Tuple[AllocationResult, Connection]:
    #     idx_path, _ = self.decode_action(action)
    #     if self.routeIndexSelected is None or idx_path <= self.routeIndexSelected:
    #         return AllocationResult.Not_Allocated, c
    #     if c.protected:
    #         raise ValueError("esta conexion no debería venir asignada")
    #     self.routeIndexSelected = None
    #     return super()._allocator(c, network, action)

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
            if len(paths) > 0:
                raise ValueError(
                    "Si no se pudo asignar una ruta principal, es porque no hubo disponiilidad, y no debería haber paths disponibles"
                )
            self.routeIndexSelected = None
            return AllocationResult.Not_Allocated, c

        self.routeIndexSelected = None

        if len(paths) <= action or len(paths) == 0:
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
            self.routeIndexSelected = None
            return AllocationResult.Allocated, c
        self.routeIndexSelected = None
        return AllocationResult.Not_Allocated, c

    def reward(self, result: AllocationResult, connection: Connection):
        # if connection.routeIndex == 0:
        #     raise ValueError(
        #         "Error, el indice no deberia ser cero porque esta
        #           es la de la ruta principal"
        #     )
        if result == AllocationResult.Allocated:
            return 1
        elif connection.protected:
            return 0
        return -1
