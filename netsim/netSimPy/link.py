# -*- coding: utf-8 -*-
"""
Created on Mon Jan 24 14:37:03 2022

@author: redno
"""

from typing import Union, Dict, List


class Link:
    __length = 1
    __slots = None
    __src = -1
    __dst = -1

    def __init__(self, id="-1", length=1, slots: Union[int, Dict] = 100):
        self.__id = id
        self.__length = length
        self.__bandSelected = "NoBand"

        # Slots by band:
        self.__slots = {}
        if isinstance(slots, int):
            self.__slots["NoBand"] = [False] * slots
        else:
            for key in slots:
                self.__slots[key] = [False] * slots[key]
        self.__src = -1
        self.__dst = -1

    def reset(
        self,
        slots: Union[
            int, Dict, None
        ] = None,  # Dict example: {"C": 344, "L": 480, "S": 760, "E": 1136}
    ):
        for key in self.__slots.keys():
            if isinstance(slots, int):
                length = len(self.__slots[key])
            else:
                length = slots[key]
            self.__slots[key] = [False] * length

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

    def isBandEnabled(self, band):
        for key in range(self.__slots):
            if (key == band) and (self.__slots[key] > 0):
                return True
        return False

    def getSlotsCount(self, band=None):
        if band is None:
            return len(self.__slots[self.__bandSelected])
        else:
            return len(self.__slots[band])

    def getSlotValue(self, slotIndex: str, band=None) -> bool:
        return self.__slots[self.__bandSelected if band is None else band][slotIndex]

    def info(self, band=None):
        pass

    def getSlots(self, band=None):
        return self.__slots[self.__bandSelected if band is None else band]

    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, id):
        self.__id = id

    @property
    def length(self):
        return self.__length

    @length.setter
    def length(self, length):
        self.__length = length

    @property
    def src(self):
        return self.__src

    @src.setter
    def src(self, src):
        self.__src = src

    @property
    def dst(self):
        return self.__dst

    @dst.setter
    def dst(self, dst):
        self.__dst = dst
