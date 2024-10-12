# -*- coding: utf-8 -*-
from typing import List, Dict, TypedDict
from .bitRate import BitRate
from uuid import UUID


class LinkDetails(TypedDict):
    slots: List[int]
    band: str


class Connection:
    def __init__(self, eventID: UUID, src: int, dst: int, bitRate: BitRate):
        self.__eventID = eventID
        self.src = src
        self.dst = dst
        self.bitRate = bitRate
        self.__connection: Dict[str, LinkDetails] = {}

    def addLinkInfo(self, linkID: str, slots: list, band: str = "NoBand"):
        self.__connection[linkID] = {"slots": slots, "band": band}

    def addLinkInfo(self, linkID: str, fromSlot: int, toSlot: int, band: str = "NoBand"):
        self.__connection[linkID] = {
            "slots": [i for i in range(fromSlot, toSlot)],
            "band": band,
        }

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
