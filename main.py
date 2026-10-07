"""
多人射击游戏主程序
包含游戏主循环、菜单系统和网络扫描功能
"""

# 标准库导入
import json
import math
import random
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress

# 第三方库导入
import pygame
from pygame.locals import *

# 本地模块导入 - 常量（现在从 settings.json 加载）
from constants import *

# AI系统选择现在从 config/settings.json 加载
# 如需修改，请编辑 settings.json 中的 "ai.use_enhanced_ai"
if USE_ENHANCED_AI:
    try:
        from ai_player_enhanced import EnhancedAIPlayer as AIPlayer

        print("[AI系统] 使用增强版AI系统（行为树+个性化特征）")
    except ImportError as e:
        print(f"[AI系统] 增强版AI导入失败: {e}，使用原版AI系统")
        from ai_player import AIPlayer
else:
    from ai_player import AIPlayer

    print("[AI系统] 使用原版AI系统")

from map import Map, Door
from camera import Camera

# 视野射线长度上限：覆盖整张地图对角线，等效于取消视距限制
# （射线仍会被墙壁和门板挡住，只是不再有固定长度截断）
VISION_MAX_RANGE = ROOM_SIZE * 3 * 1.5
from network import NetworkManager, ChatMessage, generate_default_player_name
from player import Player
from weapons import MeleeWeapon, Bullet
from items import Grenade

# 本地模块导入 - 工具和UI
from utils import *
import ui

# 本地模块导入 - 团队系统
from team import TeamManager

class AIPlayerWrapper:
    """服务端碰撞检测用的轻量 AI 包装：每帧重新绑定 pos/存活状态"""

    def __init__(self, ai):
        self.id = ai.id
        self.pos = ai.pos
        self.is_dead = ai.is_dead
        self.source = ai


# generate_default_player_name is now imported from network module

# 初始化pygame
import os

os.environ["SDL_IME_SHOW_UI"] = "1"
pygame.init()
pygame.font.init()

# 初始化UI模块的字体
ui.initialize_fonts()

# 获取字体引用（为了向后兼容）
font = ui.font
small_font = ui.small_font
large_font = ui.large_font
title_font = ui.title_font


def interpolate_network_player(player, now):
    """把其他玩家的显示位置/朝向插值到当前时刻，消除 20Hz 网络快照造成的跳变"""
    t = 1.0
    prev = player.net_prev_pos
    curr = player.net_curr_pos
    if prev is not None and curr is not None:
        span = player.net_curr_time - player.net_prev_time
        if span <= 0:
            player.pos.update(curr)
        else:
            t = (now - player.net_prev_time) / span
            if t < 0.0:
                t = 0.0
            elif t > 1.0:
                t = 1.0
            player.pos.x = prev.x + (curr.x - prev.x) * t
            player.pos.y = prev.y + (curr.y - prev.y) * t
    a_prev = player.net_prev_angle
    a_curr = player.net_curr_angle
    if a_prev is not None and a_curr is not None:
        delta = ((a_curr - a_prev + 180.0) % 360.0) - 180.0
        player.angle = a_prev + delta * t


def get_local_ip():
    """
    获取本机内网IP地址

    通过连接外部地址(8.8.8.8)来获取本机的内网IP地址。
    这种方法比直接获取hostname更可靠，因为它能正确识别多网卡情况下的主要IP。

    Returns:
        str: 本机内网IP地址，如果获取失败则返回 "127.0.0.1"

    Example:
        >>> ip = get_local_ip()
        >>> print(ip)  # 例如: "192.168.1.100"
    """
    try:
        # 连接一个外部地址来获取本机IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except OSError:
        return "127.0.0.1"




def scan_for_servers():
    """
    扫描局域网中的游戏服务器

    使用多线程并发扫描局域网内的所有IP地址，查找正在运行的游戏服务器。
    扫描策略：
    1. 优先扫描本机IP
    2. 扫描/24网段的所有主机
    3. 对于10.x.x.x网段，额外扫描/16网段（限制在10000个主机内）
    4. 使用50个并发线程提高扫描速度

    Returns:
        list: 找到的服务器信息列表，每个服务器信息包含:
              - name: 服务器名称
              - ip: 服务器IP地址
              - players: 当前玩家数
              - max_players: 最大玩家数
              - version: 游戏版本

    Example:
        >>> servers = scan_for_servers()
        >>> for server in servers:
        ...     print(f"{server['name']} - {server['ip']} ({server['players']}/{server['max_players']})")

    Note:
        - 扫描超时时间由 SCAN_TIMEOUT 常量控制
        - 服务器端口由 SERVER_PORT 常量控制
        - 扫描过程会打印详细的调试信息
    """
    found_servers = []
    seen_server_ids = set()
    server_list_lock = threading.Lock()
    local_ip = get_local_ip()

    print(f"开始扫描，本机IP: {local_ip}")

    # 获取网络段 - 尝试多种方法
    ip_lists = []

    # 方法1：基于网络段检测
    try:
        # 尝试/24网段
        network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
        ip_list_24 = list(network.hosts())
        ip_lists.append(("24位网段", ip_list_24))
        print(f"检测到/24网段: {network}, 包含{len(ip_list_24)}个IP")

        # 如果IP是10.x.x.x，也尝试/16网段
        if local_ip.startswith("10."):
            try:
                network_16 = ipaddress.IPv4Network(f"{local_ip}/16", strict=False)
                if network_16.num_addresses <= 10000:  # 限制扫描范围
                    ip_list_16 = list(network_16.hosts())
                    ip_lists.append(("16位网段", ip_list_16))
                    print(f"检测到/16网段: {network_16}, 包含{len(ip_list_16)}个IP")
            except ValueError:
                pass

    except Exception as e:
        print(f"网络段检测失败: {e}")

    # 方法2：扫描当前子网的邻近IP
    try:
        base_ip = ".".join(local_ip.split(".")[:-1])
        nearby_ips = [ipaddress.IPv4Address(f"{base_ip}.{i}") for i in range(1, 255)]
        ip_lists.append(("当前子网", nearby_ips))
        print(f"添加当前子网扫描: {base_ip}.1-254")
    except ValueError:
        pass

    # 如果没有任何IP列表，使用默认
    if not ip_lists:
        print("使用默认IP范围")
        ip_lists.append(
            (
                "默认范围",
                [ipaddress.IPv4Address(f"192.168.1.{i}") for i in range(1, 255)],
            )
        )

    # 合并所有IP并去重
    all_ips = set()
    for list_name, ip_list in ip_lists:
        all_ips.update(ip_list)
        print(f"{list_name}: {len(ip_list)}个IP")

    print(f"总共需要扫描 {len(all_ips)} 个唯一IP地址")

    def check_server(ip):
        # with 语句保证 socket 关闭，sendto 抛异常也不泄漏句柄
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(SCAN_TIMEOUT)

                # 发送服务器探测消息
                sock.sendto("server_probe".encode(), (str(ip), SERVER_PORT))

                # 等待响应
                try:
                    data, addr = sock.recvfrom(1024)
                    response = data.decode()
                    if response.startswith("server_info:"):
                        # 解析服务器信息
                        _, info = response.split(":", 1)
                        server_info = json.loads(info)
                        server_info["ip"] = str(ip)

                        # 使用服务器ID去重
                        server_id = server_info.get("id")

                        with server_list_lock:
                            if server_id and server_id in seen_server_ids:
                                # 已经发现过这个服务器（可能是通过另一个IP）
                                pass
                            else:
                                if server_id:
                                    seen_server_ids.add(server_id)
                                found_servers.append(server_info)
                                print(
                                    f"找到服务器: {ip} - {server_info.get('name', '未知')}"
                                )
                except socket.timeout:
                    pass
                except (OSError, ValueError, json.JSONDecodeError) as e:
                    # 调试：打印解析错误
                    if str(ip) == local_ip:
                        print(f"本机IP {ip} 响应解析失败: {e}")
        except OSError as e:
            # 调试：打印连接错误
            if str(ip) == local_ip:
                print(f"本机IP {ip} 连接失败: {e}")

    # 优先扫描本机IP
    local_ip_addr = ipaddress.IPv4Address(local_ip)
    if local_ip_addr in all_ips:
        print(f"优先扫描本机IP: {local_ip}")
        check_server(local_ip_addr)
        all_ips.remove(local_ip_addr)

    # 线程池并发扫描：as_completed 逐个回收，无 50 线程批 join 的长尾阻塞
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(check_server, ip): ip for ip in all_ips}
        for future in as_completed(futures):
            future.result()  # 异常已在 check_server 内处理，这里只为回收

    print(f"扫描完成，找到 {len(found_servers)} 个服务器")
    return found_servers


class Game:
    """
    游戏主类

    管理游戏的整个生命周期，包括：
    - 主菜单系统
    - 服务器扫描和连接
    - 游戏主循环
    - 玩家输入处理
    - 游戏状态更新
    - 渲染和绘制
    - 网络同步
    - 聊天系统

    Attributes:
        running (bool): 游戏是否正在运行
        clock (pygame.Clock): 游戏时钟，用于控制帧率
        screen (pygame.Surface): 游戏窗口表面
        state (str): 当前游戏状态 ("MENU", "SCANNING", "CONNECTING", "PLAYING", "ERROR")
        network_manager (NetworkManager): 网络管理器实例
        player (Player): 本地玩家实例
        other_players (dict): 其他玩家字典 {player_id: Player}
        ai_players (dict): AI玩家字典 {player_id: AIPlayer}
        game_map (Map): 游戏地图实例
        bullets (list): 当前活动的子弹列表

    Game States:
        - MENU: 主菜单状态，显示服务器列表和连接选项
        - SCANNING: 正在扫描局域网服务器
        - CONNECTING: 正在连接到服务器
        - PLAYING: 游戏进行中
        - ERROR: 发生错误，显示错误信息

    Example:
        >>> game = Game()
        >>> game.run()  # 启动游戏主循环
    """

    def __init__(self):
        self.running = True
        self.clock = pygame.time.Clock()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("游戏")

        # 相机：把世界坐标变换到屏幕坐标（含跟随朝向的旋转）
        self.camera = Camera()
        self.camera_follow = pygame.Vector2(0, 0)  # 平滑跟随玩家的相机中心

        # 游戏状态
        self.state = "MENU"  # MENU, SCANNING, CONNECTING, PLAYING, ERROR
        self.connection_info = None
        self.error_message = ""
        self.connecting_start_time = 0

        # 服务器扫描
        self.scanning_servers = False
        self.found_servers = []
        self.scan_thread = None

        # 网络管理器
        self.network_manager = None

        # 网络同步
        self.last_sync_time = 0
        self.sync_interval = 0.05  # 50ms同步间隔

        # 聊天系统
        self.chat_active = False
        self.chat_input = ""
        self.chat_cursor_blink = 0
        self.last_chat_cursor_blink = 0
        self.chat_scroll_offset = 0  # 聊天消息滚动偏移量（向上滚动的行数）
        self.chat_max_display_height = 290  # 聊天消息最大显示高度（从y=250到y=540）

        # 红色滤镜效果
        self.hit_effect_time = 0
        self.hit_effect_duration = 0.3  # 0.3秒的红色滤镜效果

        # 视角显示
        self.show_vision = True  # 默认开启视角系统

        # 调试模式
        self.debug_mode = True

        # 脚步声系统
        self.footstep_detection_range = VISION_RANGE  # 脚步声检测范围，使用视角范围常量
        self.nearby_sound_players = []  # 附近发出声音的玩家

        # 游戏规则设置
        self.game_rules = {
            "damage_multiplier": 1.0,  # 伤害倍率，默认为1.0
            "respawn_time": RESPAWN_TIME,  # 复活时间（秒）
            "friendly_fire": True,  # 友军伤害
            "bullet_speed": BULLET_SPEED,  # 子弹速度
            "footstep_range": self.footstep_detection_range,  # 脚步声范围
        }

        # AI玩家管理
        self.ai_players = {}  # AI玩家字典 {player_id: AIPlayer}
        self.next_ai_id = 100  # AI玩家ID从100开始

        # 团队系统
        self.team_manager = TeamManager()

        # 聊天系统 - 团队聊天模式
        self.team_chat_mode = False  # True=队内聊天, False=全局聊天

        # 初始化聊天菜单管理器
        self.chat_menu_manager = ui.ChatMenuManager(self.screen, self)

        # 初始化游戏内界面管理器（使用 pygame-menu 重构）
        self.hud_manager = ui.HUDManager(self.screen, self)
        self.info_panel_manager = ui.InfoPanelManager(self.screen, self)
        self.chat_history_manager = ui.ChatHistoryManager(self.screen, self)
        self.control_hints_manager = ui.ControlHintsManager(self.screen, self)
        self.minimap_manager = ui.MinimapManager(self.screen, self)

    def trigger_hit_effect(self):
        """触发被击中时的红色滤镜效果"""
        print("[受击效果] 触发红色滤镜效果")
        self.hit_effect_time = self.hit_effect_duration

    def start_server_scan(self):
        """启动服务器扫描"""
        if not self.scanning_servers:
            self.scanning_servers = True
            self.found_servers = []
            self.scan_thread = threading.Thread(target=self._scan_servers_thread)
            self.scan_thread.daemon = True
            self.scan_thread.start()

    def _scan_servers_thread(self):
        """服务器扫描线程"""
        try:
            self.found_servers = scan_for_servers()
        except Exception as e:
            print(f"扫描服务器时出错: {e}")
        finally:
            self.scanning_servers = False

    def show_menu(self):
        """显示主菜单 - 使用 pygame-menu"""
        from ui import MenuManager

        # 创建菜单管理器
        menu_manager = MenuManager(self.screen, self)

        # 自动开始扫描服务器
        if not self.scanning_servers and not self.found_servers:
            self.start_server_scan()

        while self.state == "MENU":
            events = pygame.event.get()

            for event in events:
                if event.type == QUIT:
                    self.running = False
                    return
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        self.running = False
                        return

            # 更新菜单
            menu_manager.update(events)

            # 绘制菜单
            menu_manager.draw()

            pygame.display.flip()
            self.clock.tick(FPS)

    def show_connecting_screen(self):
        """显示连接中界面"""
        dots = ""
        last_dot_time = 0

        # 玩家名称修改状态
        show_player_name_edit = False
        player_name_input = self.connection_info.get(
            "player_name", generate_default_player_name()
        )
        player_name_active = False

        while self.state == "CONNECTING":
            current_time = time.time()

            # 检查连接超时
            if current_time - self.connecting_start_time > CONNECTION_TIMEOUT:
                self.error_message = "连接超时，请检查网络连接"
                self.state = "ERROR"
                return

            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False
                    return
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE and show_player_name_edit:
                        # 取消改名（优先于返回主菜单）
                        show_player_name_edit = False
                        player_name_active = False
                    elif event.key == K_ESCAPE:
                        self.state = "MENU"
                        return
                    elif (
                        event.key == K_n
                        and not self.connection_info["is_server"]
                        and not show_player_name_edit
                    ):
                        # 按N键修改玩家名称
                        show_player_name_edit = True
                        player_name_active = True
                        player_name_input = self.connection_info.get(
                            "player_name", generate_default_player_name()
                        )
                    elif (
                        event.key == K_RETURN
                        and show_player_name_edit
                        and player_name_input.strip()
                    ):
                        # 确认修改玩家名称
                        self.connection_info["player_name"] = player_name_input.strip()
                        show_player_name_edit = False
                        player_name_active = False
                        # 重新初始化网络管理器以使用新的玩家名称
                        if self.network_manager:
                            self.network_manager.player_name = player_name_input.strip()
                    elif player_name_active:
                        if event.key == K_BACKSPACE:
                            player_name_input = player_name_input[:-1]
                        else:
                            ch = event.unicode
                            if ch.isprintable() and len(player_name_input) < 16:
                                player_name_input += ch
                elif event.type == MOUSEBUTTONDOWN:
                    # 检查是否点击了修改名称按钮
                    if (
                        not self.connection_info["is_server"]
                        and not show_player_name_edit
                    ):
                        button_rect = pygame.Rect(
                            SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 100, 200, 40
                        )
                        if button_rect.collidepoint(event.pos):
                            show_player_name_edit = True
                            player_name_active = True
                            player_name_input = self.connection_info.get(
                                "player_name", generate_default_player_name()
                            )
                    elif show_player_name_edit:
                        # 确认按钮
                        confirm_rect = pygame.Rect(
                            SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT // 2 + 150, 100, 40
                        )
                        if (
                            confirm_rect.collidepoint(event.pos)
                            and player_name_input.strip()
                        ):
                            self.connection_info["player_name"] = (
                                player_name_input.strip()
                            )
                            show_player_name_edit = False
                            player_name_active = False
                            # 重新初始化网络管理器以使用新的玩家名称
                            if self.network_manager:
                                self.network_manager.player_name = (
                                    player_name_input.strip()
                                )
                        # 取消按钮
                        cancel_rect = pygame.Rect(
                            SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT // 2 + 200, 100, 40
                        )
                        if cancel_rect.collidepoint(event.pos):
                            show_player_name_edit = False
                            player_name_active = False

            # 尝试初始化游戏
            if self.initialize_game():
                self.state = "PLAYING"
                return

            # 检查是否出现错误
            if (
                self.network_manager is not None
                and self.network_manager.connection_error
            ):
                self.error_message = self.network_manager.connection_error
                self.state = "ERROR"
                return

            # 更新动画点
            if current_time - last_dot_time > 0.5:
                dots = dots + "." if len(dots) < 3 else ""
                last_dot_time = current_time

            # 绘制连接界面
            self.screen.fill(BLACK)

            if self.connection_info["is_server"]:
                title = large_font.render("正在启动服务器" + dots, True, WHITE)
                info = font.render("等待其他玩家连接...", True, LIGHT_BLUE)
                local_ip = get_local_ip()
                ip_info = font.render(
                    f"服务器地址: {local_ip}:{SERVER_PORT}", True, GREEN
                )
                self.screen.blit(
                    ip_info,
                    (
                        SCREEN_WIDTH // 2 - ip_info.get_width() // 2,
                        SCREEN_HEIGHT // 2 + 30,
                    ),
                )
            else:
                title = large_font.render("正在连接服务器" + dots, True, WHITE)
                info = font.render(
                    f"服务器: {self.connection_info['server_ip']}", True, LIGHT_BLUE
                )

                # 显示当前玩家名称
                player_info = font.render(
                    f"玩家名称: {self.connection_info.get('player_name', generate_default_player_name())}",
                    True,
                    YELLOW,
                )
                self.screen.blit(
                    player_info,
                    (
                        SCREEN_WIDTH // 2 - player_info.get_width() // 2,
                        SCREEN_HEIGHT // 2 + 50,
                    ),
                )

                # 修改名称按钮
                if not show_player_name_edit:
                    button_rect = pygame.Rect(
                        SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 100, 200, 40
                    )
                    pygame.draw.rect(self.screen, DARK_BLUE, button_rect)
                    pygame.draw.rect(self.screen, WHITE, button_rect, 2)
                    button_text = font.render("修改名称 (N)", True, WHITE)
                    self.screen.blit(
                        button_text,
                        (
                            button_rect.x
                            + (button_rect.width - button_text.get_width()) // 2,
                            button_rect.y
                            + (button_rect.height - button_text.get_height()) // 2,
                        ),
                    )

                # 玩家名称编辑界面
                if show_player_name_edit:
                    # 输入框
                    input_rect = pygame.Rect(
                        SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 80, 200, 35
                    )
                    input_color = YELLOW if player_name_active else WHITE
                    pygame.draw.rect(self.screen, BLACK, input_rect)
                    pygame.draw.rect(self.screen, input_color, input_rect, 2)

                    input_label = font.render("玩家名称:", True, WHITE)
                    self.screen.blit(input_label, (input_rect.x, input_rect.y - 30))

                    input_surface = font.render(player_name_input, True, WHITE)
                    self.screen.blit(
                        input_surface, (input_rect.x + 10, input_rect.y + 7)
                    )

                    # 光标
                    if player_name_active and pygame.time.get_ticks() % 1000 < 500:
                        cursor_x = input_rect.x + 10 + input_surface.get_width()
                        pygame.draw.line(
                            self.screen,
                            WHITE,
                            (cursor_x, input_rect.y + 5),
                            (cursor_x, input_rect.y + input_rect.height - 5),
                            2,
                        )

                    # 确认按钮
                    confirm_rect = pygame.Rect(
                        SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT // 2 + 150, 100, 40
                    )
                    confirm_enabled = len(player_name_input.strip()) > 0
                    confirm_color = GREEN if confirm_enabled else GRAY
                    pygame.draw.rect(self.screen, confirm_color, confirm_rect)
                    pygame.draw.rect(self.screen, WHITE, confirm_rect, 2)
                    confirm_text = font.render(
                        "确认", True, WHITE if confirm_enabled else DARK_GRAY
                    )
                    self.screen.blit(
                        confirm_text,
                        (
                            confirm_rect.x
                            + (confirm_rect.width - confirm_text.get_width()) // 2,
                            confirm_rect.y
                            + (confirm_rect.height - confirm_text.get_height()) // 2,
                        ),
                    )

                    # 取消按钮
                    cancel_rect = pygame.Rect(
                        SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT // 2 + 200, 100, 40
                    )
                    pygame.draw.rect(self.screen, RED, cancel_rect)
                    pygame.draw.rect(self.screen, WHITE, cancel_rect, 2)
                    cancel_text = font.render("取消", True, WHITE)
                    self.screen.blit(
                        cancel_text,
                        (
                            cancel_rect.x
                            + (cancel_rect.width - cancel_text.get_width()) // 2,
                            cancel_rect.y
                            + (cancel_rect.height - cancel_text.get_height()) // 2,
                        ),
                    )

            self.screen.blit(
                title,
                (SCREEN_WIDTH // 2 - title.get_width() // 2, SCREEN_HEIGHT // 2 - 50),
            )
            self.screen.blit(
                info, (SCREEN_WIDTH // 2 - info.get_width() // 2, SCREEN_HEIGHT // 2)
            )

            # 取消提示
            cancel_text = small_font.render("按ESC键取消", True, GRAY)
            self.screen.blit(
                cancel_text,
                (
                    SCREEN_WIDTH // 2 - cancel_text.get_width() // 2,
                    SCREEN_HEIGHT // 2 + 250,
                ),
            )

            pygame.display.flip()
            self.clock.tick(FPS)

    def show_error_screen(self):
        """显示错误界面"""
        while self.state == "ERROR":
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False
                    return
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE or event.key == K_RETURN:
                        self.state = "MENU"
                        return

            self.screen.fill(BLACK)

            # 错误标题
            error_title = large_font.render("连接失败", True, RED)
            self.screen.blit(
                error_title,
                (
                    SCREEN_WIDTH // 2 - error_title.get_width() // 2,
                    SCREEN_HEIGHT // 2 - 100,
                ),
            )

            # 错误信息
            error_lines = self.error_message.split("\n")
            for i, line in enumerate(error_lines):
                error_text = font.render(line, True, WHITE)
                self.screen.blit(
                    error_text,
                    (
                        SCREEN_WIDTH // 2 - error_text.get_width() // 2,
                        SCREEN_HEIGHT // 2 - 50 + i * 30,
                    ),
                )

            # 提示信息
            hint_text = small_font.render("按ESC或Enter键返回主菜单", True, LIGHT_BLUE)
            self.screen.blit(
                hint_text,
                (
                    SCREEN_WIDTH // 2 - hint_text.get_width() // 2,
                    SCREEN_HEIGHT // 2 + 100,
                ),
            )

            pygame.display.flip()
            self.clock.tick(FPS)

    def initialize_game(self):
        """
        初始化游戏组件

        根据连接信息初始化网络管理器、地图、玩家等游戏组件。

        初始化步骤：
        1. 创建网络管理器（服务器或客户端模式）
        2. 等待网络连接建立
        3. 创建游戏地图
        4. 创建本地玩家
        5. 初始化子弹列表
        6. 设置相机偏移

        Returns:
            bool: 初始化是否成功
                  - True: 初始化成功，可以开始游戏
                  - False: 初始化失败，应返回菜单或显示错误

        Note:
            - 服务器模式下会自动创建服务器
            - 客户端模式下会连接到指定的服务器IP
            - 初始化失败时会设置 self.error_message
        """
        try:
            if not self.network_manager:
                # 初始化网络管理器
                if self.connection_info["is_server"]:
                    server_name = self.connection_info.get("server_name", "默认服务器")
                    print(f"[调试] 创建服务器，服务器名称: {server_name}")
                    self.network_manager = NetworkManager(
                        is_server=True, game_instance=self, server_name=server_name
                    )
                else:
                    player_name = self.connection_info.get(
                        "player_name", generate_default_player_name()
                    )
                    self.network_manager = NetworkManager(
                        is_server=False,
                        server_address=self.connection_info["server_ip"],
                        game_instance=self,
                        player_name=player_name,
                    )

            # 检查连接是否成功
            if not self.network_manager.connected:
                self.error_message = (
                    self.network_manager.connection_error or "网络连接失败"
                )
                return False

            # 等待分配玩家ID（客户端）
            if not self.connection_info["is_server"]:
                if self.network_manager.player_id is None:
                    return False

            # 初始化游戏地图（地图类型由 settings.json 的 map.type 决定）
            # 地图需先于出生点创建：出生房间从地图房间列表取，不再假设 3x3
            self.game_map = Map(MAP_TYPE)
            spawn_rect = random.choice(self.game_map.rooms)
            spawn_x = spawn_rect.centerx
            spawn_y = spawn_rect.centery

            # 创建本地玩家
            player_name = self.connection_info.get(
                "player_name", f"玩家{self.network_manager.player_id}"
            )
            self.player = Player(
                self.network_manager.player_id,
                spawn_x,
                spawn_y,
                is_local=True,
                name=player_name,
            )
            self.other_players = {}  # 存储其他玩家

            self.bullets = []  # 本地子弹对象
            self.grenades = []  # 飞行手雷列表（由服务端状态同步）
            self.last_grenade_explosion = None  # 爆炸特效状态
            self.camera_follow = pygame.Vector2(self.player.pos)
            self.camera.set_view(self.player.pos, 0.0)
            
            # 初始化道具系统
            from items import create_default_item_manager
            self.item_manager = create_default_item_manager()
            self.item_manager.generate_spawn_points(self.game_map.rooms, self.game_map.walls)
            self.item_manager.spawn_all_types()
            
            print(f"游戏初始化成功，玩家ID: {self.network_manager.player_id}")
            print(f"道具系统已初始化，生成 {len(self.item_manager.items)} 个道具")
            return True

        except Exception as e:
            print(f"初始化游戏失败: {e}")
            self.error_message = f"游戏初始化失败: {e}"
            return False

    def handle_events(self):
        events = pygame.event.get()

        # 如果聊天激活，优先交给聊天管理器处理
        if self.chat_active:
            self.chat_menu_manager.update(events)
            # 处理 ESC 退出（同步状态）
            if not self.chat_menu_manager.is_enabled():
                self.chat_active = False

            # 即使聊天激活，我们也需要处理 QUIT 事件
            for event in events:
                if event.type == QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    # 聊天激活时，上下键用于滚动查看历史消息
                    if event.key == pygame.K_UP:
                        self.chat_history_manager.scroll_up()
                    elif event.key == pygame.K_DOWN:
                        self.chat_history_manager.scroll_down()
            return

        # 非聊天模式下的标准处理
        for event in events:
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False
                elif event.key == K_y:  # 按Y开启聊天
                    self.chat_active = True
                    self.chat_menu_manager.enable()
                elif event.key == K_3:  # 按3切换武器
                    if self.player and not self.player.is_dead:
                        self.player.switch_weapon()
                elif event.key == K_UP:  # 非聊天模式下，上下键用于滚动查看历史
                    self.chat_history_manager.scroll_up()
                elif event.key == K_DOWN:
                    self.chat_history_manager.scroll_down()
                elif (
                    event.key == K_r
                    and not self.player.is_reloading
                    and not self.player.is_dead
                    and self.player.weapon_type == "gun"
                ):
                    self.player.is_reloading = True
                    self.player.reload_start = time.time()
                elif event.key == K_F3:  # 切换调试模式
                    self.debug_mode = not self.debug_mode
                elif event.key == K_F4:  # 切换视角显示
                    self.show_vision = not self.show_vision
                elif event.key == K_g:  # 按G投掷手雷
                    if self.player and not self.player.is_dead and hasattr(self.player, 'grenades'):
                        if self.player.grenades > 0:
                            # 沿当前朝向投掷
                            direction = pygame.Vector2(
                                math.cos(math.radians(self.player.angle)),
                                -math.sin(math.radians(self.player.angle)),
                            )
                            # 交由服务端权威生成并模拟（含网络同步与伤害结算）
                            self.network_manager.request_throw_grenade(
                                [self.player.pos.x, self.player.pos.y],
                                [direction.x, direction.y],
                            )
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1 and not self.player.is_dead:  # 左键按下且未死亡
                    if self.player.weapon_type == "melee":  # 近战武器时触发轻击
                        self.player.start_melee_attack(is_heavy=False)
                    else:  # 其他武器时射击
                        self.player.mouse_shooting = True
                elif event.button == 3 and not self.player.is_dead:  # 右键按下
                    if self.player.weapon_type == "melee":  # 近战武器时触发重击
                        self.player.start_melee_attack(is_heavy=True)
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1:  # 左键释放
                    if self.player.weapon_type != "melee":  # 非近战武器时停止射击
                        self.player.mouse_shooting = False

    def update(self, dt):
        # 检查网络连接状态
        if not self.network_manager.connected:
            if self.network_manager.connection_error:
                self.error_message = self.network_manager.connection_error
            else:
                self.error_message = "网络连接丢失"
            self.state = "ERROR"
            return

        current_time = time.time()

        # 检查玩家对象是否存在
        if not hasattr(self, "player") or self.player is None:
            self.error_message = "玩家对象初始化失败"
            self.state = "ERROR"
            return

        # 合并所有玩家（本地+网络）
        all_players = {self.player.id: self.player}
        all_players.update(self.other_players)

        # 服务端：添加AI玩家对象到all_players用于碰撞检测
        if self.network_manager.is_server and hasattr(self, "ai_players"):
            for ai_id, ai_player in self.ai_players.items():
                if ai_id not in all_players:
                    # 创建一个简单的Player对象用于碰撞检测
                    wrapper = AIPlayerWrapper(ai_player)
                    all_players[ai_id] = wrapper
                    dprint(
                        f"[调试] 添加AI玩家{ai_id}到all_players，位置=({wrapper.pos.x}, {wrapper.pos.y}), 死亡={wrapper.is_dead}"
                    )

        # 更新本地玩家
        self.player.update(
            dt,
            self.game_map,
            self.bullets,
            self.network_manager,
            all_players,
            chat_active=self.chat_active,
        )
        
        # 更新道具效果
        if self.player:
            self.player.update_effects(dt)
        
        # 更新道具系统
        if hasattr(self, 'item_manager') and self.item_manager:
            self.item_manager.update(dt)
            
            # 检查道具拾取（仅本地玩家存活时）
            if self.player and not self.player.is_dead:
                pickup_result = self.item_manager.check_pickup(self.player)
                if pickup_result:
                    print(f"[道具] 玩家{self.player.id}拾取道具: {pickup_result.get('message', '')}")
                    
                    # 服务端：直接应用效果并广播
                    if self.network_manager.is_server:
                        self.player.apply_item_effect(pickup_result)
                        
                        # 同步到network_manager.players字典
                        if self.player.id in self.network_manager.players:
                            self.network_manager.players[self.player.id]['health'] = self.player.health
                            self.network_manager.players[self.player.id]['armor'] = self.player.armor
                            self.network_manager.players[self.player.id]['speed_boost_end_time'] = self.player.speed_boost_end_time
                            self.network_manager.players[self.player.id]['damage_boost_end_time'] = self.player.damage_boost_end_time
                            self.network_manager.players[self.player.id]['grenades'] = getattr(self.player, 'grenades', 0)
                        
                        self.network_manager.send_item_update(self.item_manager.get_state())
                    else:
                        # 客户端：通知服务端，等待服务端确认后再应用效果
                        # 临时标记道具为不活跃，防止重复拾取
                        item_id = pickup_result.get('item_id')
                        if item_id and item_id in self.item_manager.items:
                            self.item_manager.items[item_id].is_active = False
                        self.network_manager.send_data({
                            'type': 'item_pickup',
                            'data': {
                                'player_id': self.player.id,
                                'item_id': item_id,
                                'effect': pickup_result
                            }
                        })

        # 控制网络同步频率
        if current_time - self.last_sync_time > self.sync_interval:
            self.last_sync_time = current_time

            # 同步网络玩家数据并清理断线玩家
            with self.network_manager.lock:
                # 获取当前网络中的玩家ID
                network_player_ids = set(self.network_manager.players.keys())
                # 获取当前本地其他玩家ID
                local_other_player_ids = set(self.other_players.keys())

                # 移除已断线的玩家
                disconnected_players = local_other_player_ids - network_player_ids
                for pid in disconnected_players:
                    if pid != self.player.id:  # 不要删除本地玩家
                        print(f"[客户端] 移除断线玩家{pid}")
                        del self.other_players[pid]

                # 更新或添加在线玩家
                for pid, pdata in self.network_manager.players.items():
                    # 本地玩家：只同步权威数据（健康值、死亡状态等）
                    if pid == self.player.id:
                        self.player.health = pdata.get("health", self.player.health)
                        self.player.is_dead = pdata.get("is_dead", False)
                        self.player.death_time = pdata.get("death_time", 0)
                        self.player.respawn_time = pdata.get("respawn_time", 0)
                        self.player.is_respawning = pdata.get("is_respawning", False)
                        self.player.armor = pdata.get("armor", self.player.armor)
                        self.player.speed_boost_end_time = pdata.get("speed_boost_end_time", 0)
                        self.player.damage_boost_end_time = pdata.get("damage_boost_end_time", 0)
                        self.player.grenades = pdata.get("grenades", 0)
                        self.player.protection_end = pdata.get("protection_end", 0)
                        continue

                    # 创建或更新其他玩家
                    if pid not in self.other_players:
                        pos = pdata.get("pos")
                        if (
                            not isinstance(pos, (list, tuple))
                            or len(pos) != 2
                            or not all(isinstance(v, (int, float)) for v in pos)
                        ):
                            continue  # 畸形同步包：缺有效坐标则跳过该玩家
                        player_name = pdata.get("name", f"玩家{pid}")
                        self.other_players[pid] = Player(
                            pid, pos[0], pos[1], name=player_name
                        )
                        print(f"[客户端] 添加新玩家{pid}")

                    # 更新玩家数据
                    other_player = self.other_players[pid]
                    # 只在非复活状态下更新位置（记录为插值目标，渲染时平滑过渡）
                    pos = pdata.get("pos")
                    pos_valid = (
                        isinstance(pos, (list, tuple))
                        and len(pos) == 2
                        and all(isinstance(v, (int, float)) for v in pos)
                    )
                    if not pdata.get("is_respawning", False) and pos_valid:
                        new_pos = pygame.Vector2(pos)
                        now_sync = time.time()
                        prev = other_player.net_curr_pos
                        if prev is None or new_pos.distance_to(prev) > 300:
                            # 首次出现、复活或瞬移：直接吸附，避免拖影
                            other_player.net_prev_pos = new_pos.copy()
                            other_player.net_curr_pos = new_pos.copy()
                            other_player.net_prev_time = now_sync
                            other_player.net_curr_time = now_sync
                            other_player.pos.update(new_pos)
                        else:
                            other_player.net_prev_pos = prev
                            other_player.net_curr_pos = new_pos
                            other_player.net_prev_time = other_player.net_curr_time
                            other_player.net_curr_time = now_sync
                    new_angle = pdata.get("angle", other_player.angle)
                    if other_player.net_curr_angle is None:
                        other_player.net_prev_angle = new_angle
                        other_player.net_curr_angle = new_angle
                        other_player.angle = new_angle
                    else:
                        other_player.net_prev_angle = other_player.net_curr_angle
                        other_player.net_curr_angle = new_angle
                    other_player.health = pdata.get("health", other_player.health)
                    other_player.ammo = pdata.get("ammo", other_player.ammo)
                    other_player.armor = pdata.get("armor", 0)
                    other_player.is_reloading = pdata.get("is_reloading", False)
                    other_player.shooting = pdata.get("shooting", False)
                    other_player.is_dead = pdata.get("is_dead", False)
                    other_player.death_time = pdata.get("death_time", 0)
                    other_player.respawn_time = pdata.get("respawn_time", 0)
                    other_player.is_respawning = pdata.get("is_respawning", False)
                    other_player.name = pdata.get("name", f"玩家{pid}")
                    other_player.speed_boost_end_time = pdata.get("speed_boost_end_time", 0)
                    other_player.damage_boost_end_time = pdata.get("damage_boost_end_time", 0)
                    other_player.grenades = pdata.get("grenades", 0)
                    other_player.protection_end = pdata.get("protection_end", 0)

                    # 同步团队ID
                    if "team_id" in pdata:
                        other_player.team_id = pdata["team_id"]

                    # 同步状态（包括武器类型和瞄准状态）
                    other_player.sync_from_network(pdata)

            # 服务端定期广播
            self.network_manager.update_and_broadcast()

            # 同步子弹
            self.sync_bullets()

        # AI 独立节拍：每帧更新，不再绑定 20Hz 网络同步节拍
        # （修复前 AI 每 50ms 只推进约 16.7ms 的位移，等效速度打三折）
        if self.network_manager.is_server:
            self.update_ai_players(dt, all_players)

        # 平滑其他玩家位置与朝向：在网络快照之间插值，消除 20Hz 跳变
        now_interp = time.time()
        for other_player in self.other_players.values():
            interpolate_network_player(other_player, now_interp)

        # 更新子弹
        for bullet in list(self.bullets):
            if bullet.update(dt, self.game_map, all_players, self.network_manager):
                self.bullets.remove(bullet)
                # 通知服务器移除子弹
                if self.network_manager.is_server:
                    self.network_manager.remove_bullet(bullet.id)
        
        # 手雷位置由服务端权威同步；客户端在两次同步之间做本地外推，消除 20Hz 跳变
        # （服务端主机在 update_and_broadcast 中已按帧推进，无需再外推）
        if not self.network_manager.is_server:
            grenade_walls = self.game_map.walls
            for grenade in self.grenades:
                if not grenade.exploded:
                    grenade.update(dt, grenade_walls)

        # 更新门
        door_progress_snapshot = {
            id(door): door.animation_progress for door in self.game_map.doors
        }
        self.game_map.update_doors(dt, self.network_manager)

        # 门板扫到玩家时把玩家推开
        self.resolve_door_push(all_players, door_progress_snapshot)

        # 更新相机：位置平滑跟随玩家，瞄准偏移直接叠加。
        # 偏移方向跟随朝向，若连它一起平滑，开镜转身时相机会明显拖尾。
        if not self.player.is_dead and not self.player.is_respawning:
            follow_k = 1.0 - (1.0 - CAMERA_FOLLOW_LERP) ** (dt * 60)
            self.camera_follow += (
                self.player.pos - self.camera_follow
            ) * follow_k

        target_center = self.camera_follow + self.player.aim_offset

        # 相机跟随朝向旋转：玩家正前方始终朝向屏幕上方
        angle = (90.0 - self.player.angle) % 360 if ROTATE_CAMERA else 0.0
        self.camera.set_view(target_center, angle)

        # 检测附近的脚步声
        self.detect_nearby_footsteps()

        # 更新聊天光标闪烁
        if self.chat_active:
            current_time = pygame.time.get_ticks()
            if current_time - self.last_chat_cursor_blink > 500:
                self.chat_cursor_blink = not self.chat_cursor_blink
                self.last_chat_cursor_blink = current_time

        # 更新红色滤镜效果
        if self.hit_effect_time > 0:
            self.hit_effect_time -= dt
            if self.hit_effect_time < 0:
                self.hit_effect_time = 0

    def is_circle_free(self, center, radius, ignore_door=None):
        """圆形位置是否不与墙壁或其它门板重叠"""
        rect = pygame.Rect(
            center.x - radius, center.y - radius, radius * 2, radius * 2
        )

        for wall in self.game_map.walls:
            if rect.colliderect(wall):
                return False

        for door in self.game_map.doors:
            if door is ignore_door:
                continue
            if door.check_collision(rect):
                return False

        return True

    def resolve_door_push(self, all_players, progress_snapshot):
        """门板旋转扫到玩家时把玩家推开；玩家被墙夹住时门也停下来"""
        targets = []
        if self.player is not None:
            targets.append(self.player)
        # 服务端权威模拟所有玩家（含AI）；客户端只纠正自己，避免和插值打架
        if self.network_manager is not None and self.network_manager.is_server:
            ai_players = getattr(self, "ai_players", {})
            for pid, player in all_players.items():
                if player is self.player:
                    continue
                # AI 在 all_players 里可能只是网络同步出来的副本，用真正的 AI 对象
                ai_entity = ai_players.get(pid)
                targets.append(ai_entity if ai_entity is not None else player)

        for door in self.game_map.doors:
            for player in targets:
                # all_players 里可能混有用于碰撞检测的轻量 AI 包装对象，
                # 它每帧可能被重新绑定 pos，所以要通过 source 取真实对象
                entity = getattr(player, "source", player)

                if getattr(entity, "is_dead", False) or getattr(entity, "is_respawning", False):
                    continue

                pos = getattr(entity, "pos", None)
                if not isinstance(pos, pygame.Vector2):
                    continue

                pushed = door.resolve_circle(pos, PLAYER_RADIUS)
                if pushed is None:
                    continue

                if self.is_circle_free(pushed, PLAYER_RADIUS, ignore_door=door):
                    pos.update(pushed)
                    if hasattr(entity, "position"):
                        entity.position = entity.pos
                else:
                    # 玩家被墙夹住推不动：门回退到这一帧之前的角度
                    previous = progress_snapshot.get(id(door))
                    if previous is not None and previous != door.animation_progress:
                        door.animation_progress = previous
                        door.is_open = abs(previous) >= 1.0
                        door.update_rect()
                    break

    def is_position_safe(self, x, y):
        """检查位置是否安全（不与墙壁或门碰撞）"""
        player_rect = pygame.Rect(
            x - PLAYER_RADIUS, y - PLAYER_RADIUS, PLAYER_RADIUS * 2, PLAYER_RADIUS * 2
        )

        # 检查墙壁碰撞
        for wall in self.game_map.walls:
            if player_rect.colliderect(wall):
                return False

        # 检查门碰撞
        for door in self.game_map.doors:
            if door.check_collision(player_rect):
                return False

        return True

    def get_safe_spawn_pos(self, max_attempts=50):
        """获取安全的复活位置（不与墙壁或门碰撞）"""
        rooms = getattr(self.game_map, "rooms", [])
        # 优先在房间中心附近随机（房间列表由地图类型决定，不再假设 3x3）
        for attempt in range(max_attempts):
            if not rooms:
                break
            room = random.choice(rooms)
            spawn_x = room.centerx + random.randint(-100, 100)
            spawn_y = room.centery + random.randint(-100, 100)
            spawn_x = max(room.left + 50, min(spawn_x, room.right - 50))
            spawn_y = max(room.top + 50, min(spawn_y, room.bottom - 50))
            if self.is_position_safe(spawn_x, spawn_y):
                return spawn_x, spawn_y

        # 备选：在整张地图包围盒内随机尝试
        if rooms:
            map_right = max(r.right for r in rooms)
            map_bottom = max(r.bottom for r in rooms)
            for attempt in range(max_attempts):
                spawn_x = random.randint(100, max(101, map_right - 100))
                spawn_y = random.randint(100, max(101, map_bottom - 100))
                if self.is_position_safe(spawn_x, spawn_y):
                    return spawn_x, spawn_y

        # 最后备选：第一个房间中心
        if rooms:
            return rooms[0].centerx, rooms[0].centery
        return ROOM_SIZE * 1.5, ROOM_SIZE * 1.5

    def update_ai_players(self, dt, all_players):
        """更新AI玩家（仅服务端）"""
        if not self.network_manager.is_server:
            return

        # 准备玩家位置数据供AI使用
        players_data = {}
        for pid, player in all_players.items():
            # AI 包装对象（AIPlayerWrapper）本身缺少感知字段，从真实 AI 对象取
            real_player = getattr(player, "source", player)
            players_data[pid] = {
                "pos": [player.pos.x, player.pos.y],
                "is_dead": player.is_dead,
                "health": getattr(real_player, "health", 100),
                "shooting": getattr(real_player, "shooting", False),
                "is_reloading": getattr(real_player, "is_reloading", False),
                "is_walking": getattr(real_player, "is_walking", False),
                "is_making_sound": getattr(real_player, "is_making_sound", False),
                "team_id": getattr(real_player, "team_id", None),  # 添加团队ID
            }

        # 添加网络玩家数据（合并，优先使用网络数据中的完整信息）
        for pid, pdata in self.network_manager.players.items():
            if pid in players_data:
                # 合并数据，保留网络数据中的完整信息
                players_data[pid].update(
                    {
                        "shooting": pdata.get("shooting", False),
                        "is_reloading": pdata.get("is_reloading", False),
                        "is_walking": pdata.get("is_walking", False),
                        "is_making_sound": pdata.get(
                            "is_making_sound",
                            players_data[pid].get("is_making_sound", False),
                        ),
                        "health": pdata.get(
                            "health", players_data[pid].get("health", 100)
                        ),
                        "team_id": pdata.get(
                            "team_id", players_data[pid].get("team_id")
                        ),  # 优先使用网络数据中的team_id
                    }
                )
            else:
                players_data[pid] = pdata

        # 更新每个AI玩家
        for ai_id, ai_player in list(self.ai_players.items()):
            # 同步AI的team_id（从网络数据中获取）
            if ai_id in self.network_manager.players:
                network_team_id = self.network_manager.players[ai_id].get("team_id")
                old_team_id = getattr(ai_player, "team_id", None)

                # 如果team_id改变了，更新并重新初始化行为树（如果需要）
                if network_team_id != old_team_id:
                    ai_player.team_id = network_team_id
                    # 如果使用了增强版AI，重新初始化行为树以适应新的团队状态
                    if hasattr(ai_player, "_initialize_behavior_tree"):
                        ai_player._initialize_behavior_tree()

            # 检查AI是否需要复活
            if ai_player.is_dead:
                current_time = time.time()
                if current_time >= ai_player.respawn_time:
                    # 获取安全的复活位置（不与墙壁或门碰撞）
                    spawn_x, spawn_y = self.get_safe_spawn_pos()
                    ai_player.respawn(spawn_x, spawn_y)

                    # 更新网络数据
                    if ai_id in self.network_manager.players:
                        self.network_manager.players[ai_id]["pos"] = [spawn_x, spawn_y]
                        self.network_manager.players[ai_id]["health"] = 100
                        self.network_manager.players[ai_id]["is_dead"] = False
                        self.network_manager.players[ai_id]["respawn_time"] = 0
                continue

            # 更新AI逻辑（传递team_manager以便AI识别队友）
            team_manager = getattr(self, "team_manager", None)
            action = ai_player.update(
                dt, players_data, self.game_map, self.bullets, team_manager
            )

            if action:
                # 应用移动
                move_vec = action["move"] * dt
                new_pos = ai_player.pos + move_vec

                # 碰撞检测
                player_rect = pygame.Rect(
                    new_pos.x - PLAYER_RADIUS,
                    new_pos.y - PLAYER_RADIUS,
                    PLAYER_RADIUS * 2,
                    PLAYER_RADIUS * 2,
                )

                # 检查墙壁碰撞
                collision = False
                for wall in self.game_map.walls:
                    if player_rect.colliderect(wall):
                        collision = True
                        break

                # 检查门碰撞
                if not collision:
                    for door in self.game_map.doors:
                        if door.check_collision(player_rect):
                            collision = True
                            break

                if not collision:
                    ai_player.pos = new_pos
                else:
                    # 碰撞时尝试滑动移动
                    # 尝试只在X轴移动
                    test_pos_x = pygame.Vector2(
                        ai_player.pos.x + move_vec.x, ai_player.pos.y
                    )
                    test_rect_x = pygame.Rect(
                        test_pos_x.x - PLAYER_RADIUS,
                        test_pos_x.y - PLAYER_RADIUS,
                        PLAYER_RADIUS * 2,
                        PLAYER_RADIUS * 2,
                    )

                    collision_x = False
                    for wall in self.game_map.walls:
                        if test_rect_x.colliderect(wall):
                            collision_x = True
                            break

                    if not collision_x:
                        for door in self.game_map.doors:
                            if door.check_collision(test_rect_x):
                                collision_x = True
                                break

                    if not collision_x:
                        ai_player.pos = test_pos_x
                    else:
                        # 尝试只在Y轴移动
                        test_pos_y = pygame.Vector2(
                            ai_player.pos.x, ai_player.pos.y + move_vec.y
                        )
                        test_rect_y = pygame.Rect(
                            test_pos_y.x - PLAYER_RADIUS,
                            test_pos_y.y - PLAYER_RADIUS,
                            PLAYER_RADIUS * 2,
                            PLAYER_RADIUS * 2,
                        )

                        collision_y = False
                        for wall in self.game_map.walls:
                            if test_rect_y.colliderect(wall):
                                collision_y = True
                                break

                        if not collision_y:
                            for door in self.game_map.doors:
                                if door.check_collision(test_rect_y):
                                    collision_y = True
                                    break

                        if not collision_y:
                            ai_player.pos = test_pos_y

                # 更新角度
                ai_player.angle = action["angle"]

                # 处理射击
                if action["shoot"] and ai_player.ammo > 0:
                    # 计算子弹方向向量（与玩家相同的方式）
                    bullet_dir = pygame.Vector2(
                        math.cos(math.radians(ai_player.angle)),
                        -math.sin(math.radians(ai_player.angle)),
                    )
                    bullet_pos = ai_player.pos + bullet_dir * (
                        PLAYER_RADIUS + BULLET_RADIUS
                    )

                    # 创建子弹
                    self.network_manager.request_fire_bullet(
                        [bullet_pos.x, bullet_pos.y],
                        [bullet_dir.x, bullet_dir.y],
                        ai_id,
                    )
                    ai_player.ammo -= 1
                    ai_player.last_shot_time = time.time()

                # 处理装填
                if action.get("reload", False):
                    # 如果还没有开始换弹，则开始换弹
                    if not ai_player.is_reloading:
                        ai_player.is_reloading = True
                        ai_player.reload_start_time = time.time()

                # 检查换弹是否完成
                if ai_player.is_reloading:
                    current_time = time.time()
                    if current_time - ai_player.reload_start_time >= RELOAD_TIME:
                        ai_player.ammo = MAGAZINE_SIZE
                        ai_player.is_reloading = False

                # 处理门交互
                if "interact_door" in action and action["interact_door"]:
                    door = action["interact_door"]
                    if not door.is_open:
                        # AI开门
                        door.open()
                        try:
                            door_index = self.game_map.doors.index(door)
                            self.network_manager.update_door(
                                door_index, door.get_state()
                            )
                        except ValueError:
                            pass
                        dprint(f"[AI门交互] AI玩家{ai_id}开启了门")

                # 处理静步状态
                if "is_walking" in action:
                    ai_player.is_walking = action["is_walking"]

                # 处理声音状态
                if "is_making_sound" in action:
                    ai_player.is_making_sound = action["is_making_sound"]
                if "sound_volume" in action:
                    ai_player.sound_volume = action["sound_volume"]

                # 更新网络数据
                if ai_id in self.network_manager.players:
                    self.network_manager.players[ai_id]["pos"] = [
                        ai_player.pos.x,
                        ai_player.pos.y,
                    ]
                    self.network_manager.players[ai_id]["angle"] = ai_player.angle
                    self.network_manager.players[ai_id]["health"] = ai_player.health
                    self.network_manager.players[ai_id]["ammo"] = ai_player.ammo
                    self.network_manager.players[ai_id]["is_reloading"] = (
                        ai_player.is_reloading
                    )
                    self.network_manager.players[ai_id]["shooting"] = action["shoot"]
                    self.network_manager.players[ai_id]["is_walking"] = getattr(
                        ai_player, "is_walking", False
                    )
                    self.network_manager.players[ai_id]["is_making_sound"] = getattr(
                        ai_player, "is_making_sound", False
                    )
                    self.network_manager.players[ai_id]["sound_volume"] = getattr(
                        ai_player, "sound_volume", 0.0
                    )

    def add_ai_player(self, difficulty="normal"):
        """添加AI玩家（供命令系统调用）- 性格为隐性参数"""
        if not self.network_manager.is_server:
            return None

        ai_id = self.next_ai_id
        self.next_ai_id += 1

        spawn_x, spawn_y = self.get_safe_spawn_pos()

        try:
            if USE_ENHANCED_AI:
                from ai_player_enhanced import EnhancedAIPlayer
                from ai_personality import AIPersonality, AIPersonalityTraits

                # 性格随机生成，玩家无法选择
                personality_traits = AIPersonalityTraits.random_personality()

                ai_player = EnhancedAIPlayer(
                    ai_id, spawn_x, spawn_y, difficulty, personality_traits
                )
                ai_player_name = ai_player.name
                use_enhanced_ai = True
            else:
                raise ImportError("USE_ENHANCED_AI is False")

        except ImportError:
            from ai_player import AIPlayer

            ai_player = AIPlayer(ai_id, spawn_x, spawn_y, difficulty)
            ai_player_name = f"AI_{difficulty}_{ai_id}"
            use_enhanced_ai = False

        if hasattr(ai_player, "generate_patrol_points"):
            ai_player.generate_patrol_points(self.game_map)

        self.ai_players[ai_id] = ai_player

        player_data = {
            "pos": [spawn_x, spawn_y],
            "angle": ai_player.angle,
            "health": ai_player.health,
            "ammo": ai_player.ammo,
            "is_reloading": ai_player.is_reloading,
            "shooting": False,
            "is_dead": ai_player.is_dead,
            "death_time": ai_player.death_time,
            "respawn_time": ai_player.respawn_time,
            "is_respawning": False,
            "melee_attacking": False,
            "melee_direction": 0,
            "weapon_type": ai_player.weapon_type,
            "is_aiming": ai_player.is_aiming,
            "name": ai_player_name,
            "team_id": getattr(ai_player, "team_id", None),
        }

        if use_enhanced_ai:
            player_data["is_walking"] = getattr(ai_player, "is_walking", False)
            player_data["is_making_sound"] = getattr(
                ai_player, "is_making_sound", False
            )
            player_data["sound_volume"] = getattr(ai_player, "sound_volume", 0.0)

        self.network_manager.players[ai_id] = player_data

        # 不显示性格信息
        self.network_manager._send_system_message(
            f"已添加AI玩家 (难度: {difficulty}, ID: {ai_id})"
        )

        return ai_id

    def remove_ai_player(self, ai_id):
        """移除AI玩家（供命令系统调用）"""
        if not self.network_manager.is_server:
            return False

        if ai_id in self.ai_players:
            del self.ai_players[ai_id]
            if ai_id in self.network_manager.players:
                del self.network_manager.players[ai_id]
            self.network_manager._send_system_message(f"已移除AI玩家 (ID: {ai_id})")
            return True

        return False

    def sync_bullets(self):
        """同步子弹 - 完全基于服务器数据"""
        network_bullets = self.network_manager.get_bullets()

        # 获取当前子弹ID集合
        current_bullet_ids = {b.id for b in self.bullets}
        network_bullet_ids = {b["id"] for b in network_bullets}

        # 移除不在网络列表中的子弹
        self.bullets = [b for b in self.bullets if b.id in network_bullet_ids]

        # 添加新子弹
        for bullet_data in network_bullets:
            if bullet_data["id"] not in current_bullet_ids:
                # 使用游戏规则中的子弹速度
                bullet_speed = BULLET_SPEED
                if hasattr(self, "game_rules"):
                    bullet_speed = self.game_rules["bullet_speed"]

                new_bullet = Bullet(bullet_data, bullet_speed)
                self.bullets.append(new_bullet)
        
        if not hasattr(self, 'last_grenade_explosion'):
            self.last_grenade_explosion = None

    def render(self):
        # 清空屏幕为黑色（默认背景）
        self.screen.fill(BLACK)

        # 如果启用视角系统且玩家未死亡，绘制可见的扇形区域
        if self.show_vision and not self.player.is_dead:
            self.render_vision_fan()
        else:
            # 不使用视角系统时，绘制灰色地面
            self.render_full_ground()

        # 绘制墙壁和门（始终显示）
        self.render_walls_and_doors()

        # 绘制道具
        if hasattr(self, 'item_manager') and self.item_manager:
            player_pos = getattr(self.player, 'pos', None)
            player_angle = getattr(self.player, 'angle', 0)
            is_aiming = getattr(self.player, 'is_aiming', False)
            self.item_manager.draw(
                self.screen,
                self.camera,
                player_pos,
                player_angle,
                self.game_map.walls,
                self.game_map.doors,
                is_aiming
            )

        # 绘制游戏对象
        for bullet in self.bullets:
            if self.show_vision and not self.player.is_dead:
                bullet.draw(
                    self.screen,
                    self.camera,
                    self.player.pos,
                    self.player.angle,
                    self.game_map.walls,
                    self.game_map.doors,
                    self.player.is_aiming,
                )
            else:
                bullet.draw(self.screen, self.camera)
        
        # 绘制飞行手雷
        for grenade in self.grenades:
            grenade.draw(self.screen, self.camera)
        
        if self.last_grenade_explosion:
            elapsed = time.time() - self.last_grenade_explosion['time']
            if elapsed < 1.0:
                screen_pos = self.camera.to_screen(
                    self.last_grenade_explosion['pos'].x,
                    self.last_grenade_explosion['pos'].y,
                )
                alpha = int(255 * (1.0 - elapsed))
                radius = max(1, int(Grenade.EXPLOSION_RADIUS * (elapsed / 1.0)))
                grenade_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(grenade_surface, (255, 100, 0, alpha), (radius, radius), radius)
                pygame.draw.circle(grenade_surface, (255, 200, 50, alpha), (radius, radius), int(radius * 0.7))
                self.screen.blit(grenade_surface, (screen_pos[0] - radius, screen_pos[1] - radius))
            else:
                self.last_grenade_explosion = None

        for player in self.other_players.values():
            if self.show_vision and not self.player.is_dead:
                player.draw(
                    self.screen,
                    self.camera,
                    self.player.pos,
                    self.player.angle,
                    self.game_map.walls,
                    self.game_map.doors,
                    is_local_player=False,
                    is_aiming=self.player.is_aiming,
                    team_manager=self.team_manager,
                    local_player_id=self.player.id,
                )
            else:
                player.draw(
                    self.screen,
                    self.camera,
                    None,
                    None,
                    None,
                    None,
                    is_local_player=False,
                    team_manager=self.team_manager,
                    local_player_id=self.player.id,
                )

        # 本地玩家总是绘制
        self.player.draw(
            self.screen,
            self.camera,
            None,
            None,
            None,
            None,
            is_local_player=True,
        )

        # 绘制UI（总是在最上层）
        self.render_ui()

        # 聊天系统
        self.render_chat()

        # 绘制脚步声指示器
        self.render_footstep_indicators()

        # 绘制红色滤镜效果
        if self.hit_effect_time > 0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            alpha = min(
                100, int((self.hit_effect_time / self.hit_effect_duration) * 100)
            )
            overlay.fill((255, 0, 0, alpha))
            self.screen.blit(overlay, (0, 0))

        pygame.display.flip()

    def render_vision_fan(self):
        """绘制视野扇形 - 高效率版本，考虑墙壁和门的遮挡"""
        # 根据瞄准状态选择视野角度
        current_fov = 30 if self.player.is_aiming else 120

        # 复用预分配的透明表面，避免每帧创建全屏 Surface
        vision_surface = getattr(self, "_vision_surface", None)
        if vision_surface is None or vision_surface.get_size() != (SCREEN_WIDTH, SCREEN_HEIGHT):
            vision_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            self._vision_surface = vision_surface
        vision_surface.fill((0, 0, 0, 0))

        # 玩家屏幕位置（相机中心即屏幕中心）
        player_screen_pos = self.camera.to_screen_vec(self.player.pos)

        # 使用光线投射算法计算可见区域
        half_fov = current_fov / 2

        # 优化：根据屏幕分辨率和视野角度动态调整光线数量
        # 瞄准时使用更多光线以获得更精确的边缘
        ray_count = 40 if current_fov > 60 else 20
        angle_step = current_fov / ray_count

        # 收集所有可见点，用于构建可见多边形
        visible_points = [player_screen_pos]  # 起始点是玩家位置

        # 预先筛选可能与视野相交的墙壁和门，减少循环中的检查次数
        potential_walls = []
        for wall in self.game_map.walls:
            # 简单检查：如果墙壁在玩家视野范围内，则添加到潜在列表
            wall_center_x = wall.x + wall.width / 2
            wall_center_y = wall.y + wall.height / 2
            distance = math.sqrt(
                (self.player.pos.x - wall_center_x) ** 2
                + (self.player.pos.y - wall_center_y) ** 2
            )
            if distance <= VISION_MAX_RANGE:  # 稍微扩大检查范围
                potential_walls.append(wall)

        potential_doors = []
        for door in self.game_map.doors:
            door_center_x = door.original_rect.centerx
            door_center_y = door.original_rect.centery
            distance = math.sqrt(
                (self.player.pos.x - door_center_x) ** 2
                + (self.player.pos.y - door_center_y) ** 2
            )
            reach = VISION_MAX_RANGE + max(door.panel_length, door.panel_thickness)
            if distance <= reach:
                potential_doors.append(door)

        # 使用批处理方式处理光线
        batch_size = 5  # 每批处理的光线数量
        for batch_start in range(0, ray_count + 1, batch_size):
            batch_rays = []
            batch_angles = []

            # 为这一批次准备光线数据
            for i in range(batch_start, min(batch_start + batch_size, ray_count + 1)):
                angle = self.player.angle - half_fov + (angle_step * i)
                angle_rad = math.radians(angle)
                ray_end_x = self.player.pos.x + math.cos(angle_rad) * VISION_MAX_RANGE
                ray_end_y = self.player.pos.y - math.sin(angle_rad) * VISION_MAX_RANGE
                ray_end = pygame.Vector2(ray_end_x, ray_end_y)
                batch_rays.append(ray_end)
                batch_angles.append(angle)

            # 处理这一批次的所有光线
            for j, ray_end in enumerate(batch_rays):
                closest_hit = None
                closest_distance = float("inf")

                # 检查墙壁碰撞
                for wall in potential_walls:
                    intersection = self.get_line_rect_intersection(
                        self.player.pos, ray_end, wall
                    )
                    if intersection:
                        distance = self.player.pos.distance_to(intersection)
                        if distance < closest_distance:
                            closest_distance = distance
                            closest_hit = intersection

                # 检查门碰撞（按门板当前旋转后的实际形状）
                for door in potential_doors:
                    intersection = door.line_intersection(self.player.pos, ray_end)
                    if intersection:
                        distance = self.player.pos.distance_to(intersection)
                        if distance < closest_distance:
                            closest_distance = distance
                            closest_hit = intersection

                # 确定最终点位置（射线终点或碰撞点）
                if closest_hit:
                    final_point = closest_hit
                else:
                    final_point = ray_end

                # 转换为屏幕坐标并添加到可见点列表
                visible_points.append(self.camera.to_screen(final_point.x, final_point.y))

        # 绘制可见区域多边形
        if len(visible_points) >= 3:
            try:
                # 使用抗锯齿绘制，提高视觉质量
                pygame.draw.polygon(
                    vision_surface, (*VISION_GROUND, 120), visible_points
                )

                # 合并队友的视野（团队共享视野 - 所有队员都能看到其他队员的视野）
                teammates = []
                # 优先使用团队管理器
                if hasattr(self, "team_manager"):
                    team = self.team_manager.get_player_team(self.player.id)
                    if team:
                        for member_id in team.members:
                            if member_id != self.player.id:
                                teammates.append(member_id)
                        if (
                            team.leader_id
                            and team.leader_id != self.player.id
                            and team.leader_id not in teammates
                        ):
                            teammates.append(team.leader_id)
                # 回退：基于network_manager的team_id推断队友（客户端可能没有完整的team_manager状态）
                if (
                    not teammates
                    and hasattr(self, "network_manager")
                    and hasattr(self.network_manager, "players")
                ):
                    try:
                        local_team_id = None
                        # 本地玩家team_id可能存于自身或网络表
                        local_team_id = getattr(self.player, "team_id", None)
                        if local_team_id is None:
                            local_team_id = self.network_manager.players.get(
                                self.player.id, {}
                            ).get("team_id", None)
                        if local_team_id is not None:
                            for pid, pdata in self.network_manager.players.items():
                                if (
                                    pid != self.player.id
                                    and pdata.get("team_id", None) == local_team_id
                                ):
                                    teammates.append(pid)
                    except Exception:
                        pass

                if teammates:
                    # 为队友视野使用稍微不同的颜色（更亮一些，用于区分）
                    teammate_vision_color = (
                        min(255, VISION_GROUND[0] + 30),
                        min(255, VISION_GROUND[1] + 30),
                        min(255, VISION_GROUND[2] + 30),
                        100,
                    )

                    # 为每个队友创建单独的视野区域
                    for teammate_id in teammates:
                        # 检查队友是否在游戏世界中
                        teammate = None
                        # 如果队友是本地玩家（虽然理论上不应该发生，但为了安全起见）
                        if teammate_id == self.player.id:
                            teammate = self.player
                        else:
                            # 兼容不同来源的ID类型（int/str）
                            candidate_ids = []
                            try:
                                candidate_ids.append(int(teammate_id))
                            except Exception:
                                pass
                            # 同时尝试字符串形式
                            candidate_ids.append(str(teammate_id))

                            # 在其他玩家中查找
                            found = False
                            for cid in candidate_ids:
                                if cid in self.other_players:
                                    teammate = self.other_players[cid]
                                    found = True
                                    break

                            # 在AI玩家中查找
                            if not found:
                                for cid in candidate_ids:
                                    if cid in self.ai_players:
                                        teammate = self.ai_players[cid]
                                        found = True
                                        break

                            if not found:
                                # 尝试最后再直接使用原始ID（避免遗漏）
                                if teammate_id in self.other_players:
                                    teammate = self.other_players[teammate_id]
                                elif teammate_id in self.ai_players:
                                    teammate = self.ai_players[teammate_id]

                        # 队友不在游戏世界中，跳过
                        if teammate is None:
                            continue

                        if teammate and not teammate.is_dead:
                            # 为队友使用相同的射线检测方法创建真实视野
                            teammate_fov = 120  # 队友使用正常视野
                            teammate_half_fov = teammate_fov / 2

                            # 使用与本地玩家相同的光线数量
                            teammate_ray_count = 40 if teammate_fov > 60 else 20
                            teammate_angle_step = teammate_fov / teammate_ray_count

                            # 收集队友的可见点
                            teammate_screen_pos = self.camera.to_screen(
                                teammate.pos.x, teammate.pos.y
                            )
                            teammate_visible_points = [teammate_screen_pos]

                            # 预先筛选可能与队友视野相交的墙壁和门
                            teammate_potential_walls = []
                            for wall in self.game_map.walls:
                                wall_center_x = wall.x + wall.width / 2
                                wall_center_y = wall.y + wall.height / 2
                                distance = math.sqrt(
                                    (teammate.pos.x - wall_center_x) ** 2
                                    + (teammate.pos.y - wall_center_y) ** 2
                                )
                                if distance <= VISION_MAX_RANGE:
                                    teammate_potential_walls.append(wall)

                            teammate_potential_doors = []
                            for door in self.game_map.doors:
                                door_center_x = door.original_rect.centerx
                                door_center_y = door.original_rect.centery
                                distance = math.sqrt(
                                    (teammate.pos.x - door_center_x) ** 2
                                    + (teammate.pos.y - door_center_y) ** 2
                                )
                                reach = VISION_MAX_RANGE + max(
                                    door.panel_length, door.panel_thickness
                                )
                                if distance <= reach:
                                    teammate_potential_doors.append(door)

                            # 为队友进行射线检测
                            for i in range(teammate_ray_count + 1):
                                angle = (
                                    teammate.angle
                                    - teammate_half_fov
                                    + (teammate_angle_step * i)
                                )
                                angle_rad = math.radians(angle)
                                ray_end_x = (
                                    teammate.pos.x + math.cos(angle_rad) * VISION_MAX_RANGE
                                )
                                ray_end_y = (
                                    teammate.pos.y - math.sin(angle_rad) * VISION_MAX_RANGE
                                )
                                ray_end = pygame.Vector2(ray_end_x, ray_end_y)

                                closest_hit = None
                                closest_distance = float("inf")

                                # 检查墙壁碰撞
                                for wall in teammate_potential_walls:
                                    intersection = self.get_line_rect_intersection(
                                        teammate.pos, ray_end, wall
                                    )
                                    if intersection:
                                        distance = teammate.pos.distance_to(
                                            intersection
                                        )
                                        if distance < closest_distance:
                                            closest_distance = distance
                                            closest_hit = intersection

                                # 检查门碰撞（按门板当前旋转后的实际形状）
                                for door in teammate_potential_doors:
                                    intersection = door.line_intersection(
                                        teammate.pos, ray_end
                                    )
                                    if intersection:
                                        distance = teammate.pos.distance_to(
                                            intersection
                                        )
                                        if distance < closest_distance:
                                            closest_distance = distance
                                            closest_hit = intersection

                                # 确定最终点位置
                                if closest_hit:
                                    final_point = closest_hit
                                else:
                                    final_point = ray_end

                                # 转换为屏幕坐标
                                teammate_visible_points.append(
                                    self.camera.to_screen(final_point.x, final_point.y)
                                )

                            # 绘制队友的视野区域
                            if len(teammate_visible_points) >= 3:
                                try:
                                    pygame.draw.polygon(
                                        vision_surface,
                                        teammate_vision_color,
                                        teammate_visible_points,
                                    )
                                except Exception as e:
                                    # 如果绘制失败，忽略（可能是点坐标超出屏幕范围）
                                    pass

                self.screen.blit(vision_surface, (0, 0))
            except Exception as e:
                # 如果绘制失败，降级到简单的圆形
                if (
                    0 <= player_screen_pos[0] <= SCREEN_WIDTH
                    and 0 <= player_screen_pos[1] <= SCREEN_HEIGHT
                ):
                    pygame.draw.circle(
                        self.screen,
                        VISION_GROUND,
                        (int(player_screen_pos[0]), int(player_screen_pos[1])),
                        VISION_MAX_RANGE,
                        0,
                    )

    def get_line_rect_intersection(self, start, end, rect):
        """获取线段与矩形的最近交点（Rect.clipline 为 C 实现，比逐边求交快）"""
        clipped = rect.clipline((start[0], start[1]), (end[0], end[1]))
        if not clipped:
            return None

        point_a = pygame.Vector2(clipped[0])
        point_b = pygame.Vector2(clipped[1])
        start_vec = pygame.Vector2(start)
        if start_vec.distance_squared_to(point_a) <= start_vec.distance_squared_to(point_b):
            return point_a
        return point_b

    def get_line_line_intersection(self, p1, p2, p3, p4):
        """获取两条线段的交点"""
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 0.0001:
            return None

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

        if 0 <= t <= 1 and 0 <= u <= 1:
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            return pygame.Vector2(x, y)

        return None

    def render_full_ground(self):
        """绘制完整的灰色地面（不使用视角系统时）"""
        # 绘制一个大的灰色矩形作为地面（随相机旋转）
        size = ROOM_SIZE * 3
        ground_points = [(0, 0), (size, 0), (size, size), (0, size)]
        pygame.draw.polygon(
            self.screen, LIGHT_GRAY, self.camera.to_screen_polygon(ground_points)
        )

    def render_walls_and_doors(self):
        """绘制所有墙壁和门（始终显示）"""
        # 绘制所有墙壁（随相机旋转，需要按多边形绘制）
        for wall in self.game_map.walls:
            corners = (
                (wall.left, wall.top),
                (wall.right, wall.top),
                (wall.right, wall.bottom),
                (wall.left, wall.bottom),
            )
            pygame.draw.polygon(
                self.screen, GRAY, self.camera.to_screen_polygon(corners)
            )

        # 绘制所有门（门板绕铰链旋转）
        for door in self.game_map.doors:
            points = self.camera.to_screen_polygon(door.get_corners())
            pygame.draw.polygon(self.screen, door.get_color(False), points)
            pygame.draw.polygon(self.screen, DARK_DOOR_COLOR, points, 1)

    def render_ui(self):
        """绘制UI元素（使用新的 pygame-menu 管理器）"""
        # 更新并绘制 HUD
        self.hud_manager.update()
        self.hud_manager.draw()

        # 更新并绘制信息面板
        self.info_panel_manager.update()
        self.info_panel_manager.draw()

        # 更新并绘制控制提示
        self.control_hints_manager.update()
        self.control_hints_manager.draw()

        # 更新并绘制小地图
        self.minimap_manager.draw()

    def render_multiline_text(self, text, font, color, x, y, line_spacing=5):
        """渲染多行文本，返回渲染的行数和总高度"""
        lines = text.split("\n")
        total_height = 0
        max_width = 0
        rendered_line_count = 0

        for i, line in enumerate(lines):
            # 渲染所有行，包括空行（空行也占位置）
            line_surface = font.render(line, True, color)
            line_y = y + rendered_line_count * (font.get_height() + line_spacing)

            # 半透明背景
            bg_rect = pygame.Rect(
                x - 5,
                line_y - 2,
                line_surface.get_width() + 10,
                line_surface.get_height() + 4,
            )
            bg_surface = pygame.Surface(
                (bg_rect.width, bg_rect.height), pygame.SRCALPHA
            )
            bg_surface.fill((0, 0, 0, 128))
            self.screen.blit(bg_surface, bg_rect)

            # 文本
            self.screen.blit(line_surface, (x, line_y))

            max_width = max(max_width, line_surface.get_width())
            total_height = line_y + font.get_height() - y
            rendered_line_count += 1

        return len(lines), total_height, max_width

    def render_chat(self):
        """绘制聊天系统（使用新的 pygame-menu 管理器）"""
        # 绘制聊天输入框
        if self.chat_active:
            self.chat_menu_manager.draw()

        # 更新并绘制聊天历史
        self.chat_history_manager.update()
        self.chat_history_manager.draw()


    def detect_nearby_footsteps(self):
        """检测发出声音的玩家（静步0范围，正常移动根据速度调整范围0-400，开枪600范围）"""
        if self.player.is_dead:
            self.nearby_sound_players = []
            return

        nearby_players = []

        # 检查所有玩家（包括静步的）
        for player_id, player in self.other_players.items():
            if player.is_dead:
                continue

            distance = self.player.pos.distance_to(player.pos)

            # 调试输出：显示玩家状态
            if distance < 300:  # 只对附近的玩家输出调试信息
                dprint(
                    f"[声音检测] 玩家{player_id}: 距离{distance:.1f}, 射击={player.shooting}, 静步={getattr(player, 'is_walking', False)}, 发声={getattr(player, 'is_making_sound', False)}, 音量={getattr(player, 'sound_volume', 0.0)}"
                )

            # 根据玩家状态设置不同检测范围
            if player.shooting:
                detection_range = 600  # 开枪声音范围
                sound_type = "枪声"
            elif getattr(player, "is_walking", False):
                detection_range = 0  # 静步时完全无法被探测
                sound_type = "静步"
            elif getattr(player, "is_making_sound", False):
                # 根据声音音量调整检测范围 (0.0-1.0 对应 0-400范围)
                max_range = 400  # 最大检测范围
                sound_volume = getattr(player, "sound_volume", 0.0)
                detection_range = max_range * sound_volume
                sound_type = f"脚步声(音量{sound_volume:.1f})"
            else:
                continue  # 没有声音就不检测

            if distance <= detection_range:
                # 计算方向向量
                direction = player.pos - self.player.pos
                if direction.length() > 0:
                    direction = direction.normalize()

                # 计算声音强度 (距离越近越强)
                sound_intensity = (
                    1.0 - (distance / detection_range) if detection_range > 0 else 0
                )
                # 将声音强度与音量相乘
                if not player.shooting:  # 射击声音不受音量影响
                    sound_intensity *= getattr(player, "sound_volume", 0.0)

                nearby_players.append(
                    {
                        "player": player,
                        "distance": distance,
                        "direction": direction,
                        "is_shooting": player.shooting,  # 标记是否为开枪声音
                        "sound_intensity": sound_intensity,  # 声音强度
                        "screen_pos": self.camera.to_screen_vec(player.pos),
                    }
                )

                dprint(
                    f"[声音检测] 检测到玩家{player_id}的{sound_type}，距离{distance:.1f}，强度{sound_intensity:.2f}"
                )

        self.nearby_sound_players = nearby_players

    def world_dir_to_screen(self, direction):
        """把世界方向向量转换到旋转后的屏幕方向"""
        return self.camera.rotate_direction(direction)

    def render_footstep_indicators(self):
        """渲染方向指示器（箭头指向声音来源，根据声音强度调整透明度）"""
        if self.player.is_dead or not self.nearby_sound_players:
            return

        # 获取屏幕中心位置
        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2

        for sound_info in self.nearby_sound_players:
            player = sound_info["player"]
            direction = sound_info["direction"]
            is_shooting = sound_info["is_shooting"]
            sound_intensity = sound_info["sound_intensity"]

            # 根据声音类型选择颜色
            base_color = (
                (255, 100, 100) if is_shooting else (100, 255, 100)
            )  # 红色表示开枪，绿色表示移动

            # 根据声音强度调整颜色透明度
            alpha = int(
                min(255, max(50, 255 * sound_intensity))
            )  # 最小透明度为50，最大为255
            color = (base_color[0], base_color[1], base_color[2], alpha)

            # 计算箭头位置（屏幕边缘）
            arrow_distance = 80
            screen_direction = self.world_dir_to_screen(direction)
            arrow_x = center_x + screen_direction.x * arrow_distance
            arrow_y = center_y + screen_direction.y * arrow_distance

            # 复用预分配的指示器表面，每声音清空一次
            indicator_surface = getattr(self, "_indicator_surface", None)
            if indicator_surface is None or indicator_surface.get_size() != (
                SCREEN_WIDTH,
                SCREEN_HEIGHT,
            ):
                indicator_surface = pygame.Surface(
                    (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA
                )
                self._indicator_surface = indicator_surface
            indicator_surface.fill((0, 0, 0, 0))

            # 根据声音强度调整箭头大小
            arrow_size = 10 + int(5 * sound_intensity)  # 10-15之间变化
            angle = math.atan2(screen_direction.y, screen_direction.x)

            # 箭头顶点
            end_x = arrow_x + math.cos(angle) * arrow_size
            end_y = arrow_y + math.sin(angle) * arrow_size

            # 箭头两侧
            left_x = arrow_x + math.cos(angle + 2.5) * (arrow_size * 0.7)
            left_y = arrow_y + math.sin(angle + 2.5) * (arrow_size * 0.7)
            right_x = arrow_x + math.cos(angle - 2.5) * (arrow_size * 0.7)
            right_y = arrow_y + math.sin(angle - 2.5) * (arrow_size * 0.7)

            # 绘制箭头线条
            pygame.draw.line(
                indicator_surface,
                color,
                (center_x, center_y),
                (end_x, end_y),
                2 + int(sound_intensity * 2),
            )  # 线宽根据强度变化
            pygame.draw.line(
                indicator_surface,
                color,
                (end_x, end_y),
                (left_x, left_y),
                2 + int(sound_intensity * 2),
            )
            pygame.draw.line(
                indicator_surface,
                color,
                (end_x, end_y),
                (right_x, right_y),
                2 + int(sound_intensity * 2),
            )

            # 绘制距离圈，大小根据声音强度变化
            circle_radius = int(30 + 20 * sound_intensity)  # 30-50之间变化
            pygame.draw.circle(
                indicator_surface, color, (center_x, center_y), circle_radius, 1
            )

            # 添加声音类型标签
            label = "开枪" if is_shooting else "移动"
            # 根据声音强度调整标签大小
            label_font = small_font if sound_intensity < 0.7 else font
            label_surface = label_font.render(label, True, color)
            label_x = arrow_x - label_surface.get_width() // 2
            label_y = arrow_y + 20

            # 确保标签在屏幕内
            label_x = max(
                10, min(SCREEN_WIDTH - label_surface.get_width() - 10, label_x)
            )
            label_y = max(
                10, min(SCREEN_HEIGHT - label_surface.get_height() - 10, label_y)
            )

            indicator_surface.blit(label_surface, (label_x, label_y))

            self.screen.blit(indicator_surface, (0, 0))

    def run(self):
        """
        游戏主循环

        根据当前游戏状态执行相应的逻辑：
        - MENU: 显示主菜单，处理服务器扫描和连接
        - CONNECTING: 显示连接中界面
        - ERROR: 显示错误信息
        - PLAYING: 运行游戏主循环（事件处理、更新、渲染）

        游戏循环会一直运行直到 self.running 被设置为 False。
        退出时会自动清理网络连接并关闭 pygame。

        Note:
            这是游戏的入口方法，应该在创建 Game 实例后立即调用。
        """
        while self.running:
            if self.state == "MENU":
                self.show_menu()
            elif self.state == "CONNECTING":
                self.show_connecting_screen()
            elif self.state == "ERROR":
                self.show_error_screen()
            elif self.state == "PLAYING":
                dt = min(self.clock.tick(FPS) / 1000.0, 1 / 20)
                self.handle_events()
                self.update(dt)

                # 检查是否需要切换到错误状态
                if self.state == "ERROR":
                    continue

                self.render()

        if self.network_manager:
            self.network_manager.stop()
        pygame.quit()


if __name__ == "__main__":
    game = Game()
    game.run()
