from .filemanager.readerJson import Reader
import json
from typing import Union, Dict, List, Callable, Tuple, TypedDict
import sys
from .link import Link
from .connection import Connection
import enum
from .uniformVariable import UniformVariable
from .event import Event
from .bitRate import BitRate
from uuid import UUID

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
    slots: Union[int, Dict]
    seed: int


class Network:
    def __init__(
        self,
        networkFileName: str,
        pathsFileName: str,
        bitrateFilename: str = "",
        slots: Union[int, Dict] = {
            "NoBand": 344,
            "C": 344,
            "L": 480,
            "S": 760,
            "E": 1136,
        },
        seed: int = 12345,
    ):
        self.__seed = seed
        self.__nodes, self.__links = Network.readNetwork(networkFileName)
        self.__paths = self.readPathFile(pathsFileName)
        self.__bitRates = BitRate().readBitRateFile(bitrateFilename)
        self.__slots = slots
        self.restart()

    def restart(self):
        self.__srcVariable = UniformVariable(self.__seed, self.getNodesCount())
        self.__dstVariable = UniformVariable(self.__seed, self.getNodesCount())
        self.__bitRateVariable = UniformVariable(self.__seed, len(self.__bitRates))
        self.__connections: Dict[int, Connection] = {}
        self.resetLinks()

    @staticmethod
    def readNetwork(filename):
        # Open JSON File
        j = Reader()
        return j.readNetwork(filename)

    def resetLinks(self):
        for link in self.__links.values():
            link.reset(self.__slots)

    def readPathFile(self, pathFileName) -> list[List[List[List[str]]]]:
        with open(pathFileName) as json_file:
            filePaths = json.load(json_file)
        numberOfNodes = len(self.__nodes)
        paths: List[List[List[List[Link]]]] = []
        # initializing paths as paths[src][dst]
        for i in range(0, numberOfNodes):
            paths.append([])
            for j in range(0, numberOfNodes):
                paths[i].append([])

        routesNumber = len(filePaths["routes"])
        for i in range(0, routesNumber):
            src: int = filePaths["routes"][i]["src"]
            dst: int = filePaths["routes"][i]["dst"]
            pathsCount = len(filePaths["routes"][i]["paths"])

            for j in range(0, pathsCount):
                paths[src][dst].append([])
            for j in range(0, pathsCount):
                nodesPathNumber = len(filePaths["routes"][i]["paths"][j])
                lastNode = nodesPathNumber - 1
                for k in range(0, lastNode):
                    actNode = filePaths["routes"][i]["paths"][j][k]
                    nextNode = filePaths["routes"][i]["paths"][j][k + 1]
                    paths[src][dst][j].append(f"{actNode}-{nextNode}")

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
        link = self.__links[linkID]
        for slotIndex in slotsIndexes:
            if link.getSlotValue(slotIndex, bandSelected):
                raise ValueError(
                    "Slot {} is already in use for link id {} and band {}".format(
                        slotIndex, linkID, bandSelected
                    )
                )
        link.setSlots(slotsIndexes, True, bandSelected)

    def unUseSlots(self, linkID: str, slotsIndexes: List[int], bandSelected="NoBand"):
        link = self.__links[linkID]
        link.setSlots(slotsIndexes, False, bandSelected)

    def getNodesCount(self) -> int:
        return len(self.__nodes.keys())

    def getConnection(self, connectionID: int):
        return self.__connections[connectionID]

    def generateConnectionRequest(self, eventID: UUID):
        src = self.__srcVariable.getNextIntValue()
        dst = self.__dstVariable.getNextIntValue()
        while src == dst:
            dst = self.__dstVariable.getNextIntValue()
        requestBitRate = self.__bitRateVariable.getNextIntValue()
        bitRate = self.bitRates[requestBitRate]
        con = Connection(eventID, src, dst, bitRate)
        self.addConnection(con)
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
