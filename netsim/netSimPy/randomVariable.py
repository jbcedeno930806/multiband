# -*- coding: utf-8 -*-
from numpy.random import Generator, MT19937


class RandomVariable:

    def __init__(self, seed=1234567, parameter1=10):
        self.__generator = Generator(MT19937(seed))
        self.__parameter1 = parameter1
        self.__dist = self.__generator.uniform(0, 1.0)

    def getDist(self, generator):
        self.__dist = generator.uniform(0, 1.0)
        return self.__dist

    @property
    def generator(self):
        return self.__generator

    @generator.setter
    def bitRate(self, seed):
        self.__generator = Generator(MT19937(seed))

    @property
    def parameter1(self):
        return self.__parameter1

    @parameter1.setter
    def parameter1(self, paramenter):
        self.__parameter1 = paramenter

    @property
    def dist(self):
        return self.__dist

    @dist.setter
    def dist(self, generator):
        self.__dist = generator.uniform(0, 1.0)
