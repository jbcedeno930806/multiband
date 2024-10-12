# -*- coding: utf-8 -*-
import json
from typing import List
from .link import Link


class BitRate:
    __bitRate = 0.0
    __modulation = None
    __slots = None
    __reach = None

    def __init__(self, bitRate=None):
        self.__bitRate = bitRate
        self.__modulation = []
        self.__slots = []
        self.__reach = []

    def addModulation(self, modulation, slots, reach):
        self.__modulation.append(modulation)
        self.__slots.append(slots)
        self.__reach.append(reach)

    def getModulation(self, position):
        if position >= len(self.__modulation):
            raise (
                "Bitrate "
                + self.__bitRate
                + " does not have more than "
                + len(self.__modulation)
                + " modulations."
            )
        return self.__modulation[position]

    def getNumberofSlots(self, position):
        if position >= len(self.__slots):
            raise (
                "Bitrate "
                + self.__bitRate
                + " does not have more than "
                + len(self.__slots)
                + " slots."
            )
        return self.__slots[position]

    def getBestModulationNumberOfSlots(self, route: List[Link]):
        distance = sum([link.length for link in route])
        separation = 999999
        demand = 80
        for idm, _ in enumerate(self.modulation):
            sep = self.reach[idm] - distance
            if sep >= 0 and sep <= separation:
                separation = sep
                demand = self.slots[idm]
        return demand

    def getReach(self, position):
        if position >= len(self.__reach):
            raise (
                "Bitrate "
                + self.__bitRate
                + " does not have more than "
                + len(self.__reach)
                + " reach."
            )
        return self.__reach[position]

    def readBitRateFile(self, fileName: str):
        with open(fileName) as json_file:
            info = json.load(json_file)
            bitsRate: list[BitRate] = []
            for bitRateTag in info:
                bitRate = BitRate(bitRateTag)
                for modulation in info[bitRateTag]:
                    for band in info[bitRateTag][modulation]:
                        bitRate.addModulation(
                            modulation,
                            info[bitRateTag][modulation][band]["slots"],
                            info[bitRateTag][modulation][band]["reach"],
                        )
                bitsRate.append(bitRate)
            return bitsRate

    """ """

    @property
    def bitRate(self):
        return self.__bitRate

    @bitRate.setter
    def bitRate(self, bitRate):
        self.__bitRate = bitRate

    """ """

    @property
    def modulation(self):
        return self.__modulation

    @modulation.setter
    def modulation(self, modulation):
        self.__modulation.append(modulation)

    """ """

    @property
    def slots(self):
        return self.__slots

    @slots.setter
    def slots(self, slots):
        self.__slots.append(slots)

    """ """

    @property
    def reach(self):
        return self.__reach

    @reach.setter
    def reach(self, reach):
        self.__reach.append(reach)
