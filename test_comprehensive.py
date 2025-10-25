"""
综合测试脚本
用于验证代码重构后的所有功能
"""

import sys
import time
import pygame
from pygame.locals import *

# 导入所有模块以验证导入正确性
try:
    from constants import *
    from player import Player
    from map import Map, Door
    from network import NetworkManager, ChatMessage, generate_default_player_name
    from weapons import MeleeWeapon, Bullet, Ray
    from ai_player import AIPlayer
    from utils import *
    import ui
    print("✓ 所有模块导入成功")
except Exception as e:
    print(f"✗ 模块导入失败: {e}")
    sys.exit(1)

# 初始化pygame
pygame.init()
pygame.font.init()

# 测试结果记录
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def log_test(test_name, passed, message=""):
    """记录测试结果"""
    if passed:
        test_results["passed"].append(test_name)
        print(f"✓ {test_name}")
    else:
        test_results["failed"].append((test_name, message))
        print(f"✗ {test_name}: {message}")

def log_warning(test_name, message):
    """记录警告"""
    test_results["warnings"].append((test_name, message))
    print(f"⚠ {test_name}: {message}")

# ============================================================================
# 测试 1: UI 模块测试
# ============================================================================
def test_ui_module():
    """测试UI模块功能"""
    print("\n=== 测试 UI 模块 ===")
    
    try:
        # 测试字体初始化
        ui.initialize_fonts()
        log_test("UI字体初始化", 
                 hasattr(ui, 'font') and ui.font is not None)
        
        # 测试字体属性
        log_test("UI字体属性存在", 
                 all(hasattr(ui, attr) for attr in ['font', 'small_font', 'large_font', 'title_font']))
        
    except Exception as e:
        log_test("UI模块测试", False, str(e))

# ============================================================================
# 测试 2: Utils 模块测试
# ============================================================================
def test_utils_module():
    """测试工具函数模块"""
    print("\n=== 测试 Utils 模块 ===")
    
    try:
        # 测试角度标准化
        angle = normalize_angle(370)
        log_test("角度标准化函数", -180 <= angle <= 180)
        
        # 测试角度差值计算
        diff = angle_difference(10, 350)
        log_test("角度差值计算", abs(diff) <= 180)
        
        # 测试视野检测 - 使用pygame.Vector2
        in_fov = is_in_field_of_view(pygame.Vector2(0, 0), 0, pygame.Vector2(100, 0), 90)
        log_test("视野检测函数", in_fov == True)
        
        # 测试线段矩形相交
        rect = pygame.Rect(50, 50, 100, 100)
        intersects = line_intersects_rect(pygame.Vector2(0, 75), pygame.Vector2(200, 75), rect)
        log_test("线段矩形相交检测", intersects == True)
        
    except Exception as e:
        log_test("Utils模块测试", False, str(e))

# ============================================================================
# 测试 3: Weapons 模块测试
# ============================================================================
def test_weapons_module():
    """测试武器模块"""
    print("\n=== 测试 Weapons 模块 ===")
    
    try:
        # 测试近战武器创建 - MeleeWeapon takes owner_id, not name
        melee = MeleeWeapon("player1")
        log_test("近战武器创建", melee.owner_id == "player1")
        log_test("近战武器伤害属性", melee.damage == MELEE_DAMAGE)
        
        # 测试子弹创建 - Bullet uses pos and dir
        bullet_data = {
            'id': 1,
            'pos': (100, 100),
            'dir': (1, 0),
            'owner': 'test',
            'time': time.time()
        }
        bullet = Bullet(bullet_data)
        log_test("子弹对象创建", bullet.pos.x == 100 and bullet.pos.y == 100)
        
        # 测试子弹更新 - requires game_map and players
        game_map = Map()
        players = {}
        old_x = bullet.pos.x
        bullet.update(0.1, game_map, players)
        log_test("子弹位置更新", bullet.pos.x != old_x)
        
    except Exception as e:
        log_test("Weapons模块测试", False, str(e))

# ============================================================================
# 测试 4: Player 模块测试
# ============================================================================
def test_player_module():
    """测试玩家模块"""
    print("\n=== 测试 Player 模块 ===")
    
    try:
        # 测试玩家创建
        player = Player("test_player", 100, 100, is_local=True, name="TestPlayer")
        log_test("玩家对象创建", player.id == "test_player")
        
        # 测试玩家属性 - use max_health instead of PLAYER_MAX_HEALTH
        log_test("玩家初始生命值", player.health == player.max_health)
        log_test("玩家初始位置", player.pos.x == 100 and player.pos.y == 100)
        log_test("玩家名称设置", player.name == "TestPlayer")
        
        # 测试玩家受伤
        initial_health = player.health
        player.take_damage(20)
        log_test("玩家受伤功能", player.health == initial_health - 20)
        
        # 测试武器切换 (before death)
        initial_weapon = player.weapon_type
        result = player.switch_weapon()
        log_test("武器切换功能", result == True and player.weapon_type != initial_weapon)
        
        # 测试玩家死亡 - wait for damage cooldown
        time.sleep(0.6)  # Wait for damage cooldown
        result = player.take_damage(1000)
        log_test("玩家死亡状态", player.is_dead == True and player.health == 0 and result == True)
        
        # 测试玩家复活 - respawn() takes optional network_manager
        player.respawn()
        log_test("玩家复活功能", 
                 player.health == player.max_health and not player.is_dead)
        
    except Exception as e:
        log_test("Player模块测试", False, str(e))

# ============================================================================
# 测试 5: Map 模块测试
# ============================================================================
def test_map_module():
    """测试地图模块"""
    print("\n=== 测试 Map 模块 ===")
    
    try:
        # 测试地图创建 - Map auto-generates on __init__
        game_map = Map()
        log_test("地图对象创建", game_map is not None)
        
        # Map already initialized in __init__ via generate_map()
        log_test("地图房间生成", len(game_map.rooms) > 0)
        log_test("地图墙壁生成", len(game_map.walls) > 0)
        log_test("地图门生成", len(game_map.doors) > 0)
        
        # 测试随机出生点
        spawn_pos = game_map.get_random_spawn_pos()
        log_test("随机出生点生成", 
                 spawn_pos is not None and len(spawn_pos) == 2)
        
        # 测试门对象
        if len(game_map.doors) > 0:
            door = game_map.doors[0]
            log_test("门对象属性", 
                     hasattr(door, 'is_open') and hasattr(door, 'rect'))
            
            # 测试门的交互
            door.open()
            log_test("门打开功能", door.is_opening == True or door.is_open == True)
            
            door.close()
            log_test("门关闭功能", door.is_closing == True or not door.is_open)
        
    except Exception as e:
        log_test("Map模块测试", False, str(e))

# ============================================================================
# 测试 6: Network 模块测试
# ============================================================================
def test_network_module():
    """测试网络模块"""
    print("\n=== 测试 Network 模块 ===")
    
    try:
        # 测试默认玩家名生成 - format is "玩家" + 3 digits
        player_name = generate_default_player_name()
        log_test("默认玩家名生成", 
                 player_name.startswith("玩家") and len(player_name) == 5)
        
        # 测试聊天消息创建
        chat_msg = ChatMessage("player1", "TestPlayer", "Hello World")
        log_test("聊天消息创建", 
                 chat_msg.player_id == "player1" and chat_msg.message == "Hello World")
        log_test("聊天消息玩家名", chat_msg.player_name == "TestPlayer")
        
        # 测试网络管理器创建
        network_mgr = NetworkManager()
        log_test("网络管理器创建", network_mgr is not None)
        log_test("网络管理器属性", hasattr(network_mgr, 'is_server'))
        
    except Exception as e:
        log_test("Network模块测试", False, str(e))

# ============================================================================
# 测试 7: AI Player 模块测试
# ============================================================================
def test_ai_player_module():
    """测试AI玩家模块"""
    print("\n=== 测试 AI Player 模块 ===")
    
    try:
        # 创建测试地图 - Map auto-initializes
        game_map = Map()
        
        # 测试AI玩家创建
        ai_player = AIPlayer("ai_test", 100, 100, game_map)
        log_test("AI玩家对象创建", ai_player.id == "ai_test")
        
        # 测试AI玩家属性 - uses pos not x
        log_test("AI玩家继承Player属性", 
                 hasattr(ai_player, 'health') and hasattr(ai_player, 'pos'))
        
    except Exception as e:
        log_test("AI Player模块测试", False, str(e))

# ============================================================================
# 测试 8: 集成测试 - 模拟游戏场景
# ============================================================================
def test_game_integration():
    """集成测试 - 模拟完整游戏场景"""
    print("\n=== 集成测试 ===")
    
    try:
        # 创建游戏环境 - Map auto-initializes
        game_map = Map()
        
        # 创建玩家
        spawn_pos = game_map.get_random_spawn_pos()
        player1 = Player("player1", spawn_pos[0], spawn_pos[1], 
                        is_local=True, name="Player1")
        player2 = Player("player2", spawn_pos[0] + 100, spawn_pos[1], 
                        is_local=False, name="Player2")
        
        # 创建AI玩家
        ai = AIPlayer("ai1", spawn_pos[0] + 200, spawn_pos[1], game_map)
        
        players = [player1, player2, ai]
        
        log_test("游戏环境创建", 
                 game_map is not None and len(players) == 3)
        
        # 模拟游戏更新循环
        dt = 0.016  # 约60 FPS
        bullets = {}
        for i in range(10):
            # Player.update(dt, game_map, bullets, network_manager, all_players)
            player1.update(dt, game_map, bullets)
            player2.update(dt, game_map, bullets)
            # Note: AIPlayer.update expects network-formatted player data, 
            # so we skip it in this unit test
            game_map.update(dt)
        
        log_test("游戏循环模拟", True)
        
        # 测试玩家间交互
        initial_health = player1.health
        player1.take_damage(10)
        log_test("玩家间伤害系统", player1.health < initial_health)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        log_test("集成测试", False, str(e))

# ============================================================================
# 主测试函数
# ============================================================================
def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始综合测试")
    print("=" * 60)
    
    test_ui_module()
    test_utils_module()
    test_weapons_module()
    test_player_module()
    test_map_module()
    test_network_module()
    test_ai_player_module()
    test_game_integration()
    
    # 打印测试总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"通过: {len(test_results['passed'])} 项")
    print(f"失败: {len(test_results['failed'])} 项")
    print(f"警告: {len(test_results['warnings'])} 项")
    
    if test_results['failed']:
        print("\n失败的测试:")
        for test_name, message in test_results['failed']:
            print(f"  - {test_name}: {message}")
    
    if test_results['warnings']:
        print("\n警告:")
        for test_name, message in test_results['warnings']:
            print(f"  - {test_name}: {message}")
    
    print("\n" + "=" * 60)
    
    # 返回测试是否全部通过
    return len(test_results['failed']) == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
