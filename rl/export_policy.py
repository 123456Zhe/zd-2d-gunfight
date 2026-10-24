"""把 SB3 PPO 策略导出成游戏可用的纯 numpy npz。"""

import argparse
import os

from stable_baselines3 import PPO

from .selfplay import export_policy_state


def main():
    ap = argparse.ArgumentParser(description="导出 PPO 策略为游戏推理权重")
    ap.add_argument("--model", default=os.path.join("rl", "models", "ppo_mix3_best.zip"))
    ap.add_argument("--out", default=os.path.join("assets", "rl_ai_policy.npz"))
    args = ap.parse_args()

    model = PPO.load(args.model, device="cpu")
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    export_policy_state(model.policy, args.out)
    print(f"[EXPORT] {args.model} -> {args.out}")


if __name__ == "__main__":
    main()
