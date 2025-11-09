"""
增强版AI玩家类
集成行为树系统和个性化特征
"""

import pygame
import math
import random
import time
from constants import *
from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder

# 导入行为树和个性化系统
from ai_behavior_tree import BehaviorTree
from ai_personality import AIPersonality, AIPersonalityTraits


class EnhancedAIPlayer:
    """增强版AI玩家 - 使用行为树和个性化特征"""
    
    def __init__(self, player_id, x, y, difficulty='normal', personality=None):
        self.id = player_id
        self.pos = pygame.Vector2(x, y)
        self.angle = random.uniform(0, 360)
        self.health = 100
        self.is_dead = False
        self.death_time = 0
        self.respawn_time = 0
        
        # 武器状态
        self.ammo = MAGAZINE_SIZE
        self.is_reloading = False
        self.reload_start_time = 0
        self.last_shot_time = 0
        self.weapon_type = 'gun'
        self.is_aiming = False
        
        # AI难度
        self.difficulty = difficulty
        self.reaction_time = self._get_reaction_time()
        self.accuracy = self._get_accuracy()
        
        # 个性化特征
        if personality is None:
            self.personality_traits = AIPersonalityTraits.random_personality()
        elif isinstance(personality, AIPersonalityTraits):
            self.personality_traits = personality
        else:
            self.personality_traits = AIPersonalityTraits(personality)
        
        # 名称（包含性格信息）
        self.name = f"AI_{self.personality_traits.personality_type.value}_{player_id}"
        
        # 行为树
        self.behavior_tree = BehaviorTree(None)
        self._initialize_behavior_tree()
        
        # 路径规划
        self.current_path = []
        self.path_index = 0
        self.last_pathfind_time = 0
        self.pathfind_interval = 1.0
        self.grid_size = 20
        self.game_grid = None
        self.finder = AStarFinder(diagonal_movement=DiagonalMovement.always)
        
        # 巡逻路径
        self.patrol_points = []
        self.current_patrol_index = 0
        
        # 门交互
        self.last_door_interaction = 0
        self.door_interaction_cooldown = 1.0
        self.door_positions = []
        self.target_door = None
        
        # 静步系统
        self.is_walking = False
        self.stealth_mode = False
        self.last_stealth_decision = 0
        self.stealth_decision_interval = 2.0
        
        # 声音系统
        self.is_making_sound = False
        self.sound_volume = 0.0
        self.last_move_sound_time = 0
        self.move_sound_interval = 0.3
        self.sound_detection_range = 200
        
        # 目标追踪
        self.target_player = None
        self.target_pos = None
        self.last_known_enemy_pos = None
        self.last_sound_time = 0
    
    def _get_reaction_time(self):
        """根据难度获取反应时间"""
        if self.difficulty == 'easy':
            return random.uniform(0.5, 1.0)
        elif self.difficulty == 'normal':
            return random.uniform(0.2, 0.5)
        else:  # hard
            return random.uniform(0.1, 0.2)
    
    def _get_accuracy(self):
        """根据难度获取射击精度"""
        if self.difficulty == 'easy':
            return random.uniform(15, 30)
        elif self.difficulty == 'normal':
            return random.uniform(5, 15)
        else:  # hard
            return random.uniform(0, 5)
    
    def _initialize_behavior_tree(self):
        """根据个性化特征初始化行为树"""
        tree_type = self.personality_traits.get_behavior_tree_type()
        
        if tree_type == "aggressive":
            self.behavior_tree.create_aggressive_tree()
        elif tree_type == "defensive":
            self.behavior_tree.create_defensive_tree()
        elif tree_type == "tactical":
            self.behavior_tree.create_tactical_tree()
        elif tree_type == "stealthy":
            self.behavior_tree.create_stealthy_tree()
        else:
            self.behavior_tree.create_tactical_tree()
    
    def generate_patrol_points(self, game_map):
        """生成巡逻路径点"""
        self.patrol_points = []
        num_points = random.randint(5, 8)
        for _ in range(num_points):
            x = random.randint(100, ROOM_SIZE * 3 - 100)
            y = random.randint(100, ROOM_SIZE * 3 - 100)
            self.patrol_points.append(pygame.Vector2(x, y))
        
        self.create_navigation_grid(game_map)
    
    def create_navigation_grid(self, game_map):
        """创建导航网格，考虑玩家半径以避免路径点太靠近墙壁"""
        map_width = ROOM_SIZE * 3
        map_height = ROOM_SIZE * 3
        grid_width = map_width // self.grid_size
        grid_height = map_height // self.grid_size
        
        matrix = [[1 for _ in range(grid_width)] for _ in range(grid_height)]
        
        # 计算需要扩展的网格数（考虑玩家半径 + 安全距离）
        # PLAYER_RADIUS = 20, grid_size = 20, 所以至少需要扩展1个网格
        # 为了更安全，扩展2个网格（40像素）
        expansion = max(1, int((PLAYER_RADIUS + 10) // self.grid_size))
        
        # 标记墙壁（扩大区域以避免路径点太靠近墙壁）
        for wall in game_map.walls:
            # 扩大墙壁区域
            start_x = max(0, (wall.left - PLAYER_RADIUS - 10) // self.grid_size)
            end_x = min(grid_width - 1, (wall.right + PLAYER_RADIUS + 10) // self.grid_size)
            start_y = max(0, (wall.top - PLAYER_RADIUS - 10) // self.grid_size)
            end_y = min(grid_height - 1, (wall.bottom + PLAYER_RADIUS + 10) // self.grid_size)
            
            for y in range(start_y, end_y + 1):
                for x in range(start_x, end_x + 1):
                    # 检查这个网格中心是否在墙壁的扩展区域内
                    grid_center_x = x * self.grid_size + self.grid_size // 2
                    grid_center_y = y * self.grid_size + self.grid_size // 2
                    
                    # 创建测试矩形（考虑玩家半径）
                    test_rect = pygame.Rect(
                        grid_center_x - PLAYER_RADIUS,
                        grid_center_y - PLAYER_RADIUS,
                        PLAYER_RADIUS * 2,
                        PLAYER_RADIUS * 2
                    )
                    
                    # 如果测试矩形与墙壁碰撞，标记为不可行走
                    if test_rect.colliderect(wall):
                        matrix[y][x] = 0
        
        # 记录门位置
        self.door_positions = []
        for door in game_map.doors:
            door_info = {
                'door': door,
                'center': pygame.Vector2(door.rect.centerx, door.rect.centery),
                'rect': door.rect
            }
            self.door_positions.append(door_info)
        
        self.game_grid = Grid(matrix=matrix)
    
    def find_path_to_target(self, target_pos):
        """使用A*算法找到到目标的路径"""
        if not self.game_grid:
            return []
        
        start_x = int(self.pos.x // self.grid_size)
        start_y = int(self.pos.y // self.grid_size)
        end_x = int(target_pos.x // self.grid_size)
        end_y = int(target_pos.y // self.grid_size)
        
        grid_width = self.game_grid.width
        grid_height = self.game_grid.height
        
        start_x = max(0, min(grid_width - 1, start_x))
        start_y = max(0, min(grid_height - 1, start_y))
        end_x = max(0, min(grid_width - 1, end_x))
        end_y = max(0, min(grid_height - 1, end_y))
        
        start = self.game_grid.node(start_x, start_y)
        end = self.game_grid.node(end_x, end_y)
        
        if not end.walkable:
            for radius in range(1, 5):
                found = False
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        new_x = end_x + dx
                        new_y = end_y + dy
                        if (0 <= new_x < grid_width and 0 <= new_y < grid_height):
                            test_node = self.game_grid.node(new_x, new_y)
                            if test_node.walkable:
                                end = test_node
                                found = True
                                break
                    if found:
                        break
                if found:
                    break
        
        self.game_grid.cleanup()
        path, runs = self.finder.find_path(start, end, self.game_grid)
        
        world_path = []
        for node in path:
            world_x = node.x * self.grid_size + self.grid_size // 2
            world_y = node.y * self.grid_size + self.grid_size // 2
            world_path.append(pygame.Vector2(world_x, world_y))
        
        return world_path
    
    def update_pathfinding(self, target_pos):
        """更新路径规划"""
        current_time = time.time()
        
        # 检查是否需要重新规划路径
        need_repath = (
            current_time - self.last_pathfind_time > self.pathfind_interval or 
            self.path_index >= len(self.current_path) or
            len(self.current_path) == 0
        )
        
        if need_repath:
            self.current_path = self.find_path_to_target(target_pos)
            self.path_index = 0
            self.last_pathfind_time = current_time
            
            # 如果路径规划失败，记录日志
            if len(self.current_path) == 0:
                print(f"[AI路径规划] AI{self.id}路径规划失败，目标位置: ({target_pos.x:.1f}, {target_pos.y:.1f})")
    
    def get_next_move_direction(self, game_map=None):
        """获取下一个移动方向，并检查碰撞"""
        if not self.current_path or self.path_index >= len(self.current_path):
            return pygame.Vector2(0, 0)
        
        # 如果路径为空，返回零向量
        if len(self.current_path) == 0:
            return pygame.Vector2(0, 0)
        
        # 确保路径索引有效
        if self.path_index >= len(self.current_path):
            self.path_index = len(self.current_path) - 1
        
        # 尝试找到可用的路径点
        max_attempts = min(5, len(self.current_path) - self.path_index)
        direction = pygame.Vector2(0, 0)
        
        for attempt in range(max_attempts):
            # 检查索引是否有效
            if self.path_index >= len(self.current_path):
                # 路径已完成
                return pygame.Vector2(0, 0)
            
            target = self.current_path[self.path_index]
            direction = target - self.pos
            
            # 如果到达当前目标点，移动到下一个点
            if direction.length() < self.grid_size * 0.7:
                self.path_index += 1
                if self.path_index < len(self.current_path):
                    target = self.current_path[self.path_index]
                    direction = target - self.pos
                else:
                    # 路径已完成
                    return pygame.Vector2(0, 0)
            
            if direction.length() > 0:
                direction_normalized = direction.normalize()
                
                # 如果有 game_map，检查这个方向是否会导致碰撞
                if game_map:
                    if self.can_move_in_direction(direction_normalized, game_map, distance=30):
                        # 方向安全，返回它
                        return direction_normalized
                    else:
                        # 这个路径点会导致碰撞，尝试下一个点
                        self.path_index += 1
                        # 继续循环，下次迭代会检查索引有效性
                        continue
                else:
                    # 没有 game_map，直接返回方向
                    return direction_normalized
        
        # 如果所有路径点都不可用，返回零向量
        return pygame.Vector2(0, 0)
    
    def check_door_interaction(self):
        """检查门交互"""
        current_time = time.time()
        
        if current_time - self.last_door_interaction < self.door_interaction_cooldown:
            return None
        
        if self.current_path and self.path_index < len(self.current_path):
            check_range = min(3, len(self.current_path) - self.path_index)
            
            for i in range(check_range):
                path_point = self.current_path[self.path_index + i]
                
                for door_info in self.door_positions:
                    door = door_info['door']
                    door_center = door_info['center']
                    
                    if not door.is_open:
                        distance_to_door = path_point.distance_to(door_center)
                        
                        if distance_to_door < 40:
                            ai_distance_to_door = self.pos.distance_to(door_center)
                            
                            if ai_distance_to_door < 80:
                                self.target_door = door
                                self.last_door_interaction = current_time
                                return door
        
        return None
    
    def has_line_of_sight(self, target_pos, game_map):
        """检查是否有视线到目标"""
        for wall in game_map.walls:
            if self._line_intersects_rect(self.pos, target_pos, wall):
                return False
        
        for door_info in self.door_positions:
            door = door_info['door']
            if not door.is_open:
                if self._line_intersects_rect(self.pos, target_pos, door.rect):
                    return False
        
        return True
    
    def can_shoot_at_target(self, target_pos, game_map):
        """检查是否可以向目标射击"""
        return self.has_line_of_sight(target_pos, game_map)
    
    def _line_intersects_rect(self, start, end, rect):
        """检查线段是否与矩形相交"""
        try:
            return rect.clipline((start.x, start.y), (end.x, end.y))
        except:
            min_x = min(start.x, end.x)
            max_x = max(start.x, end.x)
            min_y = min(start.y, end.y)
            max_y = max(start.y, end.y)
            
            return not (rect.right < min_x or rect.left > max_x or 
                       rect.bottom < min_y or rect.top > max_y)
    
    def get_movement_speed_multiplier(self):
        """获取移动速度倍率"""
        if self.stealth_mode:
            return 0.4
        elif self.personality_traits.aggression > 0.7:
            return 1.2  # 激进型移动更快
        else:
            return 1.0
    
    def can_move_in_direction(self, direction, game_map, distance=30):
        """检查在指定方向是否可以移动（不会碰撞）"""
        if direction.length() < 0.1:
            return False
        
        # 计算测试位置
        test_pos = self.pos + direction.normalize() * distance
        player_rect = pygame.Rect(
            test_pos.x - PLAYER_RADIUS,
            test_pos.y - PLAYER_RADIUS,
            PLAYER_RADIUS * 2,
            PLAYER_RADIUS * 2
        )
        
        # 检查墙壁碰撞
        for wall in game_map.walls:
            if player_rect.colliderect(wall):
                return False
        
        # 检查门碰撞
        for door in game_map.doors:
            if door.check_collision(player_rect):
                return False
        
        return True
    
    def find_valid_move_direction(self, game_map, preferred_directions=None):
        """找到可以移动的方向，优先使用preferred_directions"""
        if preferred_directions is None:
            # 默认尝试8个方向
            preferred_directions = [
                pygame.Vector2(1, 0),      # 右
                pygame.Vector2(-1, 0),     # 左
                pygame.Vector2(0, 1),       # 下
                pygame.Vector2(0, -1),      # 上
                pygame.Vector2(1, 1).normalize(),   # 右下
                pygame.Vector2(-1, 1).normalize(),  # 左下
                pygame.Vector2(1, -1).normalize(),  # 右上
                pygame.Vector2(-1, -1).normalize(), # 左上
            ]
        
        # 首先尝试preferred_directions
        for direction in preferred_directions:
            if self.can_move_in_direction(direction, game_map):
                return direction.normalize()
        
        # 如果preferred_directions都不行，尝试更多方向
        for angle in range(0, 360, 15):  # 每15度尝试一次
            angle_rad = math.radians(angle)
            direction = pygame.Vector2(math.cos(angle_rad), -math.sin(angle_rad))
            if self.can_move_in_direction(direction, game_map):
                return direction.normalize()
        
        # 如果所有方向都不行，返回零向量
        return pygame.Vector2(0, 0)
    
    def update_stealth_mode(self, players, game_map):
        """更新静步模式"""
        current_time = time.time()
        
        if current_time - self.last_stealth_decision < self.stealth_decision_interval:
            return
        
        self.last_stealth_decision = current_time
        
        # 使用个性化特征判断是否应该静步
        enemies = [p for p in players.values() if not p.get('is_dead', False)]
        if not enemies:
            self.stealth_mode = False
            return
        
        min_distance = float('inf')
        for enemy in enemies:
            enemy_pos = pygame.Vector2(enemy['pos'][0], enemy['pos'][1])
            distance = self.pos.distance_to(enemy_pos)
            if distance < min_distance:
                min_distance = distance
        
        # 根据个性化特征判断
        should_stealth = self.personality_traits.should_use_stealth(min_distance, len(enemies))
        self.stealth_mode = should_stealth
    
    def update_sound_generation(self, move_vector, is_shooting, is_reloading):
        """更新声音产生"""
        current_time = time.time()
        
        if is_shooting:
            self.is_making_sound = True
            self.sound_volume = 1.0
            return
        
        if is_reloading:
            self.is_making_sound = True
            self.sound_volume = 0.8
            return
        
        is_moving = move_vector.length() > 0.1
        
        if is_moving:
            self.is_making_sound = True
            
            if self.stealth_mode:
                self.sound_volume = 0.3
            else:
                self.sound_volume = 1.0
        else:
            self.is_making_sound = False
            self.sound_volume = 0.0
    
    def update(self, dt, players, game_map, bullets):
        """更新AI状态"""
        if self.is_dead:
            return None
        
        current_time = time.time()
        
        # 更新装填状态
        if self.is_reloading:
            if current_time - self.reload_start_time >= RELOAD_TIME:
                self.is_reloading = False
                self.ammo = MAGAZINE_SIZE
        
        # 更新静步模式
        self.update_stealth_mode(players, game_map)
        
        # 准备敌人和友军数据
        enemies = []
        allies = []
        
        for pid, pdata in players.items():
            if pid == self.id:
                continue
            
            player_data = {
                'id': pid,
                'pos': pdata.get('pos', [0, 0]),
                'angle': pdata.get('angle', 0),
                'health': pdata.get('health', 100),
                'is_dead': pdata.get('is_dead', False),
                'shooting': pdata.get('shooting', False),
                'is_reloading': pdata.get('is_reloading', False),
                'is_walking': pdata.get('is_walking', False),
                'is_making_sound': pdata.get('is_making_sound', False),
                'sound_volume': pdata.get('sound_volume', 0.0)
            }
            
            # 这里简化处理：所有其他玩家都视为敌人
            # 实际游戏中可以根据团队分配来区分
            enemies.append(player_data)
        
        # 执行行为树
        action = self.behavior_tree.tick(self, enemies, game_map)
        
        # 检查门交互
        door_to_open = self.check_door_interaction()
        if door_to_open:
            action['interact_door'] = door_to_open
        
        # 更新声音产生
        move_vector = action.get('move', pygame.Vector2(0, 0))
        is_shooting = action.get('shoot', False)
        is_reloading = action.get('reload', False)
        self.update_sound_generation(move_vector, is_shooting, is_reloading)
        
        # 添加静步状态
        action['is_walking'] = self.stealth_mode
        
        # 添加声音状态
        action['is_making_sound'] = self.is_making_sound
        action['sound_volume'] = self.sound_volume
        
        return action
    
    def take_damage(self, damage):
        """受到伤害"""
        self.health -= damage
        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            self.death_time = time.time()
            self.respawn_time = time.time() + RESPAWN_TIME
            return True
        return False
    
    def respawn(self, x, y):
        """复活"""
        self.pos.x = x
        self.pos.y = y
        self.health = 100
        self.is_dead = False
        self.ammo = MAGAZINE_SIZE
        self.is_reloading = False
        self.target_player = None
        self.target_pos = None

