"""
pygame-gui UI 模块

使用 pygame-gui 库实现的现代化 UI 系统，替代原生 Pygame 绘制的 UI。
提供菜单、HUD、聊天和连接界面的组件化实现。
"""

import pygame
import pygame_gui
from typing import Optional, Dict, List, Tuple
import os
import json
import platform
import ui  # 导入现有的字体加载系统


def setup_fonts_for_pygame_gui(theme_path: str = 'theme.json') -> Dict[str, str]:
    """
    设置 pygame-gui 使用的字体，集成现有字体加载系统
    
    此函数会：
    1. 使用 ui.load_fonts() 加载系统字体
    2. 根据操作系统选择合适的字体
    3. 更新主题配置文件以使用正确的字体
    4. 提供字体加载失败的后备方案
    
    Args:
        theme_path: 主题配置文件路径
        
    Returns:
        包含字体信息的字典:
        {
            'font_name': str,  # 字体名称
            'font_loaded': bool,  # 是否成功加载字体
            'system': str,  # 操作系统
            'fallback_used': bool  # 是否使用了后备字体
        }
    """
    print("=" * 60)
    print("pygame-gui 字体集成系统")
    print("=" * 60)
    
    # 检测操作系统
    system = platform.system().lower()
    print(f"检测到操作系统: {system}")
    
    # 使用现有的字体加载系统
    print("\n正在加载系统字体...")
    fonts_info = ui.load_fonts()
    font_name = fonts_info.get('font_name', 'Default')
    
    # 判断是否使用了后备字体
    fallback_used = (font_name == 'Default')
    
    if fallback_used:
        try:
            print("\n⚠️  警告: 使用默认字体，中文显示可能不完整")
        except UnicodeEncodeError:
            print("\n[WARNING] 使用默认字体，中文显示可能不完整")
        print("建议安装中文字体包以获得更好的显示效果")
        
        if system == 'linux':
            print("Ubuntu/Linux用户可以运行:")
            print("  sudo apt install fonts-noto-cjk fonts-wqy-microhei")
        elif system == 'windows':
            print("Windows用户通常已安装 Microsoft YaHei 字体")
            print("如果没有，请从系统设置中安装中文语言包")
    else:
        try:
            print(f"\n✅ 成功加载字体: {font_name}")
        except UnicodeEncodeError:
            print(f"\n[OK] 成功加载字体: {font_name}")
    
    # 根据操作系统构建字体后备列表
    if system == 'windows':
        font_fallback_list = [
            font_name if not fallback_used else 'Microsoft YaHei',
            'Microsoft YaHei',
            'SimHei',
            'SimSun',
            'Arial Unicode MS',
            'DejaVu Sans',
            'Arial'
        ]
    elif system == 'linux':
        font_fallback_list = [
            font_name if not fallback_used else 'Noto Sans CJK SC',
            'Noto Sans CJK SC',
            'Noto Sans CJK TC',
            'WenQuanYi Micro Hei',
            'WenQuanYi Zen Hei',
            'Droid Sans Fallback',
            'DejaVu Sans',
            'Liberation Sans',
            'FreeSans'
        ]
    elif system == 'darwin':  # macOS
        font_fallback_list = [
            font_name if not fallback_used else 'PingFang SC',
            'PingFang SC',
            'Hiragino Sans GB',
            'STHeiti',
            'Arial Unicode MS',
            'Helvetica',
            'Arial'
        ]
    else:
        font_fallback_list = [
            'DejaVu Sans',
            'Liberation Sans',
            'FreeSans',
            'Arial'
        ]
    
    # 去重并保持顺序
    seen = set()
    font_fallback_list = [x for x in font_fallback_list if not (x in seen or seen.add(x))]
    
    # 构建字体字符串（pygame-gui 支持逗号分隔的后备字体列表）
    font_string = ','.join(font_fallback_list)
    
    print(f"\n字体后备列表: {font_string}")
    
    # 更新主题配置文件
    try:
        if os.path.exists(theme_path):
            print(f"\n正在更新主题配置文件: {theme_path}")
            
            # 读取现有主题配置
            with open(theme_path, 'r', encoding='utf-8') as f:
                theme_data = json.load(f)
            
            # 更新字体配置
            if 'defaults' not in theme_data:
                theme_data['defaults'] = {}
            if 'font' not in theme_data['defaults']:
                theme_data['defaults']['font'] = {}
            
            # 设置字体名称（使用后备列表）
            theme_data['defaults']['font']['name'] = font_string
            
            # 确保 label 使用相同的字体
            if 'label' not in theme_data:
                theme_data['label'] = {}
            if 'font' not in theme_data['label']:
                theme_data['label']['font'] = {}
            theme_data['label']['font']['name'] = font_string
            
            # 确保 button 使用相同的字体
            if 'button' not in theme_data:
                theme_data['button'] = {}
            if 'font' not in theme_data['button']:
                theme_data['button']['font'] = {}
            theme_data['button']['font']['name'] = font_string
            # 如果没有设置 size，使用默认值
            if 'size' not in theme_data['button']['font']:
                theme_data['button']['font']['size'] = '20'
            
            # 更新所有自定义组件的字体
            for key in theme_data.keys():
                if key.startswith('#@') and isinstance(theme_data[key], dict):
                    if 'font' in theme_data[key]:
                        theme_data[key]['font']['name'] = font_string
            
            # 保存更新后的主题配置
            with open(theme_path, 'w', encoding='utf-8') as f:
                json.dump(theme_data, f, indent=2, ensure_ascii=False)
            
            try:
                print("✅ 主题配置文件更新成功")
            except UnicodeEncodeError:
                print("[OK] 主题配置文件更新成功")
        else:
            try:
                print(f"\n⚠️  警告: 主题文件 {theme_path} 不存在")
            except UnicodeEncodeError:
                print(f"\n[WARNING] 主题文件 {theme_path} 不存在")
            print("将使用 pygame-gui 默认主题")
    
    except Exception as e:
        try:
            print(f"\n❌ 错误: 更新主题配置失败: {e}")
        except UnicodeEncodeError:
            print(f"\n[ERROR] 更新主题配置失败: {e}")
        print("将使用现有主题配置")
    
    print("\n" + "=" * 60)
    print("字体集成完成")
    print("=" * 60 + "\n")
    
    # 返回字体信息
    return {
        'font_name': font_name,
        'font_loaded': not fallback_used,
        'system': system,
        'fallback_used': fallback_used,
        'font_string': font_string
    }


class UIManagerWrapper:
    """
    UIManager 包装类
    
    封装 pygame_gui.UIManager，提供统一的 UI 管理接口。
    """
    
    def __init__(self, screen_size: Tuple[int, int], theme_path: Optional[str] = None):
        """
        初始化 UIManagerWrapper
        
        Args:
            screen_size: 屏幕尺寸 (width, height)
            theme_path: 主题文件路径，如果为 None 则使用默认主题
        """
        self.screen_size = screen_size
        self.theme_path = theme_path
        
        # 初始化 pygame_gui.UIManager
        try:
            if theme_path and os.path.exists(theme_path):
                self.manager = pygame_gui.UIManager(screen_size, theme_path)
            else:
                self.manager = pygame_gui.UIManager(screen_size)
                if theme_path:
                    print(f"警告: 主题文件 {theme_path} 不存在，使用默认主题")
        except Exception as e:
            print(f"警告: 主题加载失败，使用默认主题: {e}")
            self.manager = pygame_gui.UIManager(screen_size)
    
    def update(self, time_delta: float) -> None:
        """
        更新 UI 状态
        
        Args:
            time_delta: 自上次更新以来的时间增量（秒）
        """
        self.manager.update(time_delta)
    
    def draw_ui(self, screen: pygame.Surface) -> None:
        """
        绘制 UI 到屏幕
        
        Args:
            screen: Pygame 屏幕 Surface
        """
        self.manager.draw_ui(screen)
    
    def process_events(self, event: pygame.event.Event) -> None:
        """
        处理 pygame 事件
        
        Args:
            event: Pygame 事件对象
        """
        self.manager.process_events(event)
    
    def clear(self) -> None:
        """清理所有 UI 元素"""
        self.manager.clear_and_reset()
    
    def get_manager(self) -> pygame_gui.UIManager:
        """
        获取底层的 UIManager 实例
        
        Returns:
            pygame_gui.UIManager 实例
        """
        return self.manager


class MenuUI:
    """
    主菜单 UI 类
    
    管理主菜单界面的所有 UI 组件，包括按钮、输入框、服务器列表等。
    
    状态管理:
        menu_state = {
            'scanning_servers': bool,  # 是否正在扫描服务器
            'found_servers': list,  # 发现的服务器列表
            'show_server_name_input': bool,  # 是否显示服务器名称输入框
            'show_player_name_input': bool,  # 是否显示玩家名称输入框
            'creating_server': bool,  # 是否正在创建服务器
            'selected_server_ip': str  # 选中的服务器 IP
        }
    """
    
    def __init__(self, ui_manager: UIManagerWrapper):
        """
        初始化 MenuUI
        
        Args:
            ui_manager: UIManagerWrapper 实例
        """
        self.ui_manager = ui_manager
        self.manager = ui_manager.get_manager()
        
        # UI 组件（将在 create_ui 中初始化）
        self.title_label = None
        self.subtitle_label = None
        self.create_button = None
        self.refresh_button = None
        self.ip_input = None
        self.ip_label = None
        self.connect_button = None
        self.server_name_input = None
        self.server_name_label = None
        self.server_name_confirm_button = None
        self.player_name_input = None
        self.player_name_label = None
        self.player_name_confirm_button = None
        self.server_list_panel = None
        self.server_list_title = None
        self.server_list_container = None  # 滚动容器
        self.server_items = []
        
        # 扫描状态相关
        self.scanning_label = None
        self.scanning_animation_time = 0.0
        self.scanning_dots = 0
        
        # 空列表提示
        self.empty_list_label = None
        
        # 缓存上一次的服务器列表，用于优化性能
        self._last_servers = None
        
        # 字体大小配置（用于动态计算高度）
        self.server_item_font_size = 13
        self.server_item_line_spacing = 1.0  # 最小行间距
        
        # 所有组件的列表，用于批量管理
        self.all_components = []
        
        # UI 是否已创建
        self.ui_created = False
    
    def create_ui(self) -> None:
        """
        创建所有 UI 组件
        
        此方法会创建主菜单的所有 UI 元素，包括：
        - 标题和副标题
        - 创建服务器和刷新按钮
        - IP 输入框和连接按钮
        - 服务器名称输入框
        - 玩家名称输入框
        - 服务器列表面板
        
        注意: 具体的组件创建将在后续任务中实现
        """
        if self.ui_created:
            print("警告: MenuUI 已经创建，跳过重复创建")
            return
        
        # 任务 5: 创建标题和按钮
        self._create_title_and_buttons()
        
        # 任务 6: 创建输入框
        self._create_input_fields()
        
        # 任务 7: 创建服务器列表
        self._create_server_list()
        
        self.ui_created = True
        print("MenuUI 基础结构已创建")
    
    def _create_title_and_buttons(self) -> None:
        """
        创建标题和按钮组件
        
        创建以下组件:
        - 游戏标题 (UILabel)
        - 副标题 (UILabel)
        - 创建服务器按钮 (UIButton)
        - 刷新服务器列表按钮 (UIButton)
        """
        # 获取屏幕尺寸
        screen_width, screen_height = self.ui_manager.screen_size
        
        # 创建游戏标题
        title_rect = pygame.Rect(
            (screen_width // 2 - 200, 50),  # 居中，顶部留出空间
            (400, 60)  # 宽度400，高度60
        )
        self.title_label = pygame_gui.elements.UILabel(
            relative_rect=title_rect,
            text="ZD-2D-Gunfight",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@title_label')
        )
        self.all_components.append(self.title_label)
        
        # 创建副标题
        subtitle_rect = pygame.Rect(
            (screen_width // 2 - 150, 120),  # 标题下方
            (300, 40)  # 宽度300，高度40
        )
        self.subtitle_label = pygame_gui.elements.UILabel(
            relative_rect=subtitle_rect,
            text="多人在线射击游戏",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@subtitle_label')
        )
        self.all_components.append(self.subtitle_label)
        
        # 创建"创建服务器"按钮
        create_button_rect = pygame.Rect(
            (screen_width // 2 - 100, 200),  # 副标题下方
            (200, 50)  # 宽度200，高度50
        )
        self.create_button = pygame_gui.elements.UIButton(
            relative_rect=create_button_rect,
            text="创建服务器",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@create_button')
        )
        self.all_components.append(self.create_button)
        
        # 创建"刷新服务器列表"按钮
        refresh_button_rect = pygame.Rect(
            (screen_width // 2 - 100, 260),  # 创建服务器按钮下方
            (200, 50)  # 宽度200，高度50
        )
        self.refresh_button = pygame_gui.elements.UIButton(
            relative_rect=refresh_button_rect,
            text="刷新服务器列表",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@refresh_button')
        )
        self.all_components.append(self.refresh_button)
        
        print("MenuUI 标题和按钮已创建")
    
    def _create_input_fields(self) -> None:
        """
        创建输入框组件
        
        创建以下组件:
        - IP 地址输入框 (UITextEntryLine)
        - IP 输入框标签 (UILabel)
        - 手动连接按钮 (UIButton)
        - 服务器名称输入框 (UITextEntryLine)
        - 服务器名称标签 (UILabel)
        - 服务器名称确认按钮 (UIButton)
        - 玩家名称输入框 (UITextEntryLine)
        - 玩家名称标签 (UILabel)
        - 玩家名称确认按钮 (UIButton)
        
        注意: 服务器名称和玩家名称输入框初始时是隐藏的
        """
        # 获取屏幕尺寸
        screen_width, screen_height = self.ui_manager.screen_size
        
        # === IP 地址输入区域 ===
        # 创建 IP 输入框标签
        ip_label_rect = pygame.Rect(
            (screen_width // 2 - 250, 330),  # 刷新按钮下方
            (150, 30)  # 宽度150，高度30
        )
        self.ip_label = pygame_gui.elements.UILabel(
            relative_rect=ip_label_rect,
            text="服务器 IP:",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@ip_label')
        )
        self.all_components.append(self.ip_label)
        
        # 创建 IP 地址输入框
        ip_input_rect = pygame.Rect(
            (screen_width // 2 - 90, 325),  # IP 标签右侧
            (200, 40)  # 宽度200，高度40
        )
        self.ip_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=ip_input_rect,
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@ip_input')
        )
        self.ip_input.set_text("127.0.0.1")  # 默认本地地址
        self.all_components.append(self.ip_input)
        
        # 创建"手动连接"按钮
        connect_button_rect = pygame.Rect(
            (screen_width // 2 + 120, 325),  # IP 输入框右侧
            (120, 40)  # 宽度120，高度40
        )
        self.connect_button = pygame_gui.elements.UIButton(
            relative_rect=connect_button_rect,
            text="手动连接",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@connect_button')
        )
        self.all_components.append(self.connect_button)
        
        # === 服务器名称输入区域（初始隐藏）===
        # 创建服务器名称标签
        server_name_label_rect = pygame.Rect(
            (screen_width // 2 - 200, 400),  # IP 输入区域下方
            (150, 30)  # 宽度150，高度30
        )
        self.server_name_label = pygame_gui.elements.UILabel(
            relative_rect=server_name_label_rect,
            text="服务器名称:",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@server_name_label')
        )
        self.server_name_label.hide()  # 初始隐藏
        self.all_components.append(self.server_name_label)
        
        # 创建服务器名称输入框
        server_name_input_rect = pygame.Rect(
            (screen_width // 2 - 200, 435),  # 标签下方
            (250, 40)  # 宽度250，高度40
        )
        self.server_name_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=server_name_input_rect,
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@server_name_input')
        )
        self.server_name_input.set_text("我的服务器")  # 默认名称
        self.server_name_input.hide()  # 初始隐藏
        self.all_components.append(self.server_name_input)
        
        # 创建服务器名称确认按钮
        server_name_confirm_rect = pygame.Rect(
            (screen_width // 2 + 60, 435),  # 输入框右侧
            (100, 40)  # 宽度100，高度40
        )
        self.server_name_confirm_button = pygame_gui.elements.UIButton(
            relative_rect=server_name_confirm_rect,
            text="确认",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@server_name_confirm_button')
        )
        self.server_name_confirm_button.hide()  # 初始隐藏
        self.all_components.append(self.server_name_confirm_button)
        
        # === 玩家名称输入区域（初始隐藏）===
        # 创建玩家名称标签
        player_name_label_rect = pygame.Rect(
            (screen_width // 2 - 200, 490),  # 服务器名称区域下方
            (150, 30)  # 宽度150，高度30
        )
        self.player_name_label = pygame_gui.elements.UILabel(
            relative_rect=player_name_label_rect,
            text="玩家名称:",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@player_name_label')
        )
        self.player_name_label.hide()  # 初始隐藏
        self.all_components.append(self.player_name_label)
        
        # 创建玩家名称输入框
        player_name_input_rect = pygame.Rect(
            (screen_width // 2 - 200, 525),  # 标签下方
            (250, 40)  # 宽度250，高度40
        )
        self.player_name_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=player_name_input_rect,
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@player_name_input')
        )
        self.player_name_input.set_text("玩家")  # 默认名称
        self.player_name_input.hide()  # 初始隐藏
        self.all_components.append(self.player_name_input)
        
        # 创建玩家名称确认按钮
        player_name_confirm_rect = pygame.Rect(
            (screen_width // 2 + 60, 525),  # 输入框右侧
            (100, 40)  # 宽度100，高度40
        )
        self.player_name_confirm_button = pygame_gui.elements.UIButton(
            relative_rect=player_name_confirm_rect,
            text="确认",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@player_name_confirm_button')
        )
        self.player_name_confirm_button.hide()  # 初始隐藏
        self.all_components.append(self.player_name_confirm_button)
        
        print("MenuUI 输入框已创建")
    
    def _create_server_list(self) -> None:
        """
        创建服务器列表组件
        
        创建以下组件:
        - 服务器列表容器 (UIPanel)
        - 服务器列表标题 (UILabel)
        - 服务器列表滚动容器 (UIScrollingContainer)
        
        服务器列表项将在 update_server_list 方法中动态创建
        """
        # 获取屏幕尺寸
        screen_width, screen_height = self.ui_manager.screen_size
        
        # 创建服务器列表容器面板
        # 位置在屏幕右侧，避免遮挡左侧的手动连接按钮
        # 手动连接按钮位于 y=325，高度40，所以面板从 y=380 开始
        server_list_panel_rect = pygame.Rect(
            (screen_width - 310, 380),  # 右侧，避开手动连接按钮
            (290, screen_height - 430)  # 宽度290，高度自适应
        )
        self.server_list_panel = pygame_gui.elements.UIPanel(
            relative_rect=server_list_panel_rect,
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@server_list_panel')
        )
        self.all_components.append(self.server_list_panel)
        
        # 创建服务器列表标题
        # 标题位于面板内部顶部
        server_list_title_rect = pygame.Rect(
            (5, 5),  # 相对于面板的位置
            (280, 40)  # 宽度280，高度40
        )
        self.server_list_title = pygame_gui.elements.UILabel(
            relative_rect=server_list_title_rect,
            text="可用服务器",
            manager=self.manager,
            container=self.server_list_panel,
            object_id=pygame_gui.core.ObjectID(class_id='@server_list_title')
        )
        self.all_components.append(self.server_list_title)
        
        # 创建滚动容器用于服务器列表
        # 位于标题下方，底部留出空间给扫描状态
        panel_height = server_list_panel_rect.height
        scroll_container_rect = pygame.Rect(
            (5, 50),  # 标题下方
            (280, panel_height - 110)  # 高度：面板高度 - 标题 - 底部空间
        )
        self.server_list_container = pygame_gui.elements.UIScrollingContainer(
            relative_rect=scroll_container_rect,
            manager=self.manager,
            container=self.server_list_panel,
            object_id=pygame_gui.core.ObjectID(class_id='@server_list_container')
        )
        self.all_components.append(self.server_list_container)
        
        print("MenuUI 服务器列表容器已创建")
    
    def destroy_ui(self) -> None:
        """
        清理所有 UI 组件
        
        此方法会销毁所有已创建的 UI 元素，释放资源。
        使用 kill() 方法销毁 pygame-gui 组件。
        """
        if not self.ui_created:
            return
        
        # 销毁所有组件
        components_to_destroy = [
            self.title_label,
            self.subtitle_label,
            self.create_button,
            self.refresh_button,
            self.ip_input,
            self.ip_label,
            self.connect_button,
            self.server_name_input,
            self.server_name_label,
            self.server_name_confirm_button,
            self.player_name_input,
            self.player_name_label,
            self.player_name_confirm_button,
            self.server_list_panel,
            self.server_list_title,
            self.server_list_container
        ]
        
        # 销毁服务器列表项
        for item in self.server_items:
            if 'button' in item and item['button'] is not None:
                item['button'].kill()
        
        # 销毁扫描状态标签
        if self.scanning_label is not None:
            self.scanning_label.kill()
            self.scanning_label = None
        
        # 销毁空列表提示标签
        if self.empty_list_label is not None:
            self.empty_list_label.kill()
            self.empty_list_label = None
        
        # 销毁主要组件
        for component in components_to_destroy:
            if component is not None:
                component.kill()
        
        # 清空所有引用
        self.title_label = None
        self.subtitle_label = None
        self.create_button = None
        self.refresh_button = None
        self.ip_input = None
        self.ip_label = None
        self.connect_button = None
        self.server_name_input = None
        self.server_name_label = None
        self.server_name_confirm_button = None
        self.player_name_input = None
        self.player_name_label = None
        self.player_name_confirm_button = None
        self.server_list_panel = None
        self.server_list_title = None
        self.server_list_container = None
        self.server_items.clear()
        self.all_components.clear()
        
        self.ui_created = False
        print("MenuUI 已清理")
    
    def update(self, menu_state: Dict, time_delta: float = 0.016) -> None:
        """
        更新 UI 状态
        
        根据 menu_state 更新 UI 显示，包括：
        - 显示/隐藏服务器名称输入框
        - 显示/隐藏玩家名称输入框
        - 更新服务器列表
        - 更新扫描状态
        
        Args:
            menu_state: 菜单状态字典，包含以下键：
                - scanning_servers: bool - 是否正在扫描服务器
                - found_servers: list - 发现的服务器列表
                - show_server_name_input: bool - 是否显示服务器名称输入框
                - show_player_name_input: bool - 是否显示玩家名称输入框
                - creating_server: bool - 是否正在创建服务器
                - selected_server_ip: str - 选中的服务器 IP
            time_delta: 时间增量（秒），用于动画更新
        """
        if not self.ui_created:
            return
        
        # 任务 7: 更新服务器列表（只在列表变化时更新）
        if 'found_servers' in menu_state:
            servers = menu_state['found_servers']
            # 检查服务器列表是否变化
            if self._servers_changed(servers):
                self.update_server_list(servers)
                self._last_servers = servers.copy() if servers else []
        
        # 任务 7: 更新扫描状态
        if 'scanning_servers' in menu_state:
            self.update_scanning_status(menu_state['scanning_servers'], time_delta)
        
        # 任务 8: 根据状态显示/隐藏服务器名称输入框
        if 'show_server_name_input' in menu_state:
            should_show = menu_state['show_server_name_input']
            # 检查当前是否显示
            is_visible = (self.server_name_label and 
                         self.server_name_label.visible)
            
            # 只在状态变化时更新显示
            if should_show and not is_visible:
                self.show_server_name_input()
            elif not should_show and is_visible:
                # 只隐藏服务器名称输入框
                if self.server_name_label:
                    self.server_name_label.hide()
                if self.server_name_input:
                    self.server_name_input.hide()
                if self.server_name_confirm_button:
                    self.server_name_confirm_button.hide()
        
        # 任务 8: 根据状态显示/隐藏玩家名称输入框
        if 'show_player_name_input' in menu_state:
            should_show = menu_state['show_player_name_input']
            creating_server = menu_state.get('creating_server', False)
            # 检查当前是否显示
            is_visible = (self.player_name_label and 
                         self.player_name_label.visible)
            
            # 只在状态变化时更新显示
            if should_show and not is_visible:
                self.show_player_name_input(creating_server)
            elif not should_show and is_visible:
                # 只隐藏玩家名称输入框
                if self.player_name_label:
                    self.player_name_label.hide()
                if self.player_name_input:
                    self.player_name_input.hide()
                if self.player_name_confirm_button:
                    self.player_name_confirm_button.hide()
    
    def handle_event(self, event: pygame.event.Event) -> Dict:
        """
        处理事件
        
        处理 pygame-gui 事件，包括：
        - UI_BUTTON_PRESSED: 按钮点击事件
        - UI_TEXT_ENTRY_FINISHED: 文本输入完成事件
        - UI_SELECTION_LIST_NEW_SELECTION: 列表选择事件
        
        Args:
            event: Pygame 事件对象
            
        Returns:
            事件处理结果字典，包含以下可能的键：
                - action: str - 执行的动作（如 'create_server', 'connect', 'refresh'）
                - data: dict - 相关数据（如 IP 地址、服务器名称等）
        """
        if not self.ui_created:
            return {}
        
        result = {}
        
        # 处理鼠标点击事件（用于UIPanel）
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            for item in self.server_items:
                panel_rect = item['panel'].get_abs_rect()
                if panel_rect.collidepoint(mouse_pos):
                    # 改变边框颜色作为反馈
                    item['panel'].border_colour = pygame.Color('#00FF00')
                    item['panel'].rebuild()
                    server_info = item['server_info']
                    result = {'action': 'select_server', 'data': {'server_info': server_info, 'ip': server_info.get('ip', ''), 'port': server_info.get('port', 0), 'name': server_info.get('name', '未命名服务器')}}
                    print(f"MenuUI: 选择服务器 - {server_info.get('name', '未命名')}")
                    return result
                else:
                    # 重置其他面板的边框颜色
                    item['panel'].border_colour = pygame.Color('#FFFFFF')
                    item['panel'].rebuild()
        
        # 任务 5 & 6: 处理按钮点击事件
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            # 处理"创建服务器"按钮
            if event.ui_element == self.create_button:
                result = {
                    'action': 'create_server',
                    'data': {}
                }
                print("MenuUI: 创建服务器按钮被点击")
            
            # 处理"刷新服务器列表"按钮
            elif event.ui_element == self.refresh_button:
                result = {
                    'action': 'refresh_servers',
                    'data': {}
                }
                print("MenuUI: 刷新服务器列表按钮被点击")
            
            # 处理"手动连接"按钮
            elif event.ui_element == self.connect_button:
                ip_address = self.ip_input.get_text() if self.ip_input else "127.0.0.1"
                result = {
                    'action': 'manual_connect',
                    'data': {
                        'ip': ip_address
                    }
                }
                print(f"MenuUI: 手动连接按钮被点击，IP: {ip_address}")
            
            # 处理"服务器名称确认"按钮
            elif event.ui_element == self.server_name_confirm_button:
                server_name = self.server_name_input.get_text() if self.server_name_input else "我的服务器"
                result = {
                    'action': 'confirm_server_name',
                    'data': {
                        'server_name': server_name
                    }
                }
                print(f"MenuUI: 服务器名称确认，名称: {server_name}")
            
            # 处理"玩家名称确认"按钮
            elif event.ui_element == self.player_name_confirm_button:
                player_name = self.player_name_input.get_text() if self.player_name_input else "玩家"
                result = {
                    'action': 'confirm_player_name',
                    'data': {
                        'player_name': player_name
                    }
                }
                print(f"MenuUI: 玩家名称确认，名称: {player_name}")
            

        
        # 任务 6: 处理输入框完成事件（按 Enter 键）
        elif event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
            # 处理 IP 输入框
            if event.ui_element == self.ip_input:
                ip_address = event.text
                result = {
                    'action': 'manual_connect',
                    'data': {
                        'ip': ip_address
                    }
                }
                print(f"MenuUI: IP 输入完成，IP: {ip_address}")
            
            # 处理服务器名称输入框
            elif event.ui_element == self.server_name_input:
                server_name = event.text
                result = {
                    'action': 'confirm_server_name',
                    'data': {
                        'server_name': server_name
                    }
                }
                print(f"MenuUI: 服务器名称输入完成，名称: {server_name}")
            
            # 处理玩家名称输入框
            elif event.ui_element == self.player_name_input:
                player_name = event.text
                result = {
                    'action': 'confirm_player_name',
                    'data': {
                        'player_name': player_name
                    }
                }
                print(f"MenuUI: 玩家名称输入完成，名称: {player_name}")
        
        # TODO: 在任务 7 中实现服务器列表选择事件处理
        
        return result
    
    def show_server_name_input(self) -> None:
        """
        显示服务器名称输入框
        
        当用户点击"创建服务器"按钮时调用此方法。
        """
        if not self.ui_created:
            return
        
        # 显示服务器名称相关组件
        if self.server_name_label:
            self.server_name_label.show()
        if self.server_name_input:
            self.server_name_input.show()
            self.server_name_input.focus()  # 自动聚焦到输入框
        if self.server_name_confirm_button:
            self.server_name_confirm_button.show()
        
        print("MenuUI: 显示服务器名称输入框")
    
    def show_player_name_input(self, is_creating_server: bool = False) -> None:
        """
        显示玩家名称输入框
        
        当需要输入玩家名称时调用此方法。
        
        Args:
            is_creating_server: 是否正在创建服务器
        """
        if not self.ui_created:
            return
        
        # 显示玩家名称相关组件
        if self.player_name_label:
            self.player_name_label.show()
        if self.player_name_input:
            self.player_name_input.show()
            self.player_name_input.focus()  # 自动聚焦到输入框
        if self.player_name_confirm_button:
            self.player_name_confirm_button.show()
        
        print(f"MenuUI: 显示玩家名称输入框 (创建服务器: {is_creating_server})")
    
    def hide_name_inputs(self) -> None:
        """
        隐藏名称输入框
        
        隐藏服务器名称和玩家名称输入框。
        """
        if not self.ui_created:
            return
        
        # 隐藏服务器名称相关组件
        if self.server_name_label:
            self.server_name_label.hide()
        if self.server_name_input:
            self.server_name_input.hide()
        if self.server_name_confirm_button:
            self.server_name_confirm_button.hide()
        
        # 隐藏玩家名称相关组件
        if self.player_name_label:
            self.player_name_label.hide()
        if self.player_name_input:
            self.player_name_input.hide()
        if self.player_name_confirm_button:
            self.player_name_confirm_button.hide()
        
        print("MenuUI: 隐藏名称输入框")
    
    def update_server_list(self, servers: List[Dict]) -> None:
        """
        更新服务器列表
        
        使用 UIPanel + UILabel 组合显示服务器信息，确保多行文本正确显示。
        每个服务器项包含：
        - 可点击的背景面板
        - 服务器名称标签（第一行）
        - IP:端口标签（第二行）
        
        Args:
            servers: 服务器列表，每个服务器是一个字典，包含:
                - name: str - 服务器名称
                - ip: str - 服务器 IP 地址
                - port: int - 服务器端口
                - players: int - 当前玩家数（可选）
        """
        if not self.ui_created or not self.server_list_container:
            return
        
        # 清除旧的服务器列表项
        for item in self.server_items:
            if 'panel' in item and item['panel'] is not None:
                item['panel'].kill()
            if 'name_label' in item and item['name_label'] is not None:
                item['name_label'].kill()
            if 'ip_label' in item and item['ip_label'] is not None:
                item['ip_label'].kill()
        self.server_items.clear()
        
        # 隐藏空列表提示
        if self.empty_list_label:
            self.empty_list_label.kill()
            self.empty_list_label = None
        
        # 如果服务器列表为空，显示提示
        if not servers:
            self._show_empty_list_message()
            return
        
        # 固定布局
        item_height = 60
        item_spacing = 3
        item_width = 260
        name_label_height = 25
        ip_label_height = 22
        
        # 计算总内容高度
        total_height = len(servers) * (item_height + item_spacing) + 10
        
        # 设置滚动容器的可滚动区域大小
        container_rect = self.server_list_container.relative_rect
        self.server_list_container.set_scrollable_area_dimensions(
            (container_rect.width - 5, max(total_height, container_rect.height))
        )
        
        # 创建所有服务器列表项
        current_y = 5  # 起始 Y 位置
        
        for i, server in enumerate(servers):
            # 获取服务器信息
            server_name = server.get('name', '未命名服务器')
            server_ip = server.get('ip', '未知')
            server_port = server.get('port', 0)
            server_players = server.get('players', 0)
            
            # 创建服务器列表项面板
            panel_rect = pygame.Rect((5, current_y), (item_width, item_height))
            server_panel = pygame_gui.elements.UIPanel(
                relative_rect=panel_rect,
                manager=self.manager,
                container=self.server_list_container,
                object_id=pygame_gui.core.ObjectID(class_id='@server_item_panel')
            )
            
            # 创建服务器名称标签
            name_rect = pygame.Rect((5, 5), (item_width - 10, name_label_height))
            name_label = pygame_gui.elements.UILabel(
                relative_rect=name_rect,
                text=server_name,
                manager=self.manager,
                container=server_panel,
                object_id=pygame_gui.core.ObjectID(class_id='@server_name_label')
            )
            
            # 创建IP标签
            ip_rect = pygame.Rect((5, 30), (item_width - 10, ip_label_height))
            ip_text = f"{server_ip}:{server_port} ({server_players}人)" if server_players > 0 else f"{server_ip}:{server_port}"
            ip_label = pygame_gui.elements.UILabel(
                relative_rect=ip_rect,
                text=ip_text,
                manager=self.manager,
                container=server_panel,
                object_id=pygame_gui.core.ObjectID(class_id='@server_ip_label')
            )
            
            # 保存服务器列表项信息
            self.server_items.append({
                'panel': server_panel,
                'name_label': name_label,
                'ip_label': ip_label,
                'server_info': server
            })
            
            # 更新下一个列表项的 Y 位置
            current_y += item_height + item_spacing
        
        print(f"MenuUI: 更新服务器列表，共 {len(self.server_items)} 个服务器，总高度 {total_height}px")
    
    def update_scanning_status(self, is_scanning: bool, time_delta: float = 0.016) -> None:
        """
        更新扫描状态显示
        
        显示扫描动画（动画点）或隐藏扫描提示。
        
        Args:
            is_scanning: 是否正在扫描服务器
            time_delta: 时间增量（秒），用于动画更新
        """
        if not self.ui_created or not self.server_list_panel:
            return
        
        if is_scanning:
            # 更新动画时间
            self.scanning_animation_time += time_delta
            
            # 每 0.5 秒更新一次动画点数
            if self.scanning_animation_time >= 0.5:
                self.scanning_animation_time = 0.0
                self.scanning_dots = (self.scanning_dots + 1) % 4  # 0, 1, 2, 3 循环
            
            # 构建动画文本
            dots = '.' * self.scanning_dots
            scanning_text = f"正在扫描服务器{dots}"
            
            # 创建或更新扫描状态标签
            if self.scanning_label is None:
                # 动态计算底部位置
                panel_height = self.server_list_panel.relative_rect.height
                scanning_label_rect = pygame.Rect(
                    (5, panel_height - 50),  # 面板底部往上50像素
                    (280, 40)  # 宽度280，高度40
                )
                self.scanning_label = pygame_gui.elements.UILabel(
                    relative_rect=scanning_label_rect,
                    text=scanning_text,
                    manager=self.manager,
                    container=self.server_list_panel,
                    object_id=pygame_gui.core.ObjectID(class_id='@scanning_label')
                )
            else:
                self.scanning_label.set_text(scanning_text)
        else:
            # 隐藏扫描状态标签
            if self.scanning_label is not None:
                self.scanning_label.kill()
                self.scanning_label = None
                self.scanning_animation_time = 0.0
                self.scanning_dots = 0
    
    def _show_empty_list_message(self) -> None:
        """
        显示空列表提示
        
        当服务器列表为空时，显示提示信息。
        """
        if not self.ui_created or not self.server_list_panel:
            return
        
        # 创建空列表提示标签
        # 动态计算中央位置
        panel_height = self.server_list_panel.relative_rect.height
        empty_label_rect = pygame.Rect(
            (5, panel_height // 2 - 50),  # 面板中央
            (280, 100)  # 宽度280，高度100
        )
        
        # 使用 HTML 格式的文本，确保字体正确
        empty_text = '<font face="Microsoft YaHei" size=4 color=#AAAAAA>' \
                     '未发现可用服务器<br><br>' \
                     '点击 刷新服务器列表 重新扫描' \
                     '</font>'
        
        self.empty_list_label = pygame_gui.elements.UITextBox(
            html_text=empty_text,
            relative_rect=empty_label_rect,
            manager=self.manager,
            container=self.server_list_panel,
            object_id=pygame_gui.core.ObjectID(class_id='@empty_list_label')
        )
        
        print("MenuUI: 显示空列表提示")
    
    def _servers_changed(self, new_servers: List[Dict]) -> bool:
        """
        检查服务器列表是否发生变化
        
        通过比较服务器数量和 IP 地址来判断列表是否变化。
        这是一个性能优化，避免每帧都重新创建服务器列表项。
        
        Args:
            new_servers: 新的服务器列表
            
        Returns:
            如果服务器列表发生变化返回 True，否则返回 False
        """
        # 如果是第一次调用，认为列表已变化
        if self._last_servers is None:
            return True
        
        # 如果服务器数量不同，列表已变化
        if len(new_servers) != len(self._last_servers):
            return True
        
        # 比较每个服务器的 IP 和端口
        for new_server, old_server in zip(new_servers, self._last_servers):
            if (new_server.get('ip') != old_server.get('ip') or
                new_server.get('port') != old_server.get('port')):
                return True
        
        # 列表未变化
        return False


class GameHUD:
    """
    游戏内 HUD 类
    
    管理游戏内 HUD 的所有 UI 组件，包括生命值、弹药、武器信息等。
    
    状态管理:
        hud_state = {
            'player': Player,  # 玩家对象
            'player_count': int,  # 在线玩家数量
            'debug_mode': bool,  # 是否启用调试模式
            'network_manager': NetworkManager,  # 网络管理器
            'nearby_sound_players': list,  # 附近有脚步声的玩家列表
            'bullets_count': int,  # 子弹数量
            'show_vision': bool  # 是否显示视角信息
        }
    """
    
    def __init__(self, ui_manager: UIManagerWrapper):
        """
        初始化 GameHUD
        
        Args:
            ui_manager: UIManagerWrapper 实例
        """
        self.ui_manager = ui_manager
        self.manager = ui_manager.get_manager()
        
        # UI 组件（将在 create_ui 中初始化）
        self.health_label = None
        self.weapon_label = None
        self.ammo_label = None
        self.reload_label = None
        self.melee_status_label = None
        self.aim_label = None
        self.death_label = None
        self.player_count_label = None
        self.interact_hint_label = None
        self.weapon_hint_label = None
        self.switch_hint_label = None
        self.chat_hint_label = None
        self.damage_info_label = None
        self.vision_info_label = None
        self.footstep_label = None
        self.debug_panel = None
        self.debug_labels = []
        
        # 缓存上一次的状态值（用于性能优化）
        self._last_health = None
        self._last_ammo = None
        self._last_weapon = None
        self._last_player_count = None
        self._last_reload_time = None
        self._last_melee_cooldown = None
        self._last_death_time = None
        
        # 调试模式状态
        self._debug_mode = False
        
        # 所有组件的列表，用于批量管理
        self.all_components = []
        
        # UI 是否已创建
        self.ui_created = False
        
        print("GameHUD 已初始化")
    
    def create_ui(self) -> None:
        """
        创建所有 UI 组件
        
        此方法会创建游戏内 HUD 的所有 UI 元素，包括：
        - 玩家状态显示（生命值、武器、弹药等）
        - 提示和信息显示
        - 调试信息面板
        
        注意: 具体的组件创建将在后续任务中实现
        """
        if self.ui_created:
            print("警告: GameHUD 已经创建，跳过重复创建")
            return
        
        # 任务 11: 创建玩家状态显示组件
        self._create_player_status_labels()
        
        # 任务 12: 创建提示和信息显示组件
        self._create_hint_labels()
        
        # 任务 12: 创建调试信息面板
        self._create_debug_panel()
        
        self.ui_created = True
        print("GameHUD 基础结构已创建")
    
    def _create_player_status_labels(self) -> None:
        """
        创建玩家状态显示标签
        
        创建以下组件:
        - 生命值 UILabel
        - 武器类型 UILabel
        - 弹药数量 UILabel
        - 换弹倒计时 UILabel
        - 近战武器状态 UILabel
        - 瞄准状态 UILabel
        - 死亡状态 UILabel
        """
        # 获取屏幕尺寸
        screen_width, screen_height = self.ui_manager.screen_size
        
        # 创建生命值标签（左上角）
        health_rect = pygame.Rect((10, 10), (200, 30))
        self.health_label = pygame_gui.elements.UILabel(
            relative_rect=health_rect,
            text="生命: 100/100",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@health_label')
        )
        self.all_components.append(self.health_label)
        
        # 创建武器类型标签（生命值下方）
        weapon_rect = pygame.Rect((10, 45), (200, 30))
        self.weapon_label = pygame_gui.elements.UILabel(
            relative_rect=weapon_rect,
            text="武器: 枪械",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@weapon_label')
        )
        self.all_components.append(self.weapon_label)
        
        # 创建弹药数量标签（武器类型下方）
        ammo_rect = pygame.Rect((10, 80), (200, 30))
        self.ammo_label = pygame_gui.elements.UILabel(
            relative_rect=ammo_rect,
            text="弹药: 30/30",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@ammo_label')
        )
        self.all_components.append(self.ammo_label)
        
        # 创建换弹倒计时标签（弹药下方，初始隐藏）
        reload_rect = pygame.Rect((10, 115), (200, 30))
        self.reload_label = pygame_gui.elements.UILabel(
            relative_rect=reload_rect,
            text="换弹中: 2.0s",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@reload_label')
        )
        self.reload_label.hide()  # 初始隐藏
        self.all_components.append(self.reload_label)
        
        # 创建近战武器状态标签（换弹下方，初始隐藏）
        melee_status_rect = pygame.Rect((10, 150), (250, 30))
        self.melee_status_label = pygame_gui.elements.UILabel(
            relative_rect=melee_status_rect,
            text="近战冷却: 0.8s",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@melee_status_label')
        )
        self.melee_status_label.hide()  # 初始隐藏
        self.all_components.append(self.melee_status_label)
        
        # 创建瞄准状态标签（屏幕中央上方，初始隐藏）
        aim_rect = pygame.Rect((screen_width // 2 - 100, 10), (200, 30))
        self.aim_label = pygame_gui.elements.UILabel(
            relative_rect=aim_rect,
            text="[瞄准模式]",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@aim_label')
        )
        self.aim_label.hide()  # 初始隐藏
        self.all_components.append(self.aim_label)
        
        # 创建死亡状态标签（屏幕中央，初始隐藏）
        death_rect = pygame.Rect((screen_width // 2 - 200, screen_height // 2 - 80), (400, 160))
        self.death_label = pygame_gui.elements.UITextBox(
            html_text='<font face="Microsoft YaHei" size=6 color=#FF0000><b>你已死亡</b><br><br>复活倒计时: 3.0s</font>',
            relative_rect=death_rect,
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@death_label')
        )
        self.death_label.hide()  # 初始隐藏
        self.all_components.append(self.death_label)
        
        print("GameHUD 玩家状态标签已创建")
    
    def _create_hint_labels(self) -> None:
        """
        创建提示和信息显示标签
        
        创建以下组件:
        - 玩家数量 UILabel
        - 交互提示 UILabel
        - 武器控制提示 UILabel
        - 聊天提示 UILabel
        - 伤害信息 UILabel
        - 视角信息 UILabel
        - 脚步声提示 UILabel
        """
        # 获取屏幕尺寸
        screen_width, screen_height = self.ui_manager.screen_size
        
        # 创建玩家数量标签（右上角）
        player_count_rect = pygame.Rect((screen_width - 210, 10), (200, 30))
        self.player_count_label = pygame_gui.elements.UILabel(
            relative_rect=player_count_rect,
            text="在线玩家: 1",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@player_count_label')
        )
        self.all_components.append(self.player_count_label)
        
        # 创建交互提示标签（屏幕底部中央）
        interact_hint_rect = pygame.Rect((screen_width // 2 - 150, screen_height - 150), (300, 25))
        self.interact_hint_label = pygame_gui.elements.UILabel(
            relative_rect=interact_hint_rect,
            text="[E] 开门/关门",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@interact_hint_label')
        )
        self.interact_hint_label.hide()  # 初始隐藏
        self.all_components.append(self.interact_hint_label)
        
        # 创建武器控制提示标签（屏幕底部）
        weapon_hint_rect = pygame.Rect((screen_width // 2 - 200, screen_height - 120), (400, 25))
        self.weapon_hint_label = pygame_gui.elements.UILabel(
            relative_rect=weapon_hint_rect,
            text="[鼠标左键] 射击  [R] 换弹  [鼠标右键] 瞄准",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@weapon_hint_label')
        )
        self.all_components.append(self.weapon_hint_label)
        
        # 创建切换武器提示标签（武器控制提示下方）
        switch_hint_rect = pygame.Rect((screen_width // 2 - 150, screen_height - 95), (300, 25))
        self.switch_hint_label = pygame_gui.elements.UILabel(
            relative_rect=switch_hint_rect,
            text="[Q] 切换武器",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@switch_hint_label')
        )
        self.all_components.append(self.switch_hint_label)
        
        # 创建聊天提示标签（屏幕底部）
        chat_hint_rect = pygame.Rect((screen_width // 2 - 150, screen_height - 70), (300, 25))
        self.chat_hint_label = pygame_gui.elements.UILabel(
            relative_rect=chat_hint_rect,
            text="[Y] 打开聊天  [↑↓] 滚动消息",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@chat_hint_label')
        )
        self.all_components.append(self.chat_hint_label)
        
        # 创建伤害信息标签（屏幕中央偏上，初始隐藏）
        damage_info_rect = pygame.Rect((screen_width // 2 - 150, 100), (300, 30))
        self.damage_info_label = pygame_gui.elements.UILabel(
            relative_rect=damage_info_rect,
            text="",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@damage_info_label')
        )
        self.damage_info_label.hide()  # 初始隐藏
        self.all_components.append(self.damage_info_label)
        
        # 创建视角信息标签（屏幕右上角，初始隐藏）
        vision_info_rect = pygame.Rect((screen_width - 210, 45), (200, 30))
        self.vision_info_label = pygame_gui.elements.UILabel(
            relative_rect=vision_info_rect,
            text="[V] 视角系统: 开启",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@vision_info_label')
        )
        self.all_components.append(self.vision_info_label)
        
        # 创建脚步声提示标签（屏幕右上角，初始隐藏）
        footstep_rect = pygame.Rect((screen_width - 210, 80), (200, 30))
        self.footstep_label = pygame_gui.elements.UILabel(
            relative_rect=footstep_rect,
            text="",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@footstep_label')
        )
        self.footstep_label.hide()  # 初始隐藏
        self.all_components.append(self.footstep_label)
        
        print("GameHUD 提示标签已创建")
    
    def _create_debug_panel(self) -> None:
        """
        创建调试信息面板和标签列表
        
        创建以下组件:
        - 调试信息面板 UIPanel
        - 调试信息标签列表（FPS、位置、速度、网络延迟等）
        """
        # 获取屏幕尺寸
        screen_width, screen_height = self.ui_manager.screen_size
        
        # 创建调试信息面板（屏幕左下角）
        debug_panel_rect = pygame.Rect((10, screen_height - 250), (300, 240))
        self.debug_panel = pygame_gui.elements.UIPanel(
            relative_rect=debug_panel_rect,
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@debug_panel')
        )
        self.debug_panel.hide()  # 初始隐藏
        self.all_components.append(self.debug_panel)
        
        # 创建调试信息标签列表
        debug_info_items = [
            "FPS: 60",
            "位置: (0, 0)",
            "速度: (0, 0)",
            "角度: 0°",
            "网络延迟: 0ms",
            "玩家数: 1",
            "子弹数: 0",
            "附近玩家: 0"
        ]
        
        label_height = 25
        label_y_start = 10
        
        for i, text in enumerate(debug_info_items):
            label_rect = pygame.Rect((10, label_y_start + i * label_height), (280, label_height))
            debug_label = pygame_gui.elements.UILabel(
                relative_rect=label_rect,
                text=text,
                manager=self.manager,
                container=self.debug_panel,
                object_id=pygame_gui.core.ObjectID(class_id='@debug_label')
            )
            self.debug_labels.append(debug_label)
        
        print("GameHUD 调试面板已创建")
    
    def destroy_ui(self) -> None:
        """
        清理所有 UI 组件
        
        此方法会销毁所有已创建的 UI 元素，释放资源。
        使用 kill() 方法销毁 pygame-gui 组件。
        """
        if not self.ui_created:
            return
        
        # 销毁所有主要组件
        components_to_destroy = [
            self.health_label,
            self.weapon_label,
            self.ammo_label,
            self.reload_label,
            self.melee_status_label,
            self.aim_label,
            self.death_label,
            self.player_count_label,
            self.interact_hint_label,
            self.weapon_hint_label,
            self.switch_hint_label,
            self.chat_hint_label,
            self.damage_info_label,
            self.vision_info_label,
            self.footstep_label,
            self.debug_panel
        ]
        
        # 销毁调试标签列表
        for label in self.debug_labels:
            if label is not None:
                label.kill()
        self.debug_labels.clear()
        
        # 销毁主要组件
        for component in components_to_destroy:
            if component is not None:
                component.kill()
        
        # 清空所有引用
        self.health_label = None
        self.weapon_label = None
        self.ammo_label = None
        self.reload_label = None
        self.melee_status_label = None
        self.aim_label = None
        self.death_label = None
        self.player_count_label = None
        self.interact_hint_label = None
        self.weapon_hint_label = None
        self.switch_hint_label = None
        self.chat_hint_label = None
        self.damage_info_label = None
        self.vision_info_label = None
        self.footstep_label = None
        self.debug_panel = None
        
        # 清空缓存
        self._last_health = None
        self._last_ammo = None
        self._last_weapon = None
        self._last_player_count = None
        self._last_reload_time = None
        self._last_melee_cooldown = None
        self._last_death_time = None
        
        self.all_components.clear()
        self.ui_created = False
        print("GameHUD 已清理")
    
    def update(self, hud_state: Dict) -> None:
        """
        更新 UI 状态
        
        根据 hud_state 更新 HUD 显示，包括：
        - 玩家状态（生命值、武器、弹药等）
        - 提示信息
        - 调试信息
        
        使用按需更新策略，只在值变化时更新标签，以优化性能。
        
        Args:
            hud_state: HUD 状态字典，包含以下键：
                - player: Player - 玩家对象
                - player_count: int - 在线玩家数量
                - debug_mode: bool - 是否启用调试模式
                - network_manager: NetworkManager - 网络管理器
                - nearby_sound_players: list - 附近有脚步声的玩家列表
                - bullets_count: int - 子弹数量
                - show_vision: bool - 是否显示视角信息
        """
        if not self.ui_created:
            return
        
        # 任务 11: 更新玩家状态显示
        if 'player' in hud_state:
            self._update_player_status(hud_state['player'])
        
        # 任务 12: 更新提示和信息显示
        self._update_hints(hud_state)
        
        # 任务 12: 更新调试信息
        if 'debug_mode' in hud_state and hud_state['debug_mode']:
            self._update_debug_info(hud_state)
    
    def _update_player_status(self, player) -> None:
        """
        更新玩家状态显示
        
        使用按需更新策略，只在值变化时更新标签，以优化性能。
        
        Args:
            player: Player 对象
        """
        import time
        current_time = time.time()
        
        # 更新生命值标签（只在值变化时更新）
        if self.health_label and player.health != self._last_health:
            health_text = f"生命: {player.health}/{player.max_health}"
            self.health_label.set_text(health_text)
            self._last_health = player.health
        
        # 更新武器类型标签（只在值变化时更新）
        if self.weapon_label and player.weapon_type != self._last_weapon:
            weapon_text = "武器: " + ("近战武器" if player.weapon_type == "melee" else "枪械")
            self.weapon_label.set_text(weapon_text)
            self._last_weapon = player.weapon_type
        
        # 更新弹药数量标签（只在值变化时更新，且仅在使用枪械时显示）
        if self.ammo_label:
            if player.weapon_type == "gun":
                if player.ammo != self._last_ammo:
                    from constants import MAGAZINE_SIZE
                    ammo_text = f"弹药: {player.ammo}/{MAGAZINE_SIZE}"
                    self.ammo_label.set_text(ammo_text)
                    self._last_ammo = player.ammo
                if not self.ammo_label.visible:
                    self.ammo_label.show()
            else:
                # 使用近战武器时隐藏弹药标签
                if self.ammo_label.visible:
                    self.ammo_label.hide()
        
        # 更新换弹倒计时标签（只在换弹时显示）
        if self.reload_label:
            if player.is_reloading and player.weapon_type == "gun":
                from constants import RELOAD_TIME
                reload_remaining = RELOAD_TIME - (current_time - player.reload_start)
                if reload_remaining > 0:
                    reload_text = f"换弹中: {reload_remaining:.1f}s"
                    self.reload_label.set_text(reload_text)
                    if not self.reload_label.visible:
                        self.reload_label.show()
                    self._last_reload_time = reload_remaining
                else:
                    if self.reload_label.visible:
                        self.reload_label.hide()
            else:
                if self.reload_label.visible:
                    self.reload_label.hide()
        
        # 更新近战武器状态标签（只在使用近战武器时显示）
        if self.melee_status_label and player.weapon_type == "melee":
            if hasattr(player, 'melee_weapon') and player.melee_weapon:
                # 计算冷却剩余时间
                cooldown_remaining = player.melee_weapon.cooldown - (current_time - player.melee_weapon.last_attack_time)
                if cooldown_remaining > 0:
                    melee_text = f"近战冷却: {cooldown_remaining:.1f}s"
                    self.melee_status_label.set_text(melee_text)
                    if not self.melee_status_label.visible:
                        self.melee_status_label.show()
                    self._last_melee_cooldown = cooldown_remaining
                else:
                    # 冷却完成，显示"就绪"
                    if self._last_melee_cooldown is None or self._last_melee_cooldown > 0:
                        self.melee_status_label.set_text("近战武器: 就绪")
                        if not self.melee_status_label.visible:
                            self.melee_status_label.show()
                        self._last_melee_cooldown = 0
        else:
            # 不使用近战武器时隐藏标签
            if self.melee_status_label and self.melee_status_label.visible:
                self.melee_status_label.hide()
        
        # 更新瞄准状态标签（只在瞄准时显示）
        if self.aim_label:
            if player.is_aiming:
                if not self.aim_label.visible:
                    self.aim_label.show()
            else:
                if self.aim_label.visible:
                    self.aim_label.hide()
        
        # 更新死亡状态标签（只在死亡时显示）
        if self.death_label:
            if player.is_dead:
                # 计算复活倒计时
                if player.respawn_time > 0 and player.respawn_time > current_time:
                    respawn_remaining = player.respawn_time - current_time
                    from constants import RESPAWN_TIME
                    # 确保倒计时在合理范围内
                    if 0 < respawn_remaining <= RESPAWN_TIME:
                        death_html = f'<font face="Microsoft YaHei" size=6 color=#FF0000><b>你已死亡</b><br><br>复活倒计时: {respawn_remaining:.1f}s</font>'
                        self.death_label.html_text = death_html
                        self.death_label.rebuild()
                        if not self.death_label.visible:
                            self.death_label.show()
                        self._last_death_time = respawn_remaining
                    else:
                        # 倒计时不合理，只显示死亡信息
                        if self._last_death_time != -1:
                            death_html = '<font face="Microsoft YaHei" size=6 color=#FF0000><b>你已死亡</b></font>'
                            self.death_label.html_text = death_html
                            self.death_label.rebuild()
                            if not self.death_label.visible:
                                self.death_label.show()
                            self._last_death_time = -1
                else:
                    # 没有有效的复活时间，只显示死亡信息
                    if self._last_death_time != -1:
                        death_html = '<font face="Microsoft YaHei" size=6 color=#FF0000><b>你已死亡</b></font>'
                        self.death_label.html_text = death_html
                        self.death_label.rebuild()
                        if not self.death_label.visible:
                            self.death_label.show()
                        self._last_death_time = -1
            else:
                # 玩家未死亡，隐藏死亡标签
                if self.death_label.visible:
                    self.death_label.hide()
                    self._last_death_time = None
    
    def _update_hints(self, hud_state: Dict) -> None:
        """
        更新提示和信息显示
        
        使用按需更新策略，只在值变化时更新标签，以优化性能。
        
        Args:
            hud_state: HUD 状态字典
        """
        # 更新玩家数量标签
        if 'player_count' in hud_state and self.player_count_label:
            player_count = hud_state['player_count']
            if player_count != self._last_player_count:
                self.player_count_label.set_text(f"在线玩家: {player_count}")
                self._last_player_count = player_count
        
        # 更新视角信息标签
        if 'show_vision' in hud_state and self.vision_info_label:
            show_vision = hud_state['show_vision']
            vision_text = "[V] 视角系统: " + ("开启" if show_vision else "关闭")
            self.vision_info_label.set_text(vision_text)
        
        # 更新脚步声提示标签
        if 'nearby_sound_players' in hud_state and self.footstep_label:
            nearby_players = hud_state['nearby_sound_players']
            if nearby_players:
                # 显示附近玩家的脚步声信息
                footstep_text = f"附近脚步声: {len(nearby_players)}人"
                self.footstep_label.set_text(footstep_text)
                if not self.footstep_label.visible:
                    self.footstep_label.show()
            else:
                # 没有附近玩家，隐藏标签
                if self.footstep_label.visible:
                    self.footstep_label.hide()
    
    def _update_debug_info(self, hud_state: Dict) -> None:
        """
        更新调试信息显示
        
        Args:
            hud_state: HUD 状态字典
        """
        if not self.debug_labels or len(self.debug_labels) < 8:
            return
        
        player = hud_state.get('player')
        network_manager = hud_state.get('network_manager')
        
        if player:
            # 更新 FPS（从时钟获取）
            import pygame
            clock = pygame.time.Clock()
            fps = int(clock.get_fps()) if hasattr(clock, 'get_fps') else 60
            self.debug_labels[0].set_text(f"FPS: {fps}")
            
            # 更新位置
            self.debug_labels[1].set_text(f"位置: ({int(player.x)}, {int(player.y)})")
            
            # 更新速度
            vx = getattr(player, 'vx', 0)
            vy = getattr(player, 'vy', 0)
            self.debug_labels[2].set_text(f"速度: ({vx:.1f}, {vy:.1f})")
            
            # 更新角度
            self.debug_labels[3].set_text(f"角度: {int(player.angle)}°")
        
        # 更新网络延迟
        if network_manager:
            latency = getattr(network_manager, 'latency', 0)
            self.debug_labels[4].set_text(f"网络延迟: {int(latency * 1000)}ms")
        
        # 更新玩家数
        player_count = hud_state.get('player_count', 1)
        self.debug_labels[5].set_text(f"玩家数: {player_count}")
        
        # 更新子弹数
        bullets_count = hud_state.get('bullets_count', 0)
        self.debug_labels[6].set_text(f"子弹数: {bullets_count}")
        
        # 更新附近玩家数
        nearby_players = hud_state.get('nearby_sound_players', [])
        self.debug_labels[7].set_text(f"附近玩家: {len(nearby_players)}")
    
    def set_debug_mode(self, enabled: bool) -> None:
        """
        设置调试模式
        
        启用或禁用调试信息面板的显示。
        
        Args:
            enabled: 是否启用调试模式
        """
        if self._debug_mode == enabled:
            return  # 状态未变化，无需更新
        
        self._debug_mode = enabled
        
        # 显示或隐藏调试面板
        if self.debug_panel is not None:
            if enabled:
                self.debug_panel.show()
                print("GameHUD: 调试模式已启用")
            else:
                self.debug_panel.hide()
                print("GameHUD: 调试模式已禁用")
        
        # 显示或隐藏调试标签
        for label in self.debug_labels:
            if label is not None:
                if enabled:
                    label.show()
                else:
                    label.hide()


class ChatUI:
    """
    聊天系统 UI 类
    
    管理聊天系统的所有 UI 组件，包括输入框和消息显示。
    
    状态管理:
        chat_state = {
            'chat_active': bool,  # 聊天是否激活
            'chat_input': str,  # 聊天输入文本
            'recent_messages': list[ChatMessage],  # 最近的聊天消息
            'chat_scroll_offset': int  # 聊天消息滚动偏移量
        }
    """
    
    def __init__(self, ui_manager: UIManagerWrapper):
        """
        初始化 ChatUI
        
        Args:
            ui_manager: UIManagerWrapper 实例
        """
        self.ui_manager = ui_manager
        self.manager = ui_manager.get_manager()
        
        # UI 组件（将在 create_ui 中初始化）
        self.input_box = None
        self.input_label = None
        self.message_container = None  # 使用 UIPanel 作为消息容器
        self.message_labels = []  # 消息标签列表
        self.scroll_hint_up = None
        self.scroll_hint_down = None
        
        # 状态
        self.ui_created = False
        self.is_active = False
        self.messages = []  # 存储的消息列表
        self.max_messages = 50  # 最大存储消息数（性能优化）
        
        # 滚动状态
        self.scroll_offset = 0
        
        # 所有组件列表
        self.all_components = []
    
    def create_ui(self) -> None:
        """创建所有 UI 组件"""
        if self.ui_created:
            print("警告: ChatUI 已经创建，跳过重复创建")
            return
        
        screen_width, screen_height = self.ui_manager.screen_size
        
        # 创建聊天输入框（初始隐藏）
        input_box_height = 40
        input_box_rect = pygame.Rect(
            (10, screen_height - input_box_height - 10),
            (screen_width - 20, input_box_height)
        )
        self.input_box = pygame_gui.elements.UITextEntryLine(
            relative_rect=input_box_rect,
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@chat_input_box')
        )
        self.input_box.hide()
        self.all_components.append(self.input_box)
        
        # 创建聊天提示标签（初始隐藏）
        input_label_rect = pygame.Rect(
            (15, screen_height - input_box_height - 15),
            (100, 30)
        )
        self.input_label = pygame_gui.elements.UILabel(
            relative_rect=input_label_rect,
            text="聊天:",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@chat_input_label')
        )
        self.input_label.hide()
        self.all_components.append(self.input_label)
        
        # 创建消息显示容器（半透明背景面板）
        # 位置：从 y=250 到输入框上方
        message_container_height = screen_height - 250 - input_box_height - 30
        message_container_rect = pygame.Rect(
            (10, 250),
            (screen_width - 20, message_container_height)
        )
        self.message_container = pygame_gui.elements.UIPanel(
            relative_rect=message_container_rect,
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@chat_message_container')
        )
        # 设置半透明背景
        self.message_container.background_colour = pygame.Color(0, 0, 0, 128)
        self.all_components.append(self.message_container)
        
        # 创建滚动提示标签（初始隐藏）
        hint_width = 230  # 增加宽度以容纳文本
        self.scroll_hint_up = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(
                (screen_width - hint_width - 20, 230),
                (hint_width, 30)  # 增加高度
            ),
            text="↑ 更早消息 (方向键)",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@chat_scroll_hint_up')
        )
        self.scroll_hint_up.hide()
        self.all_components.append(self.scroll_hint_up)
        
        self.scroll_hint_down = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(
                (screen_width - hint_width - 20, screen_height - input_box_height - 40),
                (hint_width, 30)  # 增加高度
            ),
            text="↓ 更多消息 (方向键)",
            manager=self.manager,
            object_id=pygame_gui.core.ObjectID(class_id='@chat_scroll_hint_down')
        )
        self.scroll_hint_down.hide()
        self.all_components.append(self.scroll_hint_down)
        
        self.ui_created = True
        print("ChatUI 已创建")
    
    def destroy_ui(self) -> None:
        """清理所有 UI 组件"""
        if not self.ui_created:
            return
        
        # 销毁所有消息标签
        for label in self.message_labels:
            if label is not None:
                label.kill()
        self.message_labels.clear()
        
        # 销毁主要组件
        for component in self.all_components:
            if component is not None:
                component.kill()
        
        self.input_box = None
        self.input_label = None
        self.message_container = None
        self.scroll_hint_up = None
        self.scroll_hint_down = None
        self.all_components.clear()
        
        self.ui_created = False
        print("ChatUI 已清理")
    
    def update(self, chat_state: Dict) -> None:
        """
        更新 UI 状态
        
        Args:
            chat_state: 聊天状态字典，包含:
                - chat_active: bool - 聊天是否激活
                - recent_messages: list[ChatMessage] - 最近的聊天消息
                - chat_scroll_offset: int - 滚动偏移量
        """
        if not self.ui_created:
            return
        
        # 更新激活状态
        chat_active = chat_state.get('chat_active', False)
        if chat_active != self.is_active:
            if chat_active:
                self.activate_input()
            else:
                self.deactivate_input()
        
        # 更新消息显示
        recent_messages = chat_state.get('recent_messages', [])
        if recent_messages != self.messages:
            self._update_messages(recent_messages)
        
        # 更新滚动偏移
        scroll_offset = chat_state.get('chat_scroll_offset', 0)
        if scroll_offset != self.scroll_offset:
            self.scroll_offset = scroll_offset
            self._update_scroll_hints()
    
    def _update_messages(self, messages: List) -> None:
        """
        更新消息显示
        
        Args:
            messages: ChatMessage 对象列表
        """
        # 限制消息数量（性能优化）
        if len(messages) > self.max_messages:
            messages = messages[-self.max_messages:]
        
        self.messages = messages
        
        # 清除旧的消息标签
        for label in self.message_labels:
            if label is not None:
                label.kill()
        self.message_labels.clear()
        
        # 创建新的消息标签
        if not messages:
            return
        
        # 从下往上显示消息
        container_height = self.message_container.rect.height
        y_position = container_height - 10  # 从底部开始
        line_height = 22  # 每行高度
        
        # 只显示最近的消息（从最新到最旧）
        display_messages = messages[-20:]  # 最多显示20条消息
        
        for msg in reversed(display_messages):
            # 格式化消息文本
            if msg.player_id == 0:
                # 系统消息
                text = f"[系统] {msg.message}"
                color = '#FFFFFF'
            else:
                # 玩家消息
                text = f"{msg.player_name}: {msg.message}"
                # 将 RGB 元组转换为十六进制颜色
                if isinstance(msg.color, tuple) and len(msg.color) >= 3:
                    color = f"#{msg.color[0]:02x}{msg.color[1]:02x}{msg.color[2]:02x}"
                else:
                    color = '#FFFFFF'
            
            # 创建消息标签（使用更宽的宽度以容纳文本）
            label_rect = pygame.Rect(
                (5, y_position - line_height),
                (self.message_container.rect.width - 15, line_height + 5)  # 增加宽度和高度
            )
            
            try:
                label = pygame_gui.elements.UILabel(
                    relative_rect=label_rect,
                    text=text,
                    manager=self.manager,
                    container=self.message_container,
                    object_id=pygame_gui.core.ObjectID(class_id='@chat_message_label')
                )
                # 设置文本颜色
                label.text_colour = pygame.Color(color)
                label.rebuild()
                
                self.message_labels.append(label)
                y_position -= line_height
                
                # 如果超出容器顶部，停止创建
                if y_position < 0:
                    break
            except Exception as e:
                print(f"创建消息标签失败: {e}")
                continue
    
    def _update_scroll_hints(self) -> None:
        """更新滚动提示的显示状态"""
        if not self.ui_created:
            return
        
        # 如果有滚动偏移，显示向下提示
        if self.scroll_offset > 0:
            self.scroll_hint_down.show()
        else:
            self.scroll_hint_down.hide()
        
        # 如果还有更多消息可以向上滚动，显示向上提示
        # 这里简化处理，假设总是可以向上滚动
        if len(self.messages) > 10:
            self.scroll_hint_up.show()
        else:
            self.scroll_hint_up.hide()
    
    def activate_input(self) -> None:
        """激活聊天输入框"""
        if not self.ui_created:
            return
        
        self.is_active = True
        self.input_box.show()
        self.input_label.show()
        self.input_box.focus()
        self.input_box.set_text("")
        print("ChatUI: 聊天输入框已激活")
    
    def deactivate_input(self) -> None:
        """关闭聊天输入框"""
        if not self.ui_created:
            return
        
        self.is_active = False
        self.input_box.hide()
        self.input_label.hide()
        self.input_box.unfocus()
        print("ChatUI: 聊天输入框已关闭")
    
    def get_input_text(self) -> str:
        """
        获取输入文本
        
        Returns:
            输入框中的文本
        """
        if self.input_box:
            return self.input_box.get_text()
        return ""
    
    def clear_input(self) -> None:
        """清空输入框"""
        if self.input_box:
            self.input_box.set_text("")
    
    def add_message(self, message) -> None:
        """
        添加聊天消息
        
        Args:
            message: ChatMessage 对象
        """
        self.messages.append(message)
        
        # 限制消息数量
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
        
        # 更新显示
        self._update_messages(self.messages)
    
    def scroll_up(self) -> None:
        """向上滚动消息"""
        self.scroll_offset += 1
        self._update_scroll_hints()
        print(f"ChatUI: 向上滚动，偏移量: {self.scroll_offset}")
    
    def scroll_down(self) -> None:
        """向下滚动消息"""
        self.scroll_offset = max(0, self.scroll_offset - 1)
        self._update_scroll_hints()
        print(f"ChatUI: 向下滚动，偏移量: {self.scroll_offset}")


class ConnectingUI:
    """
    连接界面 UI 类
    
    管理连接界面的所有 UI 组件，包括连接状态显示和玩家名称编辑。
    """
    
    def __init__(self, ui_manager: UIManagerWrapper):
        """
        初始化 ConnectingUI
        
        Args:
            ui_manager: UIManagerWrapper 实例
        """
        self.ui_manager = ui_manager
        self.manager = ui_manager.get_manager()
        
        # UI 组件（将在 create_ui 中初始化）
        self.title_label = None
        self.info_label = None
        self.ip_label = None
        self.player_name_label = None
        self.edit_name_button = None
        self.player_name_input = None
        self.confirm_button = None
        self.cancel_button = None
        
        # 动画状态
        self.animation_time = 0.0
    
    def create_ui(self, connection_info: Dict) -> None:
        """
        创建所有 UI 组件
        
        Args:
            connection_info: 连接信息字典
        """
        # TODO: 在后续任务中实现
        pass
    
    def destroy_ui(self) -> None:
        """清理所有 UI 组件"""
        # TODO: 在后续任务中实现
        pass
    
    def update(self, elapsed_time: float) -> None:
        """
        更新 UI 状态
        
        Args:
            elapsed_time: 已经过的时间（秒）
        """
        # TODO: 在后续任务中实现
        pass
    
    def show_player_name_edit(self, current_name: str) -> None:
        """
        显示玩家名称编辑界面
        
        Args:
            current_name: 当前玩家名称
        """
        # TODO: 在后续任务中实现
        pass
    
    def hide_player_name_edit(self) -> None:
        """隐藏玩家名称编辑界面"""
        # TODO: 在后续任务中实现
        pass
    
    def get_player_name(self) -> str:
        """
        获取玩家名称
        
        Returns:
            玩家名称
        """
        # TODO: 在后续任务中实现
        return ""
    
    def handle_event(self, event: pygame.event.Event) -> Dict:
        """
        处理事件
        
        Args:
            event: Pygame 事件对象
            
        Returns:
            事件处理结果字典
        """
        # TODO: 在后续任务中实现
        return {}
