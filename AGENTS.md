# AGENTS.md - 项目上下文文档

> 本文档为 AI 代理提供项目全面上下文，用于理解项目结构、技术栈和开发规范。

---

## 项目概述

**ZD 2D Gunfight** 是一个基于 Python 和 Pygame 开发的多人 2D 射击游戏，支持局域网联机对战。游戏采用俯视角，具有双武器系统、真实瞄准机制、多房间地图设计、AI 对手系统和团队协作功能。

### 核心技术栈
- **语言**: Python 3.7+
- **游戏引擎**: Pygame 2.5+
- **网络通信**: UDP Socket
- **路径规划**: pathfinding (A* 算法)
- **UI 库**: pygame-menu 4.0+
- **打包工具**: Nuitka 2.4+ (跨平台支持)

### 项目架构特点
- **模块化设计**: 代码按功能分离到独立模块
- **团队系统**: 支持创建、加入团队，队友免疫伤害
- **AI 系统**: 提供基础版和增强版 AI（行为树 + 个性化）
- **网络同步**: 基于 UDP 的状态同步（50ms 间隔）
- **跨平台**: 支持 Windows、Linux、macOS

---

## 项目结构

```
zd-2d-gunfight/
├── main.py                    # 游戏主循环和 Game 类
├── player.py                  # 玩家类（移动、射击、生命值等）
├── ai_player.py               # 基础 AI 玩家系统
├── ai_player_enhanced.py      # 增强版 AI（行为树 + 个性化）
├── ai_behavior_tree.py        # AI 行为树系统
├── ai_personality.py          # AI 个性化特征
├── ai_cost_calculator.py      # AI 决策成本计算
├── team.py                    # 团队系统模块
├── map.py                     # 地图和门系统
├── weapons.py                 # 武器系统（近战、子弹、射线）
├── network.py                 # 网络管理（NetworkManager, ChatMessage）
├── utils.py                   # 工具函数模块
├── ui.py                      # UI 渲染模块
├── constants.py               # 游戏常量配置
├── build.py                   # Nuitka 跨平台打包脚本
├── requirements.txt           # Python 依赖
└── README.md                  # 项目文档
```

---

## 核心模块详解

### 1. main.py - 游戏主程序
**职责**: 游戏入口、主循环、菜单系统、网络扫描

**关键类**:
- `Game`: 游戏主类，管理整个游戏生命周期
  - 游戏状态: MENU, SCANNING, CONNECTING, PLAYING, ERROR
  - 网络管理: NetworkManager 实例
  - 玩家管理: 本地玩家、其他玩家、AI 玩家
  - 聊天系统: 支持全局聊天和团队聊天

**关键函数**:
- `get_local_ip()`: 获取本机内网 IP 地址
- `get_network_range()`: 获取网络 IP 地址范围
- `scan_for_servers()`: 扫描局域网服务器（多线程并发）

**AI 系统选择**:
```python
USE_ENHANCED_AI = True  # True=增强版AI, False=基础版AI
```

### 2. player.py - 玩家类
**职责**: 玩家移动、射击、武器切换、生命值管理

**关键属性**:
- `pos`: 位置 (pygame.Vector2)
- `health`: 生命值 (默认 100)
- `ammo`: 弹药 (默认 30)
- `weapon_type`: 武器类型 ("gun" 或 "melee")
- `is_aiming`: 是否瞄准模式
- `team_id`: 所属团队 ID
- `is_walking`: 是否静步移动

**关键方法**:
- `update()`: 更新玩家状态
- `shoot()`: 射击
- `switch_weapon()`: 切换武器
- `take_damage()`: 受到伤害
- `respawn()`: 复活

### 3. ai_player.py - 基础 AI 系统
**职责**: 智能对手逻辑、路径规划、行为决策

**AI 难度**:
- `easy`: 反应慢 (0.5-1.0s)，精度低 (15-30° 偏差)
- `normal`: 反应中等 (0.2-0.5s)，精度中等 (5-15° 偏差)
- `hard`: 反应快 (0.1-0.2s)，精度高 (0-5° 偏差)

**AI 状态机**:
- `patrol`: 巡逻模式
- `chase`: 追击模式
- `attack`: 攻击模式
- `retreat`: 撤退模式

**技术特性**:
- A* 路径规划（pathfinding 库）
- 动态避障
- 智能门交互
- 声音感知系统
- 静步战术

### 4. ai_player_enhanced.py - 增强版 AI 系统
**职责**: 行为树驱动的 AI、个性化特征、团队协作

**AI 性格类型**:
- `aggressive`: 激进型 - 主动攻击
- `defensive`: 防御型 - 优先寻找掩体
- `tactical`: 战术型 - 侧翼、伏击
- `stealthy`: 潜行型 - 静步、伏击
- `team`: 团队型 - 配合队友
- `random`: 随机型 - 不可预测

**行为树节点**:
- 组合节点: SelectorNode, SequenceNode, ParallelNode
- 条件节点: HasEnemyInSight, IsHealthLow, HasTeammateInDanger
- 行为节点: PatrolAction, AttackAction, TeamSupportAction

### 5. team.py - 团队系统
**职责**: 团队创建、成员管理、团队关系

**关键类**:
- `Team`: 团队类
  - `team_id`: 团队 ID
  - `members`: 成员集合
  - `leader_id`: 队长 ID
  - `color`: 团队颜色

- `TeamManager`: 团队管理器
  - `teams`: 团队字典
  - `player_teams`: 玩家到团队的映射
  - `max_team_size`: 最大团队人数 (5)

**团队功能**:
- 队友免疫伤害
- 共享视野
- 团队聊天
- AI 团队配合

### 6. network.py - 网络管理
**职责**: UDP 网络通信、状态同步、聊天消息

**关键类**:
- `NetworkManager`: 网络管理器
  - 服务器模式: 管理客户端、分配 ID
  - 客户端模式: 连接服务器、同步状态

- `ChatMessage`: 聊天消息类
  - `player_id`: 发送者 ID
  - `message`: 消息内容
  - `timestamp`: 时间戳

**网络协议**:
- 端口: 5555 (UDP)
- 同步间隔: 50ms
- 消息格式: JSON
- 心跳间隔: 1.0s

### 7. map.py - 地图系统
**职责**: 地图生成、房间管理、门系统

**地图结构**:
- 3x3 九宫格房间
- 每个房间 600x600 像素
- 墙壁厚度 20 像素
- 门大小 80 像素

**关键类**:
- `Map`: 地图类
- `Door`: 门类（自动开关、动画）

### 8. weapons.py - 武器系统
**职责**: 武器管理、子弹物理、近战攻击

**武器类型**:
- **枪械**:
  - 弹药: 30 发
  - 装填时间: 2.0s
  - 子弹速度: 800 px/s
  - 伤害: 20

- **近战武器**:
  - 普通攻击: 伤害 40，范围 60px，冷却 0.8s
  - 重击: 伤害 60，范围 45px，冷却 1.2s

**关键类**:
- `MeleeWeapon`: 近战武器
- `Bullet`: 子弹
- `Ray`: 射线

### 9. utils.py - 工具函数
**职责**: 角度计算、视野检测、碰撞检测

**关键函数**:
- `normalize_angle()`: 角度归一化
- `angle_difference()`: 角度差计算
- `is_in_field_of_view()`: 视野检测
- `has_line_of_sight()`: 视线检测
- `line_intersects_rect()`: 线段与矩形相交检测

### 10. ui.py - UI 渲染
**职责**: 字体管理、界面绘制、菜单系统

**关键类**:
- `MenuManager`: 菜单管理器（pygame-menu）
- `ChatMenuManager`: 聊天菜单管理器

**字体管理**:
- 跨平台字体检测
- 中文字体验证
- Ubuntu 字体支持

### 11. constants.py - 游戏常量
**职责**: 游戏配置参数

**主要常量**:
```python
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
FPS = 60
PLAYER_SPEED = 300
BULLET_SPEED = 800
PLAYER_HEALTH = 100
MAGAZINE_SIZE = 30
RESPAWN_TIME = 3.0
SERVER_PORT = 5555
VISION_RANGE = 300
FIELD_OF_VIEW = 120
```

### 12. build.py - 打包脚本
**职责**: Nuitka 跨平台打包

**功能**:
- 自动检测操作系统
- 配置 Nuitka 参数
- 处理第三方库（pygame, pathfinding）
- 支持单文件和多文件输出

**使用方法**:
```bash
# Windows
python build.py --clean --onefile --disable-console

# Linux
python3 build.py --clean

# macOS
python3 build.py --clean --onefile
```

---

## 依赖管理

### 核心依赖 (requirements.txt)
```
pygame>=2.5
pygame-menu>=4.0
pathfinding>=1.0
numpy>=1.26
nuitka>=2.4
```

### 安装依赖
```bash
# Windows
pip install -r requirements.txt

# Linux
pip3 install -r requirements.txt
```

---

## 开发规范

### 代码风格
- **缩进**: 4 空格
- **命名**: snake_case（函数、变量），PascalCase（类）
- **类型提示**: 在关键函数中使用类型提示
- **注释**: 中文注释，说明"为什么"而非"是什么"

### 文件组织
- 每个模块职责单一
- 避免循环导入（使用延迟导入）
- 相关功能分组到同一模块

### 导入顺序
```python
# 1. 标准库
import json
import math

# 2. 第三方库
import pygame

# 3. 本地模块
from constants import *
from player import Player
```

### 常量使用
- 所有常量定义在 `constants.py`
- 使用全大写命名
- 按功能分组注释

---

## 构建和运行

### 开发环境运行
```bash
# Windows
python main.py

# Linux
python3 main.py
```

### 打包发布
```bash
# Windows（单文件，隐藏控制台）
python build.py --clean --onefile --disable-console

# Linux（多文件）
python3 build.py --clean

# macOS（App Bundle）
python3 build.py --clean --onefile
```

### 输出位置
- Windows: `dist/windows/ZD-2D-Gunfight.exe`
- Linux: `dist/linux/ZD-2D-Gunfight`
- macOS: `dist/darwin/ZD-2D-Gunfight.app`

---

## 游戏机制

### 视野系统
- **正常模式**: 120° 视角，300px 范围
- **瞄准模式**: 30° 视角，400px 范围（按住右键）
- **战争迷雾**: 不可见区域显示深灰色

### 武器切换
- 按 `3` 键切换枪械和近战武器
- 切换冷却: 0.5s

### 聊天系统
- 按 `Y` 键打开聊天框
- 支持 `.teamchat` 切换队内聊天
- 支持 `.all` 切换全局聊天
- 使用 `↑/↓` 键滚动查看历史

### 管理员命令
```
.addai [难度] [性格]    # 添加AI
.removeai <ID|all>      # 移除AI
.createteam [名称]      # 创建团队
.jointeam <ID>          # 加入团队
.leaveteam              # 离开团队
.listteams              # 列出团队
.help                   # 显示帮助
```

---

## 网络架构

### 通信协议
- **协议**: UDP
- **端口**: 5555
- **同步频率**: 50ms
- **消息格式**: JSON

### 服务器扫描
- 多线程并发扫描
- 支持 /24 和 /16 网段
- 自动检测网络范围
- 服务器 ID 去重

### 状态同步
- 服务器权威模式
- 客户端预测
- 插值平滑

---

## AI 系统架构

### 基础 AI (ai_player.py)
- 状态机驱动
- A* 路径规划
- 声音感知
- 智能射击控制

### 增强版 AI (ai_player_enhanced.py)
- 行为树驱动
- 个性化特征
- 团队协作
- 高级战术

### AI 命令
```
.addai easy              # 添加简单AI
.addai normal aggressive # 添加激进型AI
.addai hard tactical     # 添加战术型AI
.removeai all            # 移除所有AI
.listai                  # 列出AI
```

---

## 团队系统

### 团队功能
- 创建团队（最多 5 人）
- 队友免疫伤害
- 共享视野
- 团队聊天
- AI 团队配合

### 团队命令
```
.createteam [名称]       # 创建团队
.jointeam <ID>           # 加入团队
.leaveteam               # 离开团队
.team                    # 查看团队信息
.listteams               # 列出所有团队
.invite <玩家ID>         # 邀请玩家
.teamchat                # 切换队内聊天
.all                     # 切换全局聊天
```

---

## 字体系统

### 跨平台支持
- **Windows**: Microsoft YaHei, SimHei
- **Linux**: Noto Sans CJK SC, WenQuanYi Micro Hei
- **macOS**: PingFang SC, Hiragino Sans GB

### 字体验证
- 严格验证中文渲染能力
- 提供详细日志输出
- 自动降级方案

---

## 故障排除

### 常见问题

**1. Ubuntu 中文显示异常**
```bash
sudo apt install fonts-noto-cjk
fc-cache -fv
```

**2. 网络连接失败**
- 检查防火墙设置
- 确认端口 5555 开放
- 验证同一局域网

**3. 打包失败**
```bash
pip install --upgrade nuitka ordered-set
```

**4. AI 无法添加**
- 只有服务端可以添加 AI
- 检查 `USE_ENHANCED_AI` 设置

---

## 性能优化

### 建议配置
- AI 数量: 不超过 10 个
- 玩家数量: 最多 10 人
- 网络延迟: < 100ms

### 优化建议
- 使用打包版本而非 Python 脚本
- 关闭其他占用资源的程序
- 降低分辨率（修改 constants.py）
- 使用有线网络

---

## 扩展开发

### 添加新武器
1. 在 `weapons.py` 中定义新武器类
2. 在 `player.py` 中添加武器切换逻辑
3. 更新 `constants.py` 中的武器参数

### 添加新 AI 性格
1. 在 `ai_personality.py` 中定义新性格
2. 在 `ai_behavior_tree.py` 中创建对应行为树
3. 更新 `ai_player_enhanced.py` 中的性格映射

### 添加新地图
1. 在 `map.py` 中修改地图生成逻辑
2. 调整房间数量和布局
3. 更新 `constants.py` 中的地图参数

---

## 许可证

本项目采用 **GNU General Public License v3.0** 许可证。

---

## 联系方式

- **项目地址**: https://github.com/123456Zhe/zd-2d-gunfight
- **问题反馈**: 通过 GitHub Issues 提交

---

**最后更新**: 2026-01-25