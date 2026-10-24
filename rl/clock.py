"""仿真时钟。

游戏代码（AI 行为树、AI 玩家、代价计算器等）大量使用 time.time() 做冷却与计时。
训练时无头仿真会以远超实时的速度步进，若沿用真实时间轴，所有冷却都会错乱
（例如 AI 在 60fps 下每 9 帧可射一次，仿真里会变成每 ~150 步才射一次）。

因此在仿真期间把全局 time.time() 替换为可推进的 SimClock，退出 with 块立即
恢复为真实时间，避免影响 torch / stable-baselines3 的计时与超时逻辑。
"""

import time

_REAL_TIME = time.time


class SimClock:
    """可手动推进的仿真时钟（可调用，模拟 time.time()）。"""

    __slots__ = ("t",)

    def __init__(self, start=1000.0):
        # 从一个非零时间起步，避免与 AI 初始化的 last_shot_time=0 等默认值混淆
        self.t = float(start)

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += float(dt)


class patched_time:
    """上下文管理器：块内 `time.time()` 返回仿真时间。"""

    def __init__(self, clock):
        self._clock = clock

    def __enter__(self):
        time.time = self._clock
        return self._clock

    def __exit__(self, exc_type, exc, tb):
        time.time = _REAL_TIME
        return False
