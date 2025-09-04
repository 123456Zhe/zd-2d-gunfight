# ZD 2D 枪战游戏 - Ubuntu使用说明

## 🎯 最新更新

**字体兼容性修复** - 已修复Ubuntu上错误加载Microsoft YaHei字体的问题：
- ✅ 智能检测操作系统，Linux系统不再尝试加载Windows字体
- ✅ 优先使用Ubuntu原生中文字体（Noto Sans CJK SC等）
- ✅ 增强字体验证，确保中文渲染正常
- ✅ 提供详细的字体加载日志

## 快速开始

### 1. 验证字体修复效果
```bash
# 验证字体修复是否生效
python3 verify_font_fix.py

# 测试当前字体支持
python3 test_ubuntu_fonts.py
```

### 2. 检查和安装字体支持
```bash
# 运行字体检查和安装脚本
python3 install_ubuntu_fonts.py
```

### 3. 直接运行游戏
```bash
python3 main.py
```

### 4. 打包为Ubuntu应用程序
```bash
# 运行打包脚本
python3 build_ubuntu.py

# 打包完成后运行
./dist_ubuntu/zd-2d-gunfight

# 或者安装到系统
cd dist_ubuntu && ./install.sh
```

## 脚本说明

### verify_font_fix.py ⭐ 新增
- 验证字体修复效果
- 检测Windows字体在Ubuntu上的错误行为
- 测试改进后的字体选择逻辑
- 生成详细的字体兼容性报告

### install_ubuntu_fonts.py
- 检查Ubuntu系统中文字体安装状态
- 自动安装推荐的中文字体包
- 测试pygame字体加载功能
- 创建字体测试脚本

### build_ubuntu.py  
- 完整的Ubuntu应用程序打包工具
- 系统环境和依赖项检查
- 使用Nuitka进行优化打包
- 创建桌面快捷方式和安装脚本
- 生成单文件可执行程序

### test_ubuntu_fonts.py
- 测试游戏中的字体加载功能
- 可视化字体渲染测试
- 验证中文显示效果
- 支持跨平台字体检测

## 字体支持

### 🔧 修复内容
- **问题**: Ubuntu上pygame.font.SysFont('Microsoft YaHei')会错误地创建字体对象，但实际使用fallback字体
- **修复**: 智能检测操作系统，Linux系统直接使用本地字体，避免Windows字体的兼容性问题
- **效果**: 确保在Ubuntu上使用最佳的中文字体，提升显示质量

### 支持的字体（按优先级）
**Ubuntu/Linux系统:**
- Noto Sans CJK SC (Google Noto字体，推荐)
- Noto Sans CJK TC (繁体中文支持)
- WenQuanYi Micro Hei (文泉驿微米黑)
- WenQuanYi Zen Hei (文泉驿正黑)
- Droid Sans Fallback (Android字体)
- AR PL UMing CN (文鼎明体)
- AR PL UKai CN (文鼎楷体)

**Windows系统:**
- Microsoft YaHei (微软雅黑)
- SimHei (黑体)
- SimSun (宋体)

**macOS系统:**
- PingFang SC (苹方)
- Hiragino Sans GB (冬青黑体)
- STHeiti (华文黑体)

## 系统要求

- Ubuntu 18.04+ 
- Python 3.6+
- pygame
- nuitka (用于打包)

## 故障排除

如果遇到字体显示问题：
1. 运行 `python3 install_ubuntu_fonts.py`
2. 手动安装：`sudo apt install fonts-noto-cjk`
3. 刷新字体缓存：`fc-cache -fv`

如果打包失败：
1. 安装依赖：`sudo apt install python3-dev build-essential`
2. 更新nuitka：`pip3 install --upgrade nuitka`