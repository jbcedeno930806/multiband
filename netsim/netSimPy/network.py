from .filemanager.readerJson import Reader
import json
from typing import Dict, List, Callable, Tuple, TypedDict
import sys
from .link import Link
from .connection import Connection
import enum
from .uniformVariable import UniformVariable
from .event import Event
from .bitRate import BitRate
from uuid import UUID
from .node import Node

sys.path.append("../")


class AllocationResult(enum.Enum):
    Allocated = "Allocated"
    Not_Allocated = "Not_Allocated"
    Default = "Default"


class NetworkProps(TypedDict):
    networkFileName: str
    pathsFileName: str
    bitrateFilename: str
    allocator: Callable[
        [Event, Connection, list[List[List[List[Link]]]], "Network"],
        Tuple[AllocationResult, Connection],
    ]
    seed: int


class Network:
    def __init__(
        self,
        networkFileName: str,
        pathsFileName: str,
        bitrateFilename: str = "",
        seed: int = 12345,
    ):
        self.__seed = seed
        self.__nodes, self.__links, self.__bands_capacity = Network.readNetwork(
            networkFileName
        )
        self.__paths = Network.readPathFile(pathsFileName)
        self.__bitRates = BitRate.readBitRateFile(bitrateFilename)
        self._restart()

    def _restart(self):
        self.__srcVariable = UniformVariable(self.__seed, self.getNodesCount())
        self.__dstVariable = UniformVariable(self.__seed - 1, self.getNodesCount())
        self.__bitRateVariable = UniformVariable(self.__seed, len(self.__bitRates))
        self.__connections: Dict[int, Connection] = {}

    def restart(self):
        self.resetLinks()
        self._restart()

    @staticmethod
    def readNetwork(filename) -> Tuple[Dict[str, Node], Dict[str, Link], Dict[str, int]]:
        nodes = {}
        links = {}
        bands_info = {}
        with open(filename) as file:
            info = json.load(file)
            if Reader.validateJson(info):
                for readNode in info["nodes"]:
                    nodeID = readNode["id"]
                    nodes[nodeID] = Node(nodeID)
                bands_info: dict = info["bands_info"]
                for readLink in info["links"]:
                    # id = readLink["id"]
                    src = readLink["src"]
                    dst = readLink["dst"]
                    # slots = readLink["slots"]
                    length = readLink["length"]
                    link = Link(f"{src}-{dst}", src, dst, length, bands_info)
                    links[link.id] = link
            else:
                raise ("Invalid JSON file")
        return nodes, links, bands_info

    def resetLinks(self):
        for link in self.__links.values():
            link.reset()

    @staticmethod
    def readPathFile(pathFileName) -> dict[int, list]:
        paths = {}
        with open(pathFileName) as file:
            filePaths = json.load(file)
            all_routes = filePaths["routes"]
            for r in all_routes:
                src: int = r["src"]
                dst: int = r["dst"]
                routes: list = r["paths"]
                paths[src, dst] = routes
        return paths

    def allocate(self, con: Connection) -> AllocationResult:
        for linkID in con.getConnectionInfo().keys():
            linkSlots = con.getLinkSlots(linkID)
            self.useSlots(
                linkID,
                linkSlots,
                con.getBand(linkID),
            )
        self.addConnection(con)

    def deallocate(self, con: Connection):
        for linkID in con.getConnectionInfo().keys():
            linkSlots = con.getLinkSlots(linkID)
            self.unUseSlots(
                linkID,
                linkSlots,
                con.getBand(linkID),
            )
        self.removeConnection(con)

    def addConnection(self, connection: Connection):
        self.__connections[connection.eventID] = connection

    def removeConnection(self, connection: Connection):
        del self.__connections[connection.eventID]

    def useSlots(self, linkID: str, slotsIndexes: List[int], bandSelected="NoBand"):
        self.__links[linkID].setSlots(slotsIndexes, True, bandSelected)

    def unUseSlots(self, linkID: str, slotsIndexes: List[int], bandSelected="NoBand"):
        self.__links[linkID].setSlots(slotsIndexes, False, bandSelected)

    def getNodesCount(self) -> int:
        return len(self.__nodes.keys())

    def getAllConnections(self):
        return self.__connections

    def getConnection(self, connectionID: int):
        if connectionID in self.__connections:
            return self.__connections[connectionID]
        else:
            raise KeyError(
                f"ConnectionID: {connectionID} not found in the list of connections"
            )

    def getBands(self):
        return list(self.__bands_capacity.keys())

    def getCapacityOfBands(self):
        return self.__bands_capacity

    def getBandAvailibility(self, band: str):
        return sum(link.getAvailibility(band) for link in self.links.values())

    def getRouteAvailibility(self, route: List[Link], band: str):
        return sum(link.getAvailibility(band) for link in route)

    def getBandFragmentation(self, band: str):
        return sum(link.getFragmentation(band) for link in self.links.values())

    def getRouteFragmentation(self, route: List[Link], band: str):
        return sum(link.getFragmentation(band) for link in route)

    def getCapacityOfBand(self, band: str):
        return self.__bands_capacity[band]

    def generateConnectionRequest(self, eventID: UUID):
        src = self.__srcVariable.getNextIntValue()
        dst = self.__dstVariable.getNextIntValue()
        while src == dst:
            dst = self.__dstVariable.getNextIntValue()
        requestBitRate = self.__bitRateVariable.getNextIntValue()
        bitRate = self.bitRates[requestBitRate]
        con = Connection(eventID, src, dst, bitRate)
        return con

    def _computeTransmitionNodes(self):
        src = self.__srcVariable.getNextIntValue()
        dst = self.__dstVariable.getNextIntValue()
        while src == dst:
            dst = self.__dstVariable.getNextIntValue()
        return src, dst

    @property
    def nodes(self):
        return self.__nodes

    @property
    def links(self):
        return self.__links

    @property
    def paths(self):
        return self.__paths

    @property
    def bitRates(self):
        return self.__bitRates

    @bitRates.setter
    def bitRates(self, bitrateFilename):
        self.__bitRates = BitRate().readBitRateFile(bitrateFilename)
