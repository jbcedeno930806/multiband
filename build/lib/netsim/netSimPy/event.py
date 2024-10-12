# -*- coding: utf-8 -*-
import enum
import uuid


class EventType(enum.Enum):
    NoData = "NoData"
    Arrive = "Arrive"
    Departure = "Departure"


class Event:
    def __init__(
        self,
        eventType: EventType,
        startTime: float,
        endTime: float,
    ):
        self.__eventType = eventType
        self.__startTime = startTime
        self.__endTime = endTime
        self.id = uuid.uuid4()

    def getType(self):
        return self.__eventType

    def setType(self, eventType: EventType):
        self.__eventType = eventType

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

    @property
    def bitRate(self):
        return self.__bitRate

    @bitRate.setter
    def bitRate(self, bitRate):
        self.__bitRate = bitRate

    @property
    def time(self):
        return (
            self.__startTime if self.__eventType == EventType.Arrive else self.__endTime
        )
