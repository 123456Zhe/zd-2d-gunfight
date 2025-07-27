# ZD 2D Gunfight Game

一个完全由AI生成的2D多人射击游戏，使用Python和Pygame开发。

## 游戏特色

### 核心玩法
- **双武器系统**：支持枪械和近战武器切换
- **真实瞄准机制**：右键瞄准，视野动态变化
- **多人对战**：支持局域网多人游戏
- **房间系统**：多房间地图设计
- **实时物理**：子弹轨迹和碰撞检测

### 最新更新（参数优化版）
- **增强子弹速度**：从500提升至800，射击更爽快
- **提升移动速度**：从200提升至350，操作更流畅
- **扩展瞄准距离**：从150增加至400，视野更远
- **优化鼠标灵敏度**：从0.3提升至0.6，瞄准更精准
- **动态视野角度**：
  - 正常状态：120°广角视野
  - 瞄准状态：30°精准视野，自动切换

### 游戏控制
- **移动**：WASD
- **瞄准**：右键按住
- **射击**：左键
- **切换武器**：数字键3
- **交互**：E键（开/关门）
- **聊天**：Y键

### 技术特性
- **网络同步**：实时多人状态同步
- **视野系统**：基于角度的可见性判断
- **物理引擎**：精确的碰撞检测
- **UI系统**：完整的游戏界面和HUD

### 运行要求
- Python 3.7+
- Pygame 2.0+
- 支持Windows系统

### 启动方式
```bash
python main.py
```

### 打包方法
#### 生成Windows可执行文件
使用提供的打包脚本一键生成exe文件：
```bash
python build_exe.py
```

打包完成后，可执行文件将生成在 `dist/ZD-2D-Gunfight.exe`

#### 其他打包方法（更小体积）

##### 方法1：Nuitka编译（推荐）
使用Nuitka将Python代码编译为C++，生成更小的exe文件：
```bash
# 先安装Nuitka
pip install nuitka

# 使用Nuitka打包
python build_nuitka.py
# 选择1使用Nuitka打包
```
- **文件大小**：比PyInstaller小30-50%
- **性能优势**：原生编译，运行更快
- **输出位置**：`dist_nuitka/main.exe`

##### 方法2：最小化PyInstaller打包
使用高级优化参数排除不必要模块：
```bash
python build_minimal.py
# 选择1直接打包
```
- **文件大小**：通过排除大型库减少体积
- **优化级别**：最高优化设置
- **输出位置**：`dist_minimal/ZD-2D-Gunfight-Mini.exe`

##### 方法3：cx_Freeze打包
使用cx_Freeze作为替代打包工具：
```bash
# 先安装cx_Freeze
pip install cx_Freeze

# 使用cx_Freeze打包
python build_nuitka.py
# 选择2使用cx_Freeze
```
- **文件结构**：多文件模式，更灵活
- **输出位置**：`dist_cxfreeze/` 目录

#### 打包工具安装
一键安装所有打包工具：
```bash
python install_packaging_tools.py
# 选择1安装所有工具
```

#### 打包方法对比
| 方法 | 文件大小 | 打包时间 | 兼容性 | 推荐指数 |
|------|----------|----------|--------|----------|
| PyInstaller标准 | ~240MB | 中等 | 高 | ⭐⭐⭐ |
| PyInstaller最小化 | ~180MB | 中等 | 高 | ⭐⭐⭐⭐ |
| Nuitka | ~120MB | 较长 | 高 | ⭐⭐⭐⭐⭐ |
| cx_Freeze | ~200MB | 较短 | 中 | ⭐⭐⭐ |

#### 系统要求
- Windows 10/11
- 无需安装Python环境（已打包所有依赖）
- 存储空间：120-240MB（根据打包方法不同）

### 多人游戏
- 启动服务器：选择"创建服务器"
- 加入游戏：选择"加入服务器"并输入IP地址

---
*Powered by Python & Pygame*
*100% AI Generated Code*
