import numpy as np
import itertools
from .netSimPy import Link
from typing import List, Callable, Optional, Dict, Any
import torch
import optuna
from optuna.pruners import MedianPruner
from optuna.samplers import TPESampler


#######################################################
# -------------------- ENV UTILS -------------------- #
#######################################################


def get_shared_link(path: List[Link], band: str):
    """Returns an array that represents the usage of the whole path
    Args:
        path (List[str]): _description_

    Returns:
        _type_: _description_
    """
    shared_link = [False] * min([link.getSlotsCount(band) for link in path])
    for link in path:
        for slotIndex in range(len(shared_link)):
            shared_link[slotIndex] = shared_link[slotIndex] or link.getSlotValue(
                slotIndex, band
            )
    return shared_link


def rle(inarray):
    """run length encoding. Partial credit to R rle function.
    Multi datatype arrays catered for including non Numpy
    returns: tuple (runlengths, startpositions, values)"""

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


def get_available_blocks(
    slots: int, path: List[Link], band: str, max_blocks: Optional[int] = None
):
    # getting available slots across the whole path
    # False if slot is available across all the links
    # True if not
    shared_link = get_shared_link(path, band)
    # getting the number of slots necessary for this service across this path
    # getting the blocks
    initial_indices, values, lengths = rle(shared_link)
    # selecting the indices where the block is available, i.e., equals to 0
    available_indices = np.where(values == False)

    # selecting the indices where the block has sufficient slots
    sufficient_indices = np.where(lengths >= slots)

    # getting the intersection, i.e., indices where the slots are available in sufficient
    # quantity and using as much max_blocks
    if max_blocks is not None:
        final_indices = np.intersect1d(available_indices, sufficient_indices)[:max_blocks]
    else:
        final_indices = np.intersect1d(available_indices, sufficient_indices)

    return initial_indices[final_indices], lengths[final_indices]



def sample_PPO_params(trial: optuna.Trial) -> Dict[str, Any]:
    """Sampler for PPO hyperparameters."""
    learning_rate = trial.suggest_float("learning_rate", 0.0001, 0.001, step=0.0001)
    gamma = round(trial.suggest_float("gamma", 0.92, 0.98, step=0.01), 4)
    n_steps = 2 ** trial.suggest_int("n_steps", 6, 9, step=1)
    # batch_size = 2 ** trial.suggest_int("exponent_batch_size", 8, 12, True)
    n_epochs = trial.suggest_int("n_epochs", 10, 30, step=1)
    # max_grad_norm = trial.suggest_float("max_grad_norm", 2.4, 3.0, log=True)
    # gae_lambda = 1.0 - trial.suggest_float("gae_lambda", 0.009, 0.03, log=True)
    # ent_coef = trial.suggest_float("ent_coef", 0.00000001, 2.0741e-8, log=True)


    # Display true values.
    trial.set_user_attr("gamma", gamma)
    trial.set_user_attr("learning_rate", learning_rate)
    trial.set_user_attr("n_steps", n_steps)
    # trial.set_user_attr("batch_size", batch_size)
    trial.set_user_attr("n_epochs", n_epochs)
    # trial.set_user_attr("max_grad_norm", max_grad_norm)
    # trial.set_user_attr("gae_lambda_", gae_lambda)
    # trial.set_user_attr("ent_coef", ent_coef)

    return {
        "learning_rate": learning_rate,
        "gamma": gamma,
        "n_steps": n_steps,
        # "batch_size": batch_size,
        "n_epochs": n_epochs,
        # "gae_lambda": gae_lambda,
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




def pairwise(iterable):
    # pairwise('ABCDEFG') --> AB BC CD DE EF FG
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)