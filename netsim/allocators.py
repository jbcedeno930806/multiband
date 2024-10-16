import math
# import itertools
from .netSimPy import Network, Link, Connection
from .netSimPy.network import AllocationResult
from .utils import get_available_blocks, get_shared_link, pairwise
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
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
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
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
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
        bandsAndAvailibility = []

        for band in network.getBands():
            for idr, path in enumerate(paths[c.src, c.dst][:n_paths]):
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(linksOfPath, band)
                if bestModulation is not None:
                    bandsAndAvailibility.append({
                        "numberOfSlots": bestModulation["slots"],
                        "band":band,
                        "linksOfPath":linksOfPath,
                        "availibility":network.getBandAvailibility(band)
                    })
        sortedList = sorted(
            bandsAndAvailibility,
            key=lambda x:(-x['availibility'], x['numberOfSlots'])
        )

        for info in sortedList:
            shared_link = get_shared_link(info["linksOfPath"], info["band"])
            index = _ff(shared_link, info["numberOfSlots"])
            if index != -1:
                for link in info["linksOfPath"]:
                    c.addLinkInfo(
                        link.id,
                        fromSlot=index,
                        toSlot=index + info["numberOfSlots"],
                        band=info['band'],
                    )
                return AllocationResult.Allocated, c
        return AllocationResult.Not_Allocated, c

    return ldpb


# Cambiar para priorizar primero la ruta y luego la banda, similar al alg de arriba:
# Probar priorizar bandas basado en la banda de menor/mayor fragmentación

def ldpb2(n_paths=3):
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
        bandsAndAvailibility = []

        for band in network.getBands():
            for idr, path in enumerate(paths[c.src, c.dst][:n_paths]):
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(linksOfPath, band)
                if bestModulation is not None:
                    bandsAndAvailibility.append({
                        "numberOfSlots": bestModulation["slots"],
                        "band":band,
                        "linksOfPath":linksOfPath,
                        "availibility":network.getBandAvailibility(band)
                    })
        sortedList = sorted(
            bandsAndAvailibility,
            key=lambda x:(x['numberOfSlots'], -x['availibility'])
        )

        for info in sortedList:
            shared_link = get_shared_link(info["linksOfPath"], info["band"])
            index = _ff(shared_link, info["numberOfSlots"])
            if index != -1:
                for link in info["linksOfPath"]:
                    c.addLinkInfo(
                        link.id,
                        fromSlot=index,
                        toSlot=index + info["numberOfSlots"],
                        band=info['band'],
                    )
                return AllocationResult.Allocated, c
        return AllocationResult.Not_Allocated, c


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
