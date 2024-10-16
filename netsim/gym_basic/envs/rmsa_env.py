import itertools
import gym
import numpy as np
from netsim.netSimPy import (
    Link,
)
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
        self.__shape = 2 * numberOfNodes + (2 * self.j + 3) * self.n_paths
        self.observation_space = gym.spaces.Box(
            low=0, high=100, dtype=np.float32, shape=(self.__shape,)
        )
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
        return state, reward, done, info

    def _step(self, event: Event, action:int):
        connection = self.__simulator.network.generateConnectionRequest(event.id)
        result, con = self.allocator(connection, self.__simulator.network, action)
        if result == AllocationResult.Allocated:
            self.__simulator.network.allocate(con)
            event.setType(EventType.Departure)
            self.__simulator.eventsGenerator.appendEvent(event)
        return result
    
    def state(self):
        self.event = self.__simulator.runToNextArrivalEvent()
        connection = self.__simulator.network.generateConnectionRequest(self.event.id)
        src = connection.src
        dst = connection.dst
        numberOfNodes = self.__simulator.network.getNodesCount()
        source_destination_tau = np.zeros((2, numberOfNodes))
        min_node = min(src, dst)
        max_node = max(src, dst)
        source_destination_tau[0, min_node] = 1
        source_destination_tau[1, max_node] = 1
        spectrum_obs = np.full((self.n_paths, 2 * self.j + 3), fill_value=0.0)
        paths = self.__simulator.network.paths[src,dst]

        for idp, path in enumerate(paths[: self.n_paths]):
            linksOfPath: List[Link] = [
                self.__simulator.network.links[f"{src}-{dst}"] for src, dst in pairwise(path)
            ]
            shared_link = get_shared_link(linksOfPath, "C")
            bestModulation = connection.bitRate.getBestModulationByBand(linksOfPath, "C")
            demand = bestModulation["slots"]
            initial_indices, lengths = get_available_blocks(
                demand, linksOfPath, "C", self.j
            )
            avail_blocks = len(initial_indices)
            # se puede mejorar esta forma de obtener los cantidad de slots del link??:
            link_total_slots = len(shared_link)
            for idb in range(self.j):
                if idb < avail_blocks:
                    # initial slot index:
                    spectrum_obs[idp, idb * 2 + 0] = initial_indices[idb]
                    # number of contiguous FS available:
                    spectrum_obs[idp, idb * 2 + 1] = lengths[idb]
                else:
                    # max. available blocks is limited to "avail_blocks"
                    # so the link has no more available blocks:
                    spectrum_obs[idp, idb * 2 + 0] = link_total_slots
            # number of FSs necessary:
            spectrum_obs[idp, self.j * 2] = demand
            # total number of available FSs, this means: FSs = total - sum(nonAvailable)
            # -->> nonAvailable has value True
            spectrum_obs[idp, self.j * 2 + 1] = link_total_slots - np.sum(shared_link)
            # avg. number of free slots in the available blocks:
            if avail_blocks > 0:
                spectrum_obs[idp, self.j * 2 + 2] = np.sum(lengths) / len(initial_indices)
        state = np.concatenate(
            (
                source_destination_tau.reshape(
                    (1, np.prod(source_destination_tau.shape))
                ),
                spectrum_obs.reshape((1, np.prod(spectrum_obs.shape))),
            ),
            axis=1,
        ).reshape(self.__shape)
        return state
    
    def reset(self, hard_reset=False):
        if hard_reset:
            self.__simulator.network.restart()
            self.__simulator.__eventsGenerator.restart()
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

    def decode_action(self, act: int) -> tuple[int, int]:
        idx_path: int = act // self.j
        idx_block: int = act % self.j
        return idx_path, idx_block
    
    def setLambda(self, mLambda = None):
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
            initial_indices, _ = get_available_blocks(
                numberOfSlots, linksOfPath,"C", idx_block + 1
            )

            if len(initial_indices) > idx_block:
                ff_index = initial_indices[idx_block]
                for link in linksOfPath:
                    c.addLinkInfo(
                        link.id,
                        fromSlot=ff_index,
                        toSlot=ff_index + numberOfSlots,
                        band="C"
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
