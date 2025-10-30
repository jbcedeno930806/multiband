# -*- coding: utf-8 -*-
"""
Created on Wed Jun  1 17:33:53 2022

@author: redno
"""

from gymnasium.envs.registration import register

register(
    id="RMSA_ENV-v0",
    entry_point="netsim.gym_basic.envs:RMSA_ENV",
)

register(
    id="RMSA_ENV_LARGE-v0",
    entry_point="netsim.gym_basic.envs:RMSA_ENV_LARGE",
)

register(
    id="MASKING_RMSA_ENV-v0",
    entry_point="netsim.gym_basic.envs:MASKING_RMSA_ENV",
)

register(
    id="S_RMSA_ENV_BEST-v0",
    entry_point="netsim.gym_basic.envs:S_RMSA_ENV_BEST",
)

register(
    id="ROUTING_ENV-v0",
    entry_point="netsim.gym_basic.envs:ROUTING_ENV",
)

register(
    id="ROUTING_MASKED_ENV-v0",
    entry_point="netsim.gym_basic.envs:ROUTING_MASKED_ENV",
)
