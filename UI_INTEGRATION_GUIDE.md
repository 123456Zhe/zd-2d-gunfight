# pygame-gui UI 集成指南

## 概述

游戏现在支持两种 UI 系统：
1. **pygame-gui UI** - 现代化的 UI 组件系统（推荐）
2. **原生 UI** - 基于 Pygame 原生绘制的 UI（备份方案）

## 安装 pygame-gui

如果要使用 pygame-gui UI 系统，需要先安装 pygame-gui 库：

```bash
pip install pygame-gui
```

## 使用方法

### 自动检测（默认）

直接运行游戏，系统会自动检测 pygame-gui 是否可用：

```bash
python main.py
```

- 如果 pygame-gui 已安装，将使用 pygame-gui UI
- 如果 pygame-gui 未安装，将自动回退到原生 UI

### 强制使用 pygame-gui UI

```bash
python main.py --ui pygame-gui
```

如果 pygame-gui 未安装，程序会报错并提示安装。

### 强制使用原生 UI

```bash
python main.py --ui native
```

即使 pygame-gui 已安装，也会使用原生 UI。

## UI 系统对比

| 特性 | pygame-gui UI | 原生 UI |
|------|---------------|---------|
| 外观 | 现代化、主题化 | 简单、功能性 |
| 可维护性 | 高（组件化） | 中（手动绘制） |
| 性能 | 良好 | 优秀 |
| 依赖 | 需要 pygame-gui | 仅需 pygame |
| 自定义 | 通过主题文件 | 通过代码 |

## 功能特性

### pygame-gui UI 特性

1. **主题系统** - 通过 `theme.json` 配置 UI 样式
2. **组件化** - 使用 UIButton、UITextEntryLine 等标准组件
3. **事件驱动** - 使用 pygame-gui 事件系统
4. **跨平台字体** - 自动检测和配置中文字体

### 当前实现的功能

- ✅ 主菜单界面
  - 游戏标题和副标题
  - 创建服务器按钮
  - 刷新服务器列表按钮
  - IP 地址输入框
  - 手动连接按钮
  - 服务器名称输入
  - 玩家名称输入
  - 服务器列表显示

### 待实现的功能

- ⏳ 游戏内 HUD（任务 10-15）
- ⏳ 聊天系统（任务 16-21）
- ⏳ 连接界面（任务 22-25）

## 测试

### 基本集成测试

```bash
python test_menu_integration.py
```

验证 pygame-gui 是否正确安装和集成。

### UI 流程测试

```bash
python test_menu_ui_flow.py
```

打开测试窗口，手动测试 UI 组件。

### 导航流程测试

```bash
python test_menu_navigation.py
```

测试完整的菜单导航和服务器连接流程。支持自动测试：
- 按 `T` 键 - 自动测试创建服务器流程
- 按 `C` 键 - 自动测试手动连接流程

## 配置

### 主题配置

编辑 `theme.json` 文件可以自定义 UI 样式：

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

### 字体配置

字体会自动根据操作系统选择：
- **Windows**: Microsoft YaHei
- **Linux**: Noto Sans CJK SC
- **macOS**: PingFang SC

## 故障排除

### pygame-gui 未安装

**错误信息**: `警告: pygame-gui 未安装，将使用原生 UI`

**解决方法**:
```bash
pip install pygame-gui
```

### 字体显示问题

**问题**: 中文显示为方块或乱码

**解决方法**:
- **Windows**: 确保安装了中文语言包
- **Linux**: 安装中文字体包
  ```bash
  sudo apt install fonts-noto-cjk fonts-wqy-microhei
  ```

### 主题加载失败

**错误信息**: `警告: 主题加载失败，使用默认主题`

**解决方法**:
1. 检查 `theme.json` 文件是否存在
2. 检查 JSON 格式是否正确
3. 如果问题持续，删除 `theme.json` 让系统使用默认主题

## 开发指南

### 添加新的 UI 组件

1. 在 `ui_pygame_gui.py` 中的相应类添加组件
2. 在 `create_ui()` 方法中创建组件
3. 在 `update()` 方法中更新组件状态
4. 在 `handle_event()` 方法中处理事件

### 切换 UI 系统

在代码中可以通过以下方式切换：

```python
# 使用 pygame-gui UI
game = Game(use_pygame_gui=True)

# 使用原生 UI
game = Game(use_pygame_gui=False)

# 自动检测
game = Game(use_pygame_gui=None)
```

## 参考资料

- [pygame-gui 官方文档](https://pygame-gui.readthedocs.io/)
- [设计文档](.kiro/specs/pygame-gui-ui-rewrite/design.md)
- [需求文档](.kiro/specs/pygame-gui-ui-rewrite/requirements.md)
- [任务列表](.kiro/specs/pygame-gui-ui-rewrite/tasks.md)
