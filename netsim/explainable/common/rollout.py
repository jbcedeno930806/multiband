from sb3_contrib.common.maskable.utils import get_action_masks


def generate_trajectories(n_timesteps, model, env, only_accepted=True):
    trajectories = []
    timesteps_count = 0
    state = None
    done = False
    observation = env.reset()[0]
    actions = [0] * 15
    while timesteps_count < n_timesteps:
        action_masks = get_action_masks(env)
        act, state = model.predict(
            observation,
            state=state,
            episode_start=done,
            deterministic=True,
            action_masks=action_masks,
        )
        traj = {"obs": observation, "action": act}
        observation, reward, done, truncated, info = env.step(act)
        traj["reward"] = reward
        if only_accepted:
            if reward > 0:
                trajectories.append(traj)
                timesteps_count += 1
                actions[traj["action"]] += 1
        else:
            trajectories.append(traj)
            timesteps_count += 1
        if done:
            env.reset()
    return trajectories


def flatten_trajectories(traj):
    obs = [t["obs"] for t in traj]
    acts = [t["action"] for t in traj]
    rewards = [t["reward"] for t in traj]
    return obs, acts, rewards


def get_expert_acts(expert, obs, env):
    acts = []
    state = None
    done = False
    env.reset()
    action_masks = get_action_masks(env)
    for o in obs:
        act, state = expert.predict(
            o,
            state=state,
            episode_start=done,
            deterministic=True,
            action_masks=action_masks,
        )
        acts.append(act)
    return acts
