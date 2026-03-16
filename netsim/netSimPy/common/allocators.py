from .. import Network, Link, Connection
from ..network import AllocationResult
from .utils import get_available_blocks, get_shared_link, pairwise
from typing import List, Optional
import enum


def sap_ff(n_paths=3, bands: Optional[List[str]] = None):
    """Crea un asignador first-fit orientado a RL.

    Devuelve una funcion allocator que intenta asignar en la primera ruta
    disponible y usa bloques continuos con get_available_blocks.
    """
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
        # analyzed_bands = bands if bands is not None else network.getBands()
        analyzed_bands = ["C"]
        # print("analyzed_bands", analyzed_bands)
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
    """Crea un asignador con proteccion simple usando sap_ff.

    Primero asigna la conexion principal con sap_ff y luego intenta una
    conexion de respaldo en una ruta distinta. Marca c.protected si logra
    la segunda asignacion.
    """
    sap_allocator = sap_ff(n_paths, bands)
    # TODO: Corregir!!!! para que agregue el evento y la conexion a la red

    def protected_sap_ff_func(c: Connection, network: Network, action: int = 0):
        # Existe disponibilidad para la conexión principal usando sap_ff??:
        status, c = sap_allocator(c, network, 0)
        if status != AllocationResult.Allocated:
            # No existe disponibilidad:
            return AllocationResult.Not_Allocated, c
        network.allocate(c)
        # Intentar asignar la conexión de respaldo usando sap_ff en ruta alterna!!:
        block = 0
        paths = network.paths
        lengths = network.lengths
        analyzed_bands = bands if bands is not None else network.getBands()
        # crear copia de la conexión:
        route_con = Connection(c.eventID, c.src, c.dst, c.bitRate)
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
                    return AllocationResult.Allocated, route_con
        return AllocationResult.Allocated, route_con

    return protected_sap_ff_func


def one_plus_one():
    """Crea un asignador 1+1 simplificado.

    Intenta asignar una conexion principal y una copia usando la misma
    ruta base (idp=0) y banda C. Considera exito si cualquiera asigna.
    """
    def _allocate(network: Network, con: Connection, idp=0, band="C"):
        block = 0
        paths = network.paths[con.src, con.dst]
        lengths = network.lengths

        linksOfPath: List[Link] = [
            network.links[f"{src}-{dst}"] for src, dst in pairwise(paths[idp])
        ]
        bestModulation = con.bitRate.getBestModulationByBand(
            linksOfPath, lengths[con.src, con.dst][idp], band
        )
        if bestModulation is None:
            return AllocationResult.Not_Allocated, con

        numberOfSlots = bestModulation["slots"]
        indexes, _ = get_available_blocks(numberOfSlots, linksOfPath, band, block + 1)
        if len(indexes) > 0:
            con.addRouteIndex(idp)
            for link in linksOfPath:
                con.addLinkInfo(
                    link.id,
                    fromSlot=indexes[0],
                    toSlot=indexes[0] + numberOfSlots,
                    band=band,
                    modulation=bestModulation,
                )
            return AllocationResult.Allocated, con
        return AllocationResult.Not_Allocated, con

    def one_plus_one_func(c: Connection, network: Network, action: int = 0):
        status, c = _allocate(network, c, idp=0)
        if status == AllocationResult.Allocated:
            network.allocate(c)

        # crear copia de la conexión e intentar asignarla:
        route_con = Connection(c.eventID, c.src, c.dst, c.bitRate)
        status2, route_con = _allocate(network, route_con, idp=0)

        if status2 == AllocationResult.Allocated or status == AllocationResult.Allocated:
            return AllocationResult.Allocated, route_con
        return AllocationResult.Not_Allocated, route_con

    return one_plus_one_func


def sap_ff2(n_paths=3, bands: Optional[List[str]] = None):
    """Crea un asignador first-fit clasico multibanda.

    Recorre bandas y rutas en orden, usando first-fit sobre el enlace
    compartido para seleccionar el primer bloque valido.
    """
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
    """Crea un asignador que minimiza demanda por banda (valor absoluto).

    Ordena candidatos por menor demanda agregada y asigna el primer bloque
    valido entre rutas y bandas.
    """
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
    """Crea un asignador que minimiza demanda por banda (porcentaje).

    Similar a least_demand, pero normaliza por la capacidad total de banda.
    """
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
    """Crea un asignador que prioriza disponibilidad de ruta.

    Calcula disponibilidad promedio por ruta y banda, y selecciona la mejor
    combinacion antes de aplicar first-fit.
    """
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


def most_available_band_all_routes(n_paths=3):
    """Crea un asignador que prioriza disponibilidad global de banda.

    Ordena por disponibilidad total de banda y luego intenta asignar en
    cualquiera de las rutas disponibles.
    """
    def mabar(c: Connection, network: Network, action: int = 0):
        """Este algoritmo prioriza la banda mas disponible (global) e intenta asignar en
        alguna de las rutas posibles, luego la segunda banda mas disponible, y asi sucesivamente.

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


def most_available_route_percentage(n_paths=3):
    """Crea un asignador que prioriza disponibilidad de ruta (porcentaje).

    Usa disponibilidad normalizada por capacidad de banda para ordenar
    candidatos.
    """
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
    """Crea un asignador que prioriza rutas cortas y disponibilidad.

    Ordena por indice de ruta (corta a larga) y luego por disponibilidad
    dentro de cada ruta.
    """
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


def least_fragmentation_band_prioritization(
    n_paths=3, variant: Variant = Variant.Least_Fragmentation
):
    """Crea un asignador que prioriza la fragmentacion de banda.

    Si variant es Least_Fragmentation, intenta primero bandas con menor
    fragmentacion; si no, prioriza mayor fragmentacion.
    """
    def lfbp(c: Connection, network: Network, action: int = 0):
        """Este algoritmo prioriza la banda con menor/mayor fragmentacion e intenta
        asignar usando todas las rutas de la mas corta a la mas larga

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


# Se prioriza la ruta menos/más fragmentada y se escogen las rutas de la más
# corta a la más larga
def route_fragmentation_prioritization(
    n_paths=3, variant: Variant = Variant.Least_Fragmentation
):
    """Crea un asignador que prioriza la fragmentacion de ruta.

    Calcula la fragmentacion sobre los enlaces de la ruta y ordena segun
    el variant antes de aplicar first-fit.
    """
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
                            "fragmentation": network.getRouteFragmentation(
                                linksOfPath, band
                            )
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
    """Crea un asignador por fragmentacion de ruta (porcentaje).

    Variante experimental que usa fragmentacion normalizada.
    """
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
    """Crea un asignador por balanceo de ocupacion (alpha).

    Para cada alpha y orden de bandas, limita la ocupacion maxima de cada
    banda y aplica first-fit si la ocupacion cumple el umbral.
    """
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
    """Crea un asignador por particion de bitrate.

    Si el bitrate es mayor o igual al promedio, usa el segundo orden de
    bandas; si no, usa el primero.
    """
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
    """Crea un asignador por particion de longitud de ruta.

    Si la longitud de ruta es mayor o igual al promedio, usa el segundo
    orden de bandas; si no, usa el primero.
    """
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
    """Devuelve el primer indice de un bloque contiguo libre.

    shared_link es una lista booleana de ocupacion. Retorna -1 si no hay
    bloque disponible con el tamano requerido.
    """
    longitud_actual = 0
    for i in range(len(shared_link)):
        if shared_link[i] is False:
            longitud_actual += 1
            if longitud_actual == numberOfSlots:
                return i - numberOfSlots + 1
        else:
            longitud_actual = 0
    return -1
