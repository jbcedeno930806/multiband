# from .masking import predict_with_valid_classes
import numpy as np


class MixerPolicy:
    def __init__(self, expert, student, beta):
        self.student = student
        self.expert = expert
        self.beta = beta
        # self.masking = mask

    def set(self, expert, student, beta):
        self.student = student
        self.expert = expert
        self.beta = beta

    def predict(self, observation, state, episode_start, deterministic):
        model = np.random.choice(["A", "B"], p=[self.beta, 1 - self.beta])
        if model == "A":
            return self.expert.predict(observation, state, episode_start, deterministic)
        else:
            # actions = predict_with_valid_classes(
            #     self.student, [observation], self.masking
            # )
            actions = self.student.predict([observation])
            return actions[0], None
