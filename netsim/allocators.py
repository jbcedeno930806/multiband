import math
import itertools
from .netSimPy import Network, Link, Connection
from .netSimPy.network import AllocationResult
from .utils import get_available_blocks, get_shared_link
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
        for band in network.getBands():
            for path in paths[c.src, c.dst][:n_paths]:
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in itertools.pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(linksOfPath, band)
                if bestModulation is None:
                    continue
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


def sap_ff2(n_paths=3):
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
        paths = network.paths
        for band in network.getBands():
            for path in paths[c.src, c.dst][:n_paths]:
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in itertools.pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(linksOfPath, band)
                if bestModulation is None:
                    continue
                numberOfSlots = bestModulation["slots"]
                shared_link = get_shared_link(linksOfPath, band)
                index = _ff(shared_link, numberOfSlots)
                if index == -1:
                    continue
                for link in linksOfPath:
                    c.addLinkInfo(
                        link.id,
                        fromSlot=index,
                        toSlot=index + numberOfSlots,
                        band=band,
                    )
                return AllocationResult.Allocated, c
        return AllocationResult.Not_Allocated, c

    return sap_ff_func


def ldpb(n_paths=3):
    def ldpb(c: Connection, network: Network, action: int = 0):
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
        paths = network.paths
        best_idp = -1
        bestBand = None
        bestIndex = None
        numberOfSlots = -1

        percentageOfBandCapacity = math.inf
        # print("-----------------------------------")
        for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
            for band in network.getBands():
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in itertools.pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(linksOfPath, band)
                if bestModulation is not None:
                    numberOfSlots = bestModulation["slots"]
                    shared_link = get_shared_link(linksOfPath, band)
                    index = _ff(shared_link, numberOfSlots)
                    if index != -1:
                        percentage = numberOfSlots / network.getCapacityOfBand(band)
                        if percentage < percentageOfBandCapacity:
                            percentageOfBandCapacity = percentage
                            bestBand = band
                            best_idp = idp
                            bestIndex = index
        # print("-----------------------------------")
        # print("-----------------------------------")
        if bestBand is None:
            return AllocationResult.Not_Allocated, c
        path = paths[c.src, c.dst][best_idp]
        linksOfPath: List[Link] = [
            network.links[f"{src}-{dst}"] for src, dst in itertools.pairwise(path)
        ]
        bestModulation = c.bitRate.getBestModulationByBand(linksOfPath, bestBand)
        numberOfSlots = bestModulation["slots"]

        for link in linksOfPath:
            c.addLinkInfo(
                link.id,
                fromSlot=bestIndex,
                toSlot=bestIndex + numberOfSlots,
                band=bestBand,
            )
        return AllocationResult.Allocated, c

    return ldpb


def _ff(shared_link, numberOfSlots):
    longitud_actual = 0
    for i in range(len(shared_link)):
        if shared_link[i] is False:
            longitud_actual += 1
            if longitud_actual == numberOfSlots:
                return i - numberOfSlots + 1
        else:
            longitud_actual = 0
    return -1
