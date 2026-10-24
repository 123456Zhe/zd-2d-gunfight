"""SAC 对照实验：off-policy + 连续动作，可与 PPO 在同环境同奖励下比较。

默认从 BC 权重热启动 actor（只用于加速，可用 --no-bc 关闭），再用 SAC 在线训练。
"""

import argparse
import os
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

from .bc import BCPolicy
from .env import make_env
from .sim import (
    R_AIM,
    R_CAMP,
    R_CAMP_GRACE,
    R_CAMP_MAX_MULT,
    R_DAMAGE_DEALT,
    R_DAMAGE_TAKEN,
    R_DEATH,
    R_KILL,
    R_STEP,
    R_WIN,
)
from .train_ppo import BestModelCallback, EvalCallback


def load_bc_into_actor(policy, bc_path, device="cpu"):
    """把 BC 的 MLP 权重灌进 SAC actor（latent_pi + mu 一一对应）。"""
    ckpt = torch.load(bc_path, map_location=device)
    bc = BCPolicy(ckpt["obs_dim"], ckpt["action_dim"], ckpt["hidden"])
    bc.load_state_dict(ckpt["state_dict"])
    bc.to(device)
    actor = policy.actor
    with torch.no_grad():
        actor.latent_pi[0].weight.copy_(bc.net[0].weight)
        actor.latent_pi[0].bias.copy_(bc.net[0].bias)
        actor.latent_pi[2].weight.copy_(bc.net[2].weight)
        actor.latent_pi[2].bias.copy_(bc.net[2].bias)
        actor.mu.weight.copy_(bc.net[4].weight)
        actor.mu.bias.copy_(bc.net[4].bias)
        actor.log_std.weight.zero_()
        actor.log_std.bias.fill_(-1.0)
    return ckpt["hidden"]


def distill_actor(model, data_path, steps=2000, batch_size=512, lr=1e-3,
                  device="cpu", verbose=True):
    """用教师数据对 actor 做少量监督蒸馏（连续 4 维 MSE，二值 2 维 BCE）。"""
    data = np.load(data_path)
    obs = torch.as_tensor(data["obs"], dtype=torch.float32, device=device)
    act = torch.as_tensor(data["act"], dtype=torch.float32, device=device)
    n = len(obs)
    actor = model.policy.actor
    optim = torch.optim.Adam(actor.parameters(), lr=lr)
    for step in range(1, steps + 1):
        idx = torch.randint(0, n, (batch_size,), device=device)
        ob, ac = obs[idx], act[idx]
        latent = actor.latent_pi(
            actor.extract_features(ob, actor.features_extractor)
        )
        mu = actor.mu(latent)
        l_cont = F.mse_loss(torch.tanh(mu[:, :4]), ac[:, :4])
        l_bin = F.binary_cross_entropy_with_logits(mu[:, 4:], ac[:, 4:])
        loss = l_cont + l_bin
        optim.zero_grad()
        loss.backward()
        optim.step()
        if verbose and step % max(1, steps // 5) == 0:
            print(f"[SAC-BC] {step}/{steps} loss={loss.item():.4f} "
                  f"cont={l_cont.item():.4f} bin={l_bin.item():.4f}", flush=True)
    return steps


class ActorWarmupCallback(BaseCallback):
    """预热期冻结 actor、只训 critic，避免随机价值梯度把 BC 热启动策略推崩。"""

    def __init__(self, warmup_steps, verbose=1):
        super().__init__(verbose)
        self.warmup_steps = max(int(warmup_steps), 0)
        self._frozen = False

    def _set_frozen(self, frozen):
        for param in self.model.policy.actor.parameters():
            param.requires_grad = not frozen
        self._frozen = frozen
        print(f"[SAC-WARMUP] step={self.num_timesteps} "
              f"{'冻结 actor，只训 critic' if frozen else '解冻 actor'}",
              flush=True)

    def _on_step(self):
        if self.warmup_steps <= 0:
            return True
        if not self._frozen and self.num_timesteps < self.warmup_steps:
            self._set_frozen(True)
        elif self._frozen and self.num_timesteps >= self.warmup_steps:
            self._set_frozen(False)
        return True


def main():
    ap = argparse.ArgumentParser(description="SAC 微调 ZD 枪战 AI")
    ap.add_argument("--timesteps", type=int, default=250_000)
    ap.add_argument("--n-envs", type=int, default=8)
    ap.add_argument("--opponents", type=int, default=2)
    ap.add_argument("--opponents-min", type=int, default=None)
    ap.add_argument("--opponents-max", type=int, default=None)
    ap.add_argument("--difficulty", default="hard")
    ap.add_argument("--max-episode-steps", type=int, default=1800)
    ap.add_argument("--spawn-mode", default="close",
                    choices=["spread", "close", "mixed"])
    ap.add_argument("--map-type", default="arena",
                    choices=["grid3x3", "arena", "random"])
    ap.add_argument("--opponent-hp", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--hidden", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--gamma", type=float, default=0.9995)
    ap.add_argument("--tau", type=float, default=0.005)
    ap.add_argument("--buffer-size", type=int, default=300_000)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--learning-starts", type=int, default=10_000)
    ap.add_argument("--gradient-steps", type=int, default=1)
    ap.add_argument("--ent-coef", default="0.001",
                    help='"auto" 或固定熵系数；二值 shoot/reload 维度过高会学成不开火')
    ap.add_argument("--actor-warmup", type=int, default=20_000,
                    help="前 N 步冻结 actor、只训 critic（0 = 关闭）")
    ap.add_argument("--bc", default=os.path.join("rl", "models", "bc_policy_v2.pt"))
    ap.add_argument("--bc-steps", type=int, default=2000,
                    help="灌权重后再做多少步监督蒸馏；0 = 只灌权重")
    ap.add_argument("--no-bc", action="store_true")
    ap.add_argument("--out", default=os.path.join("rl", "models", "sac_arena"))
    ap.add_argument("--ckpt-dir", default=os.path.join("rl", "checkpoints_sac"))
    ap.add_argument("--ckpt-freq", type=int, default=25_000)
    ap.add_argument("--eval-freq", type=int, default=25_000)
    ap.add_argument("--eval-episodes", type=int, default=20)
    ap.add_argument("--win-reward", type=float, default=R_WIN)
    ap.add_argument("--kill-reward", type=float, default=R_KILL)
    ap.add_argument("--death-reward", type=float, default=R_DEATH)
    ap.add_argument("--step-penalty", type=float, default=R_STEP)
    ap.add_argument("--aim-weight", type=float, default=R_AIM)
    ap.add_argument("--damage-dealt-weight", type=float, default=R_DAMAGE_DEALT)
    ap.add_argument("--damage-taken-weight", type=float, default=R_DAMAGE_TAKEN)
    ap.add_argument("--camp-penalty", type=float, default=R_CAMP)
    ap.add_argument("--camp-grace", type=float, default=R_CAMP_GRACE)
    ap.add_argument("--camp-max-mult", type=float, default=R_CAMP_MAX_MULT)
    args = ap.parse_args()

    opp_min = args.opponents if args.opponents_min is None else args.opponents_min
    opp_max = args.opponents if args.opponents_max is None else args.opponents_max

    reward_overrides = {
        "win": args.win_reward,
        "kill": args.kill_reward,
        "death": args.death_reward,
        "step": args.step_penalty,
        "aim": args.aim_weight,
        "damage_dealt": args.damage_dealt_weight,
        "damage_taken": args.damage_taken_weight,
        "camp_penalty": args.camp_penalty,
        "camp_grace": args.camp_grace,
        "camp_max_mult": args.camp_max_mult,
    }
    env_fns = [
        make_env(i, args.seed, opp_max, args.difficulty,
                 args.max_episode_steps, args.spawn_mode, args.map_type,
                 args.opponent_hp, reward_overrides=reward_overrides,
                 opponents_min=opp_min, opponents_max=opp_max)
        for i in range(args.n_envs)
    ]
    vec_env = SubprocVecEnv(env_fns) if args.n_envs > 1 else DummyVecEnv(env_fns)

    try:
        ent_coef = float(args.ent_coef)
    except ValueError:
        ent_coef = args.ent_coef

    model = SAC(
        "MlpPolicy",
        vec_env,
        learning_rate=args.lr,
        buffer_size=args.buffer_size,
        learning_starts=args.learning_starts,
        batch_size=args.batch_size,
        tau=args.tau,
        gamma=args.gamma,
        train_freq=1,
        gradient_steps=args.gradient_steps,
        ent_coef=ent_coef,
        policy_kwargs=dict(
            net_arch=[args.hidden, args.hidden],
            activation_fn=nn.Tanh,
        ),
        verbose=1,
        seed=args.seed,
        device="cpu",
    )

    loaded = False
    if not args.no_bc and os.path.exists(args.bc):
        hidden = load_bc_into_actor(model.policy, args.bc)
        loaded = True
        assert hidden == args.hidden, \
            f"BC hidden={hidden} 与 --hidden={args.hidden} 不一致"
        if args.bc_steps > 0:
            distill_actor(model, os.path.join("rl", "data", "teacher.npz"),
                          steps=args.bc_steps, device="cpu")
        print(f"[SAC] 已从 {args.bc} 热启动 actor", flush=True)

    os.makedirs(args.ckpt_dir, exist_ok=True)
    callbacks = [
        ActorWarmupCallback(args.actor_warmup),
        EvalCallback(
            eval_freq=args.eval_freq,
            episodes=args.eval_episodes,
            n_opponents=opp_max,
            difficulty=args.difficulty,
            max_episode_steps=args.max_episode_steps,
            map_type=args.map_type,
            spawn_mode=args.spawn_mode,
            opponent_hp_fraction=args.opponent_hp,
        ),
        BestModelCallback(args.out + "_best"),
        CheckpointCallback(
            save_freq=max(1, args.ckpt_freq // max(args.n_envs, 1)),
            save_path=args.ckpt_dir,
            name_prefix="sac_zd",
        ),
    ]

    print("=" * 72, flush=True)
    print(f"SAC STARTED  timesteps={args.timesteps} envs={args.n_envs} "
          f"opponents={opp_min}~{opp_max}({args.difficulty}) "
          f"map={args.map_type} spawn={args.spawn_mode} "
          f"gamma={args.gamma} lr={args.lr} hidden={args.hidden} "
          f"ent={ent_coef} actor_warmup={args.actor_warmup} "
          f"bc_init={'yes' if loaded else 'no'}", flush=True)
    print("=" * 72, flush=True)

    t0 = time.time()
    try:
        model.learn(total_timesteps=args.timesteps, callback=callbacks,
                    progress_bar=False)
    finally:
        elapsed = time.time() - t0
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        model.save(args.out)
        print(f"[SAC] 训练结束 耗时 {elapsed:.1f}s "
              f"({args.timesteps / max(elapsed, 1e-6):.0f} steps/s)，已保存 {args.out}.zip",
              flush=True)
        vec_env.close()


if __name__ == "__main__":
    main()
