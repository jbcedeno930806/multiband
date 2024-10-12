# -*- coding: utf-8 -*-
from .randomVariable import RandomVariable
import math


class ExpVariable:

    def __init__(self, seed=1234567, parameter1=10):
        if parameter1 <= 0:
            raise ("Lambda parameter must be positive.")
        self.__rn = RandomVariable(seed, parameter1)

    # dist corresponde a un objeto en c++
    def getNextValue(self):
        return -1 * (
            math.log(1 - self.__rn.getDist(self.__rn.generator)) / self.__rn.parameter1
        )

    @property
    def rn(self):
        return self.__rn

    @rn.setter
    def rn(self, seed, parameter1):
        self.__rn = RandomVariable(seed, parameter1)
