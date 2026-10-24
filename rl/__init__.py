"""ZD 2D Gunfight 的强化学习训练包。

模块划分：
- clock: 仿真时钟，替换游戏逻辑里的 time.time()
- sim:   无头仿真环境（复用游戏的地图/碰撞/行为树AI逻辑）
- env:   Gymnasium 封装
- collect: 用现有行为树AI当教师采集 (obs, action) 数据
- bc:    行为克隆预训练
- train_ppo: PPO 微调
"""
