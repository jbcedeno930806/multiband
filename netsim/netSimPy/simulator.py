from abc import ABC, abstractmethod

# types:
from typing import Tuple, Union, Callable

from ..netSimPy import EventsGenerator, EventType, Network, Connection, Event
from .common.callback import NetworkCallback
from ..netSimPy.network import AllocationResult


class EventSimulator(ABC):
    def __init__(
        self,
        eventsGenerator: EventsGenerator,
    ):
        self.__eventsGenerator = eventsGenerator
        self.event: Union[Event, None] = None

    def run(self, timesteps: int, callback: Union[NetworkCallback, None] = None):
        self.steps = 0
        while self.steps != timesteps:
            self.event = self.runToNextArrivalEvent()
            if self._on_step(self.event):
                self.event.setType(EventType.Departure)
                self.__eventsGenerator.appendEvent(self.event)
            self.steps += 1
            if callback:
                callback.on_update(self.get_public_attributes())
        if callback:
            callback.on_run_end(self.get_public_attributes())

    def get_public_attributes(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    @abstractmethod
    def _on_step(self, event: Event):
        return True

    def runToNextArrivalEvent(self):
        event = self.__eventsGenerator.getNextEvent()
        while event.getType() != EventType.Arrive:
            self._on_departure_event(event)
            event = self.__eventsGenerator.getNextEvent()
        return event

    @abstractmethod
    def _on_departure_event(self, event: Event):
        print("Abstrac on departure")

    # @abstractmethod
    # def _on_run_end(self):
    #     print(f"Simulation finished for {self.steps} timesteps")

    def setLambda(self, mLambda: 100):
        self.__eventsGenerator.setLambda(mLambda)

    def reset(self):
        self.__eventsGenerator.restart()

    @property
    def eventsGenerator(self):
        return self.__eventsGenerator


class NetworkSimulator(EventSimulator):
    def __init__(
        self,
        network: Network,
        eventsGenerator: EventsGenerator,
        allocator: Union[
            Callable[
                [Connection, Network, int],
                Tuple[AllocationResult, Connection],
            ],
            None,
        ] = None,
    ):
        super().__init__(eventsGenerator)
        self.network = network
        self.allocator = allocator
        self.blockedEvents = 0

    def _on_step(self, event: Event):
        connection = self.network.generateConnectionRequest(event.id)
        result, con = self.allocator(connection, self.network)
        self.update_metrics(result, con)
        if result == AllocationResult.Allocated:
            self.network.allocate(con)
            return True
        return False

    def _on_departure_event(self, event):
        connection = self.network.getConnection(event.id)
        self.network.deallocate(connection)

    def _on_run_end(self):
        bp = round(self.blockedEvents / self.steps, 7)
        print(f"Blocking probability:{bp}")

    def update_metrics(self, result: AllocationResult, con: Connection):
        if result != AllocationResult.Allocated:
            self.blockedEvents += 1

    def reset(self, hard_reset=False):
        self.network.restart()
        super().reset()

    def setAllocatorFunc(
        self,
        custom_allocator: Union[
            Callable[
                [Connection, Network],
                Tuple[AllocationResult, Connection],
            ],
            None,
        ] = None,
    ):
        self.allocator = custom_allocator
