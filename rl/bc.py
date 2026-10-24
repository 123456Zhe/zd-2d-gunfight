"""行为克隆预训练。

用一个 MLP 拟合教师 (obs -> action) 的映射：
- 前 4 维（移动向量 + 瞄准方向 cos/sin）线性输出 + MSE（**不加 tanh**，理由见 forward）；
- 后 2 维（shoot / reload）用 logits + BCE。

网络结构与 stable-baselines3 的 MlpPolicy(net_arch=[256,256]) 对齐，
训练完成后可直接把权重灌进 PPO 策略。
"""

import argparse
import os
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .sim import OBS_DIM, ACTION_DIM, N_RAYS, ENEMY_FEATURES

CONT_DIM = 4
BIN_DIM = ACTION_DIM - CONT_DIM  # 2

# 最近敌人在观测向量中的下标（每个敌人槽 8 维：dist, cos, sin, hp, alive, los, ...）
ENEMY_BASE_IDX = 7 + N_RAYS
NEAREST_DIST_IDX = ENEMY_BASE_IDX + 0
NEAREST_LOS_IDX = ENEMY_BASE_IDX + 5

# 距离已按地图尺寸归一化；450px / 1800px = 0.25，对应行为树 AI 的交战检测范围
COMBAT_DIST_THRESHOLD = 0.25


class BCPolicy(nn.Module):
    """输出 (连续 4 维, 二值 2 维 logits)，全部是线性输出。"""

    def __init__(self, obs_dim=OBS_DIM, action_dim=ACTION_DIM, hidden=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim, hidden), nn.Tanh(),
            nn.Linear(hidden, hidden), nn.Tanh(),
            nn.Linear(hidden, action_dim),
        )

    def forward(self, obs):
        out = self.net(obs)
        # 连续维不能加 tanh：PPO 的 action_net 是线性的，BC 在这里压了 tanh 的话，
        # 权重灌进 PPO 后前 4 维语义就对不上（实测同一观测下动作向量差 0.23）。
        # 动作空间本身有界：仿真里移动向量按长度归一化、瞄准只看方向。
        cont = out[..., :CONT_DIM]
        logits = out[..., CONT_DIM:]
        return cont, logits


def _split(obs, act, val_ratio=0.1, seed=0):
    n = len(obs)
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_val = int(n * val_ratio)
    val_idx, train_idx = idx[:n_val], idx[n_val:]
    return (obs[train_idx], act[train_idx]), (obs[val_idx], act[val_idx])


def _combat_weights(obs, combat_weight):
    """交战状态加权。

    只有在“敌人有视线且距离够近”时，行为树 AI 才会真正锁定目标、把枪口转向
    敌人；此时它的动作是可观测量的函数，值得让网络重点拟合。
    而巡逻状态下目标动作依赖大量不可观测量（巡逻点、路径索引），只会往损失里
    灌噪声，并让网络退化成“瞄准 = 保持当前朝向”的恒等映射。
    """
    w = np.ones(len(obs), dtype=np.float32)
    if combat_weight > 1.0:
        engaging = (obs[:, NEAREST_LOS_IDX] > 0.5) & (
            obs[:, NEAREST_DIST_IDX] < COMBAT_DIST_THRESHOLD
        )
        w[engaging] = combat_weight
    return w / w.mean()


def train(obs, act, epochs=60, batch_size=1024, lr=1e-3, hidden=256,
          weight_bin=1.0, max_pos_weight=20.0, combat_weight=4.0, val_ratio=0.1,
          seed=0, device="cpu", verbose=True):
    (tr_obs, tr_act), (va_obs, va_act) = _split(obs, act, val_ratio, seed)

    tr_w = _combat_weights(tr_obs, combat_weight)
    va_w = _combat_weights(va_obs, combat_weight)

    tr_obs = torch.as_tensor(tr_obs, dtype=torch.float32, device=device)
    tr_act = torch.as_tensor(tr_act, dtype=torch.float32, device=device)
    tr_w = torch.as_tensor(tr_w, dtype=torch.float32, device=device)
    va_obs = torch.as_tensor(va_obs, dtype=torch.float32, device=device)
    va_act = torch.as_tensor(va_act, dtype=torch.float32, device=device)
    va_w = torch.as_tensor(va_w, dtype=torch.float32, device=device)

    if verbose:
        engaging = ((tr_obs[:, NEAREST_LOS_IDX] > 0.5)
                    & (tr_obs[:, NEAREST_DIST_IDX] < COMBAT_DIST_THRESHOLD))
        print(f"[BC] 交战样本占比={float(engaging.float().mean()):.4f} "
              f"combat_weight={combat_weight}")

    # shoot / reload 是稀疏正类，用 pos_weight 做类别平衡，否则网络会退化成“永不开火”
    pos_rate = tr_act[..., CONT_DIM:].mean(dim=0)
    pos_weight = torch.clamp(
        (1.0 - pos_rate) / torch.clamp(pos_rate, min=1e-4),
        min=1.0, max=max_pos_weight,
    ).to(device)
    if verbose:
        print(f"[BC] 正类比例 shoot={float(pos_rate[0]):.4f} "
              f"reload={float(pos_rate[1]):.4f} -> pos_weight={pos_weight.tolist()}")

    torch.manual_seed(seed)
    model = BCPolicy(OBS_DIM, ACTION_DIM, hidden).to(device)
    optim = torch.optim.Adam(model.parameters(), lr=lr)

    def loss_fn(batch_obs, batch_act, batch_w):
        cont, logits = model(batch_obs)
        w = batch_w.unsqueeze(-1)
        l_cont = (w * (cont - batch_act[..., :CONT_DIM]) ** 2).mean()
        l_bin = F.binary_cross_entropy_with_logits(
            logits, batch_act[..., CONT_DIM:],
            pos_weight=pos_weight, weight=w,
        )
        return l_cont + weight_bin * l_bin, l_cont.detach(), l_bin.detach()

    n_train = len(tr_obs)
    best_val = float("inf")
    best_state = None
    patience, bad = 12, 0

    for epoch in range(1, epochs + 1):
        model.train()
        perm = torch.randperm(n_train, device=device)
        tot = 0.0
        nb = 0
        for i in range(0, n_train, batch_size):
            idx = perm[i:i + batch_size]
            loss, _, _ = loss_fn(tr_obs[idx], tr_act[idx], tr_w[idx])
            optim.zero_grad()
            loss.backward()
            optim.step()
            tot += loss.detach().item()
            nb += 1

        model.eval()
        with torch.no_grad():
            val_loss, val_cont, val_bin = loss_fn(va_obs, va_act, va_w)
            val_loss = float(val_loss)
            cont_p, logits_p = model(va_obs)
            shoot_pred = (logits_p[:, 0] > 0).float()
            reload_pred = (logits_p[:, 1] > 0).float()
            shoot_tgt = (va_act[:, CONT_DIM] > 0.5).float()
            reload_tgt = (va_act[:, CONT_DIM + 1] > 0.5).float()
            shoot_acc = float((shoot_pred == shoot_tgt).float().mean())
            reload_acc = float((reload_pred == reload_tgt).float().mean())
            shoot_positive_rate = float(shoot_pred.mean())

        if val_loss < best_val:
            best_val = val_loss
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            bad = 0
        else:
            bad += 1

        if verbose and (epoch % 5 == 0 or epoch == 1):
            print(f"[BC] epoch {epoch:3d} train={tot / max(nb,1):.4f} "
                  f"val={val_loss:.4f} (cont={float(val_cont):.4f} bin={float(val_bin):.4f}) "
                  f"shoot_acc={shoot_acc:.3f}(pred+={shoot_positive_rate:.3f}) "
                  f"reload_acc={reload_acc:.3f}")

        if bad >= patience:
            if verbose:
                print(f"[BC] 早停于 epoch {epoch}（val 连续 {patience} 轮未改善）")
            break

    model.load_state_dict(best_state)
    metrics = {
        "val_loss": best_val,
        "shoot_acc": shoot_acc,
        "shoot_pred_rate": shoot_positive_rate,
        "reload_acc": reload_acc,
    }
    return model, metrics


def save(model, path, hidden=256):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "obs_dim": OBS_DIM,
            "action_dim": ACTION_DIM,
            "hidden": hidden,
        },
        path,
    )


def load(path, device="cpu"):
    ckpt = torch.load(path, map_location=device)
    model = BCPolicy(ckpt["obs_dim"], ckpt["action_dim"], ckpt["hidden"])
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model


def main():
    ap = argparse.ArgumentParser(description="行为克隆预训练")
    ap.add_argument("--data", default=os.path.join("rl", "data", "teacher.npz"))
    ap.add_argument("--out", default=os.path.join("rl", "models", "bc_policy.pt"))
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--batch-size", type=int, default=1024)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--hidden", type=int, default=256)
    ap.add_argument("--weight-bin", type=float, default=1.0)
    ap.add_argument("--max-pos-weight", type=float, default=20.0)
    ap.add_argument("--combat-weight", type=float, default=4.0)
    args = ap.parse_args()

    data = np.load(args.data)
    obs, act = data["obs"], data["act"]
    print(f"[BC] 载入 {args.data}  obs={obs.shape} act={act.shape}")

    t0 = time.time()
    model, metrics = train(
        obs, act, epochs=args.epochs, batch_size=args.batch_size,
        lr=args.lr, hidden=args.hidden, weight_bin=args.weight_bin,
        max_pos_weight=args.max_pos_weight, combat_weight=args.combat_weight,
    )
    print(f"[BC] 训练完成 {time.time() - t0:.1f}s  指标={metrics}")

    save(model, args.out, hidden=args.hidden)
    print(f"[BC] 已保存 {args.out}")


if __name__ == "__main__":
    main()
