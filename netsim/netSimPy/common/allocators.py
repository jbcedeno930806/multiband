from .. import Network, Link, Connection
from ..network import AllocationResult
from .utils import get_available_blocks, get_shared_link, pairwise
from typing import List, Optional
import enum


def sap_ff(n_paths=3, bands: Optional[List[str]] = None):
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
        lengths = network.lengths
        analyzed_bands = bands if bands is not None else network.getBands()
        for band in analyzed_bands:
            for idp, path in enumerate(
                paths[c.src, c.dst][: min(n_paths, len(paths[c.src, c.dst]))]
            ):
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


def protected_sap_ff(n_paths=5, bands: Optional[List[str]] = None):
    sap_allocator = sap_ff(n_paths, bands)

    def protected_sap_ff_func(c: Connection, network: Network, action: int = 0):
        # crear copia de la conexión:
        route_con = Connection(c.eventID, c.src, c.dst, c.bitRate)

        # asignar la conexión principal usando sap_ff!!:
        status, c = sap_allocator(c, network, 0)
        if status != AllocationResult.Allocated:
            return AllocationResult.Not_Allocated, c
        network.addConnection(c)

        # asignar la conexión de protección usando sap_ff en ruta alterna!!:
        block = 0
        paths = network.paths
        lengths = network.lengths
        analyzed_bands = bands if bands is not None else network.getBands()
        for band in analyzed_bands:
            for idp, path in enumerate(
                paths[route_con.src, route_con.dst][
                    : min(n_paths, len(paths[route_con.src, route_con.dst]))
                ]
            ):
                if idp <= c.routeIndex:
                    continue  # asegurar ruta diferente!!
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
                ]
                bestModulation = route_con.bitRate.getBestModulationByBand(
                    linksOfPath, lengths[route_con.src, route_con.dst][idp], band
                )
                if bestModulation is None:
                    continue
                numberOfSlots = bestModulation["slots"]
                indexes, _ = get_available_blocks(
                    numberOfSlots, linksOfPath, band, block + 1
                )
                if len(indexes) > 0:
                    route_con.addRouteIndex(idp)
                    for link in linksOfPath:
                        route_con.addLinkInfo(
                            link.id,
                            fromSlot=indexes[0],
                            toSlot=indexes[0] + numberOfSlots,
                            band=band,
                            modulation=bestModulation,
                        )
                    c.protected = True
                    return AllocationResult.Allocated, c

        return AllocationResult.Allocated, c

    return protected_sap_ff_func


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
        lengths = network.lengths
        for band in network.getBands():
            for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(
                    linksOfPath, lengths[c.src, c.dst][idp], band
                )
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


def least_demand(n_paths=3):
    def ld(c: Connection, network: Network, action: int = 0):
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
        lengths = network.lengths
        allocationInfo = []

        for band in network.getBands():
            for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(
                    linksOfPath, lengths[c.src, c.dst][idp], band
                )
                if bestModulation is not None:
                    allocationInfo.append(
                        {
                            "numberOfSlots": bestModulation["slots"],
                            "band": band,
                            "linksOfPath": linksOfPath,
                            "availibility": (
                                network.getRouteAvailibility(linksOfPath, band)
                                / len(linksOfPath)
                            )
                            / network.getCapacityOfBand(band),
                            "idp": idp,
                            "modulation": bestModulation,
                        }
                    )
        sortedList = sorted(
            allocationInfo, key=lambda x: (-x["numberOfSlots"] * len(linksOfPath))
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

    return ld


def least_demand_percentage(n_paths=3):
    def ldp(c: Connection, network: Network, action: int = 0):
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
        lengths = network.lengths
        allocationInfo = []

        for band in network.getBands():
            for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(
                    linksOfPath, lengths[c.src, c.dst][idp], band
                )
                if bestModulation is not None:
                    allocationInfo.append(
                        {
                            "numberOfSlots": bestModulation["slots"],
                            "band": band,
                            "linksOfPath": linksOfPath,
                            "availibility": (
                                network.getRouteAvailibility(linksOfPath, band)
                                / len(linksOfPath)
                            )
                            / network.getCapacityOfBand(band),
                            "idp": idp,
                            "modulation": bestModulation,
                        }
                    )
        sortedList = sorted(
            allocationInfo,
            key=lambda x: (
                -x["numberOfSlots"] * len(linksOfPath) / network.getCapacityOfBand(band)
            ),
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

    return ldp


def most_available_route(n_paths=3):
    def mar(c: Connection, network: Network, action: int = 0):
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
        lengths = network.lengths
        allocationInfo = []

        for band in network.getBands():
            for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(
                    linksOfPath, lengths[c.src, c.dst][idp], band
                )
                if bestModulation is not None:
                    allocationInfo.append(
                        {
                            "numberOfSlots": bestModulation["slots"],
                            "band": band,
                            "linksOfPath": linksOfPath,
                            "availibility": network.getRouteAvailibility(
                                linksOfPath, band
                            )
                            / len(linksOfPath),
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

    return mar


def most_available_route_percentage(n_paths=3):
    def mar(c: Connection, network: Network, action: int = 0):
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
        lengths = network.lengths
        allocationInfo = []

        for band in network.getBands():
            for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(
                    linksOfPath, lengths[c.src, c.dst][idp], band
                )
                if bestModulation is not None:
                    allocationInfo.append(
                        {
                            "numberOfSlots": bestModulation["slots"],
                            "band": band,
                            "linksOfPath": linksOfPath,
                            "availibility": (
                                network.getRouteAvailibility(linksOfPath, band)
                                / len(linksOfPath)
                            )
                            / network.getCapacityOfBand(band),
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

    return mar


# TODO Probar primero este algoritmo:
def shortest_route_most_available_route(n_paths=3):
    def srmar(c: Connection, network: Network, action: int = 0):
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
        lengths = network.lengths
        allocationInfo = []

        for band in network.getBands():
            for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(
                    linksOfPath, lengths[c.src, c.dst][idp], band
                )
                if bestModulation is not None:
                    allocationInfo.append(
                        {
                            "numberOfSlots": bestModulation["slots"],
                            "band": band,
                            "linksOfPath": linksOfPath,
                            "availibility": network.getRouteAvailibility(
                                linksOfPath, band
                            )
                            / len(linksOfPath),
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

    return srmar


class Variant(enum.Enum):
    Least_Fragmentation = "Least_Fragmentation"
    Greater_Fragmentation = "Greater_Fragmentation"


# Se prioriza la ruta menos/más fragmentada y se escogen las rutas de la más
# corta a la más larga
def route_fragmentation_prioritization(
    n_paths=3, variant: Variant = Variant.Least_Fragmentation
):
    def rfp(c: Connection, network: Network, action: int = 0):
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
        lengths = network.lengths
        allocationInfo = []

        for band in network.getBands():
            for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(
                    linksOfPath, lengths[c.src, c.dst][idp], band
                )
                if bestModulation is not None:
                    allocationInfo.append(
                        {
                            "numberOfSlots": bestModulation["slots"] * len(linksOfPath),
                            "band": band,
                            "linksOfPath": linksOfPath,
                            "fragmentation": network.getRouteFragmentation(band)
                            / len(linksOfPath),
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


# TODO Luego probar este:
def route_fragmentation_porcentage(
    n_paths=3, variant: Variant = Variant.Least_Fragmentation
):
    def rfp(c: Connection, network: Network, action: int = 0):
        paths = network.paths
        lengths = network.lengths
        allocationInfo = []

        for band in network.getBands():
            for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(
                    linksOfPath, lengths[c.src, c.dst][idp], band
                )
                if bestModulation is not None:
                    allocationInfo.append(
                        {
                            "numberOfSlots": bestModulation["slots"],
                            "band": band,
                            "linksOfPath": linksOfPath,
                            "fragmentation": (
                                network.getRouteFragmentation(linksOfPath, band)
                                / len(linksOfPath)
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


def alphaBalancing(
    n_paths=3, alphas=[0.5, 1], bandsOrders=[["C", "L", "S", "E"], ["E", "S", "L", "C"]]
):
    # alpha de 0.8 significa que la banda se puede ocupar hasta un 80% de su capacidad:
    def abpa(c: Connection, network: Network, action: int = 0):
        paths = network.paths
        lengths = network.lengths
        for ida, alpha in enumerate(alphas):
            for band in bandsOrders[ida]:
                for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
                    linksOfPath: List[Link] = [
                        network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
                    ]
                    bestModulation = c.bitRate.getBestModulationByBand(
                        linksOfPath, lengths[c.src, c.dst][idp], band
                    )
                    if bestModulation is not None:
                        if alpha == 1:
                            canAllocate = True
                        else:
                            # ocupación de la banda considerando disponibilidad
                            # de la ruta ponderada:
                            bandOccupancy = network.getCapacityOfBand(
                                band
                            ) - network.getRouteAvailibility(linksOfPath, band) / len(
                                linksOfPath
                            )
                            # alpha de 0.8 significa que la banda se puede ocupar
                            # hasta un 80% de su capacidad
                            canAllocate = (
                                bandOccupancy + bestModulation["slots"]
                                <= network.getCapacityOfBand(band) * alpha
                            )
                        if canAllocate is True:
                            shared_link = get_shared_link(linksOfPath, band)
                            index = _ff(shared_link, bestModulation["slots"])
                            if index != -1:
                                c.addRouteIndex(idp)
                                for link in linksOfPath:
                                    c.addLinkInfo(
                                        link.id,
                                        fromSlot=index,
                                        toSlot=index + bestModulation["slots"],
                                        band=band,
                                        modulation=bestModulation,
                                    )
                                return AllocationResult.Allocated, c
        return AllocationResult.Not_Allocated, c

    return abpa


def bitrate_partition_allocation(
    n_paths=1, meanBitrate=100, bandsOrders=[["C", "L", "S", "E"], ["E", "L", "S", "C"]]
):
    def bpa(c: Connection, network: Network, action: int = 0):
        paths = network.paths
        lengths = network.lengths
        bitrate = c.bitRate.getBitRate()
        selectedBands = bandsOrders[1] if bitrate >= meanBitrate else bandsOrders[0]
        for band in selectedBands:
            for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
                linksOfPath: List[Link] = [
                    network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
                ]
                bestModulation = c.bitRate.getBestModulationByBand(
                    linksOfPath, lengths[c.src, c.dst][idp], band
                )
                if bestModulation is not None:
                    shared_link = get_shared_link(linksOfPath, band)
                    index = _ff(shared_link, bestModulation["slots"])
                    if index != -1:
                        c.addRouteIndex(idp)
                        for link in linksOfPath:
                            c.addLinkInfo(
                                link.id,
                                fromSlot=index,
                                toSlot=index + bestModulation["slots"],
                                band=band,
                                modulation=bestModulation,
                            )
                        return AllocationResult.Allocated, c
        return AllocationResult.Not_Allocated, c

    return bpa


def length_partition_allocation(
    n_paths=1, meanLength=100, bandsOrders=[["E", "S", "C", "L"], ["L", "C", "S", "E"]]
):
    def lpa(c: Connection, network: Network, action: int = 0):
        paths = network.paths
        lengths = network.lengths

        for idp, path in enumerate(paths[c.src, c.dst][:n_paths]):
            linksOfPath: List[Link] = [
                network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
            ]
            route_length = lengths[c.src, c.dst][idp]
            selectedBands = (
                bandsOrders[1] if route_length >= meanLength else bandsOrders[0]
            )
            for band in selectedBands:
                bestModulation = c.bitRate.getBestModulationByBand(
                    linksOfPath, lengths[c.src, c.dst][idp], band
                )
                if bestModulation is not None:
                    shared_link = get_shared_link(linksOfPath, band)
                    index = _ff(shared_link, bestModulation["slots"])
                    if index != -1:
                        c.addRouteIndex(idp)
                        for link in linksOfPath:
                            c.addLinkInfo(
                                link.id,
                                fromSlot=index,
                                toSlot=index + bestModulation["slots"],
                                band=band,
                                modulation=bestModulation,
                            )
                        return AllocationResult.Allocated, c
        return AllocationResult.Not_Allocated, c

    return lpa


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
