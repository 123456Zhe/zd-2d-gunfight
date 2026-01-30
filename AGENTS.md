# AGENTS.md - ZD 2D 枪战

## 项目概述
**ZD 2D 枪战** - 基于 Python/Pygame 的多人 2D 俯视射击游戏，支持局域网联机、AI 对手和团队系统。

**技术栈**: Python 3.7+, Pygame 2.5+, UDP 网络, 路径查找 (A*), pygame-menu 4.0+, Nuitka 2.4+

## 构建、静态检查和测试命令

### 运行游戏
```bash
# Linux
python3 main.py

# Windows
python main.py
```

### 使用 Nuitka 构建
```bash
# Linux（多文件）
python3 build.py --clean

# Windows（单文件，无控制台）
python build.py --clean --onefile --disable-console

# macOS（应用打包）
python3 build.py --clean --onefile
```

### 安装依赖
```bash
pip3 install -r requirements.txt
```

### 静态检查和类型检查
```bash
# 先安装开发依赖
pip3 install ruff mypy

# 运行 ruff 检查
ruff check .

# 运行类型检查
mypy .
```

### 运行测试
```bash
# 运行所有测试
python3 -m pytest

# 运行单个测试文件
python3 -m pytest tests/test_player.py

# 运行单个测试
python3 -m pytest tests/test_player.py::TestPlayer::test_shoot
```

## 代码风格规范

### 命名约定
- **类**: PascalCase（例如 `NetworkManager`, `Game`）
- **函数/变量**: snake_case（例如 `get_local_ip()`, `player_pos`）
- **常量**: UPPER_SNAKE_CASE（例如 `SERVER_PORT`, `FPS`）
- **私有成员**: 前导下划线（例如 `_update_state()`）

### 导入顺序
```python
# 1. 标准库
import json
import math
from typing import Dict, List, Optional

# 2. 第三方库
import pygame
import pygame_menu

# 3. 本地模块（绝对导入）
from constants import SCREEN_WIDTH, FPS
from player import Player
```

### 格式
- **缩进**: 4 个空格（不使用制表符）
- **行长度**: 100 个字符
- **空行**: 类定义之间 2 行，函数之间 1 行
- **不加注释** 除非解释"原因"（而非"是什么"）
- **代码中不使用表情符号**

### 类型提示
- 为函数参数和返回值使用类型提示
- 使用 `Optional[T]` 替代 `Union[T, None]`
- 使用 `typing` 中的 `List[T]`, `Dict[K, V]`

### 错误处理
- 使用具体异常（不使用裸 `except:`）
- 重新抛出前记录错误上下文
- 在函数边界验证输入
- 优雅处理网络错误（UDP 是不可靠的）

### 文件组织
- 主要类（Player, Game, NetworkManager）每个文件一个类
- 工具函数放在 `utils.py`
- 常量放在 `constants.py`
- 避免循环导入（必要时使用延迟导入）

### 关键文件
- `main.py`: 游戏循环、菜单系统、服务器扫描
- `player.py`: 玩家移动、射击、生命值
- `network.py`: UDP 通信、状态同步
- `ai_player_enhanced.py`: 行为树 AI
- `team.py`: 团队管理系统
- `map.py`: 基于房间的地图生成
- `constants.py`: 所有游戏配置

### 游戏常量
所有可调参数都在 `constants.py` 中：
- 屏幕: 800x600, 60 FPS
- 玩家: 100 生命值, 300 速度
- 武器: 30 弹药, 800 子弹速度
- 网络: UDP 端口 5555, 50ms 同步间隔
- 视野: 300 像素范围, 120° 视角

## 配置文件

所有游戏配置已移至 `settings.json`，包括：

### 游戏设置 (`game`)
- `screen_width/screen_height`: 屏幕分辨率 (默认 800x600)
- `fps`: 帧率 (默认 60)
- `player_speed`: 玩家移动速度 (默认 300)
- `bullet_speed`: 子弹速度 (默认 800)
- `bullet_damage`: 子弹伤害 (默认 20)
- `respawn_time`: 复活时间 (默认 3.0秒)

### 网络设置 (`network`)
- `server_port`: 服务器端口 (默认 5555)
- `heartbeat_interval`: 心跳间隔 (默认 1.0秒)
- `client_timeout`: 客户端超时 (默认 5.0秒)

### AI 设置 (`ai`)
- `use_enhanced_ai`: 使用增强版AI (默认 true)

### 命令设置 (`commands`)
- `prefix`: 命令前缀 (默认 ".")
- `enabled`: 启用命令系统 (默认 true)

### 修改配置
直接编辑 `settings.json` 文件即可修改配置，无需重新编译。

## 故障排除
- **没有中文字体**: 在 Linux 上安装 `fonts-noto-cjk`
- **端口 5555 被阻塞**: 检查防火墙设置
- **构建失败**: `pip install --upgrade nuitka ordered-set`

## 游戏内指令系统

游戏内支持通过聊天框输入指令来执行各种操作。所有指令以 `.` 开头。

### 使用方法
在聊天框中输入指令，按 Enter 发送：
```
.kill          # 自杀
.list          # 列出在线玩家
.team add 我的队伍  # 创建团队
.team join 1   # 加入团队 ID 为 1 的团队
```

### 指令列表

#### 玩家操作
| 指令 | 别名 | 说明 |
|------|------|------|
| `.kill` | - | 自杀 |
| `.list` | `.players` | 列出在线玩家 |
| `.listai` | - | 列出 AI 玩家 |

#### 聊天相关
| 指令 | 别名 | 说明 |
|------|------|------|
| `.teamchat` | `.tc` | 切换到团队聊天模式 |
| `.all` | - | 切换到全局聊天模式 |

#### AI 管理（仅服务器）
| 指令 | 别名 | 说明 |
|------|------|------|
| `.addai [难度]` | `.spawn` | 添加 AI 玩家 |
| `.removeai <ID\|all>` | `.delete` | 移除 AI 玩家 |

- 难度: `easy`, `normal`, `hard`
- AI 性格由系统随机生成，玩家无法查看或选择

#### 团队管理
| 指令 | 说明 |
|------|------|
| `.team add [名称]` | 创建团队 |
| `.team delete <ID>` | 删除团队（仅队长或服务器） |
| `.team list` | 列出所有团队 |
| `.team join <ID>` | 加入团队 |
| `.team leave` | 离开当前团队 |

#### 管理员指令（玩家 ID 为 1）
| 指令 | 说明 |
|------|------|
| `.kick <玩家ID> [原因]` | 踢出玩家 |
| `.heal <玩家ID\|all> [生命值]` | 治疗玩家（默认 100） |
| `.broadcast <消息>` | 广播系统公告 |

#### 帮助
| 指令 | 说明 |
|------|------|
| `.help` | 显示帮助信息 |
| `.help <指令名>` | 显示指定指令的详细信息 |

### 代码位置
- 指令系统核心: `game_commands.py`
- 聊天界面集成: `ui.py`
