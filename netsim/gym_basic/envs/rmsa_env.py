import gymnasium as gym
import numpy as np
from netsim.netSimPy import (
    Link,
)
from gymnasium.spaces import MultiBinary
from netsim.netSimPy.network import AllocationResult
from netsim.netSimPy import Simulator, Event, Connection, Network, EventType
from netsim.utils import get_shared_link, get_available_blocks, pairwise

# types:
from typing import List, Tuple, Union, Callable


class RMSA_ENV(gym.Env):
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
        simulator: Simulator,
        episode_length=100,
        j=5,
        n_paths=3,
        allocator: Union[
            Callable[
                [Connection, Network, int],
                Tuple[AllocationResult, Connection],
            ],
            None,
        ] = None,
    ):
        self.episode_length = episode_length
        self.j = j
        self.n_paths = n_paths
        self.allocator = self._allocator if allocator is None else allocator
        self.__simulator = simulator
        numberOfNodes = self.__simulator.network.getNodesCount()
        self.allDemands = [1, 2, 3, 4, 5, 6, 8, 9, 11, 15, 18, 22, 44]
        self.__shape = (
            2 * numberOfNodes + self.n_paths * 344 + self.n_paths * len(self.allDemands)
        )
        self.observation_space = MultiBinary(self.__shape)
        self.action_space_len = self.n_paths * self.j
        self.action_space = gym.spaces.Discrete(self.action_space_len)
        self.information_keywords = self.__info__
        self.numberOfArrivalEvents = 0
        self.totalNumberOfArrivals = 0
        self.blockedEvents = 0
        self.event: Event = None

    def step(self, action):
        self.numberOfArrivalEvents += 1
        self.totalNumberOfArrivals += 1

        result = self._step(self.event, action)
        if result != AllocationResult.Allocated:
            self.blockedEvents += 1
        reward = self.reward(result)
        done = self.done()
        info = {}
        state = self.state()
        truncated = False
        return state, reward, done, truncated, info

    def _step(self, event: Event, action: int):
        connection = self.__simulator.network.generateConnectionRequest(event.id)
        result, con = self.allocator(connection, self.__simulator.network, action)
        if result == AllocationResult.Allocated:
            self.__simulator.network.allocate(con)
            event.setType(EventType.Departure)
            self.__simulator.eventsGenerator.appendEvent(event)
        return result

    def state(self):
        self.event = self.__simulator.runToNextArrivalEvent()
        network = self.__simulator.network
        connection = network.generateConnectionRequest(self.event.id)
        numberOfNodes = network.getNodesCount()

        # Source state
        src = connection.src
        dst = connection.dst
        srcState = np.zeros(numberOfNodes)
        dstState = np.zeros(numberOfNodes)
        srcState[src] = 1
        dstState[dst] = 1

        paths = network.paths[src, dst]
        slotsOfBand = network.getCapacityOfBand("C")
        linksState = np.zeros((self.n_paths, slotsOfBand))
        # allDemands = np.array([1, 2, 3, 4, 6, 7, 8, 11, 14, 16, 20, 27, 32, 40, 80])
        demandState = np.full((self.n_paths, len(self.allDemands)), fill_value=0)
        for idp, path in enumerate(paths[: self.n_paths]):
            linksOfPath: List[Link] = [
                network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
            ]
            linksState[idp] = [
                1 if slot is True else 0
                for slot in get_shared_link(linksOfPath, band="C")
            ]
            bestModulation = connection.bitRate.getBestModulationByBand(linksOfPath, "C")
            demand = bestModulation["slots"]
            demandPos = -1
            try:
                demandPos = self.allDemands.index(demand)
            except ValueError:
                raise ValueError("Invalid demand used for connection request")
            demandState[idp, demandPos] = 1

        linksState = linksState.reshape(self.n_paths * 344)
        demandState = demandState.reshape(self.n_paths * len(self.allDemands))
        return np.concatenate(
            (srcState, dstState, linksState, demandState),
        )

    def reset(self, seed=None, options: Union[None, dict[str]] = None):
        if options is not None:
            hard_reset = options["hard_reset"]
        else:
            hard_reset = False
        if hard_reset:
            self.__simulator.network.restart()
            self.__simulator.eventsGenerator.restart()
            self.restartMetrics()
        return self.state(), {}

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

    def decode_action(self, act: int) -> tuple[int, int]:
        idx_path: int = act // self.j
        idx_block: int = act % self.j
        return idx_path, idx_block

    def setLambda(self, mLambda=None):
        if mLambda is not None:
            self.__simulator.eventsGenerator.setLambda(mLambda)

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
            paths = self.__simulator.network.paths[c.src, c.dst]
            selected_path = paths[idx_path]

            linksOfPath: List[Link] = [
                network.links[f"{src}-{dst}"] for src, dst in pairwise(selected_path)
            ]
            bestModulation = c.bitRate.getBestModulationByBand(linksOfPath, "C")
            numberOfSlots = bestModulation["slots"]
            initial_indices, _lengths = get_available_blocks(
                numberOfSlots,
                linksOfPath,
                "C",
            )
            if len(initial_indices) > idx_block:
                ff_index = initial_indices[idx_block]
                for link in linksOfPath:
                    c.addLinkInfo(
                        link.id,
                        fromSlot=ff_index,
                        toSlot=ff_index + numberOfSlots,
                        band="C",
                    )
                return AllocationResult.Allocated, c
        return AllocationResult.Not_Allocated, c

    def setAllocatorFunc(
        self,
        custom_allocator: Union[
            Callable[
                [Connection, Network, int],
                Tuple[AllocationResult, Connection],
            ],
            None,
        ] = None,
    ):
        self.allocator = (
            custom_allocator if custom_allocator is not None else self._allocator
        )
