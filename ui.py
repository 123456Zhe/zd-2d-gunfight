"""
UI模块 - 处理所有用户界面相关功能
使用 pygame-menu 重写菜单系统
包括字体加载、菜单绘制、HUD显示、聊天界面等
"""

import pygame
import pygame_menu
from pygame_menu import themes
import platform
from constants import *

# 全局字体变量
fonts = None
font = None
small_font = None
large_font = None
title_font = None


def load_fonts():
    """加载字体，支持Windows、Ubuntu和其他Linux发行版"""
    import os

    # 确保pygame字体模块已初始化
    if not pygame.font.get_init():
        pygame.font.init()

    # 检测操作系统
    system = platform.system().lower()

    # 根据操作系统选择字体候选列表
    if system == "windows":
        font_candidates = [
            "Microsoft YaHei",
            "SimHei",
            "SimSun",
            "Arial Unicode MS",
            "DejaVu Sans",
            "Arial",
        ]
    elif system == "linux":
        # Linux/Ubuntu字体优先级
        font_candidates = [
            "Noto Sans CJK SC",  # Ubuntu默认中文字体
            "Noto Sans CJK TC",  # 繁体中文
            "WenQuanYi Micro Hei",  # 文泉驿微米黑
            "WenQuanYi Zen Hei",  # 文泉驿正黑
            "Droid Sans Fallback",  # Android字体
            "AR PL UMing CN",  # 文鼎明体
            "AR PL UKai CN",  # 文鼎楷体
            "DejaVu Sans",  # 通用字体
            "Liberation Sans",  # LibreOffice字体
            "FreeSans",  # GNU字体
        ]
    elif system == "darwin":  # macOS
        font_candidates = [
            "PingFang SC",
            "Hiragino Sans GB",
            "STHeiti",
            "Arial Unicode MS",
            "Helvetica",
            "Arial",
        ]
    else:
        # 其他系统使用通用字体
        font_candidates = ["DejaVu Sans", "Liberation Sans", "FreeSans", "Arial"]

    print(f"检测到操作系统: {system}")
    print(f"尝试加载 {len(font_candidates)} 个字体候选...")

    # 尝试加载字体并验证中文渲染
    for i, font_name in enumerate(font_candidates, 1):
        try:
            # 尝试创建字体对象
            test_font = pygame.font.SysFont(font_name, 20)

            if test_font:
                # 验证字体是否能正确渲染中文
                try:
                    # 测试中文渲染
                    test_surface = test_font.render("中文测试", True, (255, 255, 255))

                    # 检查渲染结果是否有效（宽度大于0）
                    if test_surface.get_width() > 0:
                        print(f"[OK] [{i:2d}] {font_name} - 加载成功，中文渲染正常")

                        return {
                            "font": pygame.font.SysFont(font_name, 20),
                            "small_font": pygame.font.SysFont(font_name, 16),
                            "large_font": pygame.font.SysFont(font_name, 28),
                            "title_font": pygame.font.SysFont(font_name, 40),
                            "font_name": font_name,
                        }
                    else:
                        print(f"[FAIL] [{i:2d}] {font_name} - 中文渲染失败")

                except Exception as render_error:
                    print(f"[FAIL] [{i:2d}] {font_name} - 中文渲染异常: {render_error}")
                    continue
            else:
                print(f"[FAIL] [{i:2d}] {font_name} - 字体对象创建失败")

        except Exception as font_error:
            print(f"[FAIL] [{i:2d}] {font_name} - 字体加载异常: {font_error}")
            continue

    # 如果所有字体都失败，使用默认字体
    print("[WARN] 警告: 无法加载任何系统字体，使用pygame默认字体")
    print("建议安装中文字体包以获得更好的显示效果")

    if system == "linux":
        print(
            "Ubuntu/Linux用户可以运行: sudo apt install fonts-noto-cjk fonts-wqy-microhei"
        )

    return {
        "font": pygame.font.Font(None, 20),
        "small_font": pygame.font.Font(None, 16),
        "large_font": pygame.font.Font(None, 28),
        "title_font": pygame.font.Font(None, 40),
        "font_name": "Default",
    }


def initialize_fonts():
    """初始化字体并设置全局变量"""
    global fonts, font, small_font, large_font, title_font

    fonts = load_fonts()
    font = fonts["font"]
    small_font = fonts["small_font"]
    large_font = fonts["large_font"]
    title_font = fonts["title_font"]

    # 显示当前使用的字体信息
    current_font_name = fonts.get("font_name", "Unknown")
    print(f"当前使用字体: {current_font_name}")

    # 如果使用默认字体，给出提示
    if current_font_name == "Default":
        print("提示: 游戏将使用默认字体，中文显示可能不完整")

    return fonts


def get_fonts():
    """获取已加载的字体字典"""
    return {
        "font": font,
        "small_font": small_font,
        "large_font": large_font,
        "title_font": title_font,
        "fonts": fonts,
    }


# ========== pygame-menu 菜单系统 ==========


def create_custom_theme():
    """创建自定义菜单主题"""
    custom_theme = themes.THEME_DARK.copy()

    # 使用已加载的全局字体对象
    global font, title_font
    if font:
        custom_theme.widget_font = font
    if title_font:
        custom_theme.title_font = title_font

    # 自定义颜色
    custom_theme.background_color = (20, 20, 30, 230)
    custom_theme.title_background_color = (40, 60, 100)
    custom_theme.title_font_color = WHITE
    custom_theme.widget_font_color = WHITE
    custom_theme.selection_color = (0, 200, 255)

    # 按钮样式
    custom_theme.widget_margin = (0, 15)
    custom_theme.title_font_size = 45
    custom_theme.widget_font_size = 22

    return custom_theme


class MenuManager:
    """
    使用 pygame-menu 管理游戏菜单的类
    """

    def __init__(self, screen, game_instance):
        """
        初始化菜单管理器

        参数:
            screen: pygame 屏幕对象
            game_instance: Game 类的实例，用于回调
        """
        self.screen = screen
        self.game = game_instance
        self.theme = create_custom_theme()

        # 菜单状态
        self.server_name = "我的服务器"
        self.player_name = ""
        self.manual_ip = ""
        self.selected_server_ip = None

        # 服务器列表更新状态跟踪
        self.last_server_count = 0
        self.last_scanning_state = False

        # 创建主菜单
        self.main_menu = self._create_main_menu()

        # 子菜单
        self.server_name_menu = None
        self.player_name_menu = None
        self.server_list_menu = None

    def _create_main_menu(self):
        """创建主菜单"""
        menu = pygame_menu.Menu(
            "多人射击游戏", SCREEN_WIDTH, SCREEN_HEIGHT, theme=self.theme
        )

        # 副标题
        menu.add.label("武器切换 + 瞄准系统", font_size=18, font_color=LIGHT_BLUE)
        menu.add.vertical_margin(20)

        # 创建服务器按钮
        menu.add.button("创建服务器", self._show_create_server_menu)

        # 刷新服务器按钮
        menu.add.button("刷新服务器列表", self._refresh_servers)

        # 手动输入IP
        menu.add.vertical_margin(10)
        menu.add.label("─── 手动连接 ───", font_size=16, font_color=GRAY)
        self.ip_input = menu.add.text_input(
            "IP地址: ", default="", maxchar=50, onchange=self._on_ip_change
        )
        menu.add.button("手动连接", self._manual_connect)

        # 服务器列表区域（初始为空标签）
        menu.add.vertical_margin(20)
        menu.add.label("─── 局域网服务器 ───", font_size=16, font_color=GRAY)
        self.server_list_frame = menu.add.frame_v(
            400, 200, background_color=(30, 30, 40)
        )
        # 禁用 margin 警告
        self.server_list_frame._pack_margin_warning = False
        self.no_server_label = self.server_list_frame.pack(
            menu.add.label("正在扫描服务器...", font_size=14, font_color=YELLOW)
        )

        return menu

    def _show_create_server_menu(self):
        """显示创建服务器的子菜单（服务器名称输入）"""
        self.server_name_menu = pygame_menu.Menu(
            "创建服务器", SCREEN_WIDTH, SCREEN_HEIGHT, theme=self.theme
        )

        self.server_name_menu.add.label("请输入服务器名称：", font_size=18)
        self.server_name_input = self.server_name_menu.add.text_input(
            "服务器名称: ", default="我的服务器", maxchar=20
        )
        self.server_name_menu.add.vertical_margin(20)
        self.server_name_menu.add.button("下一步", self._on_server_name_confirm)
        self.server_name_menu.add.button("返回", pygame_menu.events.BACK)

        self.main_menu._open(self.server_name_menu)

    def _on_server_name_confirm(self):
        """服务器名称确认后，进入玩家名称输入"""
        self.server_name = self.server_name_input.get_value().strip()
        if not self.server_name:
            self.server_name = "我的服务器"

        self._show_player_name_menu(is_server=True)

    def _show_player_name_menu(self, is_server=False, server_ip=None):
        """显示玩家名称输入菜单"""
        from network import generate_default_player_name

        self.player_name_menu = pygame_menu.Menu(
            "输入玩家名称", SCREEN_WIDTH, SCREEN_HEIGHT, theme=self.theme
        )

        self.player_name_menu.add.label("请输入你的玩家名称：", font_size=18)
        self.player_name_input = self.player_name_menu.add.text_input(
            "玩家名称: ", default=generate_default_player_name(), maxchar=16
        )
        self.player_name_menu.add.vertical_margin(20)

        if is_server:
            self.player_name_menu.add.button(
                "创建服务器", lambda: self._start_game(is_server=True)
            )
        else:
            self.selected_server_ip = server_ip
            self.player_name_menu.add.button(
                "连接服务器", lambda: self._start_game(is_server=False)
            )

        self.player_name_menu.add.button("返回", pygame_menu.events.BACK)

        if self.server_name_menu:
            self.server_name_menu._open(self.player_name_menu)
        else:
            self.main_menu._open(self.player_name_menu)

    def _start_game(self, is_server):
        """开始游戏（创建服务器或连接）"""
        self.player_name = self.player_name_input.get_value().strip()
        if not self.player_name:
            from network import generate_default_player_name

            self.player_name = generate_default_player_name()

        if is_server:
            self.game.connection_info = {
                "is_server": True,
                "server_name": self.server_name,
                "player_name": self.player_name,
            }
        else:
            server_ip = self.selected_server_ip or self.manual_ip
            self.game.connection_info = {
                "is_server": False,
                "server_ip": server_ip,
                "player_name": self.player_name,
            }

        self.game.state = "CONNECTING"
        self.game.connecting_start_time = __import__("time").time()
        self.main_menu.disable()

    def _on_ip_change(self, value):
        """IP输入变化时的回调"""
        self.manual_ip = value

    def _manual_connect(self):
        """手动连接按钮点击"""
        ip = self.ip_input.get_value().strip()
        if ip:
            self.manual_ip = ip
            self._show_player_name_menu(is_server=False, server_ip=ip)

    def _refresh_servers(self):
        """刷新服务器列表"""
        self.game.start_server_scan()
        self._update_server_list_display()

    def _update_server_list_display(self):
        """更新服务器列表显示"""
        # 显式从菜单中移除旧的 widget，防止重叠和内存泄漏
        if hasattr(self.server_list_frame, "get_widgets"):
            for widget in self.server_list_frame.get_widgets():
                try:
                    self.main_menu.remove_widget(widget)
                except:
                    pass

        # 清空现有服务器列表区域
        self.server_list_frame.clear()

        if self.game.scanning_servers:
            label = self.main_menu.add.label(
                "正在扫描服务器...", font_size=14, font_color=YELLOW
            )
            self.server_list_frame.pack(label)
        elif self.game.found_servers:
            for i, server in enumerate(self.game.found_servers[:5]):
                server_name = server.get("name", "未知服务器")
                server_ip = server.get("ip", "?")
                players = server.get("players", 0)
                max_players = server.get("max_players", "?")

                btn_text = f"{server_name} ({server_ip}) [{players}/{max_players}]"
                btn = self.main_menu.add.button(
                    btn_text,
                    lambda ip=server_ip: self._on_server_selected(ip),
                    font_size=14,
                )
                self.server_list_frame.pack(btn)
        else:
            label = self.main_menu.add.label(
                "未找到局域网服务器", font_size=14, font_color=GRAY
            )
            self.server_list_frame.pack(label)

        # 只要不在扫描中，就显示刷新按钮
        if not self.game.scanning_servers:
            # 添加间隔
            self.server_list_frame.pack(self.main_menu.add.vertical_margin(10))
            # 添加手动刷新按钮
            refresh_btn = self.main_menu.add.button(
                "刷新列表", self._refresh_servers, font_size=14
            )
            self.server_list_frame.pack(refresh_btn)

        # 强制更新菜单布局以防止 UI 消失
        # 这是一个 workaround，解决动态修改 frame 内容后可能导致的渲染问题
        try:
            if hasattr(self.server_list_frame, "_update_position"):
                self.server_list_frame._update_position()

            # 强制菜单重新计算布局
            self.main_menu.resize(
                self.main_menu.get_width(), self.main_menu.get_height()
            )
        except Exception as e:
            print(f"UI更新警告: {e}")

    def _on_server_selected(self, server_ip):
        """服务器列表项被点击"""
        self._show_player_name_menu(is_server=False, server_ip=server_ip)

    def update(self, events):
        """更新菜单状态"""
        # 只在服务器列表状态变化时更新显示
        current_server_count = len(self.game.found_servers)
        current_scanning = self.game.scanning_servers

        if (
            current_server_count != self.last_server_count
            or current_scanning != self.last_scanning_state
        ):
            self._update_server_list_display()
            self.last_server_count = current_server_count
            self.last_scanning_state = current_scanning

        if self.main_menu.is_enabled():
            # 简化的事件过滤逻辑：
            # 1. 拦截 TEXTINPUT 并放行，由 pygame-menu 本生处理（处理中文 IME 最稳）
            # 2. 过滤掉产生可打印字符的 KEYDOWN，防止与 TEXTINPUT 重复导致双打
            # 3. 放行所有控制键（退格、回车等）
            filtered_events = []
            for event in events:
                if event.type == pygame.KEYDOWN:
                    # 如果是有 unicode 的可打印字符，过滤掉，依赖 TEXTINPUT
                    if event.unicode and event.unicode.isprintable():
                        continue
                filtered_events.append(event)

            self.main_menu.update(filtered_events)

    def draw(self):
        """绘制菜单"""
        if self.main_menu.is_enabled():
            self.main_menu.draw(self.screen)

    def is_enabled(self):
        """菜单是否启用"""
        return self.main_menu.is_enabled()

    def enable(self):
        """启用菜单"""
        self.main_menu.enable()

    def disable(self):
        """禁用菜单"""
        self.main_menu.disable()


class ChatMenuManager:
    """
    游戏内聊天菜单管理器
    支持中文输入的聊天系统
    """

    def __init__(self, screen, game):
        self.screen = screen
        self.game = game
        self.enabled = False
        self.input_text = ""
        self.cursor_pos = 0  # 光标位置
        self.cursor_blink = True
        self.last_blink_time = 0
        self.held_keys_on_enable = set()

        # 聊天框尺寸
        self.chat_width = SCREEN_WIDTH - 120
        self.chat_height = 70
        self.chat_x = 60
        self.chat_y = SCREEN_HEIGHT - 90

        # IME编辑状态
        self.ime_editing = False
        self.ime_editing_text = ""
        self.ime_editing_pos = 0

    def enable(self):
        """开启聊天输入"""
        self.enabled = True
        self.input_text = ""
        self.cursor_pos = 0
        self.cursor_blink = True
        self.game.chat_active = True

        # 启动文本输入
        pygame.key.start_text_input()

        # 设置输入法候选框位置
        input_rect = pygame.Rect(
            self.chat_x + 10, self.chat_y + 30, self.chat_width - 20, 30
        )
        pygame.key.set_text_input_rect(input_rect)

        # 记录当前按下的键，防止按键泄露
        keys = pygame.key.get_pressed()
        self.held_keys_on_enable = {i for i in range(len(keys)) if keys[i]}

    def disable(self):
        """关闭聊天输入"""
        self.enabled = False
        self.input_text = ""
        self.cursor_pos = 0
        self.game.chat_active = False
        self.game.chat_input = ""

        # 停止文本输入
        pygame.key.stop_text_input()

    def is_enabled(self):
        """是否启用"""
        return self.enabled

    def update(self, events):
        """更新聊天菜单"""
        if not self.enabled:
            return

        # 更新光标闪烁
        current_time = pygame.time.get_ticks()
        if current_time - self.last_blink_time > 500:
            self.cursor_blink = not self.cursor_blink
            self.last_blink_time = current_time

        for event in events:
            # ESC 关闭聊天
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.disable()
                return

            # Enter 发送消息
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                # 如果正在使用输入法编辑，不发送消息
                if not self.ime_editing:
                    self._send_message()
                return

            # 处理 KEYDOWN 事件
            if event.type == pygame.KEYDOWN:
                # 过滤初始按下的键
                if event.key in self.held_keys_on_enable:
                    continue

                # 退格键
                if event.key == pygame.K_BACKSPACE:
                    if self.ime_editing:
                        # IME编辑模式下，退格键由系统处理
                        pass
                    elif self.cursor_pos > 0:
                        self.input_text = (
                            self.input_text[: self.cursor_pos - 1]
                            + self.input_text[self.cursor_pos :]
                        )
                        self.cursor_pos -= 1

                # Delete 键
                elif event.key == pygame.K_DELETE:
                    if not self.ime_editing and self.cursor_pos < len(self.input_text):
                        self.input_text = (
                            self.input_text[: self.cursor_pos]
                            + self.input_text[self.cursor_pos + 1 :]
                        )

                # 左箭头
                elif event.key == pygame.K_LEFT:
                    if not self.ime_editing:
                        self.cursor_pos = max(0, self.cursor_pos - 1)

                # 右箭头
                elif event.key == pygame.K_RIGHT:
                    if not self.ime_editing:
                        self.cursor_pos = min(len(self.input_text), self.cursor_pos + 1)

                # Home 键
                elif event.key == pygame.K_HOME:
                    if not self.ime_editing:
                        self.cursor_pos = 0

                # End 键
                elif event.key == pygame.K_END:
                    if not self.ime_editing:
                        self.cursor_pos = len(self.input_text)

            # TEXTINPUT 事件 - 用于接收输入法输入的文本
            elif event.type == pygame.TEXTINPUT:
                self.ime_editing = False
                self.ime_editing_text = ""

                # 在光标位置插入文本
                if len(self.input_text) + len(event.text) <= MAX_CHAT_LENGTH:
                    self.input_text = (
                        self.input_text[: self.cursor_pos]
                        + event.text
                        + self.input_text[self.cursor_pos :]
                    )
                    self.cursor_pos += len(event.text)

            # TEXTEDITING 事件 - 输入法正在编辑
            elif event.type == pygame.TEXTEDITING:
                self.ime_editing = True
                self.ime_editing_text = event.text
                self.ime_editing_pos = event.start

        # 同步到 game
        self.game.chat_input = self.input_text

    def _send_message(self):
        """发送消息"""
        text = self.input_text.strip()
        if text:
            if text.startswith("."):
                from game_commands import process_command

                if hasattr(self.game, "network_manager"):
                    is_server = getattr(self.game.network_manager, "is_server", False)
                    player_id = getattr(self.game.network_manager, "player_id", 0)
                    result = process_command(text, self.game, player_id, is_server)
                    if result:
                        from network import ChatMessage

                        self.game.network_manager.chat_messages.append(
                            ChatMessage(0, "系统", result)
                        )
            else:
                is_team_chat = getattr(self.game, "team_chat_mode", False)
                if self.game.network_manager:
                    self.game.network_manager.send_chat_message(
                        text, is_team_chat=is_team_chat
                    )
        self.disable()

    def draw(self):
        """绘制聊天菜单"""
        if not self.enabled:
            return

        global font, small_font

        # 绘制背景
        bg_rect = pygame.Rect(
            self.chat_x, self.chat_y, self.chat_width, self.chat_height
        )
        pygame.draw.rect(self.screen, (15, 15, 20, 220), bg_rect)
        pygame.draw.rect(self.screen, (100, 100, 120), bg_rect, 2)

        # 聊天模式标签
        is_team_chat = getattr(self.game, "team_chat_mode", False)
        mode_text = "团队聊天" if is_team_chat else "全局聊天"
        mode_color = GREEN if is_team_chat else LIGHT_BLUE
        mode_surface = small_font.render(mode_text, True, mode_color)
        self.screen.blit(mode_surface, (self.chat_x + 10, self.chat_y + 8))

        # 输入框背景
        input_rect = pygame.Rect(
            self.chat_x + 10, self.chat_y + 30, self.chat_width - 20, 30
        )
        pygame.draw.rect(self.screen, (30, 30, 40, 230), input_rect)
        pygame.draw.rect(self.screen, (60, 60, 80), input_rect, 1)

        # 绘制输入文字
        text_x = input_rect.x + 8
        text_y = input_rect.y + 5

        if self.ime_editing:
            # IME编辑模式：显示光标前的文本 + 编辑中的文本 + 光标后的文本
            # 光标前的文本
            text_before = self.input_text[: self.cursor_pos]
            text_before_surface = font.render(text_before, True, WHITE)
            self.screen.blit(text_before_surface, (text_x, text_y))

            # 编辑中的文本（带下划线）
            text_editing = self.ime_editing_text
            if text_editing:
                text_editing_surface = font.render(text_editing, True, (0, 200, 255))
                edit_x = text_x + text_before_surface.get_width()
                self.screen.blit(text_editing_surface, (edit_x, text_y))

                # 绘制下划线
                underline_y = text_y + font.get_height() + 2
                pygame.draw.line(
                    self.screen,
                    (0, 200, 255),
                    (edit_x, underline_y),
                    (edit_x + text_editing_surface.get_width(), underline_y),
                    2,
                )

            # 光标位置
            if self.cursor_blink:
                cursor_x = text_x + text_before_surface.get_width()
                if text_editing:
                    cursor_x += text_editing_surface.get_width()
                cursor_y = text_y
                pygame.draw.line(
                    self.screen,
                    (0, 200, 255),
                    (cursor_x, cursor_y),
                    (cursor_x, cursor_y + font.get_height()),
                    2,
                )
        else:
            # 普通模式：显示所有文本
            text_surface = font.render(self.input_text, True, WHITE)
            self.screen.blit(text_surface, (text_x, text_y))

            # 光标位置
            if self.cursor_blink:
                # 计算光标位置
                text_before_cursor = self.input_text[: self.cursor_pos]
                text_before_surface = font.render(text_before_cursor, True, WHITE)
                cursor_x = text_x + text_before_surface.get_width()
                cursor_y = text_y
                pygame.draw.line(
                    self.screen,
                    (0, 200, 255),
                    (cursor_x, cursor_y),
                    (cursor_x, cursor_y + font.get_height()),
                    2,
                )

        # 提示文字
        hint_text = "ESC 关闭 | Enter 发送 | .帮助 查看命令"
        hint_surface = small_font.render(hint_text, True, GRAY)
        hint_x = self.chat_x + self.chat_width - hint_surface.get_width() - 10
        hint_y = self.chat_y + 8
        self.screen.blit(hint_surface, (hint_x, hint_y))


# ========== 旧的 draw_menu 函数（保留以兼容，但标记为弃用） ==========


def draw_menu(screen, menu_state):
    """
    [已弃用] 绘制主菜单 - 请使用 MenuManager 类

    参数:
        screen: pygame屏幕对象
        menu_state: 包含菜单状态的字典
    """
    print("警告: draw_menu 已弃用，请使用 MenuManager 类")
    # 清空屏幕
    screen.fill(BLACK)

    # 简单显示一个提示
    if title_font:
        title = title_font.render("多人射击游戏", True, WHITE)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))

    if font:
        hint = font.render("菜单正在使用 pygame-menu 重写中...", True, YELLOW)
        screen.blit(
            hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT // 2)
        )


def draw_hud(screen, hud_state):
    """
    绘制游戏HUD（生命值、弹药、武器信息等）

    参数:
        screen: pygame屏幕对象
        hud_state: 包含HUD状态的字典，包括:
            - player: 玩家对象
            - player_count: 玩家数量
            - debug_mode: 是否显示调试信息
            - network_manager: 网络管理器对象
            - nearby_sound_players: 附近发出声音的玩家列表
    """
    player = hud_state["player"]

    # 生命值
    health_text = f"生命: {player.health}/{player.max_health}"
    screen.blit(font.render(health_text, True, WHITE), (20, 20))

    # 武器类型
    weapon_text = f"武器: {'近战' if player.weapon_type == 'melee' else '枪械'}"
    screen.blit(
        font.render(
            weapon_text, True, YELLOW if player.weapon_type == "melee" else GREEN
        ),
        (20, 50),
    )

    # 根据武器类型显示不同信息
    if player.weapon_type == "gun":
        ammo_text = f"弹药: {player.ammo}/{MAGAZINE_SIZE}"
        screen.blit(font.render(ammo_text, True, WHITE), (20, 80))

        if player.is_reloading:
            import time

            reload_time = max(0, RELOAD_TIME - (time.time() - player.reload_start))
            reload_text = f"换弹中: {reload_time:.1f}s"
            screen.blit(font.render(reload_text, True, YELLOW), (20, 110))
    else:
        # 近战武器状态
        if player.melee_weapon.can_attack():
            melee_text = "近战武器: 就绪"
            melee_color = GREEN
        else:
            import time

            remaining_cooldown = MELEE_COOLDOWN - (
                time.time() - player.melee_weapon.last_attack_time
            )
            melee_text = f"近战武器: {remaining_cooldown:.1f}s"
            melee_color = RED

        screen.blit(font.render(melee_text, True, melee_color), (20, 80))

    # 瞄准状态
    if player.is_aiming:
        aim_text = "瞄准中"
        screen.blit(font.render(aim_text, True, AIM_COLOR), (20, 110))

    # 死亡状态
    if player.is_dead:
        import time

        current_time = time.time()
        # 修复：确保复活时间有效且大于当前时间才显示倒计时
        if player.respawn_time > 0 and player.respawn_time > current_time:
            remaining_time = player.respawn_time - current_time
            # 限制显示的最大复活时间为10秒，防止显示异常大的数值
            if remaining_time <= 10.0:
                death_text = f"已死亡 - 复活倒计时: {remaining_time:.1f}s"
            else:
                death_text = "已死亡 - 等待复活..."
        else:
            death_text = "已死亡 - 等待复活..."
        death_surface = font.render(death_text, True, RED)
        screen.blit(
            death_surface,
            (SCREEN_WIDTH // 2 - death_surface.get_width() // 2, SCREEN_HEIGHT // 2),
        )

    # 玩家数量
    player_count = hud_state["player_count"]
    count_text = f"玩家数: {player_count}"
    screen.blit(font.render(count_text, True, WHITE), (SCREEN_WIDTH - 150, 20))

    # 显示玩家ID和回收池信息（调试模式）
    if hud_state["debug_mode"] and hud_state["network_manager"].is_server:
        recycled_text = f"回收池: {sorted(hud_state['network_manager'].recycled_ids) if hud_state['network_manager'].recycled_ids else '空'}"
        screen.blit(font.render(recycled_text, True, YELLOW), (SCREEN_WIDTH - 250, 50))

    # 控制提示
    if not player.is_dead and not player.is_respawning:
        interact_text = "按E键开/关门"
        screen.blit(
            font.render(interact_text, True, WHITE),
            (SCREEN_WIDTH - 150, SCREEN_HEIGHT - 120),
        )

        # 武器控制提示
        if player.weapon_type == "gun":
            weapon_text = "左键射击 右键瞄准"
        else:
            weapon_text = "左键近战攻击"
        screen.blit(
            font.render(weapon_text, True, WHITE),
            (SCREEN_WIDTH - 200, SCREEN_HEIGHT - 90),
        )

        # 切换武器提示
        switch_text = "按3切换武器"
        screen.blit(
            font.render(switch_text, True, WHITE),
            (SCREEN_WIDTH - 150, SCREEN_HEIGHT - 60),
        )

    # 聊天提示
    chat_hint = "按Y键聊天"
    screen.blit(
        font.render(chat_hint, True, WHITE), (SCREEN_WIDTH - 150, SCREEN_HEIGHT - 30)
    )

    # 显示伤害信息
    damage_text = f"射击伤害: {BULLET_DAMAGE} 近战伤害: {MELEE_DAMAGE}"
    screen.blit(font.render(damage_text, True, WHITE), (20, 140))

    # 视角相关信息
    current_fov = 30 if player.is_aiming else 120
    vision_text = f"视角: {current_fov}° {'(瞄准)' if player.is_aiming else '(正常)'})"
    screen.blit(font.render(vision_text, True, YELLOW), (20, 170))

    # 脚步声提示
    if hud_state["nearby_sound_players"]:
        footstep_text = f"附近脚步声: {len(hud_state['nearby_sound_players'])}个玩家"
        screen.blit(font.render(footstep_text, True, RED), (20, 200))

    # 调试信息
    if hud_state["debug_mode"]:
        debug_y = 200
        screen.blit(font.render(f"玩家ID: {player.id}", True, YELLOW), (20, debug_y))
        debug_y += 25
        screen.blit(
            font.render(
                f"服务器: {'是' if hud_state['network_manager'].is_server else '否'}",
                True,
                YELLOW,
            ),
            (20, debug_y),
        )
        debug_y += 25
        screen.blit(
            font.render(f"武器类型: {player.weapon_type}", True, YELLOW), (20, debug_y)
        )
        debug_y += 25
        screen.blit(
            font.render(
                f"瞄准状态: {'是' if player.is_aiming else '否'}", True, YELLOW
            ),
            (20, debug_y),
        )
        debug_y += 25
        screen.blit(
            font.render(
                f"瞄准偏移: ({player.aim_offset.x:.1f}, {player.aim_offset.y:.1f})",
                True,
                YELLOW,
            ),
            (20, debug_y),
        )
        debug_y += 25
        screen.blit(
            font.render(
                f"门状态: {len(hud_state['network_manager'].doors)}个已同步",
                True,
                YELLOW,
            ),
            (20, debug_y),
        )
        debug_y += 25
        bullets_count = hud_state.get("bullets_count", 0)
        network_bullets_count = len(hud_state["network_manager"].get_bullets())
        screen.blit(
            font.render(
                f"子弹数: {bullets_count} 网络: {network_bullets_count}", True, YELLOW
            ),
            (20, debug_y),
        )
        debug_y += 25
        screen.blit(
            font.render(f"按F3切换调试模式 F4切换视角显示", True, YELLOW), (20, debug_y)
        )
        debug_y += 25
        show_vision = hud_state.get("show_vision", False)
        screen.blit(
            font.render(f"视角系统: {'开' if show_vision else '关'}", True, YELLOW),
            (20, debug_y),
        )
        debug_y += 25
        screen.blit(
            font.render(
                f"脚步声: {len(hud_state['nearby_sound_players'])}个玩家", True, YELLOW
            ),
            (20, debug_y),
        )


def draw_chat(screen, chat_state):
    """
    绘制聊天系统（输入框和消息历史）

    参数:
        screen: pygame屏幕对象
        chat_state: 包含聊天状态的字典，包括:
            - chat_active: 聊天是否激活
            - chat_input: 聊天输入文本
            - chat_cursor_blink: 光标是否显示
            - recent_messages: 最近的聊天消息列表
            - chat_scroll_offset: 聊天消息滚动偏移量
    """
    # 聊天输入框
    if chat_state["chat_active"]:
        chat_box_height = 35
        chat_box = pygame.Rect(
            10, SCREEN_HEIGHT - chat_box_height - 10, SCREEN_WIDTH - 20, chat_box_height
        )
        pygame.draw.rect(screen, BLACK, chat_box)
        pygame.draw.rect(screen, WHITE, chat_box, 2)

        # 聊天提示和输入文字
        chat_prompt = "聊天: "
        prompt_surface = font.render(chat_prompt, True, WHITE)
        screen.blit(prompt_surface, (chat_box.x + 5, chat_box.y + 5))

        # 输入文字
        input_surface = font.render(chat_state["chat_input"], True, WHITE)
        input_x = chat_box.x + 5 + prompt_surface.get_width()
        screen.blit(input_surface, (input_x, chat_box.y + 5))

        # 光标
        if chat_state["chat_cursor_blink"]:
            cursor_x = input_x + input_surface.get_width()
            cursor_y = chat_box.y + 5
            pygame.draw.line(
                screen,
                WHITE,
                (cursor_x, cursor_y),
                (cursor_x, cursor_y + font.get_height()),
                2,
            )

    # 聊天消息历史
    recent_messages = chat_state["recent_messages"]
    if recent_messages:
        # 定义显示区域
        chat_y_start = SCREEN_HEIGHT - 60 - (chat_state["chat_active"] * 45)  # 底部位置
        chat_y_min = 250  # 顶部限制
        display_height = chat_y_start - chat_y_min  # 可显示区域高度

        # 第一步：计算所有消息的行信息
        message_lines = []  # 存储每条消息的行信息 [(msg, lines, total_height), ...]

        for msg in recent_messages:
            # 创建消息文本
            if msg.player_id == 0:
                message_text = msg.message
            else:
                message_text = f"{msg.player_name}: {msg.message}"

            # 分割成行
            if "\n" in message_text:
                lines = message_text.split("\n")
            else:
                lines = [message_text]

            # 计算高度
            line_height = small_font.get_height() + 5
            total_height = len(lines) * line_height

            message_lines.append((msg, lines, total_height))

        # 第二步：应用滚动偏移，计算要显示的消息范围
        # 从最新的消息开始，向上累积高度
        scroll_pixels = chat_state["chat_scroll_offset"] * (
            small_font.get_height() + 5
        )  # 将行偏移转换为像素偏移

        # 限制滚动偏移量
        total_content_height = (
            sum(h for _, _, h in message_lines) + len(message_lines) * 10
        )  # 加上消息间距
        max_scroll = max(0, total_content_height - display_height)
        scroll_pixels = min(scroll_pixels, max_scroll)

        # 第三步：渲染消息（从下往上，应用滚动偏移）
        current_y = chat_y_start + scroll_pixels  # 加上滚动偏移

        for msg, lines, total_height in reversed(message_lines):
            # 计算消息的起始Y坐标
            message_y = current_y - total_height
            message_end_y = current_y

            # 检查消息是否在可见区域内
            if message_end_y < chat_y_min:
                # 消息完全在可见区域上方，停止渲染
                break

            if message_y < chat_y_min and message_end_y > chat_y_min:
                # 消息部分可见，需要裁剪
                # 计算可见的行
                line_height = small_font.get_height() + 5
                visible_start_line = max(0, int((chat_y_min - message_y) / line_height))

                # 只渲染可见的行
                for i in range(visible_start_line, len(lines)):
                    line = lines[i]
                    line_y = message_y + i * line_height

                    if line_y >= chat_y_min and line_y < chat_y_start:
                        line_surface = small_font.render(line, True, msg.color)

                        # 半透明背景
                        bg_rect = pygame.Rect(
                            10,
                            line_y - 2,
                            line_surface.get_width() + 10,
                            line_surface.get_height() + 4,
                        )
                        bg_surface = pygame.Surface(
                            (bg_rect.width, bg_rect.height), pygame.SRCALPHA
                        )
                        bg_surface.fill((0, 0, 0, 128))
                        screen.blit(bg_surface, bg_rect)

                        # 文本
                        screen.blit(line_surface, (15, line_y))

            elif message_y >= chat_y_min:
                # 消息完全可见
                line_height = small_font.get_height() + 5
                for i, line in enumerate(lines):
                    line_y = message_y + i * line_height
                    line_surface = small_font.render(line, True, msg.color)

                    # 半透明背景
                    bg_rect = pygame.Rect(
                        10,
                        line_y - 2,
                        line_surface.get_width() + 10,
                        line_surface.get_height() + 4,
                    )
                    bg_surface = pygame.Surface(
                        (bg_rect.width, bg_rect.height), pygame.SRCALPHA
                    )
                    bg_surface.fill((0, 0, 0, 128))
                    screen.blit(bg_surface, bg_rect)

                    # 文本
                    screen.blit(line_surface, (15, line_y))

            # 移动到下一条消息
            current_y = message_y - 10  # 消息间距

        # 显示滚动提示（任何时候都显示，不仅限于聊天激活时）
        if len(message_lines) > 0:
            # 检查是否可以滚动
            if scroll_pixels > 0:
                hint_text = "↓ 更多消息 (方向键)"
                hint_surface = small_font.render(hint_text, True, YELLOW)
                screen.blit(
                    hint_surface,
                    (SCREEN_WIDTH - hint_surface.get_width() - 20, chat_y_start + 10),
                )

            if scroll_pixels < max_scroll:
                hint_text = "↑ 更早消息 (方向键)"
                hint_surface = small_font.render(hint_text, True, YELLOW)
                screen.blit(
                    hint_surface,
                    (SCREEN_WIDTH - hint_surface.get_width() - 20, chat_y_min - 20),
                )


# ========== 游戏内界面重构 - HUD 管理器 ==========


class HUDManager:
    """
    游戏内 HUD 管理器
    使用直接绘制方式，避免 pygame-menu 背景问题
    """

    def __init__(self, screen, game):
        self.screen = screen
        self.game = game

        # HUD 位置设置
        self.hud_x = 10
        self.hud_y = 10
        self.line_height = 22
        self.padding = 5

        # 缓存的HUD数据
        self.health_text = ""
        self.health_color = GREEN
        self.weapon_text = ""
        self.weapon_color = YELLOW
        self.ammo_text = ""
        self.ammo_color = WHITE
        self.status_text = ""
        self.status_color = ORANGE
        self.aim_text = ""
        self.aim_color = AIM_COLOR

        self.buff_texts = []
        self.grenade_text = ""
        self.grenade_color = WHITE

    def update(self):
        """更新 HUD 内容"""
        if not self.game.player:
            return

        player = self.game.player
        import time
        current_time = time.time()

        self.health_text = f"生命: {player.health}/{player.max_health}"
        self.health_color = (
            GREEN if player.health > 50 else (YELLOW if player.health > 25 else RED)
        )

        weapon_name = "近战" if player.weapon_type == "melee" else "枪械"
        self.weapon_text = f"武器: {weapon_name}"
        self.weapon_color = YELLOW if player.weapon_type == "melee" else GREEN

        if player.weapon_type == "gun":
            self.ammo_text = f"弹药: {player.ammo}/{MAGAZINE_SIZE}"
            self.ammo_color = WHITE

            if player.is_reloading:
                reload_time = max(0, RELOAD_TIME - (current_time - player.reload_start))
                self.status_text = f"换弹中: {reload_time:.1f}s"
                self.status_color = YELLOW
                self.aim_text = ""
            else:
                self.status_text = ""
                if player.is_aiming:
                    self.aim_text = "瞄准中"
                    self.aim_color = AIM_COLOR
                else:
                    self.aim_text = ""
        else:
            if player.melee_weapon.can_attack():
                self.ammo_text = "近战武器: 就绪"
                self.ammo_color = GREEN
                self.status_text = ""
            else:
                remaining_cooldown = MELEE_COOLDOWN - (
                    current_time - player.melee_weapon.last_attack_time
                )
                self.ammo_text = f"近战武器: {remaining_cooldown:.1f}s"
                self.ammo_color = RED
                self.status_text = ""
            self.aim_text = ""

        self.buff_texts = []

        if player.armor > 0:
            self.buff_texts.append((f"护甲: {player.armor}", (100, 150, 255)))

        if hasattr(player, 'speed_boost_end_time') and player.speed_boost_end_time > current_time:
            remaining = player.speed_boost_end_time - current_time
            self.buff_texts.append((f"加速: {remaining:.1f}s", (100, 255, 100)))

        if hasattr(player, 'damage_boost_end_time') and player.damage_boost_end_time > current_time:
            remaining = player.damage_boost_end_time - current_time
            self.buff_texts.append((f"伤害提升: {remaining:.1f}s", (255, 100, 100)))

        grenade_count = getattr(player, 'grenades', 0)
        if grenade_count > 0:
            self.grenade_text = f"手雷: {grenade_count}"
            self.grenade_color = (255, 200, 100)
        else:
            self.grenade_text = ""

    def draw(self):
        """绘制 HUD"""
        global font, small_font

        health_surface = font.render(self.health_text, True, self.health_color)
        self.screen.blit(health_surface, (self.hud_x, self.hud_y))

        weapon_surface = font.render(self.weapon_text, True, self.weapon_color)
        self.screen.blit(weapon_surface, (self.hud_x, self.hud_y + self.line_height))

        ammo_surface = font.render(self.ammo_text, True, self.ammo_color)
        self.screen.blit(ammo_surface, (self.hud_x, self.hud_y + self.line_height * 2))

        current_line = 3

        if self.status_text:
            status_surface = font.render(self.status_text, True, self.status_color)
            self.screen.blit(
                status_surface, (self.hud_x, self.hud_y + self.line_height * current_line)
            )
            current_line += 1

        if self.aim_text:
            aim_surface = font.render(self.aim_text, True, self.aim_color)
            self.screen.blit(aim_surface, (self.hud_x, self.hud_y + self.line_height * current_line))
            current_line += 1

        if self.buff_texts:
            buff_y = self.hud_y + self.line_height * current_line + 5
            for buff_text, buff_color in self.buff_texts:
                buff_surface = small_font.render(buff_text, True, buff_color)
                self.screen.blit(buff_surface, (self.hud_x, buff_y))
                buff_y += 16

        if self.grenade_text:
            grenade_y = self.hud_y + self.line_height * current_line
            if self.buff_texts:
                grenade_y += len(self.buff_texts) * 16 + 5
            grenade_surface = font.render(self.grenade_text, True, self.grenade_color)
            self.screen.blit(grenade_surface, (self.hud_x, grenade_y))


class InfoPanelManager:
    """
    信息面板管理器
    显示玩家数量、调试信息等
    使用直接绘制方式避免 pygame-menu 背景问题
    """

    def __init__(self, screen, game):
        self.screen = screen
        self.game = game

        # 信息面板位置设置（右上角）
        self.panel_x = SCREEN_WIDTH - 180
        self.panel_y = 10
        self.line_height = 18

        # 缓存的数据
        self.player_count_text = ""
        self.debug_text = ""
        self.debug_color = LIGHT_GRAY

    def update(self):
        """更新信息面板内容"""
        # 更新玩家数量
        player_count = len(self.game.other_players) + 1
        self.player_count_text = f"玩家数: {player_count}"

        # 更新调试信息
        if self.game.debug_mode:
            player = self.game.player
            self.debug_text = f"ID:{player.id} FPS:{int(self.game.clock.get_fps())}"
            self.debug_color = YELLOW
        else:
            self.debug_text = ""

    def draw(self):
        """绘制信息面板"""
        global small_font

        # 绘制玩家数量
        player_count_surface = small_font.render(
            self.player_count_text, True, LIGHT_GRAY
        )
        self.screen.blit(player_count_surface, (self.panel_x, self.panel_y))

        # 绘制调试信息（如果有）
        if self.debug_text:
            debug_surface = small_font.render(self.debug_text, True, self.debug_color)
            self.screen.blit(
                debug_surface, (self.panel_x, self.panel_y + self.line_height)
            )


class ChatHistoryManager:
    """
    聊天历史显示管理器
    支持滚动查看历史消息
    """

    def __init__(self, screen, game):
        self.screen = screen
        self.game = game
        self.messages = []
        self.max_messages = 50
        self.display_messages = 12

        self.history_x = 20
        self.history_y = SCREEN_HEIGHT - 320
        self.history_width = 400
        self.history_height = 200

        self.scroll_offset = 0
        self.line_height = 0

        self.chat_font = None

    def update(self):
        """更新聊天历史内容"""
        if not self.game.network_manager:
            return

        new_messages = self.game.network_manager.get_recent_chat_messages()

        # 只在有新消息时更新
        if len(new_messages) != len(self.messages):
            self.messages = new_messages[-self.max_messages :]
            # 有新消息时，自动滚动到底部
            self.scroll_offset = 0

    def scroll_up(self):
        """向上滚动（查看更早的消息）"""
        self.scroll_offset += 1

    def scroll_down(self):
        """向下滚动（查看最新的消息）"""
        self.scroll_offset = max(0, self.scroll_offset - 1)

    def _get_chat_font(self):
        if self.chat_font is None:
            global fonts
            if fonts and "font_name" in fonts:
                self.chat_font = pygame.font.SysFont(fonts["font_name"], 13)
            else:
                self.chat_font = pygame.font.Font(None, 13)
        return self.chat_font

    def draw(self):
        if not self.messages:
            return

        chat_font = self._get_chat_font()

        bg_rect = pygame.Rect(
            self.history_x, self.history_y, self.history_width, self.history_height
        )
        bg_surface = pygame.Surface((self.history_width, self.history_height), pygame.SRCALPHA)
        bg_surface.fill((15, 15, 20, 120))
        self.screen.blit(bg_surface, (self.history_x, self.history_y))
        pygame.draw.rect(self.screen, (60, 60, 80, 150), bg_rect, 1)

        title_surface = chat_font.render("── 聊天消息 ──", True, GRAY)
        self.screen.blit(title_surface, (self.history_x + 10, self.history_y + 5))

        line_height = chat_font.get_height() + 2
        self.line_height = line_height

        all_lines = []
        max_text_width = self.history_width - 20

        for msg in self.messages:
            if msg.player_id == 0:
                message_text = msg.message
                msg_color = WHITE
            else:
                message_text = f"{msg.player_name}: {msg.message}"
                msg_color = msg.color

            lines = message_text.split("\n")

            for line in lines:
                if chat_font.size(line)[0] > max_text_width:
                    current_line = ""
                    for char in line:
                        test_line = current_line + char
                        if chat_font.size(test_line)[0] <= max_text_width:
                            current_line = test_line
                        else:
                            if current_line:
                                all_lines.append((current_line, msg_color))
                            current_line = char
                    if current_line:
                        all_lines.append((current_line, msg_color))
                else:
                    all_lines.append((line, msg_color))

            all_lines.append(("", None))

        available_height = self.history_height - 22
        max_visible_lines = int(available_height / line_height)

        max_scroll = max(0, len(all_lines) - max_visible_lines)
        self.scroll_offset = min(self.scroll_offset, max_scroll)

        start_line = max(0, len(all_lines) - max_visible_lines - self.scroll_offset)
        end_line = min(len(all_lines), start_line + max_visible_lines)

        y_offset = 20
        for i in range(start_line, end_line):
            line_text, line_color = all_lines[i]

            if not line_text:
                y_offset += 2
                continue

            line_surface = chat_font.render(line_text, True, line_color)
            self.screen.blit(
                line_surface, (self.history_x + 10, self.history_y + y_offset)
            )
            y_offset += line_height

        if self.scroll_offset > 0:
            hint_text = "↑"
            hint_surface = chat_font.render(hint_text, True, YELLOW)
            hint_x = self.history_x + self.history_width - hint_surface.get_width() - 10
            self.screen.blit(hint_surface, (hint_x, self.history_y + 5))

        if self.scroll_offset < max_scroll:
            hint_text = "↓"
            hint_surface = chat_font.render(hint_text, True, YELLOW)
            hint_x = self.history_x + self.history_width - hint_surface.get_width() - 10
            self.screen.blit(hint_surface, (hint_x, self.history_y + 5))


class ControlHintsManager:
    """
    控制提示管理器
    显示操作提示
    使用直接绘制方式避免 pygame-menu 背景问题
    """

    def __init__(self, screen, game):
        self.screen = screen
        self.game = game

        # 控制提示位置设置（右下角，避免与小地图重叠）
        self.hints_x = SCREEN_WIDTH - 220
        self.hints_y = SCREEN_HEIGHT - 90
        self.line_height = 18

        # 缓存的数据
        self.interact_text = ""
        self.weapon_text = ""
        self.switch_text = "按3切换武器"
        self.chat_text = "按Y键聊天"

    def update(self):
        """更新控制提示"""
        if not self.game.player:
            return

        player = self.game.player

        # 根据玩家状态显示不同提示
        if player.is_dead or player.is_respawning:
            self.interact_text = ""
            self.weapon_text = ""
            self.switch_text = ""
        else:
            # 交互提示
            self.interact_text = "按E键开/关门"

            # 武器提示
            if player.weapon_type == "gun":
                self.weapon_text = "左键射击 右键瞄准"
            else:
                self.weapon_text = "左键近战攻击"

            self.switch_text = "按3切换武器"

    def draw(self):
        """绘制控制提示"""
        global small_font

        current_y = self.hints_y

        # 绘制交互提示（如果有）
        if self.interact_text:
            interact_surface = small_font.render(self.interact_text, True, LIGHT_GRAY)
            self.screen.blit(interact_surface, (self.hints_x, current_y))
            current_y += self.line_height

        # 绘制武器提示（如果有）
        if self.weapon_text:
            weapon_surface = small_font.render(self.weapon_text, True, LIGHT_GRAY)
            self.screen.blit(weapon_surface, (self.hints_x, current_y))
            current_y += self.line_height

        # 绘制切换武器提示（如果有）
        if self.switch_text:
            switch_surface = small_font.render(self.switch_text, True, LIGHT_GRAY)
            self.screen.blit(switch_surface, (self.hints_x, current_y))
            current_y += self.line_height

        # 绘制聊天提示
        chat_surface = small_font.render(self.chat_text, True, LIGHT_GRAY)
        self.screen.blit(chat_surface, (self.hints_x, current_y))


class MinimapManager:
    """
    小地图管理器
    显示玩家、队友和地图结构
    使用直接绘制方式避免 pygame-menu 背景问题
    """

    def __init__(self, screen, game):
        self.screen = screen
        self.game = game
        self.minimap_width = 200
        self.minimap_height = 150
        self.minimap_scale = 0.08
        self.minimap_surface = pygame.Surface((self.minimap_width, self.minimap_height))

        # 小地图位置设置（右下角，与控制提示分开，避免与ChatHistoryManager重叠）
        # ChatHistoryManager在左侧，高度120，y=SCREEN_HEIGHT-250
        # 小地图放在右侧，y=SCREEN_HEIGHT-280，确保不重叠
        self.minimap_x = SCREEN_WIDTH - self.minimap_width - 30
        self.minimap_y = SCREEN_HEIGHT - self.minimap_height - 140

    def update(self):
        """更新小地图内容"""
        if not self.game.player or not self.game.game_map:
            return

        # 清空小地图
        self.minimap_surface.fill(BLACK)

        # 计算小地图中心
        minimap_center_x = self.minimap_width / 2
        minimap_center_y = self.minimap_height / 2

        # 绘制墙壁
        for wall in self.game.game_map.walls:
            rel_x = (
                wall.x - self.game.player.pos.x
            ) * self.minimap_scale + minimap_center_x
            rel_y = (
                wall.y - self.game.player.pos.y
            ) * self.minimap_scale + minimap_center_y
            rel_width = wall.width * self.minimap_scale
            rel_height = wall.height * self.minimap_scale

            if (
                rel_x + rel_width > 0
                and rel_x < self.minimap_width
                and rel_y + rel_height > 0
                and rel_y < self.minimap_height
            ):
                pygame.draw.rect(
                    self.minimap_surface,
                    DARK_GRAY,
                    (rel_x, rel_y, rel_width, rel_height),
                )

        # 绘制门
        for door in self.game.game_map.doors:
            if not door.is_open:
                rel_x = (
                    door.rect.x - self.game.player.pos.x
                ) * self.minimap_scale + minimap_center_x
                rel_y = (
                    door.rect.y - self.game.player.pos.y
                ) * self.minimap_scale + minimap_center_y
                rel_width = door.rect.width * self.minimap_scale
                rel_height = door.rect.height * self.minimap_scale

                if (
                    rel_x + rel_width > 0
                    and rel_x < self.minimap_width
                    and rel_y + rel_height > 0
                    and rel_y < self.minimap_height
                ):
                    pygame.draw.rect(
                        self.minimap_surface,
                        DOOR_COLOR,
                        (rel_x, rel_y, rel_width, rel_height),
                    )

        # 绘制本地玩家（始终在中心）
        player_color = (
            DEAD_COLOR if self.game.player.is_dead else self.game.player.color
        )
        if self.game.player.weapon_type == "melee":
            player_color = MELEE_COLOR
        pygame.draw.circle(
            self.minimap_surface,
            player_color,
            (int(minimap_center_x), int(minimap_center_y)),
            4,
        )

        # 绘制小地图边框
        pygame.draw.rect(
            self.minimap_surface,
            WHITE,
            (0, 0, self.minimap_width, self.minimap_height),
            2,
        )

    def _get_teammates(self):
        """获取队友列表"""
        teammates = []
        if hasattr(self.game, "team_manager"):
            try:
                teammates = list(
                    self.game.team_manager.get_teammates(self.game.player.id)
                )
            except Exception:
                pass

        if not teammates and hasattr(self.game, "network_manager"):
            try:
                local_team_id = getattr(self.game.player, "team_id", None)
                if local_team_id is not None:
                    for pid, pdata in self.game.network_manager.players.items():
                        if (
                            pid != self.game.player.id
                            and pdata.get("team_id", None) == local_team_id
                        ):
                            teammates.append(pid)
            except Exception:
                pass

        return teammates

    def _find_player(self, player_id):
        """查找玩家对象"""
        if player_id in self.game.other_players:
            return self.game.other_players[player_id]
        elif player_id in self.game.ai_players:
            return self.game.ai_players[player_id]
        return None

    def draw(self):
        """绘制小地图"""
        self.update()

        global small_font

        # 创建带阴影的小地图
        shadow_offset = 3
        shadow_surface = pygame.Surface((self.minimap_width, self.minimap_height))
        shadow_surface.fill((0, 0, 0, 100))

        # 绘制阴影
        self.screen.blit(
            shadow_surface,
            (self.minimap_x + shadow_offset, self.minimap_y + shadow_offset),
        )

        # 绘制小地图
        self.screen.blit(self.minimap_surface, (self.minimap_x, self.minimap_y))

        # 绘制小地图边框
        pygame.draw.rect(
            self.screen,
            WHITE,
            (self.minimap_x, self.minimap_y, self.minimap_width, self.minimap_height),
            2,
        )

        # 绘制标题
        title_surface = small_font.render("── 小地图 ──", True, GRAY)
        title_x = self.minimap_x + (self.minimap_width - title_surface.get_width()) // 2
        self.screen.blit(title_surface, (title_x, self.minimap_y - 18))
