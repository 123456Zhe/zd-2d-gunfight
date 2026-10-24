"""在无头仿真里评估策略表现。

支持两种策略来源：
- --bc  rl/models/bc_policy.pt        （行为克隆网络）
- --ppo rl/models/ppo_zd.zip          （stable-baselines3 PPO 模型）
不带参数则用随机策略作为基线。
"""

import argparse
import os

import numpy as np
import torch

from .sim import HeadlessSim, ACTION_DIM


def _bc_policy(path):
    from .bc import load as load_bc

    model = load_bc(path)

    def policy(obs):
        with torch.no_grad():
            cont, logits = model(torch.as_tensor(obs, dtype=torch.float32).unsqueeze(0))
        action = np.zeros(ACTION_DIM, dtype=np.float32)
        action[:4] = cont[0].numpy()
        action[4:] = np.where(logits[0].numpy() > 0, 1.0, -1.0)
        return action

    return policy


def _ppo_policy(path):
    from stable_baselines3 import PPO

    model = PPO.load(path, device="cpu")

    def policy(obs):
        action, _ = model.predict(obs, deterministic=True)
        return action

    return policy


def _random_policy(rng):
    def policy(obs):
        return rng.uniform(-1.0, 1.0, size=ACTION_DIM).astype(np.float32)

    return policy


def evaluate(policy, episodes=30, n_opponents=1, difficulty="normal",
             max_episode_steps=1800, spawn_mode="spread", map_type="grid3x3",
             opponent_hp_fraction=1.0, seed=20_000_000):
    sim = HeadlessSim(
        n_opponents=n_opponents,
        opponent_difficulty=difficulty,
        max_episode_steps=max_episode_steps,
        map_type=map_type,
        opponent_hp_fraction=opponent_hp_fraction,
    )
    survived, wins = 0, 0
    kills, deaths, dealt, taken, lengths, shots = [], [], [], [], [], []
    for ep in range(episodes):
        sim.reset(seed=seed + ep, spawn_mode=spawn_mode, map_type=map_type)
        done = False
        info = {}
        length = 0
        while not done:
            obs = sim.obs()
            _, _, terminated, truncated, info = sim.step(policy(obs))
            length += 1
            done = terminated or truncated
        survived += 1 if not info.get("learner_dead", False) else 0
        wins += 1 if info.get("win", False) else 0
        kills.append(info.get("kills", 0))
        deaths.append(info.get("deaths", 0))
        dealt.append(info.get("damage_dealt", 0.0))
        taken.append(info.get("damage_taken", 0.0))
        lengths.append(length)
        shots.append(info.get("shots", 0))

    return {
        "episodes": episodes,
        "win_rate": wins / episodes,
        "survive_rate": survived / episodes,
        "kills": float(np.mean(kills)),
        "deaths": float(np.mean(deaths)),
        "damage_dealt": float(np.mean(dealt)),
        "damage_taken": float(np.mean(taken)),
        "episode_len": float(np.mean(lengths)),
        "shots": float(np.mean(shots)),
    }


def _fmt(name, m, shots=True):
    base = (f"{name:<10} 胜率={m['win_rate']:.2f} 存活率={m['survive_rate']:.2f} "
            f"击杀={m['kills']:.2f} 死亡={m['deaths']:.2f} "
            f"输出伤害={m['damage_dealt']:.1f} "
            f"承受伤害={m['damage_taken']:.1f} 步数={m['episode_len']:.0f}")
    if shots:
        base += f" 射击={m['shots']:.0f}"
    return base


def main():
    ap = argparse.ArgumentParser(description="评估策略")
    ap.add_argument("--bc", default=None)
    ap.add_argument("--ppo", default=None)
    ap.add_argument("--episodes", type=int, default=30)
    ap.add_argument("--opponents", type=int, default=1)
    ap.add_argument("--difficulty", default="normal")
    ap.add_argument("--max-episode-steps", type=int, default=1800)
    ap.add_argument("--spawn-mode", default="spread",
                    choices=["spread", "close", "mixed"])
    ap.add_argument("--map-type", default="grid3x3",
                    choices=["grid3x3", "arena", "random"])
    ap.add_argument("--opponent-hp", type=float, default=1.0,
                    help="对手血量系数（课程学习用）")
    args = ap.parse_args()

    common = dict(
        episodes=args.episodes,
        n_opponents=args.opponents,
        difficulty=args.difficulty,
        max_episode_steps=args.max_episode_steps,
        spawn_mode=args.spawn_mode,
        map_type=args.map_type,
        opponent_hp_fraction=args.opponent_hp,
    )

    print(f"对手={args.opponents}({args.difficulty}) 对手血量={args.opponent_hp} "
          f"出生={args.spawn_mode} 地图={args.map_type} 局数={args.episodes}")

    rng = np.random.default_rng(0)
    print(_fmt("random", evaluate(_random_policy(rng), **common)))

    if args.bc and os.path.exists(args.bc):
        print(_fmt("BC", evaluate(_bc_policy(args.bc), **common)))
    if args.ppo and os.path.exists(args.ppo):
        print(_fmt("PPO", evaluate(_ppo_policy(args.ppo), **common)))


if __name__ == "__main__":
    main()
