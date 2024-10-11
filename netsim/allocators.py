from .netSimPy import Network, Link, Connection
from .netSimPy.network import AllocationResult
from .utils import get_available_blocks
from typing import List
import numpy as np
from .gym_basic.envs import RMSA_ENV


def sap_ff(n_paths=3):
    def sap_ff_func(c: Connection, network: Network, action: int):
        """_summary_

        Args:
            c (Connection): _description_
            paths (list[List[List[List[Link]]]]): Esta variable contiene una lista de
            rutas de la forma: ruta(index) = paths[src][dst][index], cada ruta contiene una lista de id de enlaces.
            network (Network): _description_

        Returns:
            _type_: _description_
        """
        block = 0
        paths = network.paths
        for path in paths[c.src][c.dst][:n_paths]:
            linksOfPath: List[Link] = [network.links[linkID] for linkID in path]
            numberOfSlots = c.bitRate.getBestModulationNumberOfSlots(linksOfPath)
            indexes, _ = get_available_blocks(c.bitRate, linksOfPath, block + 1)
            if len(indexes) > 0:
                for link in linksOfPath:
                    c.addLinkInfo(
                        link.id,
                        fromSlot=indexes[0],
                        toSlot=indexes[0] + numberOfSlots,
                    )
                return AllocationResult.Allocated, c
        return AllocationResult.Not_Allocated, c

    return sap_ff_func


def heuristic_sap_ff(env: RMSA_ENV):
    def func(observations: np.ndarray) -> np.ndarray:
        actions = []
        n_paths = env.n_paths
        sim = env.getSimulator()
        numberOfNodes = sim.controller.network.getNumberOfNodes()
        j = env.j
        offset = 2 * numberOfNodes
        for obs in observations:
            for idp in range(n_paths):
                if obs[offset + idp * (2 * j + 3)] != 344:
                    actions.append(idp * j)
                    break
                elif idp == n_paths - 1:
                    actions.append(n_paths * j)
        final_actions = np.array(actions)
        return final_actions

    return func
