# -*- coding: utf-8 -*-
"""
Created on Wed Jun  1 17:33:53 2022

@author: redno
"""

from gym.envs.registration import register

register(
    id="RMSA_ENV-v0",
    entry_point="netsim.gym_basic.envs:RMSA_ENV",
)

register(
    id="STATE_RMSA_ENV-v0",
    entry_point="netsim.gym_basic.envs:STATE_RMSA_ENV",
)
register(
    id="STATE_RMSA2_ENV-v0",
    entry_point="netsim.gym_basic.envs:STATE_RMSA2_ENV",
)
