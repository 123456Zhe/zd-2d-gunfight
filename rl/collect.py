"""用现有行为树 AI 当教师，采集 (obs, action) 数据用于行为克隆。

多进程并行跑仿真，每个 worker 独立生成若干步转移，最后合并存成 .npz。
"""

import argparse
import multiprocessing as mp
import os
import time

import numpy as np

from .sim import HeadlessSim, OBS_DIM, ACTION_DIM


def _collect_chunk(job):
    (chunk_id, num_steps, n_opponents, difficulty, seed,
     max_episode_steps, spawn_mode, map_type, learner_personality) = job
    sim = HeadlessSim(
        n_opponents=n_opponents,
        opponent_difficulty=difficulty,
        max_episode_steps=max_episode_steps,
        learner_personality=learner_personality,
    )

    obs_buf = np.empty((num_steps, OBS_DIM), dtype=np.float32)
    act_buf = np.empty((num_steps, ACTION_DIM), dtype=np.float32)

    n = 0
    episode = 0
    episode_returns = []
    while n < num_steps:
        sim.reset(seed=seed + chunk_id * 1_000_003 + episode,
                  spawn_mode=spawn_mode, map_type=map_type)
        episode += 1
        ret = 0.0
        done = False
        while not done and n < num_steps:
            obs_t, label, _, reward, terminated, truncated, _ = sim.teacher_step()
            obs_buf[n] = obs_t
            act_buf[n] = label
            n += 1
            ret += reward
            done = terminated or truncated
        episode_returns.append(ret)

    stats = {
        "steps": n,
        "episodes": episode,
        "ep_return_mean": float(np.mean(episode_returns)) if episode_returns else 0.0,
    }
    return obs_buf[:n], act_buf[:n], stats


def collect(num_steps, n_opponents=1, difficulty="normal", seed=0,
            max_episode_steps=1800, workers=None, spawn_mode="close",
            map_type="random", learner_personality="aggressive", verbose=True):
    if workers is None:
        workers = max(1, min(os.cpu_count() or 1, 8))

    chunk = max(1, num_steps // workers)
    jobs = [
        (i, chunk, n_opponents, difficulty, seed, max_episode_steps,
         spawn_mode, map_type, learner_personality)
        for i in range(workers)
    ]

    t0 = time.time()
    if workers == 1:
        results = [_collect_chunk(jobs[0])]
    else:
        ctx = mp.get_context("spawn")
        with ctx.Pool(workers) as pool:
            results = pool.map(_collect_chunk, jobs)

    obs = np.concatenate([r[0] for r in results], axis=0)
    act = np.concatenate([r[1] for r in results], axis=0)
    elapsed = time.time() - t0

    if verbose:
        total = len(obs)
        print(f"[采集] {total} 步 / {workers} worker，耗时 {elapsed:.1f}s "
              f"({total / max(elapsed, 1e-6):.0f} steps/s)")
        print(f"[采集] 动作分布: shoot={act[:, 4].mean():.4f} "
              f"reload={act[:, 5].mean():.4f} "
              f"move_mag={(np.linalg.norm(act[:, :2], axis=1)).mean():.3f} "
              f"aim_mag={(np.linalg.norm(act[:, 2:4], axis=1)).mean():.3f} "
              f"(spawn={spawn_mode}, map={map_type}, teacher={learner_personality})")

    return obs, act


def main():
    ap = argparse.ArgumentParser(description="采集行为树教师数据")
    ap.add_argument("--steps", type=int, default=300_000)
    ap.add_argument("--opponents", type=int, default=1)
    ap.add_argument("--difficulty", default="normal")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-episode-steps", type=int, default=1800)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--spawn-mode", default="close",
                    choices=["spread", "close", "mixed"])
    ap.add_argument("--map-type", default="random",
                    choices=["grid3x3", "arena", "random"])
    ap.add_argument("--learner-personality", default="aggressive",
                    choices=["aggressive", "defensive", "tactical",
                             "stealthy", "team_player"])
    ap.add_argument("--out", default=os.path.join("rl", "data", "teacher.npz"))
    args = ap.parse_args()

    obs, act = collect(
        args.steps,
        n_opponents=args.opponents,
        difficulty=args.difficulty,
        seed=args.seed,
        max_episode_steps=args.max_episode_steps,
        workers=args.workers,
        spawn_mode=args.spawn_mode,
        map_type=args.map_type,
        learner_personality=args.learner_personality,
    )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    np.savez_compressed(args.out, obs=obs, act=act)
    print(f"[采集] 已保存 {args.out}  obs={obs.shape} act={act.shape}")


if __name__ == "__main__":
    main()
