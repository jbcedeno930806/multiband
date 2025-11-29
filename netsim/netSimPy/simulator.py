# types:
from typing import Tuple, Union, Callable, Optional
from ..netSimPy import EventsGenerator, EventType, Network, Connection, Event

from .common.evaluators import EventEvaluator
from ..netSimPy.network import AllocationResult


class EventSimulator:
    def __init__(
        self,
        eventsGenerator: EventsGenerator,
    ):
        self.__eventsGenerator = eventsGenerator
        self.event: Optional[Event] = None
        self.steps = 0

    def run(self, timesteps: int, callback: Optional[EventEvaluator] = None):
        callback and callback.on_init()
        self.steps = 0
        while self.steps != timesteps:
            self.event = self.runToNextArrivalEvent()
            if self._on_step(self.event):
                self.event.setType(EventType.Departure)
                self.__eventsGenerator.appendEvent(self.event)
            self.steps += 1
            callback and callback.on_update(self.get_public_attributes())
        result = callback.on_run_end(self.get_public_attributes()) if callback else None
        return result

    def get_public_attributes(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    def _on_step(self, event: Event):
        return True

    def runToNextArrivalEvent(self):
        event = self.__eventsGenerator.getNextEvent()
        while event.getType() != EventType.Arrive:
            self._on_departure_event(event)
            event = self.__eventsGenerator.getNextEvent()
        self._on_arrival(event)
        return event

    def _on_arrival(self, event):
        return

    def _on_departure_event(self, event: Event):
        return

    def setLambda(self, value: int = 100):
        self.__eventsGenerator.setLambda(value)

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
        self.connection = None
        self.allocator = allocator

    def _on_step(self, event: Event):
        self.connection = self.network.generateConnectionRequest(event.id)
        result, con = self.allocator(self.connection, self.network)
        if result == AllocationResult.Allocated:
            self.network.allocate(con)
            return True
        return False

    def _on_departure_event(self, event):
        self.network.deallocate(event.id)

    def reset(self):
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

    def getNetwork(self):
        return self.network
