# ZD 2D Gunfight Game - 完整项目文档

> 一个完全由AI生成的2D多人射击游戏，使用Python和Pygame开发

---

## 📋 目录

1. [项目概述](#项目概述)
2. [游戏特色](#游戏特色)
3. [系统要求](#系统要求)
4. [安装与运行](#安装与运行)
5. [游戏操作指南](#游戏操作指南)
6. [多人游戏](#多人游戏)
7. [管理员命令](#管理员命令)
8. [打包发布](#打包发布)
9. [Ubuntu支持](#ubuntu支持)
10. [字体系统](#字体系统)
11. [聊天系统](#聊天系统)
12. [故障排除](#故障排除)
13. [开发信息](#开发信息)
14. [许可证](#许可证)

---

## 项目概述

ZD 2D Gunfight是一款基于Python和Pygame开发的多人射击游戏，支持局域网联机对战。游戏采用俯视角视角，提供双武器系统、真实瞄准机制和多房间地图设计。

### 技术栈
- **语言**: Python 3.7+
- **游戏引擎**: Pygame 2.0+
- **网络**: UDP Socket
- **打包工具**: PyInstaller / Nuitka / cx_Freeze

### 项目结构
```
zd-2d-gunfight/
├── main.py              # 主游戏文件
├── player.py            # 玩家类
├── map.py               # 地图系统
├── weapons.py           # 武器系统
├── network.py           # 网络管理
├── constants.py         # 游戏常量
├── README.md            # 主文档
├── README_Ubuntu.md     # Ubuntu支持文档
├── Ubuntu使用说明.md    # Ubuntu快速指南
├── 字体修复说明.md      # 字体兼容性说明
└── build_*.py           # 打包脚本
```

---

## 游戏特色

### 核心玩法

- **双武器系统**: 支持枪械和近战武器切换
- **真实瞄准机制**: 右键瞄准，视野动态变化（120°→30°）
- **多人对战**: 支持局域网多人游戏，最多10名玩家
- **房间系统**: 3x3多房间地图设计，带自动门系统
- **实时物理**: 精确的子弹轨迹和碰撞检测
- **视野系统**: 基于角度的可见性判断，增加战术性
- **聊天系统**: 实时聊天，支持滚动查看历史记录

### 最新更新

#### 参数优化版
- **增强子弹速度**: 从500提升至800，射击更爽快
- **提升移动速度**: 从200提升至350，操作更流畅
- **扩展瞄准距离**: 从150增加至400，视野更远
- **优化鼠标灵敏度**: 从0.3提升至0.6，瞄准更精准

#### 聊天系统增强
- **消息永久保留**: 聊天记录不再自动消失
- **可滚动显示**: 使用上下方向键查看历史消息
- **多行支持**: 完美支持换行显示（如.help命令输出）
- **智能裁剪**: 超出显示区域的消息自动裁剪

#### 字体兼容性修复
- **跨平台支持**: 智能检测操作系统，选择最佳字体
- **Ubuntu优化**: 优先使用Noto Sans CJK SC等原生字体
- **字体验证**: 严格验证中文渲染能力
- **详细日志**: 提供清晰的字体加载信息

---

## 系统要求

### Windows
- Windows 10/11
- Python 3.7+ (开发环境)
- 存储空间: 120-240MB (打包后)

### Ubuntu/Linux
- Ubuntu 18.04+ (推荐20.04+)
- Python 3.6+
- 中文字体支持
- 存储空间: 500MB+

### macOS
- macOS 10.14+
- Python 3.7+
- 存储空间: 200MB+

---

## 安装与运行

### 方法1: 直接运行源码

#### Windows
```bash
# 安装依赖
pip install pygame

# 运行游戏
python main.py
```

#### Ubuntu/Linux
```bash
# 安装依赖
pip3 install pygame

# 安装中文字体（推荐）
sudo apt install fonts-noto-cjk

# 运行游戏
python3 main.py
```

### 方法2: 运行打包版本

下载对应平台的可执行文件，双击运行即可。

---

## 游戏操作指南

### 基础控制


| 操作 | 按键 | 说明 |
|------|------|------|
| 移动 | W/A/S/D | 上/左/下/右移动 |
| 瞄准 | 鼠标移动 | 控制瞄准方向 |
| 精准瞄准 | 右键按住 | 视野缩小至30°，提高精度 |
| 射击 | 左键 | 发射子弹（枪械）或攻击（近战） |
| 切换武器 | 数字键3 | 在枪械和近战武器间切换 |
| 装填弹药 | R键 | 重新装填弹药（2秒） |
| 开关门 | E键 | 手动控制门的开关 |
| 聊天 | Y键 | 打开聊天输入框 |
| 滚动消息 | ↑/↓键 | 查看聊天历史记录 |
| 调试模式 | F3键 | 切换调试信息显示 |
| 视角显示 | F4键 | 切换视野扇形显示 |
| 退出 | ESC键 | 退出游戏或关闭聊天 |

### 武器系统详解

#### 枪械武器
- **弹药容量**: 30发
- **装填时间**: 2秒
- **射击模式**: 半自动（点射）
- **有效射程**: 800像素
- **伤害**: 标准伤害
- **适用场景**: 中远距离战斗

#### 近战武器
- **攻击范围**: 扇形区域（60°角度，100像素范围）
- **攻击速度**: 快速连击
- **伤害类型**: 范围伤害
- **冷却时间**: 0.5秒
- **适用场景**: 近距离高伤害输出

### 瞄准系统

#### 正常模式
- **视野角度**: 120°广角
- **视野距离**: 标准距离
- **适用场景**: 观察周围环境，移动战斗

#### 瞄准模式（按住右键）
- **视野角度**: 30°精准视野
- **视野距离**: 400像素（扩展）
- **射击精度**: 提高
- **适用场景**: 远程精确射击

### 房间与门系统

#### 自动门
- 靠近门时自动开启
- 离开后自动关闭
- 开启动画流畅

#### 手动控制
- 按E键手动开关门
- 可用于战术布置
- 关闭的门阻挡视线和子弹

---

## 多人游戏

### 服务器设置

#### 创建服务器
1. 启动游戏，选择"创建服务器"
2. 输入服务器名称（可选）
3. 输入玩家名称（可选，默认随机生成）
4. 点击"开始游戏"
5. 记录显示的IP地址和端口

#### 服务器信息
- **默认端口**: 5555 (UDP)
- **最大玩家数**: 10人
- **网络类型**: 局域网
- **同步频率**: 50ms

### 客户端连接

#### 自动扫描
1. 选择"加入服务器"
2. 等待自动扫描完成
3. 从列表中选择服务器
4. 输入玩家名称
5. 点击"连接"

#### 手动连接
1. 选择"加入服务器"
2. 点击"手动输入IP"
3. 输入服务器IP地址
4. 输入玩家名称
5. 点击"连接"

### 网络配置

#### 防火墙设置（Windows）
```powershell
# 允许UDP 5555端口
netsh advfirewall firewall add rule name="ZD 2D Gunfight" dir=in action=allow protocol=UDP localport=5555
```

#### 防火墙设置（Ubuntu）
```bash
# 允许UDP 5555端口
sudo ufw allow 5555/udp
```

---

## 管理员命令

管理员命令仅限服务器端使用，在聊天框中输入。

### 命令列表

#### .help
显示所有可用命令
```
.help
```

#### .list / .players
显示在线玩家列表
```
.list
```

#### .kick
踢出指定玩家
```
.kick <玩家ID> [原因]
```
示例: `.kick 2 违规行为`

#### .broadcast
广播系统消息
```
.broadcast <消息内容>
```
示例: `.broadcast 游戏即将重启`

#### .heal
治疗玩家
```
.heal <玩家ID|all> [生命值]
```
示例: 
- `.heal 2 100` - 将玩家2的生命值设为100
- `.heal all` - 治疗所有玩家至满血

#### .respawn
复活死亡玩家
```
.respawn <玩家ID|all>
```
示例:
- `.respawn 2` - 复活玩家2
- `.respawn all` - 复活所有死亡玩家

#### .tp
传送玩家到指定坐标
```
.tp <玩家ID|all> <x> <y>
```
示例: `.tp 2 500 500` - 将玩家2传送到(500, 500)

#### .kill
自杀（所有玩家可用）
```
.kill
```

#### .weapon
切换武器类型
```
.weapon
```

#### .ammo
补充弹药
```
.ammo
```

#### .speed
临时提高移动速度
```
.speed [倍率] [持续时间]
```
示例: `.speed 2 10` - 2倍速度持续10秒

---

## 打包发布

### Windows打包

#### 方法1: 标准PyInstaller打包
```bash
python build_exe.py
```
- 输出: `dist/ZD-2D-Gunfight.exe`
- 大小: ~240MB
- 兼容性: 高

#### 方法2: 最小化打包
```bash
python build_minimal.py
```
- 输出: `dist_minimal/ZD-2D-Gunfight-Mini.exe`
- 大小: ~180MB
- 优化: 排除不必要模块

#### 方法3: Nuitka编译（推荐）
```bash
# 安装Nuitka
pip install nuitka

# 打包
python build_nuitka.py
```
- 输出: `dist_nuitka/main.exe`
- 大小: ~120MB
- 性能: 原生编译，运行更快

#### 方法4: cx_Freeze打包
```bash
# 安装cx_Freeze
pip install cx_Freeze

# 打包
python setup_cxfreeze.py build
```
- 输出: `build/exe.win-amd64-3.x/`
- 大小: ~200MB
- 结构: 多文件模式

### Ubuntu打包

```bash
# 运行打包脚本
python3 build_ubuntu.py

# 输出文件
dist_ubuntu/
├── zd-2d-gunfight              # 可执行文件
├── zd-2d-gunfight.desktop      # 桌面快捷方式
└── install.sh                  # 安装脚本

# 安装到系统
cd dist_ubuntu
./install.sh
```

### 打包工具对比

| 方法 | 文件大小 | 打包时间 | 兼容性 | 性能 | 推荐指数 |
|------|----------|----------|--------|------|----------|
| PyInstaller标准 | ~240MB | 中等 | 高 | 标准 | ⭐⭐⭐ |
| PyInstaller最小化 | ~180MB | 中等 | 高 | 标准 | ⭐⭐⭐⭐ |
| Nuitka | ~120MB | 较长 | 高 | 优秀 | ⭐⭐⭐⭐⭐ |
| cx_Freeze | ~200MB | 较短 | 中 | 标准 | ⭐⭐⭐ |

---

## Ubuntu支持

### 快速开始

#### 1. 安装依赖
```bash
sudo apt update
sudo apt install python3 python3-pip python3-dev build-essential
pip3 install pygame nuitka
```

#### 2. 安装中文字体
```bash
# 自动安装
python3 install_ubuntu_fonts.py

# 或手动安装
sudo apt install fonts-noto-cjk fonts-wqy-microhei
fc-cache -fv
```

#### 3. 验证字体修复
```bash
python3 verify_font_fix.py
```

#### 4. 运行游戏
```bash
python3 main.py
```

### 支持的Ubuntu版本
- ✅ Ubuntu 20.04 LTS (Focal Fossa)
- ✅ Ubuntu 22.04 LTS (Jammy Jellyfish)
- ✅ Ubuntu 23.04 (Lunar Lobster)
- ✅ Ubuntu 23.10 (Mantic Minotaur)
- ⚠️ Ubuntu 18.04 LTS (需要Python 3.8+)

---

## 字体系统

### 字体兼容性修复

#### 问题描述
在Ubuntu上，`pygame.font.SysFont('Microsoft YaHei')`会错误地返回字体对象，但实际使用fallback字体，导致显示效果差。

#### 修复方案
1. **智能操作系统检测**: 根据系统选择合适的字体列表
2. **严格字体验证**: 验证中文渲染能力，而不仅仅检查字体对象
3. **详细日志输出**: 提供清晰的字体加载信息

### 支持的字体

#### Ubuntu/Linux（按优先级）
1. **Noto Sans CJK SC** - Google Noto字体（推荐）
2. **Noto Sans CJK TC** - 繁体中文支持
3. **WenQuanYi Micro Hei** - 文泉驿微米黑
4. **WenQuanYi Zen Hei** - 文泉驿正黑
5. **Droid Sans Fallback** - Android字体
6. **AR PL UMing CN** - 文鼎明体
7. **AR PL UKai CN** - 文鼎楷体

#### Windows
1. **Microsoft YaHei** - 微软雅黑
2. **SimHei** - 黑体
3. **SimSun** - 宋体
4. **Arial Unicode MS**

#### macOS
1. **PingFang SC** - 苹方
2. **Hiragino Sans GB** - 冬青黑体
3. **STHeiti** - 华文黑体

### 字体安装

#### Ubuntu最小安装（推荐）
```bash
sudo apt install fonts-noto-cjk
```

#### Ubuntu完整安装
```bash
sudo apt install fonts-noto-cjk fonts-wqy-microhei fonts-wqy-zenhei
```

#### 验证字体
```bash
# 列出已安装的中文字体
fc-list :lang=zh

# 测试字体渲染
python3 test_ubuntu_fonts.py
```

---

## 聊天系统

### 功能特性

#### 基础功能
- **实时聊天**: 所有玩家可见
- **玩家标识**: 显示玩家名称和ID
- **系统消息**: 服务器通知和命令反馈

#### 高级功能
- **消息永久保留**: 聊天记录不会自动消失
- **可滚动显示**: 使用方向键查看历史
- **多行支持**: 完美支持换行文本
- **智能裁剪**: 超出区域自动裁剪

### 使用方法

#### 发送消息
1. 按Y键打开聊天框
2. 输入消息内容
3. 按Enter发送
4. 按ESC取消

#### 查看历史
- 按↑键: 向上滚动，查看更早的消息
- 按↓键: 向下滚动，查看更新的消息
- 无需打开聊天框即可滚动

#### 显示区域
- **顶部限制**: y=250
- **底部限制**: y=540
- **可见高度**: 290像素
- **滚动提示**: 显示是否有更多消息

### 命令系统

所有以`.`开头的消息会被识别为命令，详见[管理员命令](#管理员命令)章节。

---

## 故障排除

### 连接问题

#### 无法连接到服务器
**可能原因**:
- 服务器未启动
- 不在同一局域网
- 防火墙阻止
- IP地址错误

**解决方法**:
1. 确认服务器已启动并显示IP
2. 检查网络连接（ping测试）
3. 配置防火墙允许UDP 5555端口
4. 尝试手动输入IP地址

#### 扫描不到服务器
**可能原因**:
- 网络设备阻止UDP广播
- 不在同一网段
- 防火墙阻止扫描

**解决方法**:
1. 使用"刷新服务器列表"
2. 手动输入服务器IP
3. 检查路由器设置

### 字体问题

#### Ubuntu中文显示异常
**解决方法**:
```bash
# 1. 运行字体测试
python3 test_ubuntu_fonts.py

# 2. 安装推荐字体
sudo apt install fonts-noto-cjk

# 3. 刷新字体缓存
fc-cache -fv

# 4. 验证修复
python3 verify_font_fix.py
```

#### Windows中文显示方块
**解决方法**:
1. 确保系统已安装中文字体
2. 重启游戏
3. 检查系统语言设置

### 性能问题

#### 游戏卡顿
**优化方法**:
1. 关闭其他占用资源的程序
2. 使用打包版本而非Python脚本
3. 降低游戏分辨率（修改constants.py）
4. 更新显卡驱动

#### 网络延迟高
**优化方法**:
1. 使用有线网络连接
2. 减少同时连接的玩家数
3. 确保服务器网络稳定
4. 避免网络繁忙时段

### 打包问题

#### Nuitka打包失败
**解决方法**:
```bash
# Windows
pip install --upgrade nuitka
pip install ordered-set

# Ubuntu
sudo apt install gcc g++ python3-dev
pip3 install --upgrade nuitka
```

#### PyInstaller打包失败
**解决方法**:
```bash
# 清理缓存
rmdir /s /q build dist  # Windows
rm -rf build dist       # Linux

# 重新安装
pip uninstall pyinstaller
pip install pyinstaller
```

---

## 开发信息

### 项目文件说明

#### 核心文件
- `main.py` - 主游戏逻辑，包含Game类和主循环
- `player.py` - 玩家类，处理移动、射击、生命值等
- `map.py` - 地图系统，包含房间和门的管理
- `weapons.py` - 武器系统，定义枪械和近战武器
- `network.py` - 网络管理，处理客户端-服务器通信
- `constants.py` - 游戏常量配置

~~游戏功能的分装有问题~~

#### 打包脚本
- `build_exe.py` - Windows标准打包
- `build_minimal.py` - Windows最小化打包
- `build_nuitka.py` - Nuitka编译打包
- `build_ubuntu.py` - Ubuntu打包
- `setup_cxfreeze.py` - cx_Freeze打包配置

#### 工具脚本
- `install_ubuntu_fonts.py` - Ubuntu字体安装助手
- `test_ubuntu_fonts.py` - 字体测试工具
- `verify_font_fix.py` - 字体修复验证
- `install_packaging_tools.py` - 打包工具安装

### 技术架构

#### 游戏循环
```python
while running:
    # 1. 处理事件
    handle_events()
    
    # 2. 更新游戏状态
    update_game_state()
    
    # 3. 网络同步
    sync_network()
    
    # 4. 渲染画面
    render()
    
    # 5. 控制帧率
    clock.tick(60)
```

#### 网络架构
- **协议**: UDP
- **模式**: 客户端-服务器
- **同步**: 状态同步（50ms间隔）
- **消息格式**: JSON

#### 视野系统
- **算法**: 基于角度的扇形视野
- **检测**: 射线投射法
- **优化**: 视野裁剪，只渲染可见对象

### 游戏常量配置

主要常量定义在`constants.py`中：

```python
# 屏幕设置
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# 玩家设置
PLAYER_SPEED = 350
PLAYER_RADIUS = 20
PLAYER_HEALTH = 100

# 武器设置
BULLET_SPEED = 800
BULLET_DAMAGE = 10
MAGAZINE_SIZE = 30
RELOAD_TIME = 2.0

# 视野设置
VISION_RANGE = 400
NORMAL_FOV = 120
AIMING_FOV = 30

# 网络设置
SERVER_PORT = 5555
BUFFER_SIZE = 4096
```

### 贡献指南

欢迎提交Issue和Pull Request！

#### 提交Issue
- 描述问题或建议
- 提供复现步骤
- 附上系统信息和错误日志

#### 提交PR
- Fork项目
- 创建功能分支
- 提交清晰的commit信息
- 确保代码通过测试
- 提交Pull Request

---

## 许可证

本项目采用 **GNU General Public License v3.0** 许可证。

### 主要条款
- ✅ 可以自由使用、修改和分发
- ✅ 可以用于商业用途
- ⚠️ 修改后的代码必须开源
- ⚠️ 必须保留原作者版权信息
- ⚠️ 必须使用相同的GPL v3许可证

详见 [LICENSE](LICENSE) 文件。

---

## 联系方式

- **项目地址**: https://github.com/123456Zhe/zd-2d-gunfight
- **问题反馈**: 通过GitHub Issues提交

---


**Enjoy the game! 🎮**
