import gym
import numpy as np
from netsim.netSimPy import (
    EventsGenerator,
    EventType,
    Network,
    Connection,
    Link,
)
from netsim.netSimPy.network import AllocationResult
from ...utils import get_shared_link, get_available_blocks
from gym.spaces import Box

# types:
from typing import List, Tuple, Union, Callable


class STATE_RMSA_ENV(gym.Env):
    __shape = None
    allocation_result = None
    # metadata = None
    timestep_info = None
    episode_info = None
    # used to display info on each timestep:
    episode_services_processed = 0
    episode_services_accepted = 0
    episode_bit_rate_requested = 0
    episode_bit_rate_provisioned = 0
    __info__ = {
        "src": 0,
        "dst": 0,
        "bitRate": 0,
        "action": 0,
        "reward": 0,
        "service_blocking_rate": 0,
        "episode_service_blocking_rate": 0,
        "bit_rate_blocking_rate": 0,
        "episode_bit_rate_blocking_rate": 0,
    }

    def __init__(
        self,
        network: Network,
        eventsGenerator: EventsGenerator,
        custom_allocator: Union[
            Callable[
                [Connection, Network],
                Tuple[AllocationResult, Connection],
            ],
            None,
        ] = None,
        episode_length=100,
        j=1,
        n_paths=1,
    ):
        self.episode_length = episode_length
        self.j = j
        self.n_paths = n_paths
        self.__network = network
        self.setAllocatorFunc(custom_allocator)
        self.__eventsGenerator = eventsGenerator
        numberOfNodes = self.__network.getNodesCount()
        self.allDemands = np.array([1, 2, 3, 4, 6, 7, 8, 11, 14, 16, 20, 27, 32, 40, 80])
        self.__shape = (
            2 * numberOfNodes
            + len(self.__network.links.values()) * 344
            + 3 * len(self.allDemands)
        )

        self.observation_space = gym.spaces.Box(
            low=0, high=1, dtype=np.int64, shape=(self.__shape,)
        )
        self.action_space_len = self.n_paths * self.j
        self.action_space = gym.spaces.Discrete(self.action_space_len)
        self.information_keywords = self.__info__
        self.numberOfArrivalEvents = 0
        self.totalNumberOfArrivals = 0
        self.blockedEvents = 0
        # self.restart_metrics()

    def step(self, action):
        self.numberOfArrivalEvents += 1
        self.totalNumberOfArrivals += 1
        event = self.__eventsGenerator.getCurrentEvent()
        con = self.__network.getConnection(event.id)

        allocation_result, con = self.allocator(con, self.__network, action)
        if allocation_result == AllocationResult.Allocated:
            self.__network.allocate(con)
            event.setType(EventType.Departure)
            self.__eventsGenerator.appendEvent(event)
        else:
            self.blockedEvents += 1
            self.__network.removeConnection(con)
        reward = self.reward(allocation_result)
        done = self.done()
        info = {}
        state = self.state()
        return state, reward, done, info

    def runToNextArrivalEvent(self):
        event = self.__eventsGenerator.getNextEvent()
        while event.getType() != EventType.Arrive:
            connection = self.__network.getConnection(event.id)
            self.__network.deallocate(connection)
            event = self.__eventsGenerator.getNextEvent()
        return event

    def state(self):
        event = self.runToNextArrivalEvent()
        connection = self.__network.generateConnectionRequest(event.id)
        src = connection.src
        dst = connection.dst
        numberOfNodes = self.__network.getNodesCount()
        srcState = np.zeros(numberOfNodes)
        dstState = np.zeros(numberOfNodes)

        srcState[src] = 1
        dstState[dst] = 1

        allLinks = self.__network.links.values()
        linksState = []
        for link in allLinks:
            slots = [1 if slot is True else 0 for slot in link.getSlots()]
            linksState.extend(slots)
        linksState = np.array(linksState)

        paths = self.__network.paths[src][dst]
        # allDemands = np.array([1, 2, 3, 4, 6, 7, 8, 11, 14, 16, 20, 27, 32, 40, 80])
        demandState = np.full((self.n_paths, 15), fill_value=0)
        for idp, path in enumerate(paths):
            linksOfPath: List[Link] = [self.__network.links[linkID] for linkID in path]
            demand = connection.bitRate.getBestModulationNumberOfSlots(linksOfPath)
            demandPos = np.where(self.allDemands == demand)[0][0]
            demandState[idp, demandPos] = 1

        demandState = demandState.reshape(self.n_paths * len(self.allDemands))
        state = np.concatenate(
            (
                srcState,
                dstState,
                linksState,
                demandState,
            ),
        )
        return state

    def reset(self, hard_reset=False):
        if hard_reset:
            self.__network.restart()
            self.__eventsGenerator.restart()
            self.restartMetrics()
        return self.state()

    def restartMetrics(self):
        self.numberOfArrivalEvents = 0
        self.totalNumberOfArrivals = 0
        self.blockedEvents = 0

    def done(self):
        return self.numberOfArrivalEvents % self.episode_length == 0

    def reward(self, allocation_result):
        episode_reward = 0
        if allocation_result == AllocationResult.Allocated:
            episode_reward = 1
        else:
            episode_reward = -1
        return episode_reward

    def _allocator(
        self,
        c: Connection,
        network: Network,
        action: int,
    ):
        if action == self.n_paths * self.j:
            return AllocationResult.Not_Allocated, c
        else:
            # get the route and block
            idx_path, idx_block = self.decode_action(action)
            paths = self.__network.paths[c.src][c.dst]
            selected_path = paths[idx_path]

            linksOfPath: List[Link] = [
                self.__network.links[linkID] for linkID in selected_path
            ]

            numberOfSlots = c.bitRate.getBestModulationNumberOfSlots(linksOfPath)
            initial_indices, lengths = get_available_blocks(
                c.bitRate, linksOfPath, idx_block + 1
            )
            initial_indices, _ = self.get_spread_spectrum_availibility(
                initial_indices, lengths
            )

            if len(initial_indices) > idx_block:
                ff_index = initial_indices[idx_block]
                for link in linksOfPath:
                    c.addLinkInfo(
                        link.id,
                        fromSlot=ff_index,
                        toSlot=ff_index + numberOfSlots,
                    )
                return AllocationResult.Allocated, c
        return AllocationResult.Not_Allocated, c

    def decode_action(self, act: int) -> tuple[int, int]:
        idx_path: int = act // self.j
        idx_block: int = act % self.j
        return idx_path, idx_block

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
        self.allocator = (
            custom_allocator if custom_allocator is not None else self._allocator
        )

    def get_spread_spectrum_availibility(self, initial_indices: tuple, lengths: tuple):
        indexes = np.argsort(lengths)[: self.j]
        return [initial_indices[i] for i in indexes], [lengths[i] for i in indexes]
