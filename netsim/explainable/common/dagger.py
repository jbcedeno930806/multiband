import numpy as np
from .rollout import generate_trajectories, flatten_trajectories, get_expert_acts
from .policy import MixerPolicy
from .masking import predict_with_valid_classes, compute_mask
from sklearn.metrics import confusion_matrix
from sklearn.metrics import accuracy_score


class Dagger:
    def __init__(self, expert, student_policy, env, beta_func):
        self.expert = expert
        self.student_policy = student_policy
        self.env = env
        self.beta_func = beta_func
        self.masking = compute_mask(env)

    def train(self, n_rounds=10, timesteps_by_round=25000, n_evaluations=10000):
        print("Starting round 1")
        print("Sampling new trajectories for round: {1} ")
        # clear_output(wait=True)
        obs, acts, _rewards = flatten_trajectories(
            generate_trajectories(timesteps_by_round, self.expert, self.env)
        )
        self.student_policy.fit(obs, acts)
        evaluate_student(self.student_policy, self.expert, self.env, n_evaluations)

        for r in range(1, n_rounds):
            print(f"Starting round {r+1}")
            mixer = MixerPolicy(
                self.expert,
                self.student_policy,
                beta=self.beta_func(r),
                mask=self.masking,
            )
            print(f"Sampling new trajectories for round: {r+1} ")
            obs2, _acts, _rewards = flatten_trajectories(
                generate_trajectories(timesteps_by_round, mixer, self.env)
            )
            acts2 = get_expert_acts(self.expert, obs2, self.env)

            # extend and update:
            shuffle = np.arange(len(obs2))
            np.random.shuffle(shuffle)
            obs2 = [obs2[s] for s in shuffle]
            acts2 = [acts2[s] for s in shuffle]
            obs.extend(obs2)
            acts.extend(acts2)
            print(f"Fitting student for round: {r+1} ")
            self.student_policy.fit(obs, acts)
            evaluate_student(self.student_policy, self.expert, self.env, n_evaluations)

        return self.student_policy


def evaluate_student(student, expert, env, n_timesteps):
    traj = generate_trajectories(n_timesteps, expert, env)
    x_test = [t["obs"] for t in traj]
    y_test = [t["action"] for t in traj]
    masking = compute_mask(env)
    y_pred = predict_with_valid_classes(student, x_test, masking)

    conf_matrix = confusion_matrix(y_test, y_pred)
    score = accuracy_score(y_test, y_pred)
    print(score, conf_matrix)
