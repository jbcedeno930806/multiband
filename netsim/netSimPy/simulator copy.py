from abc import ABC, abstractmethod
import enum
from netsim.netSimPy import EventsGenerator, EventType, Network, Connection, Event

from netsim.netSimPy.network import AllocationResult

# types:
from typing import Tuple, Union, Callable


class Allocation(enum.Enum):
    Allocated = "Allocated"
    Not_Allocated = "Not_Allocated"
    Default = "Default"


class EventSimulator(ABC):
    def __init__(
        self,
        eventsGenerator: EventsGenerator,
    ):
        self.__eventsGenerator = eventsGenerator
        self.steps = 0

    def run(self, timesteps: int, callback=None):
        self.steps = 0
        while self.steps != timesteps:
            event = self.runToNextArrivalEvent()
            should_allocate, *_rest = self._on_step(event)
            if should_allocate:
                event.setType(EventType.Departure)
                self.__eventsGenerator.appendEvent(event)
            self.steps += 1
        self._on_run_end()

    @abstractmethod
    def _on_step(self, event: Event) -> Tuple[bool, ...]:
        """
        This method will be called by the simulator for the current event on the ``run()
        method``.
        args:
            event (Event): _description_
        returns:
            bool: If the method returns True, the event is added for departure.
        """
        return [True]

    def runToNextArrivalEvent(self):
        event = self.__eventsGenerator.getNextEvent()
        while event.getType() != EventType.Arrive:
            self._on_departure(event)
            event = self.__eventsGenerator.getNextEvent()
        self._on_arrival(event)
        return event

    def _on_arrival(self, event: Event):
        pass

    @abstractmethod
    def _on_departure(self, event: Event):
        pass

    @abstractmethod
    def _on_run_end(self):
        print(f"Simulation finished for {self.steps} timesteps")

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
        self.__network = network
        self.allocator = allocator

    def _on_step(self, event: Event):
        connection = self.network.generateConnectionRequest(event.id)
        result, con = self.allocator(connection, self.network)
        if result == AllocationResult.Allocated:
            self.network.allocate(con)
            # self.update_metrics(result, con)
            return [True]
        # self.update_metrics(result, con)
        return [False]

    def _on_departure(self, event):
        connection = self.network.getConnection(event.id)
        self.network.deallocate(connection)

    def _on_run_end(self):
        pass
        # bp = round(self.blockedEvents / self.steps, 7)
        # print("totalAttendedByBand", self.totalAttendedByBand)
        # print("fragmentationByBand", self.fragmentationByBand)
        # print("attendedByRouteIndex", self.attendedByRouteIndex)
        # print(f"Blocking probability:{bp}")

    # def update_metrics(self, result: AllocationResult, con: Connection):
    #     if result != AllocationResult.Allocated:
    #         self.blockedEvents += 1
    #         if con.routeIndex is not None:
    #             if con.routeIndex not in self.attendedByRouteIndex:
    #                 self.attendedByRouteIndex[con.routeIndex] = 1
    #             else:
    #                 self.attendedByRouteIndex[con.routeIndex] += 1
    #     else:
    #         self.totalAttended += 1
    #         self.totalAttendedByBand[con.getBand(con.linksID[0])] += 1
    #     for band in self.bands:
    #         self.fragmentationByBand[band].append(self.network.getBandFragmentation(band))

    def reset(self, hard_reset=False):
        self.__network.restart()
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

    @property
    def network(self):
        return self.__network
