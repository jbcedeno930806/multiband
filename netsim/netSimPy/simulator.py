from netsim.netSimPy import EventsGenerator, EventType, Network, Connection, Event
from netsim.netSimPy.network import AllocationResult

# types:
from typing import Tuple, Union, Callable


class Simulator:
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
        self.__network = network
        self.__eventsGenerator = eventsGenerator
        self.allocator = allocator
        self.blockedEvents = 0

    def run(self, timesteps: int):
        steps = 0
        self.blockedEvents = 0
        while steps != timesteps:
            event = self.runToNextArrivalEvent()
            result, _ = self.__step(event)
            if result != AllocationResult.Allocated:
                self.blockedEvents += 1
            steps += 1
        bp = round(self.blockedEvents/steps, 7)
        print(f"Blocking probability:{bp}")
        return bp

    def __step(self, event: Event):
        connection = self.__network.generateConnectionRequest(event.id)
        result, con = self.allocator(connection, self.__network)
        if result == AllocationResult.Allocated:
            self.__network.allocate(con)
            event.setType(EventType.Departure)
            self.__eventsGenerator.appendEvent(event)
        return result, con
    

    def runToNextArrivalEvent(self):
        event = self.__eventsGenerator.getNextEvent()
        while event.getType() != EventType.Arrive:
            connection = self.__network.getConnection(event.id)
            self.__network.deallocate(connection)
            event = self.__eventsGenerator.getNextEvent()
        return event

    def setLambda(self, mLambda: 100):
        self.__eventsGenerator.setLambda(mLambda)

    def reset(self, hard_reset=False):
        self.__network.restart()
        self.__eventsGenerator.restart()

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

    @property
    def eventsGenerator(self):
        return self.__eventsGenerator
