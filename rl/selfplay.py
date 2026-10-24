"""自对弈对手：用当前策略的快照驱动对手。

主进程把 SB3 策略网络里与动作相关的权重导出成 npz；每个 worker 进程用一个纯
numpy 的 Tanh MLP 做前向，避免在 8 个环境进程里各加载一份 torch（省内存也更快）。
权重键名与 SB3 MlpPolicy 的 state_dict 完全对齐，因此可以直接复用。
"""

import numpy as np

_W0 = "mlp_extractor.policy_net.0.weight"
_B0 = "mlp_extractor.policy_net.0.bias"
_W2 = "mlp_extractor.policy_net.2.weight"
_B2 = "mlp_extractor.policy_net.2.bias"
_AW = "action_net.weight"
_AB = "action_net.bias"

SYNC_KEYS = (_W0, _B0, _W2, _B2, _AW, _AB)


def export_policy_state(policy, path):
    """把策略网络导出成 npz，供 worker 进程加载（只需 numpy）。"""
    sd = policy.state_dict()
    missing = [k for k in SYNC_KEYS if k not in sd]
    if missing:
        raise KeyError(f"策略网络缺少自对弈所需权重: {missing}")
    np.savez(path, **{k: sd[k].detach().cpu().numpy() for k in SYNC_KEYS})


class SnapshotPolicy:
    """确定性前向的策略快照，输入观测向量、输出动作向量。"""

    def __init__(self):
        self._w = None

    @property
    def ready(self):
        return self._w is not None

    def load(self, path):
        with np.load(path) as z:
            self._w = {k: z[k].astype(np.float32) for k in SYNC_KEYS}

    def __call__(self, obs):
        w = self._w
        if w is None:
            raise RuntimeError("自对弈权重尚未同步")
        x = np.asarray(obs, dtype=np.float32)
        h = np.tanh(x @ w[_W0].T + w[_B0])
        h = np.tanh(h @ w[_W2].T + w[_B2])
        return h @ w[_AW].T + w[_AB]
