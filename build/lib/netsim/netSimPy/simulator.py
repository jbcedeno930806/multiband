from netsim.netSimPy import (
    EventsGenerator,
    EventType,
    Network,
    Connection,
)
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
                [Connection, Network],
                Tuple[AllocationResult, Connection],
            ],
            None,
        ] = None,
        n_paths=1,
    ):
        self.n_paths = n_paths
        self.__network = network
        self.__eventsGenerator = eventsGenerator
        self.setAllocatorFunc(allocator)
        self.blockedEvents = 0
        self.numberOfArrivalEvents = 0
        self.totalNumberOfArrivals = 0

    def run(self, timesteps: int):
        steps = 0
        while steps != timesteps:
            event = self.runToNextArrivalEvent()
            connection = self.__network.generateConnectionRequest(event.id)
            # print(connection.bitRate)
            result, con = self.allocator(connection, self.__network)
            if result == AllocationResult.Allocated:
                self.__network.allocate(con)
                event.setType(EventType.Departure)
                self.__eventsGenerator.appendEvent(event)
            else:
                self.blockedEvents += 1
                self.__network.removeConnection(con)

            steps += 1
        print(f"Blocking probability:{round(self.blockedEvents/steps, 7)}")

    def runToNextArrivalEvent(self):
        event = self.__eventsGenerator.getNextEvent()
        while event.getType() != EventType.Arrive:
            connection = self.__network.getConnection(event.id)
            self.__network.deallocate(connection)
            event = self.__eventsGenerator.getNextEvent()
        return event

    def setLambda(self, mLambda: 100):
        self.__eventsGenerator.setLambda(mLambda)

    def reset(self):
        self.__network.restart()
        self.__eventsGenerator.restart()
        self.restartMetrics()

    def restartMetrics(self):
        self.numberOfArrivalEvents = 0
        self.totalNumberOfArrivals = 0
        self.blockedEvents = 0

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
