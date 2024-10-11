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
        # info = self.save_and_update_metrics(done, reward, action)
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
        source_destination_tau = np.zeros((2, numberOfNodes))
        min_node = min(src, dst)
        max_node = max(src, dst)
        source_destination_tau[0, min_node] = 1
        source_destination_tau[1, max_node] = 1

        spectrum_obs = np.full((self.n_paths, 2 * self.j + 3), fill_value=0.0)
        paths = self.__network.paths[src][dst]

        for idp, path in enumerate(paths[: self.n_paths]):
            linksOfPath: List[Link] = [self.__network.links[linkID] for linkID in path]
            shared_link = get_shared_link(linksOfPath)
            demand = connection.bitRate.getBestModulationNumberOfSlots(linksOfPath)
            initial_indices, lengths = get_available_blocks(
                connection.bitRate, linksOfPath, self.j
            )
            # if self.use_spread_spectrum:
            initial_indices, lengths = self.get_spread_spectrum_availibility(
                initial_indices, lengths
            )
            avail_blocks = len(initial_indices)
            # this is for the intermadiate reward:
            # best_fit = self.j * [0]
            # for idb in range(self.j):
            #     if idb < avail_blocks and demand == lengths[idb]:
            #         best_fit[idb] = 1

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

        # self.timestep_info["src"] = src
        # self.timestep_info["dst"] = dst
        # self.timestep_info["bitRate"] = int(event.bitRate.bitRate)
        return state

    def setLambda(self, mLambda: 100):
        self.__eventsGenerator.setLambda(mLambda)

    def reset(self, hard_reset=False, mLmabda=100):
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

    # def save_and_update_metrics(self, done, reward, action):
    #     # updateing counters:
    #     self.episode_services_processed += 1
    #     self.episode_services_accepted += 1 if reward == 1 else 0
    #     self.episode_bit_rate_requested += self.timestep_info["bitRate"]
    #     self.episode_bit_rate_provisioned += (
    #         self.timestep_info["bitRate"] if reward == 1 else 0
    #     )

    #     self.timestep_info["reward"] = reward
    #     self.timestep_info["action"] = action
    #     # TODO: Calcular estos:
    #     self.timestep_info["episode_service_blocking_rate"] = (
    #         self.episode_services_processed - self.episode_services_accepted
    #     ) / self.episode_services_processed
    #     self.timestep_info["episode_bit_rate_blocking_rate"] = (
    #         self.episode_bit_rate_requested - self.episode_bit_rate_provisioned
    #     ) / self.episode_bit_rate_requested

    #     infos = self.timestep_info

    #     self.episode_info.append(self.timestep_info)
    #     if done:
    #         # saving metrics only when episode ends:
    #         df = pd.DataFrame(self.episode_info)
    #         df.to_csv(
    #             self.output_name,
    #             mode="a",
    #         )
    #         self.episode_info = []

    #     self.timestep_info = {}
    #     return infos

    # def restart_metrics(self):
    #     self.timestep_info = {}
    #     self.episode_info = []

    #     # counters:
    #     self.episode_services_accepted = 0
    #     self.episode_services_processed = 0
    #     self.episode_bit_rate_requested = 0
    #     self.episode_bit_rate_provisioned = 0

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
