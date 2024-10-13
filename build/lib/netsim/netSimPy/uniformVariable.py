# -*- coding: utf-8 -*-
from numpy.random import Generator, MT19937, SeedSequence


class UniformVariable:
    def __init__(self, seed, parameter):
        if parameter < 0:
            raise ("Parameter 1  must be positive.")
        self.__parameter = parameter
        sg = SeedSequence(seed)
        self.__generator = Generator(MT19937(sg))
        # self._dist = np.random.uniform(0, parameter, parameter)
        self._dist = self.__generator.uniform(0, 1.0)

    def getNextValue(self):
        return self.__generator.random() * self.__parameter

    def getNextIntValue(self):
        return int(self.__generator.random() * self.__parameter)

    @property
    def parameter(self):
        return self.__parameter

    @parameter.setter
    def parameter(self, parameter):
        self.__parameter = parameter

    @property
    def generator(self):
        return self.__generator

    @parameter.setter
    def parameter(self, seed):
        sg = SeedSequence(seed)
        self.__generator = Generator(MT19937(sg))

    @property
    def dist(self):
        return self.__dist
