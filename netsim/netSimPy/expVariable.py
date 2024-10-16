# -*- coding: utf-8 -*-
from .randomVariable import RandomVariable
import numpy as np


class ExpVariable:

    def __init__(self, seed=1234567, rate=10):
        if rate <= 0:
            raise ("Lambda parameter must be positive.")
        self.rate = rate
        np.random.seed(seed)
        # self.__rn = RandomVariable(seed, rate)

    # dist corresponde a un objeto en c++
    def getNextValue(self):

        return np.random.exponential(scale=1 / self.rate, size=1)

        # return -1 * (
        #     math.log(1 - self.__rn.getDist(self.__rn.generator)) / self.__rn.rate
        # )

    # @property
    # def rn(self):
    #     return self.__rn

    # @rn.setter
    # def rn(self, seed, rate):
    #     self.__rn = RandomVariable(seed, rate)
