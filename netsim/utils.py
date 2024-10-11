import numpy as np
import pandas as pd
from .netSimPy import BitRate, Network, Link
import os
from sb3_contrib.common.maskable.utils import get_action_masks
import gym
from stable_baselines3.common.callbacks import EvalCallback
from sb3_contrib.common.maskable.callbacks import MaskableEvalCallback
from IPython.display import clear_output
from typing import List, Union, Callable, Optional, Dict, Tuple, Any
from stable_baselines3.common import base_class
import torch
from stable_baselines3.common.vec_env import (
    DummyVecEnv,
    VecEnv,
    VecMonitor,
    is_vecenv_wrapped,
)
import warnings
import optuna
from optuna.pruners import MedianPruner
from optuna.samplers import TPESampler


#######################################################
# -------------------- ENV UTILS -------------------- #
#######################################################


def get_shared_link(path: List[Link]):
    """Returns an array that represents the usage of the whole path
    Args:
        path (List[str]): _description_

    Returns:
        _type_: _description_
    """
    shared_link = [False] * min([link.getSlotsCount() for link in path])
    for link in path:
        for slotIndex in range(len(shared_link)):
            shared_link[slotIndex] = shared_link[slotIndex] or link.getSlotValue(
                slotIndex
            )
    return shared_link


def rle(inarray):
    """run length encoding. Partial credit to R rle function.
    Multi datatype arrays catered for including non Numpy
    returns: tuple (runlengths, startpositions, values)"""
    # from: https://stackoverflow.com/questions/1066758/find-length-of-sequences-of-identical-values-in-a-numpy-array-run-length-encodi
    ia = np.asarray(inarray)  # force numpy
    n = len(ia)
    if n == 0:
        return (None, None, None)
    else:
        y = np.array(ia[1:] != ia[:-1])  # pairwise unequal (string safe)
        i = np.append(np.where(y), n - 1)  # must include last element posi
        z = np.diff(np.append(-1, i))  # run lengths
        p = np.cumsum(np.append(0, z))[:-1]  # positions
        return p, ia[i], z


def get_available_blocks(b: BitRate, path: List[Link], max_blocks: Optional[int] = None):
    # getting available slots across the whole path
    # False if slot is available across all the links
    # True if not
    shared_link = get_shared_link(path)
    # getting the number of slots necessary for this service across this path
    slots = b.getBestModulationNumberOfSlots(path)
    # getting the blocks
    initial_indices, values, lengths = rle(shared_link)
    # selecting the indices where the block is available, i.e., equals to 0
    available_indices = np.where(values == False)

    # selecting the indices where the block has sufficient slots
    sufficient_indices = np.where(lengths >= slots)

    # getting the intersection, i.e., indices where the slots are available in sufficient quantity
    # and using as much max_blocks
    if max_blocks is not None:
        final_indices = np.intersect1d(available_indices, sufficient_indices)[:max_blocks]
    else:
        final_indices = np.intersect1d(available_indices, sufficient_indices)

    return initial_indices[final_indices], lengths[final_indices]


#######################################################
# -------------------- GYM UTILS -------------------- #
#######################################################


def evaluate_policy(
    env,
    n_eval_episodes: int = 10,
    model: Union["base_class.BaseAlgorithm", None] = None,
    deterministic: bool = True,
    render: bool = False,
    callback: Optional[Callable[[Dict[str, Any], Dict[str, Any]], None]] = None,
    reward_threshold: Optional[float] = None,
    warn: bool = True,
    return_episode_rewards: bool = False,
    heuristic_policy=None,
    return_dataframe=False,
    seed: int = 10,
    use_masking=False,
) -> Union[Tuple[float, float], Tuple[List[float], List[int]]]:
    """
    Runs policy for ``n_eval_episodes`` episodes and returns average reward.
    If a vector env is passed in, this divides the episodes to evaluate onto the
    different elements of the vector env. This static division of work is done to
    remove bias. See https://github.com/DLR-RM/stable-baselines3/issues/402 for more
    details and discussion.

    .. note::
        If environment has not been wrapped with ``Monitor`` wrapper, reward and
        episode lengths are counted as it appears with ``env.step`` calls. If
        the environment contains wrappers that modify rewards or episode lengths
        (e.g. reward scaling, early episode reset), these will affect the evaluation
        results as well. You can avoid this by wrapping environment with ``Monitor``
        wrapper before anything else.

    :param model: The RL agent you want to evaluate.
    :param env: The optical_network environment or ``VecEnv`` environment.
    :param n_eval_episodes: Number of episode to evaluate the agent
    :param deterministic: Whether to use deterministic or stochastic actions
    :param render: Whether to render the environment or not
    :param callback: callback function to do additional checks,
        called after each step. Gets locals() and globals() passed as parameters.
    :param reward_threshold: Minimum expected reward per episode,
        this will raise an error if the performance is not met
    :param return_episode_rewards: If True, a list of rewards and episode lengths
        per episode will be returned instead of the mean.
    :param warn: If True (default), warns user about lack of a Monitor wrapper in the
        evaluation environment.
    :return: Mean reward per episode, std of reward per episode.
        Returns ([float], [int]) when ``return_episode_rewards`` is True, first
        list containing per-episode rewards and second containing per-episode lengths
        (in number of steps).
    """
    # Avoid circular import
    from stable_baselines3.common.monitor import Monitor

    if not isinstance(env, VecEnv):
        env = DummyVecEnv([lambda: env])
    is_monitor_wrapped = (
        is_vecenv_wrapped(env, VecMonitor) or env.env_is_wrapped(Monitor)[0]
    )

    if not is_monitor_wrapped and warn:
        warnings.warn(
            "Evaluation environment is not wrapped with a ``Monitor`` wrapper. "
            "This may result in reporting modified episode lengths and rewards, if other wrappers happen to modify these. "
            "Consider wrapping environment first with ``Monitor`` wrapper.",
            UserWarning,
        )

    n_envs = env.num_envs
    episode_rewards = []
    episode_lengths = []

    episode_counts = np.zeros(n_envs, dtype="int")
    # Divides episodes among different sub environments in the vector as evenly as possible
    episode_count_targets = np.array(
        [(n_eval_episodes + i) // n_envs for i in range(n_envs)], dtype="int"
    )

    current_rewards = np.zeros(n_envs)
    current_lengths = np.zeros(n_envs, dtype="int")

    env.seed(seed)
    observations = env.reset()

    states = None
    episode_starts = np.ones((env.num_envs,), dtype=bool)
    df = {}
    while (episode_counts < episode_count_targets).any():
        if model is not None:
            if use_masking:
                action_masks = get_action_masks(env)
                actions, states = model.predict(
                    observations,
                    state=states,
                    episode_start=episode_starts,
                    deterministic=deterministic,
                    action_masks=action_masks,
                )
            else:
                acts, states = model.predict(
                    observations,
                    state=states,
                    episode_start=episode_starts,
                    deterministic=deterministic,
                )
                if isinstance(acts, tuple):
                    actions = [acts[0]]
                else:
                    actions = acts
        else:
            actions = heuristic_policy(observations)

        observations, rewards, dones, infos = env.step(actions)
        current_rewards += rewards
        current_lengths += 1
        for i in range(n_envs):
            if episode_counts[i] < episode_count_targets[i]:
                reward = rewards[i]
                done = dones[i]
                info = infos[i]
                episode_starts[i] = done

                if callback is not None:
                    callback(locals(), globals())

                if dones[i]:
                    if return_dataframe:
                        for key in info.keys():
                            if key in df:
                                df[key].append(info[key])
                            else:
                                df[key] = [info[key]]

                    if is_monitor_wrapped:
                        # Atari wrapper can send a "done" signal when
                        # the agent loses a life, but it does not correspond
                        # to the true end of episode
                        if "episode" in info.keys():
                            # Do not trust "done" with episode endings.
                            # Monitor wrapper includes "episode" key in info if environment
                            # has been wrapped with it. Use those rewards instead.
                            episode_rewards.append(info["episode"]["r"])
                            episode_lengths.append(info["episode"]["l"])
                            # Only increment at the real end of an episode
                            episode_counts[i] += 1
                    else:
                        episode_rewards.append(current_rewards[i])
                        episode_lengths.append(current_lengths[i])
                        episode_counts[i] += 1
                    current_rewards[i] = 0
                    current_lengths[i] = 0

        if render:
            env.render()

    mean_reward = np.mean(episode_rewards)
    std_reward = np.std(episode_rewards)
    if reward_threshold is not None:
        assert mean_reward > reward_threshold, (
            "Mean reward below threshold: " f"{mean_reward:.2f} < {reward_threshold:.2f}"
        )
    if return_episode_rewards:
        if return_dataframe:
            return episode_rewards, episode_lengths, pd.DataFrame(df)
        return episode_rewards, episode_lengths
    else:
        if return_dataframe:
            return mean_reward, std_reward, pd.DataFrame(df)
        return mean_reward, std_reward


class CustomCallback(MaskableEvalCallback):
    """Callback used for evaluating and reporting a trial."""

    # **IMPORTANT**
    # SELECT CAREFULLY THE "n_eval_episodes" AND "eval_freq" FOR SAVING A GOOD MODEL.
    # LARGE eval_freq MAY NOT CONSIDER TO SAVE WELL TRAINING MODELS.
    # A LARGE eval_freq MAY BE USED IN COMBINATION WITH LARGE TOTAL_TIMESTEPS IN MODEL TRAININGS
    def __init__(
        self,
        eval_env: gym.Env,
        trial: optuna.Trial = None,
        n_eval_episodes: int = 5,
        eval_freq: int = 10000,
        deterministic: bool = True,
        verbose: int = 0,
        log_path=None,
        use_masking: bool = False,
        verbose_type=0,
        output_name: str = "data.csv",
        env_metadata={
            "episode_length": 1000,
            "n_blocks": 5,
            "n_paths": 3,
            "slots": 344,
            "traffic": 10000,
        },
        info_keywords={
            "src": 0,
            "dst": 0,
            "bitRate": 0,
            "action": 0,
            "reward": 0,
            "service_blocking_rate": 0,
            "episode_service_blocking_rate": 0,
            "bit_rate_blocking_rate": 0,
            "episode_bit_rate_blocking_rate": 0,
        },
    ):
        super().__init__(
            eval_env=eval_env,
            n_eval_episodes=n_eval_episodes,
            eval_freq=eval_freq,
            deterministic=deterministic,
            verbose=0,
            log_path=log_path,
            best_model_save_path=log_path,
            use_masking=use_masking,
        )
        self.verbose = verbose
        self.verbose_type = verbose_type
        self.trial = trial
        self.eval_idx = 0
        self.is_pruned = False
        self.best_reward_at = 0
        self.output_name = output_name
        self.info_keywords = info_keywords
        # self.episode_infos = []
        df = pd.DataFrame([env_metadata])
        df.to_csv(self.output_name, mode="w", index=False)

    def update_locals(self, locals: dict[str, Any]):
        # Guardado de información
        super().update_locals(locals)
        envs_info = []

        info_keys = self.info_keywords
        for info in locals["infos"]:
            infos = {}
            for key in info.keys():
                if key in info_keys:
                    infos[key] = info[key]
            envs_info.append(infos)
        df = pd.DataFrame(envs_info)

        if self.n_calls == 0:
            df.to_csv(self.output_name, mode="a", index=False)
        else:
            df.to_csv(self.output_name, mode="a", header=False, index=False)

    def _on_step(self) -> bool:
        if self.eval_freq > 0 and self.n_calls % self.eval_freq == 0:
            super()._on_step()
            if self.last_mean_reward >= self.best_mean_reward:
                self.best_reward_at = self.num_timesteps
                # This code is used to get consider a best reward when
                # self.last_mean_reward == self.best_mean_reward
                # This is performed since I consider later model adjustements in training are relevant
                if self.last_mean_reward == self.best_mean_reward:
                    if self.best_model_save_path is not None:
                        self.model.save(
                            os.path.join(self.best_model_save_path, "best_model")
                        )
                    self.best_mean_reward = self.last_mean_reward
                    # Trigger callback on new best model, if needed
                    if self.callback_on_new_best is not None:
                        continue_training = self.callback_on_new_best.on_step()
                ### -----------------------------------------------------------------------------------------
            if self.verbose_type == 0 and self.trial is None:
                self.printInfo()
            self.eval_idx += 1
            if self.trial is not None:
                self.trial.report(self.last_mean_reward, self.eval_idx)
                # Prune trial if need.
                if self.trial.should_prune():
                    self.is_pruned = True
                    return False
        return True

    def printInfo(self):
        if len(self.evaluations_results) > 0:
            episode_rewards = self.evaluations_results[-1]
            std_reward = np.std(episode_rewards)
            self.verbose_type == 0 and clear_output(wait=True)
            print(
                f"Eval num_timesteps={self.num_timesteps}, "
                f"episode_reward={self.last_mean_reward:.2f} +/- {std_reward:.2f}"
            )
            print(
                f"Best mean reward: {self.best_mean_reward:.2f} at timestep No. {self.best_reward_at}"
            )


def linear_schedule(initial_value: float, final_value=0) -> Callable[[float], float]:
    """
    Linear learning rate schedule.

    :param initial_value: Initial learning rate.
    :return: schedule that computes
      current learning rate depending on remaining progress
    """

    def func(progress_remaining: float) -> float:
        """
        Progress will decrease from 1 (beginning) to 0.

        :param progress_remaining:
        :return: current learning rate
        """
        assert initial_value > final_value
        return final_value + progress_remaining * (initial_value - final_value)

    return func


def step_schedule(start_value, final_value, n_steps: 5) -> Callable[[float], float]:
    """
    Linear learning rate schedule.

    :param initial_value: Initial learning rate.
    :return: schedule that computes
      current learning rate depending on remaining progress
    """
    accum = (final_value - start_value) / n_steps
    step_width = 1 / n_steps

    def func(progress_remaining: float) -> float:
        """
        Progress will decrease from 1 (beginning) to 0.

        :param progress_remaining:
        :return: current learning rate
        """

        return start_value + (1 - progress_remaining) // step_width * accum

    return func


#######################################################
# -------- HYPERPARAMETER TUNNING WITH OPTUNA ------- #
#######################################################


def sample_PPO_params(trial: optuna.Trial) -> Dict[str, Any]:
    """Sampler for PPO hyperparameters."""
    gamma = round(trial.suggest_float("gamma", 0.96, 0.98, step=0.0025), 4)
    # max_grad_norm = trial.suggest_float("max_grad_norm", 2.4, 3.0, log=True)
    # gae_lambda = 1.0 - trial.suggest_float("gae_lambda", 0.009, 0.03, log=True)
    # n_steps = 2 ** trial.suggest_int("exponent_n_steps", 9, 10, True)
    learning_rate = trial.suggest_float("learning_rate", 0.001, 0.004, step=0.00025)
    # ent_coef = trial.suggest_float("ent_coef", 0.00000001, 2.0741e-8, log=True)
    # n_epochs = trial.suggest_int("n_epochs", 6, 10, True)

    # Display true values.
    trial.set_user_attr("gamma", gamma)
    # trial.set_user_attr("max_grad_norm", max_grad_norm)
    # trial.set_user_attr("gae_lambda_", gae_lambda)
    # trial.set_user_attr("n_steps", n_steps)
    trial.set_user_attr("learning_rate", learning_rate)
    # trial.set_user_attr("ent_coef", ent_coef)
    # trial.set_user_attr("n_epochs", n_epochs)

    return {
        # "n_steps": n_steps,
        # "n_epochs": n_epochs,
        "gamma": gamma,
        # "gae_lambda": gae_lambda,
        "learning_rate": learning_rate,
        # "ent_coef": ent_coef,
        # "max_grad_norm": max_grad_norm,
    }


def optimize(
    objective: Callable,
    n_trials=100,
    n_startup_trials=10,
    n_warmup_steps=0,
    study_name="NoName",
    **kwargs,
):
    torch.set_num_threads(1)

    sampler = TPESampler(n_startup_trials=n_startup_trials, seed=4)
    # Do not prune before 1/3 of the max budget is used.
    pruner = MedianPruner(
        n_startup_trials=n_startup_trials, n_warmup_steps=n_warmup_steps
    )

    study = optuna.create_study(
        sampler=sampler, pruner=pruner, direction="maximize", study_name=study_name
    )
    try:
        study.optimize(objective, n_trials=n_trials, **kwargs)
    except KeyboardInterrupt:
        pass

    print("Number of finished trials: ", len(study.trials))

    print("Best trial:")
    trial = study.best_trial

    print("  Value: ", trial.value)

    print("  Params: ")
    for key, value in trial.params.items():
        print("    {}: {}".format(key, value))

    print("  User attrs:")
    for key, value in trial.user_attrs.items():
        print("    {}: {}".format(key, value))

    return study


def get_episode_actions():
    with open("data.csv") as f:
        file = f.readlines()
        episode_length = int(file[1].split(",")[0])
        n_blocks = int(file[1].split(",")[1])
        n_paths = int(file[1].split(",")[2])
        n_episodes = (len(file) - 3) // episode_length
        episodes_action = []

        for n_episode in range(n_episodes):
            episode_actions = [0] * n_blocks * n_paths
            for line in file[
                3 + n_episode * episode_length : 3 + (n_episode + 1) * episode_length
            ]:
                (
                    src,
                    dst,
                    bitRate,
                    reward,
                    action,
                    episode_service_blocking_rate,
                    episode_bit_rate_blocking_rate,
                ) = line.split(",")
                episode_actions[int(action)] += 1
            episodes_action.append(episode_actions)
        return episodes_action
