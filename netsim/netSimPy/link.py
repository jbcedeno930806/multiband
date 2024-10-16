# -*- coding: utf-8 -*-
from typing import Union, Dict, List


class Link:
    __length = 0
    __bandSelected = "NoBand"

    def __init__(
        self,
        id: str,
        src: int = -1,
        dst: int = -1,
        length=1,
        slots: Union[int, Dict[str, list]] = 100,
    ):
        self.__id = id
        self.__src = src
        self.__dst = dst
        self.__length = length

        # Slots by band:
        self.__slots:Dict[str, list] = {}
        if isinstance(slots, int):
            self.__slots[self.__bandSelected] = [False] * slots
        else:
            for key in slots:
                self.__slots[key] = [False] * slots[key]

    def reset(
        self,
    ):
        for key in self.__slots:
            self.__slots[key] = [False] * len(self.__slots[key])

    def setSlots(
        self, slotsIndexes: List[int], value: bool, band: str = "NoBand"
    ) -> None:
        for slotIndex in slotsIndexes:
            self.__slots[band][slotIndex] = value

    def getBands(self):
        bands = []
        for key in range(self.__slots):
            if self.__slots[key] > 0:
                bands.append(key)
        return bands

    def isBandEnabled(self, band):
        return band in self.__slots

    def getSlotsCount(self, band=None):
        if band is None:
            return len(self.__slots[self.__bandSelected])
        else:
            return len(self.__slots[band])

    def getSlotValue(self, slotIndex: str, band=None) -> bool:
        return self.__slots[self.__bandSelected if band is None else band][slotIndex]

    def getInfo(self, band=None):
        pass

    def getSlots(self, band=None):
        return self.__slots[self.__bandSelected if band is None else band]
    
    def getAvailibility(self, band=None):
        available = self.__slots[self.__bandSelected if band is None else band]
        return available.count(False)
    
    @property
    def id(self):
        return self.__id

    @property
    def length(self):
        return self.__length

    @length.setter
    def length(self, length):
        self.__length = length

    @property
    def src(self):
        return self.__src

    @property
    def dst(self):
        return self.__dst
