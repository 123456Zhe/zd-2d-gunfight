# 快速开始 - pygame-gui UI 系统

## 🚀 5 分钟快速上手

### 1. 安装依赖

```bash
pip install pygame-gui
```

### 2. 运行游戏

```bash
# 使用新的 pygame-gui UI（推荐）
python main.py

# 或者使用原生 UI
python main.py --ui native
```

### 3. 测试 UI 系统

```bash
# 快速验证安装
python test_menu_integration.py

# 测试 UI 切换
python test_ui_switching.py
```

## 📖 基本使用

### 在代码中使用

```python
import main

# 方式 1: 自动检测（推荐）
game = main.Game()
game.run()

# 方式 2: 强制使用 pygame-gui
game = main.Game(use_pygame_gui=True)
game.run()

# 方式 3: 强制使用原生 UI
game = main.Game(use_pygame_gui=False)
game.run()
```

### 命令行使用

```bash
# 自动检测（默认）
python main.py

# 强制使用 pygame-gui
python main.py --ui pygame-gui

# 强制使用原生 UI
python main.py --ui native
```

## 🎮 菜单操作

### 创建服务器
1. 点击"创建服务器"按钮
2. 输入服务器名称（默认："我的服务器"）
3. 点击"确认"
4. 输入玩家名称
5. 点击"确认"开始游戏

### 手动连接
1. 在 IP 输入框输入服务器地址
2. 点击"手动连接"按钮
3. 输入玩家名称
4. 点击"确认"连接服务器

### 从列表连接
1. 点击"刷新服务器列表"按钮
2. 点击列表中的服务器
3. 输入玩家名称
4. 点击"确认"连接服务器

## 🔧 自定义主题

编辑 `theme.json` 文件：

```json
{
  "defaults": {
    "colours": {
      "normal_bg": "#000000",
      "normal_text": "#FFFFFF"
    },
    "font": {
      "name": "Microsoft YaHei",
      "size": "20"
    }
  }
}
```

## ❓ 常见问题

### Q: pygame-gui 未安装怎么办？
A: 运行 `pip install pygame-gui` 或使用原生 UI：`python main.py --ui native`

### Q: 中文显示为方块？
A: 
- **Windows**: 安装中文语言包
- **Linux**: `sudo apt install fonts-noto-cjk`

### Q: 如何切换回原生 UI？
A: 使用命令 `python main.py --ui native`

### Q: 主题加载失败？
A: 检查 `theme.json` 文件是否存在且格式正确

## 📚 更多信息

- 完整指南: `UI_INTEGRATION_GUIDE.md`
- 验证报告: `TASK_9_VERIFICATION.md`
- 任务总结: `TASK_9_SUMMARY.md`

## 🎯 下一步

- 探索游戏功能
- 自定义 UI 主题
- 查看完整文档了解更多功能

---

**提示**: 如果遇到问题，请查看 `UI_INTEGRATION_GUIDE.md` 中的故障排除部分。
