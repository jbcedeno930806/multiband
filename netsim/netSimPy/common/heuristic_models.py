class FirstFitModel:
    def predict(self, observation, state, episode_start, deterministic):
        if observation[28] >= 0:
            return 0, None
        elif observation[41] >= 0:
            return 5, None
        # elif observation[54] >= 0:
        #     return 9, None
        if observation[28] > -1:
            print("ERROR2")
        return 10, None
