# RL 训练包（ZD 2D Gunfight）

用**行为克隆热启动 + PPO 微调**训练一个对战 AI。整套东西跑在**无头仿真**上，
不渲染、不联网，可多进程并行采样。

工作目录：项目根目录（`/home/zhe/zd-2d-gunfight`）。

---

## 1. 快速开始

```bash
# 0) 环境（已创建，含 torch-cpu + stable-baselines3）
#    依赖：pygame / pathfinding / numpy / gymnasium / torch / stable-baselines3
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install --index-url https://download.pytorch.org/whl/cpu torch
.venv/bin/python -m pip install stable_baselines3

# 1) 用内置行为树 AI 当教师采集 (obs, action) 数据
.venv/bin/python -m rl.collect --steps 400000 --workers 10 \
    --spawn-mode close --map-type random --learner-personality aggressive \
    --out rl/data/teacher.npz

# 2) 行为克隆预训练（输出可被 PPO 直接加载的初始化权重）
.venv/bin/python -m rl.bc --data rl/data/teacher.npz --epochs 40 \
    --combat-weight 6.0 --out rl/models/bc_policy.pt

# 3) PPO 微调（BC 权重会自动灌进策略网络）
.venv/bin/python -m rl.train_ppo --timesteps 1000000 --n-envs 8 \
    --map-type random --spawn-mode mixed --opponent-hp 0.5 \
    --gamma 0.995 --out rl/models/ppo_zd

# 4) 评估
.venv/bin/python -m rl.evaluate --bc rl/models/bc_policy.pt \
    --ppo rl/models/ppo_zd.zip --episodes 20 --spawn-mode close
```

## 2. 文件说明

| 文件 | 作用 |
|------|------|
| `clock.py` | 仿真时钟。游戏逻辑大量依赖 `time.time()` 做冷却，训练时仿真速度远超实时，必须在步进期间把时间源替换掉，退出立即还原（否则 `time.time` 冻结会干扰 torch/sb3 的计时与超时） |
| `sim.py` | **核心**。无头仿真：复用 `Map` / `EnhancedAIPlayer` / 碰撞与子弹逻辑，脱离渲染与网络。含观测/动作编解码、奖励、占据网格射线与视线 |
| `env.py` | Gymnasium 封装（`Box` 观测/动作 + `make_env` 工厂，供 `SubprocVecEnv` 使用） |
| `collect.py` | 行为树教师数据采集（多进程） |
| `bc.py` | 行为克隆（网络结构与 SB3 `MlpPolicy(net_arch=[256,256])` 对齐，权重可直灌） |
| `train_ppo.py` | PPO 微调 + 定期评估回调（支持每局随机 1~3 对手） |
| `train_sac.py` | SAC 对照实验（BC actor 热启动 + 蒸馏；当前版本会崩，见第 12 节） |
| `evaluate.py` | 评估 BC / PPO / SAC / 随机基线 |
| `export_policy.py` | 把 PPO 策略导出成游戏用的纯 numpy npz |

## 3. 接口设计

**观测（47 维向量）**

| 段 | 维度 | 内容 |
|----|------|------|
| 自身 | 7 | 血量、弹药比例、是否换弹、sin/cos(朝向)、位置 x/y |
| 射线 | 16 | 以自身朝向为基准每 22.5° 一条，归一化到最近障碍距离 |
| 敌人×3 | 8×3 | 距离、相对方位 sin/cos、血量、存活、是否有视线、是否开火、是否换弹 |

只用射线 + 相对量，不用像素：Pygame 渲染太慢，CNN 训练成本高。

**动作（6 维，`Box(-1,1)`）**：`[move_x, move_y, aim_cos, aim_sin, shoot, reload]`

环境对超范围动作是安全的：移动向量按长度归一化、瞄准按方向归一化、开火/换弹只看符号。
（PPO 用标准对角高斯，动作无界，靠这一层兜底。）

**回合**：击杀对手即胜（`+1`），阵亡即负（`-1`），超时截断（无奖励）。
对手**不复活**——这样才有明确的"赢"这个目标。

## 4. 奖励设计

```
每步 = -0.0005                          # 轻微催促结束
      + 0.0005 × 对准可见敌人程度        # 连续塑形（不是"对准才给分"）
      + 0.01 × 造成伤害
      - 0.01 × 承受伤害
      + 1.0  × 击杀
终局 = +1.0 胜利 / -1.0 阵亡
```

两个**必须避免**的坑（都实测踩过）：

1. **不要给"存活到超时"正奖励** —— 加了 `+0.5` 之后策略立刻学会远远绕圈不打。
2. **瞄准塑形必须很小** —— 给到 `0.002/步`（整局上限 +2.4）时，"枪口对着敌人绕圈但不开火"
   比真打（击杀 +2、阵亡 −1）更划算，PPO 直接把输出伤害从 45 训到 16.7。

## 5. 地图选择器与新增地图

`map.py` 现在支持 `Map(map_type)`：

- `"grid3x3"`：原九宫格（**默认，游戏行为完全不变**）
- `"arena"`：同尺寸（1800×1800）开放式竞技场，只有外墙 + 中央十字 + 四角/四边掩体，无房间分隔、无门

配置入口：`settings.json` → `map.type`（`config.py` 的 `MAP_TYPE`，`main.py` 用它建图）。
RL 侧额外支持 `"random"`（每局随机采样），用于泛化。

**实测结论（与直觉相反）**：分隔性**不是**训练效果差的主因。

| 地图 | 出生 | 平均输出伤害 | 有交火局占比 |
|------|------|------|------|
| grid3x3 | spread | 13.0 | 0.25 |
| arena | spread | 7.0 | 0.20 |
| grid3x3 | close | 52.0 | 0.65 |
| arena | close | 16.0 | 0.30 |

九宫格的门起到了**漏斗**作用，反而比开阔地图更容易撞上敌人。
真正的瓶颈是**出生距离 + 检测范围（300~400px）+ 随机巡逻**，所以 `--spawn-mode close`
才是提高学习信号最有效的杠杆。arena 的价值在于视线通畅、便于学瞄准，以及泛化。

## 6. 重要发现

- **内置 AI 的难度参数是生效的**（早期本文档判断为"失效"，已过时）：`reaction_time`
  在 `ai_has_reacted()` 里限制锁定后的开火延迟，`accuracy` 在 `apply_aim_skill()` 里
  叠加到子弹方向上。close 出生、固定 aggressive 性格、40 局实测：

  | 难度 | 学员胜率 | 学员承伤 | 对手每局开火 |
  |------|------|------|------|
  | easy | 0.93 | 2.5 | 0.1 |
  | normal | 0.90 | 8.5 | 0.5 |
  | hard | 0.38 | 73.5 | 2.9 |

  但三档跨度太大（easy/normal 几乎不开火），做精细课程不如 `--opponent-hp` 平滑；
  难度可以当粗粒度分层使用。
- **教师性格决定数据质量**。用 `tactical` 当教师时，其行为树优先级是
  "装填 > 支援 > 协同 > **侧翼** > 掩护 > 攻击"，大部分时间在跑位：整局只开 3.5 枪。
  换成 `aggressive` 后单局开火 9.1 枪、输出伤害 110（vs 62.5）。**采集务必用 aggressive。**
- **BC 的失效模式是"恒等映射"**。观测里含 `sin/cos(自身朝向)`，而巡逻状态下教师 angle
  就等于移动方向，于是 MSE 会退化成"瞄准 = 保持当前朝向"。解法是只对
  "敌人有视线且距离 < 450px"的交战样本加权（`--combat-weight`），让网络重点拟合真正
  由可观测量决定的条件行为。
- **SB3 的 `n_calls` 不能用来触发定期评估**：它只按 rollout 内循环计数（每个 rollout
  仅 +`n_steps`），取模几乎永不触发。评估回调改用累计 `num_timesteps` 阈值。
- **`squash_output=True` 在 SB3 2.9 必须配 gSDE**，否则直接 assert 失败。这里用标准
  对角高斯 + 环境侧兜底。

## 7. 当前状态与下一步

已验证：

| 策略 | 胜率 | 输出伤害 | 射击次数 |
|------|------|------|------|
| 随机 | 0.00 | 2.0 | 2.6 |
| BC（起点） | 0.00 | 38.0 | 6.9 |
| 内置行为树教师 | ~0.25 | 92~110 | 6.4~9.1 |
| PPO 300k（对手血量 0.5） | 0.2~0.4 | ~28 | — |
| v3_best（grid 1v1 close） | 0.83 | 87.3 | 14 |
| arena2_best（arena 1v1 close） | 0.85 | 91.0 | 18 |
| arena2_best（arena 1v2 close） | 0.72 | 167.6 | 30 |
| arena2_best（grid 1v2 close） | 0.72 | 172.4 | 21 |

- BC 明显强于随机，达到教师的 ~40%——作为热启动是合格的。
- 交战状态下瞄准误差中位数仅 **8°**、有视线时开火率 **89~99%**，说明观测/动作/机制都正常。
- PPO 训练稳定（`approx_kl ≈ 0.02`、`clip_fraction ≈ 0.2`），但 200k~300k 步内**没有明显上升趋势**。

因此：**管线是通的、训练能跑，但还没训出一个强 AI。** 下一步按性价比排序：

1. **加长训练**：游戏 AI 的 RL 通常需要 1e6~1e7 步，当前只跑了 3e5。
2. **课程推进**：`--opponent-hp 0.3 → 0.5 → 0.7 → 1.0` 分段训练，每段从上段权重续训。
3. **自对弈**：把对手换成历史策略快照（league），避免被固定脚本 bot 卡住上限。
4. **奖励精调**：当前 `承受伤害` 与 `造成伤害` 同权重，容易诱导避战；可下调并加重击杀权重。
5. **观测增强**：加入"敌人最后已知位置"（带时间衰减），对应行为树 AI 的声音记忆，
   缓解丢失目标后的盲目。
6. **粗粒度难度分层**：`--difficulty easy|normal|hard` 已生效（见第 6 节实测），
   可作为入门/最终门槛；与 `--opponent-hp` 组合使用比单用难度更平滑。

## 8. 性能参考

- 采集（10 进程，close 出生）：**~1500~2900 steps/s**
- PPO（8 个并行环境，CPU）：**~870 steps/s**（含梯度更新）
- 单进程仿真的瓶颈是 `EnhancedAIPlayer` 的 A\* 寻路（失败路径会遍历整张网格）

## 9. 产出的文件

```
rl/data/teacher.npz          # 教师数据集
rl/models/bc_policy.pt       # 行为克隆权重
rl/models/ppo_zd.zip         # PPO 权重（SB3 格式）
rl/models/ppo_v3_best.zip    # grid close 1v1 最佳
rl/models/ppo_arena2_best.zip # arena close 1v2 最佳（950k）
rl/models/ppo_mix3_best.zip  # arena 1~3 对手 + 50% 自对弈最佳（1.35M）
rl/models/sac_arena2b_best.zip # SAC 对照组最佳（仅 25k，0.30）
rl/checkpoints/              # 训练中途检查点
rl/checkpoints_arena2/       # arena 遭遇战训练检查点
```

游戏本身不受影响：`Map()` 默认仍是 `grid3x3`，`settings.json` 的 `map.type` 也是 `grid3x3`。

## 10. 自对弈与课程学习

### 先修的一个关键 bug：gamma 与回合长度不匹配

回合上限 1800 步，而 `--gamma 0.995` 的有效视野只有 `1/(1-0.995)=200` 步。
第 1100 步才拿到的胜利 `+1` 会被折扣成 `0.995^1100 ≈ 0.004`，**"赢"这个目标等于
不存在**；策略实际只在优化"未来 200 步内多打伤害、少挨伤害"，于是学会苟着不打完。
实测：1M 步 PPO 把 BC 从胜率 0.37 / 伤害 44.2 练到 0.18 / 27.4（100 局评估，
两个条件都是腰斩）。

默认 gamma 已改为 **0.9995**（有效视野 ~2000 步 > 回合上限）。奖励权重全部
提成命令行参数，便于单独调：

```bash
--win-reward 1.0 --kill-reward 1.0 --death-reward -1.0 \
--step-penalty -0.0005 --aim-weight 0.0005 \
--damage-dealt-weight 0.01 --damage-taken-weight 0.003
```

### 课程学习（对手血量分阶段推进）

```bash
python -m rl.train_ppo --timesteps 1000000 --n-envs 8 --spawn-mode mixed \
    --map-type random --curriculum 0.3,0.5,0.7,1.0
```

各阶段按训练进度等分，通过 `env_method("set_opponent_hp", hp)` 直接改各 worker
的对手血量（对局中即时生效）；评估回调跟随当前阶段血量，`[EVAL]` 行会打印
`对手血量=`, 保证整条曲线在同一把尺子上比较。

### 自对弈（把当前策略快照当对手）

```bash
--selfplay-prob 0.5 --selfplay-sync 100000
```

- 每局以 `--selfplay-prob` 的概率把对手换成当前策略快照，其余局仍是行为树；
  混合可以既有策略风格的对手，又不脱离脚本 AI 的分布。
- 快照每 `--selfplay-sync` 步刷新一次，第 0 步先同步一次，所以对手从 BC 策略起步。
- 实现：主进程把策略权重的动作相关部分导出成 npz，worker 进程用**纯 numpy** 的
  Tanh MLP 前向（不在 8 个环境进程里各装一份 torch）。已验证与 SB3 确定性预测
  逐元素一致（最大偏差 1.9e-9）。

### 续训与检查点

```bash
# 断点续训：--timesteps 仍是累计目标步数
python -m rl.train_ppo --resume rl/checkpoints/ppo_zd_800000_steps.zip \
    --timesteps 1000000 --n-envs 8
```

`--ckpt-freq`（默认 5 万步）控制检查点间隔；`train_ppo.py` 结束时会显式
`vec_env.close()`，不再出现"训练完成后进程挂着不退出"。

### 苟着扣分（`--camp-penalty`）

承伤与造成伤害同权重会把策略推向"不暴露、不交战"，只修 gamma 修不回来（实测
1M 步 PPO 局内步数从 1091 涨到 1409、输出伤害腰斩）。因此给"不交战"本身定价：

- **判定交火**：本步打出伤害，或看见敌人（600px 内有视线）**同时开了枪**。
  只看"有视线"不算——站着挨打不还击、或远远吊着不打，正是要罚的苟着行为；
  对着墙开枪也不算（没有视线内的敌人），防止刷判定。
- **扣分**：连续 `--camp-grace`（默认 4 秒 = 240 步）没交火后，每步扣
  `--camp-penalty`（默认 0.001），并随苟着时长线性加重，上限 `--camp-max-mult`
  （默认 3 倍）。
- 量级：整局 1300 步全程苟着约 **-2.3**（对比：赢一局 +1.0、打 1 点伤害 +0.01），
  而正常找人 300 步只花约 -0.08、真交火的局几乎不触发；`--camp-penalty 0` 可完全关闭。
- `info` 里多了 `engaged` / `steps_since_engage`，方便监控苟着比例。

## 11. 遭遇战 / 多人遭遇战（arena + close）

“找人”是地图设计问题，所以先在不要求搜索的 arena 地图上、close 出生专练交战。

```bash
.venv/bin/python -m rl.train_ppo \
    --resume rl/models/ppo_v3_best.zip \
    --timesteps 850000 --n-envs 8 \
    --map-type arena --spawn-mode close --opponents 2 --difficulty hard \
    --selfplay-prob 0.2 --selfplay-sync 100000 \
    --eval-freq 50000 --eval-episodes 20 \
    --damage-taken-weight 0.003 --warmup-steps 0 \
    --out rl/models/ppo_arena2 --ckpt-dir rl/checkpoints_arena2
```

同种子复评（新模型 `ppo_arena2_best` vs 旧 `ppo_v3_best`）：

| 场景 | 旧胜率 | 新胜率 | 新输出伤害 |
|------|------|------|------|
| arena 1v2 close | 0.48 | **0.72** | 167.6 |
| arena 1v1 close | 0.60（20 局） | **0.85**（20 局） | 91.0 |
| grid3x3 1v2 close | 0.48 | **0.72** | 172.4 |

- 训练中每 50k 做一次 20 局 eval，波动较大：150k 时 0.20，550k 0.75，950k 0.85，1M 0.80。
- `--selfplay-prob 0.2`：20% 的局把对手换成当前策略快照，其余仍是脚本 hard，
  既引入比教师更强的对手，又不脱离脚本 AI 的分布。
- 教师是脚本行为树，和人类差距很大，不能只靠模仿。这轮从已经强于教师的
  `ppo_v3_best` 续训并加入自对弈。

### 1~3 对手混编 + 50% 自对弈

在上一轮基础上继续提高对抗强度：每局随机 1~3 个对手，50% 概率整局换成当前策略快照。

```bash
.venv/bin/python -m rl.train_ppo \
    --resume rl/models/ppo_arena2_best.zip \
    --timesteps 500000 --n-envs 8 \
    --map-type arena --spawn-mode close --difficulty hard \
    --opponents 3 --opponents-min 1 --opponents-max 3 \
    --selfplay-prob 0.5 --selfplay-sync 100000 \
    --eval-freq 50000 --eval-episodes 20 \
    --damage-taken-weight 0.003 --warmup-steps 0 \
    --out rl/models/ppo_mix3 --ckpt-dir rl/checkpoints_mix3
```

同种子复评（`ppo_arena2_best` → `ppo_mix3_best`）：

| 场景 | 旧胜率 | 新胜率 | 旧伤害 | 新伤害 |
|------|------|------|------|------|
| arena 3v1 close | 0.67（30 局） | **0.70**（20 局） | 222.7 | 256.0 |
| arena 2v1 close | 0.67（30 局） | **0.85**（20 局） | 163.3 | 187.0 |
| arena 1v1 close | 0.90（20 局） | 0.85（20 局） | 96.0 | 93.0 |
| grid3x3 3v1 close | 0.40（30 局） | **0.50**（30 局） | 205.3 | 218.0 |

训练中 eval 在 1.35M 步达到 0.95（3 对手、20 局），波动较大；最终 1.45M 收尾 0.80。
混编主要提升多人场景和 grid 泛化，1v1 基本持平。

## 12. SAC 对照实验（负结果）

`rl/train_sac.py` 用 SAC 从 BC actor 热启动，在相同 arena/close/奖励下训练。两版配置都失败了：

| 配置 | 25k | 50k | 75k | 100k+ |
|------|------|------|------|------|
| auto 熵，8 环境，4 grad steps | 0.05 | 0.10 | 0.00 | 0.00 |
| ent=0.001，4 环境，1 grad step，actor 预热 25k | 0.30 | 0.00 | 0.00 | — |

- 失败模式一致：actor 解冻后很快退化成“不开火、拖到超时”，eval 伤害掉到 1~12。
- 原因是动作空间是 **4 连续 + 2 二值**（shoot/reload）。SAC 的对角高斯把二值维也当连续量，
  熵项/价值梯度会把 shoot 的均值推回 0；预训练权重只能短暂维持。
- 结论：这个混合动作空间下，**PPO（on-policy + BC 热启动）明显更稳**。要让 SAC 可用，
  需要给 shoot/reload 单独做 Bernoulli 头（混合动作策略），或改用 BC 正则化的
  AWAC/IQL 类算法；标准 Gaussian SAC 不建议继续投入。
- 速度参考：SAC 4 环境约 194~319 steps/s，PPO 8 环境约 600~760 steps/s。

## 13. 部署到游戏（神经网络 AI）

游戏侧由 `rl_ai.py` 加载导出的 numpy 权重，不依赖 torch / stable-baselines3：

```bash
.venv/bin/python -m rl.export_policy \
    --model rl/models/ppo_mix3_best.zip \
    --out assets/rl_ai_policy.npz
```

- `settings.json` → `ai.use_rl_ai: true` 时，`.addai` 创建 `AI_RL_<ID>`。
- `ai.rl_policy_path` 指向权重；`ai.rl_fallback: true` 时加载失败自动回退行为树。
- `rl_ai.py` 复刻了训练观测（自身 7 维 + 16 射线 + 3 敌人×8 维）和动作应用，
  并对开火冷却、换弹、队友挡枪线做了游戏侧约束。
- 一致性校验：numpy 前向与 SB3 `predict(deterministic=True)` 最大误差 `<1e-6`；
  观测编码与 `HeadlessSim.obs()` 在 grid3x3 / arena 上逐元素一致。
- 导出权重会随 `build.py` 一起打进发行版（`assets/rl_ai_policy.npz`）。
