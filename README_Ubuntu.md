# ZD 2D Gunfight - Ubuntu支持指南

这个指南将帮助你在Ubuntu系统上正确运行和打包ZD 2D Gunfight游戏。

## 系统要求

- Ubuntu 18.04 或更高版本
- Python 3.6 或更高版本
- 至少 500MB 可用磁盘空间

## 快速开始

### 1. 安装依赖项

```bash
# 更新包列表
sudo apt update

# 安装Python开发工具
sudo apt install python3 python3-pip python3-dev build-essential

# 安装游戏依赖
pip3 install pygame nuitka
```

### 2. 安装中文字体支持

运行字体安装脚本：

```bash
python3 install_ubuntu_fonts.py
```

或手动安装：

```bash
# 安装推荐的中文字体
sudo apt install fonts-noto-cjk fonts-wqy-microhei

# 刷新字体缓存
fc-cache -fv
```

### 3. 运行游戏

```bash
python3 main.py
```

### 4. 打包为Ubuntu应用程序

```bash
python3 build_ubuntu.py
```

打包完成后，可执行文件将位于 `dist_ubuntu/zd-2d-gunfight`

## 详细说明

### 字体支持

游戏支持以下中文字体（按优先级排序）：

1. **Noto Sans CJK SC** - Google Noto字体（推荐）
2. **WenQuanYi Micro Hei** - 文泉驿微米黑
3. **WenQuanYi Zen Hei** - 文泉驿正黑
4. **Droid Sans Fallback** - Android字体
5. **AR PL UMing CN** - 文鼎明体

如果没有安装中文字体，游戏将使用默认字体，可能无法正确显示中文。

### 打包选项

`build_ubuntu.py` 脚本提供以下功能：

- **系统环境检查** - 验证Python版本和系统依赖
- **依赖项检查** - 确保所需的Python包已安装
- **字体支持检查** - 检测和安装中文字体
- **Nuitka打包** - 生成优化的单文件可执行程序
- **桌面快捷方式** - 创建.desktop文件
- **安装脚本** - 生成用户友好的安装脚本

### 生成的文件

打包完成后，`dist_ubuntu/` 目录将包含：

```
dist_ubuntu/
├── zd-2d-gunfight              # 主可执行文件
├── zd-2d-gunfight.desktop      # 桌面快捷方式
└── install.sh                  # 安装脚本
```

### 安装到系统

使用生成的安装脚本：

```bash
cd dist_ubuntu
./install.sh
```

这将：
- 将游戏安装到 `~/.local/share/zd-2d-gunfight/`
- 在 `~/.local/bin/` 创建符号链接
- 添加桌面快捷方式到应用程序菜单

### 卸载

```bash
rm -rf ~/.local/share/zd-2d-gunfight
rm -f ~/.local/bin/zd-2d-gunfight
rm -f ~/.local/share/applications/zd-2d-gunfight.desktop
```

## 故障排除

### 字体问题

如果游戏中文显示异常：

1. 运行字体测试：
   ```bash
   python3 test_fonts.py
   ```

2. 手动安装字体：
   ```bash
   sudo apt install fonts-noto-cjk
   fc-cache -fv
   ```

### 打包问题

如果Nuitka打包失败：

1. 检查依赖：
   ```bash
   pip3 install --upgrade nuitka
   sudo apt install gcc g++ python3-dev
   ```

2. 清理缓存：
   ```bash
   rm -rf dist_ubuntu
   python3 -m nuitka --version
   ```

### 运行时问题

如果游戏无法启动：

1. 检查Python版本：
   ```bash
   python3 --version
   ```

2. 检查pygame安装：
   ```bash
   python3 -c "import pygame; print(pygame.version.ver)"
   ```

3. 检查权限：
   ```bash
   chmod +x dist_ubuntu/zd-2d-gunfight
   ```

## 性能优化

### 系统优化

```bash
# 安装硬件加速支持
sudo apt install mesa-utils

# 检查OpenGL支持
glxinfo | grep "direct rendering"
```

### 游戏设置

在游戏中可以调整以下设置来提高性能：
- 降低分辨率
- 关闭特效
- 减少视野范围

## 网络配置

如果遇到网络连接问题：

1. 检查防火墙设置：
   ```bash
   sudo ufw status
   sudo ufw allow 5555/udp  # 游戏端口
   ```

2. 检查网络接口：
   ```bash
   ip addr show
   ```

## 支持的Ubuntu版本

- ✅ Ubuntu 20.04 LTS (Focal Fossa)
- ✅ Ubuntu 22.04 LTS (Jammy Jellyfish)
- ✅ Ubuntu 23.04 (Lunar Lobster)
- ✅ Ubuntu 23.10 (Mantic Minotaur)
- ⚠️ Ubuntu 18.04 LTS (需要手动安装Python 3.8+)

## 贡献

如果你在Ubuntu上遇到问题或有改进建议，请提交Issue或Pull Request。

## 许可证

本项目遵循MIT许可证。详见LICENSE文件。