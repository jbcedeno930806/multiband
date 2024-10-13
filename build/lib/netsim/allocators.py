from .netSimPy import Network, Link, Connection
from .netSimPy.network import AllocationResult
from .utils import get_available_blocks
from typing import List


def sap_ff(n_paths=3):
    def sap_ff_func(c: Connection, network: Network, action: int = 0):
        """_summary_

        Args:
            c (Connection): _description_
            paths (list[List[List[List[Link]]]]): Esta variable contiene una lista de
            rutas de la forma: ruta(index) = paths[src, dst][index],
            cada ruta contiene una lista de id de enlaces.
            network (Network): _description_

        Returns:
            _type_: _description_
        """
        block = 0
        paths = network.paths
        # TODO: Corregir esto que está en duro:
        for band in ["C", "L", "S", "E"]:
            for path in paths[c.src, c.dst][:n_paths]:
                linksOfPath: List[Link] = [network.links[linkID] for linkID in path]
                bestModulation = c.bitRate.getBestModulationByBand(linksOfPath, band)
                if bestModulation is None:
                    return AllocationResult.Allocated, c
                numberOfSlots = bestModulation["slots"]
                indexes, _ = get_available_blocks(
                    numberOfSlots, linksOfPath, band, block + 1
                )
                if len(indexes) > 0:
                    for link in linksOfPath:
                        c.addLinkInfo(
                            link.id,
                            fromSlot=indexes[0],
                            toSlot=indexes[0] + numberOfSlots,
                            band=band,
                        )
                    return AllocationResult.Allocated, c
        return AllocationResult.Not_Allocated, c

    return sap_ff_func
