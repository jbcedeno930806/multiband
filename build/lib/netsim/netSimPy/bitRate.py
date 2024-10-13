# -*- coding: utf-8 -*-
import json
from typing import Dict, List, TypedDict
import math
from .link import Link


class ModulationInfo(TypedDict):
    reach: int
    slots: int


class BitRate:
    __bitRate = 0.0
    __bitrate_data = None

    def __init__(self, bitRate: int, bitrate_data: Dict[str, Dict[str, ModulationInfo]]):
        self.__bitRate = bitRate
        self.__bitrate_data = bitrate_data

    def getAvailableModulationsByBand(
        self, route: List[Link], band: str
    ) -> Dict[str, ModulationInfo]:
        distance = sum([link.length for link in route])
        available_modulations = {}
        for modulation in self.__bitrate_data[band]:
            if self.__bitrate_data[band][modulation]["reach"] >= distance:
                available_modulations[modulation] = self.__bitrate_data[band][modulation]
        return available_modulations

    def getAvailableModulations(self, route: List[Link]):
        available_modulations = {}
        for band in self.__bitrate_data:
            byBand = self.getAvailableModulationsByBand(route, band)
            available_modulations[band] = byBand
        return available_modulations

    def getBestModulationByBand(self, route: List[Link], band: str):
        route_length = sum([link.length for link in route])
        available_modulations = self.getAvailableModulationsByBand(route, band)
        best_modulation = None
        best_diff = math.inf
        for modulation in available_modulations.values():
            diff = modulation["reach"] - route_length
            if diff >= 0 and diff <= best_diff:
                best_modulation = modulation
                best_diff = diff
        print("best_modulation:", best_modulation)
        return best_modulation

    @staticmethod
    def readBitRateFile(fileName: str):
        with open(fileName) as json_file:
            info = json.load(json_file)
            bitsRate: list[BitRate] = []
            for bitRateTag in info:
                bitRate = BitRate(bitRateTag, info[bitRateTag])
                bitsRate.append(bitRate)
            return bitsRate

    def getBitRate(self):
        return self.__bitRate

    def getReach(self, band, modulation):
        return self.__bitrate_data[band][modulation]["reach"]

    def getSlots(self, band, modulation):
        return self.__bitrate_data[band][modulation]["slots"]

    def getModulation(self, band: str):
        return self.__bitrate_data[band]

    def __str__(self):
        return f"BitRate:{self.__bitRate}\nData:\t{self.__bitrate_data}"
