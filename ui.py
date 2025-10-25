"""
UI模块 - 处理所有用户界面相关功能
包括字体加载、菜单绘制、HUD显示、聊天界面等
"""

import pygame
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
    if system == 'windows':
        font_candidates = [
            'Microsoft YaHei',
            'SimHei',
            'SimSun',
            'Arial Unicode MS',
            'DejaVu Sans',
            'Arial'
        ]
    elif system == 'linux':
        # Linux/Ubuntu字体优先级
        font_candidates = [
            'Noto Sans CJK SC',      # Ubuntu默认中文字体
            'Noto Sans CJK TC',      # 繁体中文
            'WenQuanYi Micro Hei',   # 文泉驿微米黑
            'WenQuanYi Zen Hei',     # 文泉驿正黑
            'Droid Sans Fallback',   # Android字体
            'AR PL UMing CN',        # 文鼎明体
            'AR PL UKai CN',         # 文鼎楷体
            'DejaVu Sans',           # 通用字体
            'Liberation Sans',       # LibreOffice字体
            'FreeSans'               # GNU字体
        ]
    elif system == 'darwin':  # macOS
        font_candidates = [
            'PingFang SC',
            'Hiragino Sans GB',
            'STHeiti',
            'Arial Unicode MS',
            'Helvetica',
            'Arial'
        ]
    else:
        # 其他系统使用通用字体
        font_candidates = [
            'DejaVu Sans',
            'Liberation Sans',
            'FreeSans',
            'Arial'
        ]
    
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
                        print(f"✅ [{i:2d}] {font_name} - 加载成功，中文渲染正常")
                        
                        return {
                            'font': pygame.font.SysFont(font_name, 20),
                            'small_font': pygame.font.SysFont(font_name, 16),
                            'large_font': pygame.font.SysFont(font_name, 28),
                            'title_font': pygame.font.SysFont(font_name, 40),
                            'font_name': font_name
                        }
                    else:
                        print(f"❌ [{i:2d}] {font_name} - 中文渲染失败")
                        
                except Exception as render_error:
                    print(f"❌ [{i:2d}] {font_name} - 中文渲染异常: {render_error}")
                    continue
            else:
                print(f"❌ [{i:2d}] {font_name} - 字体对象创建失败")
                
        except Exception as font_error:
            print(f"❌ [{i:2d}] {font_name} - 字体加载异常: {font_error}")
            continue
    
    # 如果所有字体都失败，使用默认字体
    print("⚠️  警告: 无法加载任何系统字体，使用pygame默认字体")
    print("建议安装中文字体包以获得更好的显示效果")
    
    if system == 'linux':
        print("Ubuntu/Linux用户可以运行: sudo apt install fonts-noto-cjk fonts-wqy-microhei")
    
    return {
        'font': pygame.font.Font(None, 20),
        'small_font': pygame.font.Font(None, 16),
        'large_font': pygame.font.Font(None, 28),
        'title_font': pygame.font.Font(None, 40),
        'font_name': 'Default'
    }

def initialize_fonts():
    """初始化字体并设置全局变量"""
    global fonts, font, small_font, large_font, title_font
    
    fonts = load_fonts()
    font = fonts['font']
    small_font = fonts['small_font']
    large_font = fonts['large_font']
    title_font = fonts['title_font']
    
    # 显示当前使用的字体信息
    current_font_name = fonts.get('font_name', 'Unknown')
    print(f"当前使用字体: {current_font_name}")
    
    # 如果使用默认字体，给出提示
    if current_font_name == 'Default':
        print("提示: 游戏将使用默认字体，中文显示可能不完整")
    
    return fonts

def get_fonts():
    """获取已加载的字体字典"""
    return {
        'font': font,
        'small_font': small_font,
        'large_font': large_font,
        'title_font': title_font,
        'fonts': fonts
    }


def draw_menu(screen, menu_state):
    """
    绘制主菜单
    
    参数:
        screen: pygame屏幕对象
        menu_state: 包含菜单状态的字典，包括:
            - selected_option: 当前选中的选项
            - input_text: IP输入框文本
            - input_active: IP输入框是否激活
            - server_name_input: 服务器名称输入
            - player_name_input: 玩家名称输入
            - server_name_active: 服务器名称输入框是否激活
            - player_name_active: 玩家名称输入框是否激活
            - show_server_name_input: 是否显示服务器名称输入框
            - show_player_name_input: 是否显示玩家名称输入框
            - scanning_servers: 是否正在扫描服务器
            - found_servers: 找到的服务器列表
            - button_rects: 按钮矩形字典
    """
    # 清空屏幕
    screen.fill(BLACK)
    
    # 标题
    title = title_font.render("多人射击游戏", True, WHITE)
    screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 50))
    
    # 副标题
    subtitle = font.render("武器切换 + 瞄准系统", True, LIGHT_BLUE)
    screen.blit(subtitle, (SCREEN_WIDTH//2 - subtitle.get_width()//2, 100))
    
    # 左侧控制面板
    panel_title = large_font.render("游戏控制", True, WHITE)
    screen.blit(panel_title, (50, 120))
    
    # 获取按钮矩形
    button_create = menu_state['button_rects']['button_create']
    button_refresh = menu_state['button_rects']['button_refresh']
    input_box = menu_state['button_rects']['input_box']
    button_connect = menu_state['button_rects']['button_connect']
    server_name_box = menu_state['button_rects']['server_name_box']
    server_name_button = menu_state['button_rects']['server_name_button']
    player_name_box = menu_state['button_rects']['player_name_box']
    player_name_button = menu_state['button_rects']['player_name_button']
    
    # 创建服务器按钮
    create_color = GREEN if menu_state['selected_option'] == 0 else DARK_BLUE
    pygame.draw.rect(screen, create_color, button_create)
    pygame.draw.rect(screen, WHITE, button_create, 3)
    create_text = font.render("创建服务器", True, WHITE)
    screen.blit(create_text, (button_create.x + (button_create.width - create_text.get_width())//2,
                             button_create.y + (button_create.height - create_text.get_height())//2))
    
    # 刷新服务器按钮
    refresh_color = GREEN if menu_state['selected_option'] == 2 else DARK_BLUE
    pygame.draw.rect(screen, refresh_color, button_refresh)
    pygame.draw.rect(screen, WHITE, button_refresh, 3)
    refresh_text = font.render("刷新服务器列表", True, WHITE)
    screen.blit(refresh_text, (button_refresh.x + (button_refresh.width - refresh_text.get_width())//2,
                              button_refresh.y + (button_refresh.height - refresh_text.get_height())//2))
    
    # IP输入框
    input_color = YELLOW if menu_state['input_active'] else WHITE
    pygame.draw.rect(screen, BLACK, input_box)
    pygame.draw.rect(screen, input_color, input_box, 2)
    
    ip_label = font.render("手动输入IP:", True, WHITE)
    screen.blit(ip_label, (input_box.x, input_box.y - 30))
    
    input_surface = font.render(menu_state['input_text'], True, WHITE)
    screen.blit(input_surface, (input_box.x + 10, input_box.y + 7))
    
    # 光标
    if menu_state['input_active'] and pygame.time.get_ticks() % 1000 < 500:
        cursor_x = input_box.x + 10 + input_surface.get_width()
        pygame.draw.line(screen, WHITE, 
                       (cursor_x, input_box.y + 5), 
                       (cursor_x, input_box.y + input_box.height - 5), 2)
    
    # 手动连接按钮
    connect_enabled = len(menu_state['input_text'].strip()) > 0
    connect_color = GREEN if connect_enabled else GRAY
    pygame.draw.rect(screen, connect_color, button_connect)
    pygame.draw.rect(screen, WHITE, button_connect, 2)
    connect_text = font.render("手动连接", True, WHITE if connect_enabled else DARK_GRAY)
    screen.blit(connect_text, (button_connect.x + (button_connect.width - connect_text.get_width())//2,
                              button_connect.y + (button_connect.height - connect_text.get_height())//2))
    
    # 服务器命名输入框
    if menu_state['show_server_name_input'] and not menu_state['show_player_name_input']:
        server_name_color = YELLOW if menu_state['server_name_active'] else WHITE
        pygame.draw.rect(screen, BLACK, server_name_box)
        pygame.draw.rect(screen, server_name_color, server_name_box, 2)
        
        server_name_label = font.render("服务器名称:", True, WHITE)
        screen.blit(server_name_label, (server_name_box.x, server_name_box.y - 30))
        
        server_name_surface = font.render(menu_state['server_name_input'], True, WHITE)
        screen.blit(server_name_surface, (server_name_box.x + 10, server_name_box.y + 7))
        
        # 光标
        if menu_state['server_name_active'] and pygame.time.get_ticks() % 1000 < 500:
            cursor_x = server_name_box.x + 10 + server_name_surface.get_width()
            pygame.draw.line(screen, WHITE, 
                           (cursor_x, server_name_box.y + 5), 
                           (cursor_x, server_name_box.y + server_name_box.height - 5), 2)
        
        # 确认按钮
        server_name_enabled = len(menu_state['server_name_input'].strip()) > 0
        server_name_btn_color = GREEN if server_name_enabled else GRAY
        pygame.draw.rect(screen, server_name_btn_color, server_name_button)
        pygame.draw.rect(screen, WHITE, server_name_button, 2)
        server_name_btn_text = font.render("确认创建", True, WHITE if server_name_enabled else DARK_GRAY)
        screen.blit(server_name_btn_text, (server_name_button.x + (server_name_button.width - server_name_btn_text.get_width())//2,
                                          server_name_button.y + (server_name_button.height - server_name_btn_text.get_height())//2))
    
    # 玩家命名输入框
    if menu_state['show_player_name_input']:
        player_name_color = YELLOW if menu_state['player_name_active'] else WHITE
        pygame.draw.rect(screen, BLACK, player_name_box)
        pygame.draw.rect(screen, player_name_color, player_name_box, 2)
        
        player_name_label = font.render("玩家名称:", True, WHITE)
        screen.blit(player_name_label, (player_name_box.x, player_name_box.y - 30))
        
        player_name_surface = font.render(menu_state['player_name_input'], True, WHITE)
        screen.blit(player_name_surface, (player_name_box.x + 10, player_name_box.y + 7))
        
        # 光标
        if menu_state['player_name_active'] and pygame.time.get_ticks() % 1000 < 500:
            cursor_x = player_name_box.x + 10 + player_name_surface.get_width()
            pygame.draw.line(screen, WHITE, 
                           (cursor_x, player_name_box.y + 5), 
                           (cursor_x, player_name_box.y + player_name_box.height - 5), 2)
        
        # 确认按钮
        player_name_enabled = len(menu_state['player_name_input'].strip()) > 0
        player_name_btn_color = GREEN if player_name_enabled else GRAY
        pygame.draw.rect(screen, player_name_btn_color, player_name_button)
        pygame.draw.rect(screen, WHITE, player_name_button, 2)
        player_name_btn_text = font.render("确认连接", True, WHITE if player_name_enabled else DARK_GRAY)
        screen.blit(player_name_btn_text, (player_name_button.x + (player_name_button.width - player_name_btn_text.get_width())//2,
                                          player_name_button.y + (player_name_button.height - player_name_btn_text.get_height())//2))
    
    # 右侧服务器列表
    server_list_x = menu_state['server_list_x']
    server_list_y = menu_state['server_list_y']
    server_list_width = menu_state['server_list_width']
    server_item_height = menu_state['server_item_height']
    
    list_title = large_font.render("局域网服务器", True, WHITE)
    screen.blit(list_title, (server_list_x, 120))
    
    if menu_state['scanning_servers']:
        # 显示扫描状态
        scan_text = font.render("正在扫描局域网服务器...", True, YELLOW)
        screen.blit(scan_text, (server_list_x, server_list_y))
        
        # 动画点
        dots = "." * ((pygame.time.get_ticks() // 500) % 4)
        dots_text = font.render(dots, True, YELLOW)
        screen.blit(dots_text, (server_list_x + scan_text.get_width() + 10, server_list_y))
        
    elif menu_state['found_servers']:
        # 显示找到的服务器
        for i, server in enumerate(menu_state['found_servers'][:5]):  # 最多显示5个服务器
            server_rect = pygame.Rect(server_list_x, server_list_y + i * (server_item_height + 10), 
                                    server_list_width, server_item_height)
            
            # 服务器背景
            pygame.draw.rect(screen, DARK_BLUE, server_rect)
            pygame.draw.rect(screen, WHITE, server_rect, 2)
            
            # 服务器信息
            server_name = font.render(server.get('name', '未知服务器'), True, WHITE)
            server_ip = small_font.render(f"IP: {server['ip']}", True, LIGHT_BLUE)
            player_info = small_font.render(f"玩家: {server.get('players', 0)}/{server.get('max_players', '?')}", True, GREEN)
            
            screen.blit(server_name, (server_rect.x + 10, server_rect.y + 5))
            screen.blit(server_ip, (server_rect.x + 10, server_rect.y + 25))
            screen.blit(player_info, (server_rect.x + 10, server_rect.y + 40))
            
            # 连接提示
            connect_hint = small_font.render("点击连接", True, YELLOW)
            screen.blit(connect_hint, (server_rect.x + server_rect.width - connect_hint.get_width() - 10, 
                                      server_rect.y + server_rect.height//2 - connect_hint.get_height()//2))
    else:
        # 没有找到服务器
        no_server_text = font.render("未找到局域网服务器", True, GRAY)
        screen.blit(no_server_text, (server_list_x, server_list_y))
        hint_text = small_font.render("点击\"刷新服务器列表\"重新扫描", True, GRAY)
        screen.blit(hint_text, (server_list_x, server_list_y + 30))


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
    player = hud_state['player']
    
    # 生命值
    health_text = f"生命: {player.health}/{player.max_health}"
    screen.blit(font.render(health_text, True, WHITE), (20, 20))
    
    # 武器类型
    weapon_text = f"武器: {'近战' if player.weapon_type == 'melee' else '枪械'}"
    screen.blit(font.render(weapon_text, True, YELLOW if player.weapon_type == 'melee' else GREEN), (20, 50))
    
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
            remaining_cooldown = MELEE_COOLDOWN - (time.time() - player.melee_weapon.last_attack_time)
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
        screen.blit(death_surface, (SCREEN_WIDTH//2 - death_surface.get_width()//2, SCREEN_HEIGHT//2))
    
    # 玩家数量
    player_count = hud_state['player_count']
    count_text = f"玩家数: {player_count}"
    screen.blit(font.render(count_text, True, WHITE), (SCREEN_WIDTH - 150, 20))
    
    # 显示玩家ID和回收池信息（调试模式）
    if hud_state['debug_mode'] and hud_state['network_manager'].is_server:
        recycled_text = f"回收池: {sorted(hud_state['network_manager'].recycled_ids) if hud_state['network_manager'].recycled_ids else '空'}"
        screen.blit(font.render(recycled_text, True, YELLOW), (SCREEN_WIDTH - 250, 50))
    
    # 控制提示
    if not player.is_dead and not player.is_respawning:
        interact_text = "按E键开/关门"
        screen.blit(font.render(interact_text, True, WHITE),
                     (SCREEN_WIDTH - 150, SCREEN_HEIGHT - 120))
        
        # 武器控制提示
        if player.weapon_type == "gun":
            weapon_text = "左键射击 右键瞄准"
        else:
            weapon_text = "左键近战攻击"
        screen.blit(font.render(weapon_text, True, WHITE),
                     (SCREEN_WIDTH - 200, SCREEN_HEIGHT - 90))
        
        # 切换武器提示
        switch_text = "按3切换武器"
        screen.blit(font.render(switch_text, True, WHITE),
                     (SCREEN_WIDTH - 150, SCREEN_HEIGHT - 60))
    
    # 聊天提示
    chat_hint = "按Y键聊天"
    screen.blit(font.render(chat_hint, True, WHITE),
                 (SCREEN_WIDTH - 150, SCREEN_HEIGHT - 30))
    
    # 显示伤害信息
    damage_text = f"射击伤害: {BULLET_DAMAGE} 近战伤害: {MELEE_DAMAGE}"
    screen.blit(font.render(damage_text, True, WHITE), (20, 140))
    
    # 视角相关信息
    current_fov = 30 if player.is_aiming else 120
    vision_text = f"视角: {current_fov}° {'(瞄准)' if player.is_aiming else '(正常)'})"
    screen.blit(font.render(vision_text, True, YELLOW), (20, 170))
    
    # 脚步声提示
    if hud_state['nearby_sound_players']:
        footstep_text = f"附近脚步声: {len(hud_state['nearby_sound_players'])}个玩家"
        screen.blit(font.render(footstep_text, True, RED), (20, 200))
    
    # 调试信息
    if hud_state['debug_mode']:
        debug_y = 200
        screen.blit(font.render(f"玩家ID: {player.id}", True, YELLOW), (20, debug_y))
        debug_y += 25
        screen.blit(font.render(f"服务器: {'是' if hud_state['network_manager'].is_server else '否'}", True, YELLOW), (20, debug_y))
        debug_y += 25
        screen.blit(font.render(f"武器类型: {player.weapon_type}", True, YELLOW), (20, debug_y))
        debug_y += 25
        screen.blit(font.render(f"瞄准状态: {'是' if player.is_aiming else '否'}", True, YELLOW), (20, debug_y))
        debug_y += 25
        screen.blit(font.render(f"瞄准偏移: ({player.aim_offset.x:.1f}, {player.aim_offset.y:.1f})", True, YELLOW), (20, debug_y))
        debug_y += 25
        screen.blit(font.render(f"门状态: {len(hud_state['network_manager'].doors)}个已同步", True, YELLOW), (20, debug_y))
        debug_y += 25
        bullets_count = hud_state.get('bullets_count', 0)
        network_bullets_count = len(hud_state['network_manager'].get_bullets())
        screen.blit(font.render(f"子弹数: {bullets_count} 网络: {network_bullets_count}", True, YELLOW), (20, debug_y))
        debug_y += 25
        screen.blit(font.render(f"按F3切换调试模式 F4切换视角显示", True, YELLOW), (20, debug_y))
        debug_y += 25
        show_vision = hud_state.get('show_vision', False)
        screen.blit(font.render(f"视角系统: {'开' if show_vision else '关'}", True, YELLOW), (20, debug_y))
        debug_y += 25
        screen.blit(font.render(f"脚步声: {len(hud_state['nearby_sound_players'])}个玩家", True, YELLOW), (20, debug_y))


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
    if chat_state['chat_active']:
        chat_box_height = 35
        chat_box = pygame.Rect(10, SCREEN_HEIGHT - chat_box_height - 10, SCREEN_WIDTH - 20, chat_box_height)
        pygame.draw.rect(screen, BLACK, chat_box)
        pygame.draw.rect(screen, WHITE, chat_box, 2)
        
        # 聊天提示和输入文字
        chat_prompt = "聊天: "
        prompt_surface = font.render(chat_prompt, True, WHITE)
        screen.blit(prompt_surface, (chat_box.x + 5, chat_box.y + 5))
        
        # 输入文字
        input_surface = font.render(chat_state['chat_input'], True, WHITE)
        input_x = chat_box.x + 5 + prompt_surface.get_width()
        screen.blit(input_surface, (input_x, chat_box.y + 5))
        
        # 光标
        if chat_state['chat_cursor_blink']:
            cursor_x = input_x + input_surface.get_width()
            cursor_y = chat_box.y + 5
            pygame.draw.line(screen, WHITE, 
                           (cursor_x, cursor_y), 
                           (cursor_x, cursor_y + font.get_height()), 2)
    
    # 聊天消息历史
    recent_messages = chat_state['recent_messages']
    if recent_messages:
        # 定义显示区域
        chat_y_start = SCREEN_HEIGHT - 60 - (chat_state['chat_active'] * 45)  # 底部位置
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
            if '\n' in message_text:
                lines = message_text.split('\n')
            else:
                lines = [message_text]
            
            # 计算高度
            line_height = small_font.get_height() + 5
            total_height = len(lines) * line_height
            
            message_lines.append((msg, lines, total_height))
        
        # 第二步：应用滚动偏移，计算要显示的消息范围
        # 从最新的消息开始，向上累积高度
        scroll_pixels = chat_state['chat_scroll_offset'] * (small_font.get_height() + 5)  # 将行偏移转换为像素偏移
        
        # 限制滚动偏移量
        total_content_height = sum(h for _, _, h in message_lines) + len(message_lines) * 10  # 加上消息间距
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
                        bg_rect = pygame.Rect(10, line_y - 2, line_surface.get_width() + 10, line_surface.get_height() + 4)
                        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
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
                    bg_rect = pygame.Rect(10, line_y - 2, line_surface.get_width() + 10, line_surface.get_height() + 4)
                    bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
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
                screen.blit(hint_surface, (SCREEN_WIDTH - hint_surface.get_width() - 20, chat_y_start + 10))
            
            if scroll_pixels < max_scroll:
                hint_text = "↑ 更早消息 (方向键)"
                hint_surface = small_font.render(hint_text, True, YELLOW)
                screen.blit(hint_surface, (SCREEN_WIDTH - hint_surface.get_width() - 20, chat_y_min - 20))
