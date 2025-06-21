# -*- coding: utf-8 -*-
from typing import List, TypedDict
from .event import Event, EventType
from .expVariable import ExpVariable


class GeneratorProps(TypedDict):
    mLamda: int
    seed: int
    mu: int


class EventsGenerator:
    def __init__(
        self,
        seed=12345,
        mLambda=10000,
        mu=100,
    ):
        self.__seed = seed
        self.__lambda = mLambda
        self.__mu = mu
        self.__arriveVariable = ExpVariable(self.__seed, self.__lambda)
        self.__departVariable = ExpVariable(self.__seed, self.__mu)
        self.restart()

    def restart(self):
        self.__clock = 0
        self.__arriveVariable = ExpVariable(self.__seed, self.__lambda)
        self.__departVariable = ExpVariable(self.__seed, self.__mu)
        self.__events: List[Event] = []
        startTime = self.__clock + self._getNextArrivalValue()
        endTime = startTime + self._getNextDepartValue()
        self.appendEvent(self.createEvent(startTime, endTime))

    def getNextEvent(self) -> Event:
        event = self.__events.pop(0)
        self.__clock = event.time
        if event.getType() == EventType.Arrive:
            startTime = self.__clock + self._getNextArrivalValue()
            endTime = startTime + self._getNextDepartValue()
            newEvent = self.createEvent(startTime, endTime)
            self.appendEvent(newEvent)
        return event

    @staticmethod
    def createEvent(startTime: float, endTime: float) -> Event:
        return Event(
            EventType.Arrive,
            startTime,
            endTime,
        )

    def appendEvent(self, event: Event):
        if event in self.__events:
            return
        inserted = False
        for i, ev in enumerate(self.__events):
            time = event.time
            if time < ev.time:
                self.__events.insert(i, event)
                inserted = True
                break
        if not inserted:
            self.__events.append(event)

    def _getNextDepartValue(self):
        return self.__departVariable.getNextValue()

    def _getNextArrivalValue(self):
        return self.__arriveVariable.getNextValue()

    @property
    def mu(self):
        return self.__mu

    @mu.setter
    def mu(self, mu: float):
        self.__mu = mu
        self.__departVariable = ExpVariable(self.__seed, self.__mu)

    @property
    def mlabmda(self):
        return self.mlabmda

    @mlabmda.setter
    def mlabmda(self, mlabmda: float):
        self.mlabmda = mlabmda

    def setLambda(self, lambdaValue):
        self.__lambda = lambdaValue
        self.__arriveVariable = ExpVariable(self.__seed, self.__lambda)

    @property
    def events(self):
        return self.__events

    @events.setter
    def events(self, events):
        self.__events = events
