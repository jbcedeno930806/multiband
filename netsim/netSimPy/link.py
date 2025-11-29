# -*- coding: utf-8 -*-
from typing import Union, Dict, List

NO_BAND = "NoBand"


class Link:
    __length = 0
    __defauldBand = NO_BAND

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
        self.__link_failure: bool = False

        # Slots by band:
        self.__slots: Dict[str, list] = {}
        if isinstance(slots, int):
            self.__slots[self.__defauldBand] = [False] * slots
        else:
            for key in slots:
                self.__slots[key] = [False] * slots[key]

    def set_failure(self, status: bool):
        self.reset(status)
        self.__link_failure = status

    def is_in_fail(self):
        return self.__link_failure

    def reset(self, failure=False):
        self.__link_failure = failure
        for key in self.__slots:
            self.__slots[key] = [False if not failure else True] * len(self.__slots[key])

    def setSlots(self, slotsIndexes: List[int], value: bool, band: str = NO_BAND) -> None:
        if self.is_in_fail():
            return
        if value is False:
            for slotIndex in slotsIndexes:
                self.__slots[band][slotIndex] = False
            return
        for slotIndex in slotsIndexes:
            if not self.getSlotValue(slotIndex, band):
                self.__slots[band][slotIndex] = True
            else:
                raise ValueError(
                    "Slot {} is already in use for link id {} and band {}".format(
                        slotIndex, self.id, band
                    )
                )

    def getBands(self):
        return list(self.__slots.keys())

    def isBandEnabled(self, band):
        return band in self.__slots

    def getSlotsCount(self, band: str = NO_BAND):
        try:
            return len(self.__slots[band])
        except KeyError:
            raise KeyError(
                "Band {} is invalid. Available bands are {}".format(
                    band, list(self.__slots.keys())
                )
            )

    def getSlotValue(self, slotIndex: str, band: str = NO_BAND) -> bool:
        try:
            return self.__slots[band][slotIndex]
        except KeyError:
            raise KeyError(
                "You must select a band. Available bands are {}".format(
                    list(self.__slots.keys())
                )
            )

    def getBandInfo(self, band: str = NO_BAND):
        pass

    def getSlots(self, band: str = NO_BAND):
        try:
            return self.__slots[band]
        except KeyError:
            raise KeyError(
                "You must select a band. Available bands are {}".format(
                    list(self.__slots.keys())
                )
            )

    def getAvailibility(self, band: str = NO_BAND):
        try:
            return self.__slots[band].count(False)
        except KeyError:
            raise KeyError(
                "You must select a band. Available bands are {}".format(
                    list(self.__slots.keys())
                )
            )

    def getFragmentation(self, band: str = NO_BAND):
        if band in self.__slots:
            slots = self.__slots[band]
            try:
                last_used_slot = slots[::-1].index(True)
                return slots[: len(slots) - last_used_slot].count(False)
            except ValueError:
                return 0
        else:
            raise KeyError(
                "You must select a band. Available bands are {}".format(
                    list(self.__slots.keys())
                )
            )

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
