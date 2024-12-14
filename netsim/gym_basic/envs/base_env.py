from abc import ABC, abstractmethod
import gymnasium as gym

# local imports:
from ...netSimPy.network import AllocationResult
from ...netSimPy import NetworkSimulator, Connection, Network, Event, EventType


# types:
from typing import Tuple, Union, Callable, Dict, Any


class BASE_ENV(gym.Env, ABC):
    reset_keywords = ["hard_reset"]

    def __init__(
        self,
        simulator: NetworkSimulator,
        episode_length=100,
        allocator: Union[
            Callable[
                [Connection, Network, int],
                Tuple[AllocationResult, Connection],
            ],
            None,
        ] = None,
    ):
        super().__init__()
        self.episode_length = episode_length
        self.allocator = self._allocator if allocator is None else allocator
        self.simulator = simulator
        self.numberOfArrivalEvents = 0
        self.event: Event = None
        self.connection: Connection = None

    def step(self, action):
        self.numberOfArrivalEvents += 1
        result, con = self.allocator(self.connection, self.simulator.network, action)
        if result == AllocationResult.Allocated:
            self.simulator.network.allocate(con)
            self.event.setType(EventType.Departure)
            self.simulator.eventsGenerator.appendEvent(self.event)
        reward = self.reward(result)
        done = self.done()
        info = {}
        state = self.state()
        truncated = False
        return state, reward, done, truncated, info

    def reward(self, result: AllocationResult):
        if result == AllocationResult.Allocated:
            episode_reward = 1
        else:
            episode_reward = -1
        return episode_reward

    def done(self):
        return self.numberOfArrivalEvents % self.episode_length == 0

    def state(self):
        self.event = self.simulator.runToNextArrivalEvent()
        self.connection = self.simulator.network.generateConnectionRequest(self.event.id)
        return self._state(self.connection)

    @abstractmethod
    def _state(self, connection: Connection):
        pass

    def reset(self, seed=None, options: Union[Dict[str, Any], None] = None):
        if options is None:
            options = {}
        if "allocator" in options:
            allocator = options.get("allocator")
            self.allocator = allocator if allocator is not None else self._allocator
        if "lambda" in options:
            mLambda = options.get("lambda")
            self.simulator.eventsGenerator.setLambda(mLambda)
        hard_reset = options.get("hard_reset", False)
        if hard_reset:
            self.simulator.network.restart()
            self.simulator.eventsGenerator.restart()
            self.numberOfArrivalEvents = 0
            self.event: Event = None
            self.connection: Connection = None
        return self.state(), {}

    @abstractmethod
    def _allocator(
        self,
        c: Connection,
        network: Network,
        action: int,
    ) -> Tuple[AllocationResult, Connection]:
        pass
