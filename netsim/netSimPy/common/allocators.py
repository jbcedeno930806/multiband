from .. import Network, Link, Connection
from ..network import AllocationResult
from .utils import get_available_blocks, get_shared_link, pairwise
from typing import List
import enum


def sap_ff(n_paths=3):
    def sap_ff_func(c: Connection, network: Network, action: int = 0):
        """Versión de first-fit usada en aprendizaje reforzado, donde te da los bloques

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
            for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
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
                    c.addRouteIndex(idp)
                    for link in linksOfPath:
                        c.addLinkInfo(
                            link.id,
                            fromSlot=indexes[0],
                            toSlot=indexes[0] + numberOfSlots,
                            band=band,
                            modulation=bestModulation,
                        )
                    return AllocationResult.Allocated, c
        return AllocationResult.Not_Allocated, c

    return sap_ff_func


def sap_ff2(n_paths=3):
    def sap_ff_func(c: Connection, network: Network, action: int = 0):
        """Versión clásica del first-fit en multibanda, sin ningún cambio adicional.
        Se intenta en todas lasa rutas de la primera banda, luego todas las rutas de
        la segunda banda, y así suc.

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
            for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
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
                c.addRouteIndex(idp)
                for link in linksOfPath:
                    c.addLinkInfo(
                        link.id,
                        fromSlot=index,
                        toSlot=index + numberOfSlots,
                        band=band,
                        modulation=bestModulation,
                    )
                return AllocationResult.Allocated, c
        return AllocationResult.Not_Allocated, c

    return sap_ff_func


def most_available_band_all_routes(n_paths=3):
    def mabar(c: Connection, network: Network, action: int = 0):
        """Este algoritmo prioriza la banda más dispobible e intenta asignar en
        alguna de las rutas posibles, luego la segunda banda más disponible e
        intenta asignar usando las rutas posibles, y así sucesivamente.

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
        allocationInfo = []

        for band in network.getBands():
            for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(linksOfPath, band)
                if bestModulation is not None:
                    allocationInfo.append(
                        {
                            "numberOfSlots": bestModulation["slots"],
                            "band": band,
                            "linksOfPath": linksOfPath,
                            "availibility": network.getBandAvailibility(band),
                            "idp": idp,
                            "modulation": bestModulation,
                        }
                    )
        sortedList = sorted(
            allocationInfo, key=lambda x: (-x["availibility"], x["numberOfSlots"])
        )

        for info in sortedList:
            shared_link = get_shared_link(info["linksOfPath"], info["band"])
            index = _ff(shared_link, info["numberOfSlots"])
            if index != -1:
                c.addRouteIndex(info["idp"])
                for link in info["linksOfPath"]:
                    c.addLinkInfo(
                        link.id,
                        fromSlot=index,
                        toSlot=index + info["numberOfSlots"],
                        band=info["band"],
                        modulation=info["modulation"],
                    )
                return AllocationResult.Allocated, c
        return AllocationResult.Not_Allocated, c

    return mabar


# Cambiar para priorizar primero la ruta y luego la banda, similar al alg de arriba:
# Probar priorizar bandas basado en la banda de menor/mayor fragmentación


def shortest_route_most_available_band(n_paths=3):
    def srmab(c: Connection, network: Network, action: int = 0):
        """Este algoritmo prioriza la ruta más corta y selecciona la banda más disponible,
        luego la segunda ruta más corta y la banda más disponible, y así sucesivamente

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
        allocationInfo = []

        for band in network.getBands():
            for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(linksOfPath, band)
                if bestModulation is not None:
                    allocationInfo.append(
                        {
                            "numberOfSlots": bestModulation["slots"],
                            "band": band,
                            "linksOfPath": linksOfPath,
                            "availibility": network.getBandAvailibility(band),
                            "idp": idp,
                            "modulation": bestModulation,
                        }
                    )
        sortedList = sorted(allocationInfo, key=lambda x: (x["idp"], -x["availibility"]))

        for info in sortedList:
            shared_link = get_shared_link(info["linksOfPath"], info["band"])
            index = _ff(shared_link, info["numberOfSlots"])
            if index != -1:
                c.addRouteIndex(info["idp"])
                for link in info["linksOfPath"]:
                    c.addLinkInfo(
                        link.id,
                        fromSlot=index,
                        toSlot=index + info["numberOfSlots"],
                        band=info["band"],
                        modulation=info["modulation"],
                    )
                return AllocationResult.Allocated, c
        return AllocationResult.Not_Allocated, c

    return srmab


class Variant(enum.Enum):
    Least_Fragmentation = "Least_Fragmentation"
    Greater_Fragmentation = "Greater_Fragmentation"


def least_fragmentation_band_prioritization(
    n_paths=3, variant: Variant = Variant.Greater_Fragmentation
):
    def lfbp(c: Connection, network: Network, action: int = 0):
        """Este algoritmo prioriza la banda con menor/mayor fragmentación e intenta
        asignar usando todas las rutas de la más corta a la más larga

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
        allocationInfo = []

        for band in network.getBands():
            for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(linksOfPath, band)
                if bestModulation is not None:
                    allocationInfo.append(
                        {
                            "numberOfSlots": bestModulation["slots"],
                            "band": band,
                            "linksOfPath": linksOfPath,
                            "fragmentation": network.getBandFragmentation(band),
                            "idp": idp,
                            "modulation": bestModulation,
                        }
                    )
        if variant is Variant.Least_Fragmentation:
            callback = lambda x: (x["fragmentation"], x["numberOfSlots"])
        else:
            callback = lambda x: (-x["fragmentation"], x["numberOfSlots"])
        sortedList = sorted(allocationInfo, key=callback)

        for info in sortedList:
            shared_link = get_shared_link(info["linksOfPath"], info["band"])
            index = _ff(shared_link, info["numberOfSlots"])
            if index != -1:
                c.addRouteIndex(info["idp"])
                for link in info["linksOfPath"]:
                    c.addLinkInfo(
                        link.id,
                        fromSlot=index,
                        toSlot=index + info["numberOfSlots"],
                        band=info["band"],
                        modulation=info["modulation"],
                    )
                return AllocationResult.Allocated, c
        return AllocationResult.Not_Allocated, c

    return lfbp


def band_fragmentation_porcentage(
    n_paths=3, variant: Variant = Variant.Greater_Fragmentation
):
    def bfp(c: Connection, network: Network, action: int = 0):
        paths = network.paths
        allocationInfo = []

        for band in network.getBands():
            for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(linksOfPath, band)
                if bestModulation is not None:
                    allocationInfo.append(
                        {
                            "numberOfSlots": bestModulation["slots"],
                            "band": band,
                            "linksOfPath": linksOfPath,
                            "fragmentation": network.getBandFragmentation(band)
                            / network.getCapacityOfBand(band),
                            "idp": idp,
                            "modulation": bestModulation,
                        }
                    )
        if variant is Variant.Least_Fragmentation:
            callback = lambda x: (x["fragmentation"], x["numberOfSlots"])
        else:
            callback = lambda x: (-x["fragmentation"], x["numberOfSlots"])
        sortedList = sorted(allocationInfo, key=callback)

        for info in sortedList:
            shared_link = get_shared_link(info["linksOfPath"], info["band"])
            index = _ff(shared_link, info["numberOfSlots"])
            if index != -1:
                c.addRouteIndex(info["idp"])
                for link in info["linksOfPath"]:
                    c.addLinkInfo(
                        link.id,
                        fromSlot=index,
                        toSlot=index + info["numberOfSlots"],
                        band=info["band"],
                        modulation=info["modulation"],
                    )
                return AllocationResult.Allocated, c
        return AllocationResult.Not_Allocated, c

    return bfp


def route_fragmentation_porcentage(
    n_paths=3, variant: Variant = Variant.Greater_Fragmentation
):
    def rfp(c: Connection, network: Network, action: int = 0):
        paths = network.paths
        allocationInfo = []

        for band in network.getBands():
            for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(linksOfPath, band)
                if bestModulation is not None:
                    allocationInfo.append(
                        {
                            "numberOfSlots": bestModulation["slots"],
                            "band": band,
                            "linksOfPath": linksOfPath,
                            "fragmentation": network.getRouteFragmentation(
                                linksOfPath, band
                            )
                            / network.getCapacityOfBand(band),
                            "idp": idp,
                            "modulation": bestModulation,
                        }
                    )
        if variant is Variant.Least_Fragmentation:
            callback = lambda x: (x["fragmentation"], x["numberOfSlots"])
        else:
            callback = lambda x: (-x["fragmentation"], x["numberOfSlots"])
        sortedList = sorted(allocationInfo, key=callback)

        for info in sortedList:
            shared_link = get_shared_link(info["linksOfPath"], info["band"])
            index = _ff(shared_link, info["numberOfSlots"])
            if index != -1:
                c.addRouteIndex(info["idp"])
                for link in info["linksOfPath"]:
                    c.addLinkInfo(
                        link.id,
                        fromSlot=index,
                        toSlot=index + info["numberOfSlots"],
                        band=info["band"],
                        modulation=info["modulation"],
                    )
                return AllocationResult.Allocated, c
        return AllocationResult.Not_Allocated, c

    return rfp


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
