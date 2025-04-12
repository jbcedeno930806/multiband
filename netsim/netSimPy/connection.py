# -*- coding: utf-8 -*-
from typing import List, Dict, TypedDict, Union
from .bitRate import BitRate
from uuid import UUID


class LinkDetails(TypedDict):
    slots: List[int]
    band: str
    modulation: str


class Connection:
    def __init__(self, eventID: UUID, src: int, dst: int, bitRate: BitRate):
        self.__eventID = eventID
        self.src = src
        self.dst = dst
        self.bitRate = bitRate
        self.routeIndex: Union[int, None] = None
        self.__connection: Dict[str, LinkDetails] = {}
        self._protected = False

    def addLinkInfo(
        self, linkID: str, slots: list, band: str = "NoBand", modulation="Unset"
    ):
        self.__connection[linkID] = {
            "slots": slots,
            "band": band,
            "modulation": modulation,
        }

    def addLinkInfo(
        self,
        linkID: str,
        fromSlot: int,
        toSlot: int,
        band: str = "NoBand",
        modulation="Unset",
    ):
        self.__connection[linkID] = {
            "slots": [i for i in range(fromSlot, toSlot)],
            "band": band,
            "modulation": modulation,
        }

    def addRouteIndex(self, index: int):
        self.routeIndex = index

    @property
    def eventID(self):
        return self.__eventID

    @property
    def linksID(self):
        return [key for key in self.__connection.keys()]

    def getSlots(self):
        return [data["slots"] for data in self.__connection.values()]

    def getLinkSlots(self, linkID: str):
        # print("linkID", self.__connection[linkID]["slots"])
        return self.__connection[linkID]["slots"]

    def getBands(self):
        return [data["band"] for data in self.__connection.values()]

    def getBand(self, linkID: str):
        return self.__connection[linkID]["band"]

    def getConnectionInfo(self):
        return self.__connection

    def getModulationName(self, linkID: str):
        return self.__connection[linkID]["modulation"]["name"]

    @property
    def protected(self):
        return self._protected

    @protected.setter
    def protected(self, status: bool):
        self._protected = status
