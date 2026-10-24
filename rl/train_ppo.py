"""PPO 微调。

先用行为克隆的权重初始化策略网络与 log_std，再在无头环境里做 PPO。
对手是游戏内置的行为树 AI（可调难度 / 数量）。
"""

import argparse
import os
import time

import numpy as np
import torch
import torch.nn as nn
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

from .bc import BCPolicy
from .env import make_env
from .selfplay import export_policy_state
from .sim import (
    ACTION_DIM,
    OBS_DIM,
    HeadlessSim,
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


def load_bc_into_policy(policy, bc_path, device="cpu"):
    ckpt = torch.load(bc_path, map_location=device)
    bc = BCPolicy(ckpt["obs_dim"], ckpt["action_dim"], ckpt["hidden"])
    bc.load_state_dict(ckpt["state_dict"])
    sd = bc.state_dict()
    with torch.no_grad():
        pn = policy.mlp_extractor.policy_net
        pn[0].weight.copy_(sd["net.0.weight"])
        pn[0].bias.copy_(sd["net.0.bias"])
        pn[2].weight.copy_(sd["net.2.weight"])
        pn[2].bias.copy_(sd["net.2.bias"])
        policy.action_net.weight.copy_(sd["net.4.weight"])
        policy.action_net.bias.copy_(sd["net.4.bias"])
    return ckpt["hidden"]


class EvalCallback(BaseCallback):
    """定期在独立仿真里跑确定性策略，统计存活率 / 击杀 / 伤害。"""

    def __init__(self, eval_freq=20_000, episodes=20, n_opponents=1,
                 difficulty="normal", max_episode_steps=1800, verbose=1,
                 map_type="grid3x3", spawn_mode="spread",
                 opponent_hp_fraction=1.0, hp_getter=None):
        super().__init__(verbose)
        self.eval_freq = eval_freq
        self.eval_episodes = episodes
        self.n_opponents = n_opponents
        self.difficulty = difficulty
        self.max_episode_steps = max_episode_steps
        self.map_type = map_type
        self.spawn_mode = spawn_mode
        self.opponent_hp_fraction = opponent_hp_fraction
        # 课程学习时跟随当前阶段血量，保证 EVAL 曲线在同一把尺子上
        self.hp_getter = hp_getter
        self._sim_hp = None
        self.sim = None
        # 用累计环境步数触发，而不是 n_calls：在 SB3 里 n_calls 只按 rollout 内
        # 循环计数（每个 rollout 只增加 n_steps 次），用取模会几乎永不触发。
        self.next_eval = eval_freq

    def _on_step(self):
        if self.eval_freq <= 0 or self.num_timesteps < self.next_eval:
            return True
        while self.next_eval <= self.num_timesteps:
            self.next_eval += self.eval_freq
        hp = self.opponent_hp_fraction
        if self.hp_getter is not None:
            hp = float(self.hp_getter())
        if self.sim is None or hp != self._sim_hp:
            self._sim_hp = hp
            self.sim = HeadlessSim(
                n_opponents=self.n_opponents,
                opponent_difficulty=self.difficulty,
                max_episode_steps=self.max_episode_steps,
                map_type=self.map_type,
                opponent_hp_fraction=hp,
            )

        survived, wins = 0, 0
        kills, deaths, dealt, taken, lengths = [], [], [], [], []
        for ep in range(self.eval_episodes):
            self.sim.reset(seed=10_000_000 + ep, spawn_mode=self.spawn_mode)
            done = False
            info = {}
            length = 0
            while not done:
                obs = self.sim.obs()
                action, _ = self.model.predict(obs, deterministic=True)
                _, _, terminated, truncated, info = self.sim.step(action)
                length += 1
                done = terminated or truncated
            survived += 1 if not info.get("learner_dead", False) else 0
            wins += 1 if info.get("win", False) else 0
            kills.append(info.get("kills", 0))
            deaths.append(info.get("deaths", 0))
            dealt.append(info.get("damage_dealt", 0.0))
            taken.append(info.get("damage_taken", 0.0))
            lengths.append(length)

        survive_rate = survived / self.eval_episodes
        win_rate = wins / self.eval_episodes
        msg = (f"[EVAL] step={self.num_timesteps} 对手血量={self._sim_hp:.2f} "
               f"胜率={win_rate:.2f} "
               f"存活率={survive_rate:.2f} "
               f"击杀={np.mean(kills):.2f} 死亡={np.mean(deaths):.2f} "
               f"输出伤害={np.mean(dealt):.1f} 承受伤害={np.mean(taken):.1f} "
               f"步数={np.mean(lengths):.0f}")
        if self.verbose:
            print(msg, flush=True)
        if self.logger is not None:
            self.logger.record("eval/win_rate", win_rate)
            self.logger.record("eval/survive_rate", survive_rate)
            self.logger.record("eval/kills", float(np.mean(kills)))
            self.logger.record("eval/deaths", float(np.mean(deaths)))
            self.logger.record("eval/damage_dealt", float(np.mean(dealt)))
            self.logger.record("eval/damage_taken", float(np.mean(taken)))
            self.logger.record("eval/episode_len", float(np.mean(lengths)))
        return True


class CurriculumCallback(BaseCallback):
    """对手血量课程：按训练进度分阶段推进。

    课程是这套环境里最有效的杠杆（自制 AI 的 difficulty 参数是失效的）。
    通过 env_method 直接改各 worker 的对手血量，评估回调经 hp_getter 跟随当前
    阶段，保证 EVAL 曲线全程可比。
    """

    def __init__(self, stages, total_timesteps, start_fraction=0.0, verbose=1):
        super().__init__(verbose)
        self.stages = [float(s) for s in stages]
        self.total_target = max(int(total_timesteps), 1)
        self.start_fraction = float(start_fraction)
        self.stage_index = -1

    def _stage_for(self, timesteps):
        if not self.stages:
            return 0
        progress = timesteps / self.total_target
        if progress <= self.start_fraction:
            return 0
        span = max(1e-9, 1.0 - self.start_fraction)
        idx = int((progress - self.start_fraction) / span * len(self.stages))
        return min(idx, len(self.stages) - 1)

    def hp_getter(self):
        if not self.stages:
            return 1.0
        return self.stages[max(0, self.stage_index)]

    def _on_step(self):
        if not self.stages:
            return True
        idx = self._stage_for(self.num_timesteps)
        if idx != self.stage_index:
            self.stage_index = idx
            hp = self.stages[idx]
            self.training_env.env_method("set_opponent_hp", hp)
            print(f"[CURRICULUM] step={self.num_timesteps} "
                  f"阶段 {idx + 1}/{len(self.stages)} 对手血量系数={hp}", flush=True)
        return True


class SelfPlayCallback(BaseCallback):
    """自对弈：定期把当前策略快照导出给各 worker，作为对手使用。

    第一次 _on_step 就同步，让对手从 BC 策略起步（而不是只有行为树），
    之后每 sync_freq 步刷新一次。对手动作与学员共用同一套编码。
    """

    def __init__(self, path, sync_freq=100_000, verbose=1):
        super().__init__(verbose)
        self.path = path
        self.sync_freq = max(int(sync_freq), 1)
        self.next_sync = 0

    def _on_step(self):
        if self.num_timesteps < self.next_sync:
            return True
        while self.next_sync <= self.num_timesteps:
            self.next_sync += self.sync_freq
        export_policy_state(self.model.policy, self.path)
        self.training_env.env_method("load_selfplay_weights", self.path)
        print(f"[SELFPLAY] step={self.num_timesteps} 已同步策略快照", flush=True)
        return True


class WarmupCallback(BaseCallback):
    """预热期只训 critic：前 warmup_steps 步冻结策略网络与 log_std。

    刚初始化时价值网络是随机的，优势估计基本是噪声；用一个已经不错的 BC 策略
    去吃这种噪声梯度，会被一步推出 BC 流形（实测 100 局 0.55 -> 0.26 且回不来）。
    """

    def __init__(self, warmup_steps, verbose=1):
        super().__init__(verbose)
        self.warmup_steps = max(int(warmup_steps), 0)
        self._frozen = False

    def _set_frozen(self, frozen):
        policy = self.model.policy
        for module in (policy.mlp_extractor.policy_net, policy.action_net):
            for param in module.parameters():
                param.requires_grad = not frozen
        policy.log_std.requires_grad = not frozen
        self._frozen = frozen
        print(f"[WARMUP] step={self.num_timesteps} "
              f"{'冻结策略，只训 critic' if frozen else '解冻策略，开始更新'}",
              flush=True)

    def _on_step(self):
        if self.warmup_steps <= 0:
            return True
        if not self._frozen and self.num_timesteps < self.warmup_steps:
            self._set_frozen(True)
        elif self._frozen and self.num_timesteps >= self.warmup_steps:
            self._set_frozen(False)
        return True


class BestModelCallback(BaseCallback):
    """盯住评估胜率，把最好的一版另存出来：评估掉分也能回滚，不会比起点更差。"""

    def __init__(self, save_path, metric="eval/win_rate", verbose=1):
        super().__init__(verbose)
        self.save_path = save_path
        self.metric = metric
        self.best = -float("inf")

    def _on_step(self):
        if self.logger is None:
            return True
        value = self.logger.name_to_value.get(self.metric)
        if value is None:
            return True
        if float(value) > self.best:
            self.best = float(value)
            self.model.save(self.save_path)
            print(f"[BEST] step={self.num_timesteps} {self.metric}={self.best:.3f} "
                  f"-> {self.save_path}.zip", flush=True)
        return True


def build_model(args, vec_env):
    # 使用标准对角高斯策略：动作无界，但环境会对移动向量做长度归一化、对瞄准做
    # 方向归一化、对开火/换弹只看符号，因此超范围动作是安全的。
    policy_kwargs = dict(
        net_arch=[args.hidden, args.hidden],
        activation_fn=nn.Tanh,
        log_std_init=args.log_std_init,
    )
    model = PPO(
        "MlpPolicy",
        vec_env,
        learning_rate=args.lr,
        n_steps=args.n_steps,
        batch_size=args.batch_size,
        n_epochs=args.n_epochs,
        gamma=args.gamma,
        gae_lambda=0.95,
        ent_coef=args.ent_coef,
        clip_range=0.2,
        target_kl=args.target_kl,
        vf_coef=0.5,
        max_grad_norm=0.5,
        verbose=1,
        policy_kwargs=policy_kwargs,
        seed=args.seed,
        device="cpu",
    )
    return model


def main():
    ap = argparse.ArgumentParser(description="PPO 微调 ZD 枪战 AI")
    ap.add_argument("--timesteps", type=int, default=1_000_000)
    ap.add_argument("--n-envs", type=int, default=8)
    ap.add_argument("--opponents", type=int, default=1)
    ap.add_argument("--difficulty", default="normal")
    ap.add_argument("--max-episode-steps", type=int, default=1800)
    ap.add_argument("--spawn-mode", default="mixed",
                    choices=["spread", "close", "mixed"])
    ap.add_argument("--map-type", default="random",
                    choices=["grid3x3", "arena", "random"])
    ap.add_argument("--opponent-hp", type=float, default=1.0,
                    help="对手血量系数；<1 作为课程学习，先让学员学会赢")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--hidden", type=int, default=256)
    # 热启动策略很脆：2e-4 会在最初几步把 BC 策略推偏（实测 1M 步后 0.55 -> 0.26）。
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--n-steps", type=int, default=1024)
    ap.add_argument("--batch-size", type=int, default=512)
    ap.add_argument("--n-epochs", type=int, default=5)
    ap.add_argument("--target-kl", type=float, default=0.05)
    # 回合上限 1800 步：gamma=0.995 时有效视野只有 200 步，
    # 第 1100 步才拿到的胜利会被折扣成 0.4%，"赢"这个目标等于不存在。
    ap.add_argument("--gamma", type=float, default=0.9995)
    ap.add_argument("--ent-coef", type=float, default=0.005)
    ap.add_argument("--log-std-init", type=float, default=-1.5)
    ap.add_argument("--bc", default=os.path.join("rl", "models", "bc_policy.pt"))
    ap.add_argument("--out", default=os.path.join("rl", "models", "ppo_zd"))
    ap.add_argument("--ckpt-dir", default=os.path.join("rl", "checkpoints"))
    ap.add_argument("--eval-freq", type=int, default=50_000)
    ap.add_argument("--eval-episodes", type=int, default=10)
    ap.add_argument("--no-bc", action="store_true")
    ap.add_argument("--warmup-steps", type=int, default=50_000,
                    help="前 N 步冻结策略、只训 critic（0 = 关闭）")
    ap.add_argument("--resume", default=None,
                    help="从已有 PPO 检查点续训；--timesteps 仍是累计目标步数")
    ap.add_argument("--ckpt-freq", type=int, default=50_000,
                    help="检查点间隔（环境总步数）")
    ap.add_argument("--curriculum", default="",
                    help="对手血量课程，逗号分隔（如 0.3,0.5,0.7,1.0）；留空用 --opponent-hp")
    ap.add_argument("--curriculum-start", type=float, default=0.0,
                    help="课程开始前的训练进度比例")
    ap.add_argument("--selfplay-prob", type=float, default=0.0,
                    help="每局把对手换成当前策略快照的概率（0 = 关闭自对弈）")
    ap.add_argument("--selfplay-sync", type=int, default=100_000,
                    help="自对弈策略快照刷新间隔（环境总步数）")
    ap.add_argument("--win-reward", type=float, default=R_WIN)
    ap.add_argument("--kill-reward", type=float, default=R_KILL)
    ap.add_argument("--death-reward", type=float, default=R_DEATH)
    ap.add_argument("--step-penalty", type=float, default=R_STEP)
    ap.add_argument("--aim-weight", type=float, default=R_AIM)
    ap.add_argument("--damage-dealt-weight", type=float, default=R_DAMAGE_DEALT)
    ap.add_argument("--damage-taken-weight", type=float, default=R_DAMAGE_TAKEN)
    ap.add_argument("--camp-penalty", type=float, default=R_CAMP,
                    help="苟着（长时间不交火）每步扣分基数；0 = 关闭")
    ap.add_argument("--camp-grace", type=float, default=R_CAMP_GRACE,
                    help="多久没交火开始扣分（秒）")
    ap.add_argument("--camp-max-mult", type=float, default=R_CAMP_MAX_MULT,
                    help="扣分随苟着时长增长的倍数上限")
    args = ap.parse_args()

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
        make_env(i, args.seed, args.opponents, args.difficulty,
                 args.max_episode_steps, args.spawn_mode, args.map_type,
                 args.opponent_hp, selfplay_prob=args.selfplay_prob,
                 reward_overrides=reward_overrides)
        for i in range(args.n_envs)
    ]
    vec_env = SubprocVecEnv(env_fns) if args.n_envs > 1 else DummyVecEnv(env_fns)

    reset_timesteps = True
    loaded = False
    if args.resume:
        model = PPO.load(args.resume, env=vec_env, device="cpu")
        reset_timesteps = False
        print(f"[PPO] 从 {args.resume} 续训，已完成 {model.num_timesteps} 步", flush=True)
    else:
        model = build_model(args, vec_env)
        if not args.no_bc and os.path.exists(args.bc):
            hidden = load_bc_into_policy(model.policy, args.bc)
            loaded = True
            assert hidden == args.hidden, \
                f"BC hidden={hidden} 与 --hidden={args.hidden} 不一致"

    os.makedirs(args.ckpt_dir, exist_ok=True)

    curriculum = None
    if args.curriculum.strip():
        stages = [float(s) for s in args.curriculum.split(",") if s.strip()]
        curriculum = CurriculumCallback(
            stages, args.timesteps, start_fraction=args.curriculum_start
        )

    callbacks = [WarmupCallback(args.warmup_steps)]
    if args.selfplay_prob > 0.0:
        callbacks.append(SelfPlayCallback(
            os.path.join(args.ckpt_dir, "selfplay_policy.npz"),
            sync_freq=args.selfplay_sync,
        ))
    if curriculum is not None:
        callbacks.append(curriculum)
    callbacks.append(EvalCallback(
        eval_freq=args.eval_freq,
        episodes=args.eval_episodes,
        n_opponents=args.opponents,
        difficulty=args.difficulty,
        max_episode_steps=args.max_episode_steps,
        map_type=args.map_type,
        spawn_mode=args.spawn_mode,
        opponent_hp_fraction=args.opponent_hp,
        hp_getter=(curriculum.hp_getter if curriculum is not None else None),
    ))
    callbacks.append(BestModelCallback(args.out + "_best"))
    callbacks.append(CheckpointCallback(
        save_freq=max(1, args.ckpt_freq // max(args.n_envs, 1)),
        save_path=args.ckpt_dir,
        name_prefix="ppo_zd",
    ))

    print("=" * 72, flush=True)
    print(f"TRAINING STARTED  timesteps={args.timesteps} envs={args.n_envs} "
          f"opponents={args.opponents}({args.difficulty}) "
          f"map={args.map_type} spawn={args.spawn_mode} "
          f"opp_hp={args.opponent_hp} "
          f"curriculum={args.curriculum or '-'} "
          f"selfplay={args.selfplay_prob}(sync {args.selfplay_sync}) "
          f"gamma={args.gamma} "
          f"bc_init={'yes' if loaded else ('resume' if args.resume else 'no')} "
          f"log_std={args.log_std_init}", flush=True)
    print(f"奖励: step={args.step_penalty} aim={args.aim_weight} "
          f"dealt={args.damage_dealt_weight} taken={args.damage_taken_weight} "
          f"kill={args.kill_reward} win={args.win_reward} "
          f"death={args.death_reward} "
          f"camp={args.camp_penalty}(grace {args.camp_grace}s, "
          f"max x{args.camp_max_mult})", flush=True)
    print("=" * 72, flush=True)

    t0 = time.time()
    try:
        model.learn(
            total_timesteps=args.timesteps,
            callback=callbacks,
            progress_bar=False,
            reset_num_timesteps=reset_timesteps,
        )
    finally:
        # SubprocVecEnv 的子进程不会被 SB3 自动回收：不显式 close 时主进程会在
        # 训练结束后一直挂着不退出（nohup/CI 里表现为任务永不结束）。
        elapsed = time.time() - t0
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        model.save(args.out)
        print(f"[PPO] 训练结束 耗时 {elapsed:.1f}s "
              f"({args.timesteps / max(elapsed, 1e-6):.0f} steps/s)，已保存 {args.out}.zip")
        vec_env.close()


if __name__ == "__main__":
    main()
