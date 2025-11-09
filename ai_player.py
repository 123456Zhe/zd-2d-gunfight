import pygame
import math
import random
import time
from constants import *
from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder

class AIPlayer:
    """AI玩家类"""
    def __init__(self, player_id, x, y, difficulty='normal'):
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
        
        # AI状态
        self.difficulty = difficulty  # 'easy', 'normal', 'hard'
        self.target_player = None
        self.target_pos = None
        self.last_decision_time = 0
        self.decision_interval = self._get_decision_interval()
        self.state = 'patrol'  # 'patrol', 'chase', 'attack', 'retreat'
        
        # 巡逻路径
        self.patrol_points = []
        self.current_patrol_index = 0
        
        # 反应时间
        self.reaction_time = self._get_reaction_time()
        self.last_seen_enemy_time = 0
        
        # 射击精度
        self.accuracy = self._get_accuracy()
        
        # 名称
        self.name = f"AI_{player_id}"
        
        # 路径规划
        self.current_path = []
        self.path_index = 0
        self.last_pathfind_time = 0
        self.pathfind_interval = 1.0  # 每秒重新计算路径
        self.grid_size = 20  # 网格大小（像素）
        self.game_grid = None
        self.finder = AStarFinder(diagonal_movement=DiagonalMovement.always)
        
        # 门交互
        self.last_door_interaction = 0
        self.door_interaction_cooldown = 1.0  # 门交互冷却时间
        self.nearby_doors = []  # 附近的门
        self.target_door = None  # 当前目标门
        
        # 静步系统
        self.is_walking = False  # 是否静步
        self.stealth_mode = False  # 是否进入隐蔽模式
        self.last_stealth_decision = 0
        self.stealth_decision_interval = 2.0  # 静步决策间隔
        
        # 战术状态
        self.last_enemy_distance = float('inf')
        self.enemy_approaching = False  # 敌人是否在接近
        self.in_combat = False  # 是否在战斗中
        
        # 声音产生系统
        self.is_making_sound = False  # 是否正在发出声音
        self.sound_volume = 0.0  # 声音音量 (0.0-1.0)
        self.last_move_sound_time = 0  # 上次移动声音时间
        self.move_sound_interval = 0.3  # 移动声音间隔
        
        # 声音感知系统
        self.sound_detection_range = 200  # 声音检测范围
        self.last_heard_sounds = []  # 最近听到的声音
        self.sound_memory_duration = 5.0  # 声音记忆持续时间
        self.suspected_enemy_positions = []  # 怀疑的敌人位置
        self.last_known_enemy_pos = None  # 最后已知的敌人位置
        self.last_sound_time = 0
    
    def _get_decision_interval(self):
        """根据难度获取决策间隔"""
        if self.difficulty == 'easy':
            return random.uniform(1.2, 1.8)  # 降低难度：增加决策间隔
        elif self.difficulty == 'normal':
            return random.uniform(0.6, 1.0)  # 降低难度：增加决策间隔
        else:  # hard
            return random.uniform(0.2, 0.4)
    
    def _get_reaction_time(self):
        """根据难度获取反应时间"""
        if self.difficulty == 'easy':
            return random.uniform(1.0, 1.8)  # 降低难度：增加反应时间
        elif self.difficulty == 'normal':
            return random.uniform(0.4, 0.8)  # 降低难度：增加反应时间
        else:  # hard
            return random.uniform(0.1, 0.2)
    
    def _get_accuracy(self):
        """根据难度获取射击精度（角度偏差）"""
        if self.difficulty == 'easy':
            return random.uniform(25, 45)  # 降低难度：增加偏差
        elif self.difficulty == 'normal':
            return random.uniform(10, 20)  # 降低难度：增加偏差
        else:  # hard
            return random.uniform(0, 5)
    
    def generate_patrol_points(self, game_map):
        """生成巡逻路径点"""
        self.patrol_points = []
        # 在地图中随机生成5-8个巡逻点
        num_points = random.randint(5, 8)
        for _ in range(num_points):
            x = random.randint(100, ROOM_SIZE * 3 - 100)
            y = random.randint(100, ROOM_SIZE * 3 - 100)
            self.patrol_points.append(pygame.Vector2(x, y))
        
        # 创建导航网格
        self.create_navigation_grid(game_map)
    
    def create_navigation_grid(self, game_map):
        """创建用于路径规划的网格，动态考虑门的状态"""
        # 计算网格尺寸
        map_width = ROOM_SIZE * 3
        map_height = ROOM_SIZE * 3
        grid_width = map_width // self.grid_size
        grid_height = map_height // self.grid_size
        
        # 创建网格矩阵（1=可通行，0=不可通行）
        matrix = [[1 for _ in range(grid_width)] for _ in range(grid_height)]
        
        # 标记墙壁为不可通行
        for wall in game_map.walls:
            start_x = max(0, wall.left // self.grid_size)
            end_x = min(grid_width - 1, wall.right // self.grid_size)
            start_y = max(0, wall.top // self.grid_size)
            end_y = min(grid_height - 1, wall.bottom // self.grid_size)
            
            for y in range(start_y, end_y + 1):
                for x in range(start_x, end_x + 1):
                    matrix[y][x] = 0
        
        # 处理门：所有门都标记为可通行，AI会在经过时自动开门
        self.door_positions = []  # 记录所有门的位置
        for door in game_map.doors:
            # 记录门的位置和状态，用于路径经过时的开门判断
            door_info = {
                'door': door,
                'center': pygame.Vector2(door.rect.centerx, door.rect.centery),
                'rect': door.rect
            }
            self.door_positions.append(door_info)
            
            # 所有门区域都标记为可通行
            # AI会在路径规划时将门视为可通行，但在实际移动时检查并开门
        
        # 创建pathfinding网格
        self.game_grid = Grid(matrix=matrix)
    
    def find_path_to_target(self, target_pos):
        """使用A*算法找到到目标的路径"""
        if not self.game_grid:
            return []
        
        # 转换坐标到网格坐标
        start_x = int(self.pos.x // self.grid_size)
        start_y = int(self.pos.y // self.grid_size)
        end_x = int(target_pos.x // self.grid_size)
        end_y = int(target_pos.y // self.grid_size)
        
        # 确保坐标在网格范围内
        grid_width = self.game_grid.width
        grid_height = self.game_grid.height
        
        start_x = max(0, min(grid_width - 1, start_x))
        start_y = max(0, min(grid_height - 1, start_y))
        end_x = max(0, min(grid_width - 1, end_x))
        end_y = max(0, min(grid_height - 1, end_y))
        
        # 获取起点和终点
        start = self.game_grid.node(start_x, start_y)
        end = self.game_grid.node(end_x, end_y)
        
        # 如果终点不可通行，寻找附近的可通行点
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
        
        # 清理网格（重置之前的路径）
        self.game_grid.cleanup()
        
        # 寻找路径
        path, runs = self.finder.find_path(start, end, self.game_grid)
        
        # 转换回世界坐标
        world_path = []
        for node in path:
            world_x = node.x * self.grid_size + self.grid_size // 2
            world_y = node.y * self.grid_size + self.grid_size // 2
            world_path.append(pygame.Vector2(world_x, world_y))
        
        return world_path
    
    def check_door_interaction(self):
        """检查路径上是否有门需要开启"""
        current_time = time.time()
        
        # 冷却时间检查
        if current_time - self.last_door_interaction < self.door_interaction_cooldown:
            return None
        
        # 检查当前路径上是否有关闭的门
        if self.current_path and self.path_index < len(self.current_path):
            # 检查接下来几个路径点附近是否有门
            check_range = min(3, len(self.current_path) - self.path_index)  # 检查接下来3个路径点
            
            for i in range(check_range):
                path_point = self.current_path[self.path_index + i]
                
                # 检查这个路径点附近是否有关闭的门
                for door_info in self.door_positions:
                    door = door_info['door']
                    door_center = door_info['center']
                    
                    if not door.is_open:
                        # 检查路径点是否经过门区域
                        distance_to_door = path_point.distance_to(door_center)
                        
                        if distance_to_door < 40:  # 路径点在门附近
                            # 检查AI当前位置是否足够接近门来开启
                            ai_distance_to_door = self.pos.distance_to(door_center)
                            
                            if ai_distance_to_door < 80:  # AI在开门范围内
                                self.target_door = door
                                self.last_door_interaction = current_time
                                return door
        
        # 也检查AI当前位置附近是否有关闭的门（作为备用）
        for door_info in self.door_positions:
            door = door_info['door']
            door_center = door_info['center']
            
            if not door.is_open:
                distance = self.pos.distance_to(door_center)
                
                # 如果AI非常接近门，也尝试开门
                if distance < 50:
                    self.target_door = door
                    self.last_door_interaction = current_time
                    return door
        
        return None
    
    def check_path_for_doors(self):
        """检查当前路径是否经过关闭的门，并标记需要开启的门"""
        doors_to_open = []
        
        if not self.current_path:
            return doors_to_open
        
        # 检查整个路径
        for path_point in self.current_path:
            for door_info in self.door_positions:
                door = door_info['door']
                door_center = door_info['center']
                
                if not door.is_open:
                    # 检查路径点是否经过门区域
                    distance = path_point.distance_to(door_center)
                    
                    if distance < 30:  # 路径经过门区域
                        if door not in doors_to_open:
                            doors_to_open.append(door)
        
        return doors_to_open
    
    def update_stealth_mode(self, players, game_map):
        """更新静步模式决策 - 综合视觉和声音威胁"""
        current_time = time.time()
        
        # 定期重新评估静步需求
        if current_time - self.last_stealth_decision < self.stealth_decision_interval:
            return
        
        self.last_stealth_decision = current_time
        
        # 检测当前威胁
        detected_sounds = self.detect_sounds(players, game_map)
        visual_contacts = self.detect_visual_enemies(players, game_map)
        
        # 分析威胁等级
        min_threat_distance = float('inf')
        threat_count = 0
        high_threat = False
        
        # 视觉威胁（更严重）
        for contact in visual_contacts:
            threat_count += 1
            if contact['distance'] < min_threat_distance:
                min_threat_distance = contact['distance']
            if contact['distance'] < 100:
                high_threat = True
        
        # 声音威胁
        for sound in detected_sounds:
            if sound['type'] == 'gunshot':
                threat_count += 1
                high_threat = True
                if sound['distance'] < min_threat_distance:
                    min_threat_distance = sound['distance']
            elif sound['type'] in ['footstep', 'footstep_quiet']:
                if sound['distance'] < min_threat_distance:
                    min_threat_distance = sound['distance']
        
        # 静步决策逻辑
        should_stealth = False
        
        # 情况1：被敌人看到但距离适中，需要隐蔽移动
        if visual_contacts and 80 < min_threat_distance < 200:
            should_stealth = True
        
        # 情况2：听到附近声音，静步接近调查
        if 50 < min_threat_distance < 150 and self.state in ['patrol', 'chase']:
            should_stealth = True
        
        # 情况3：多个威胁源，需要隐蔽
        if threat_count >= 2:
            should_stealth = True
        
        # 情况4：生命值较低，需要隐蔽
        if self.health < 50:
            should_stealth = True
        
        # 情况5：正在装填弹药，需要隐蔽
        if self.is_reloading:
            should_stealth = True
        
        # 情况6：高威胁情况下不使用静步（需要快速机动）
        if high_threat and min_threat_distance < 80:
            should_stealth = False
        
        # 情况7：在激烈战斗中不使用静步
        if self.state == 'attack' and min_threat_distance < 100:
            should_stealth = False
        
        self.stealth_mode = should_stealth
        self.in_combat = (min_threat_distance < 200 and self.state in ['attack', 'retreat'])
        
        if should_stealth:
            print(f"[AI静步] AI{self.id}进入静步模式，威胁距离{min_threat_distance:.1f}")
    
    def update_sound_generation(self, move_vector, is_shooting, is_reloading):
        """更新AI的声音产生 - 修复闪烁问题"""
        current_time = time.time()
        
        # 射击声音（最高优先级）
        if is_shooting:
            self.is_making_sound = True
            self.sound_volume = 1.0
            print(f"[AI声音] AI{self.id}射击，产生枪声")
            return
        
        # 装填声音（次高优先级）
        if is_reloading:
            self.is_making_sound = True
            self.sound_volume = 0.8
            print(f"[AI声音] AI{self.id}装填，产生装填声")
            return
        
        # 移动声音（脚步声）- 修复闪烁问题
        is_moving = move_vector.length() > 0.1
        
        if is_moving:
            # 移动时持续产生声音，不依赖间隔
            self.is_making_sound = True
            
            if self.stealth_mode:
                # 静步声音很小
                self.sound_volume = 0.3
                # 只在间隔时间到达时输出调试信息，避免刷屏
                if current_time - self.last_move_sound_time > self.move_sound_interval:
                    self.last_move_sound_time = current_time
                    print(f"[AI声音] AI{self.id}静步移动，产生轻微脚步声")
            else:
                # 正常移动声音
                self.sound_volume = 1.0
                # 只在间隔时间到达时输出调试信息，避免刷屏
                if current_time - self.last_move_sound_time > self.move_sound_interval:
                    self.last_move_sound_time = current_time
                    print(f"[AI声音] AI{self.id}正常移动，产生脚步声")
        else:
            # 不移动时不产生声音
            self.is_making_sound = False
            self.sound_volume = 0.0
    
    def get_movement_speed_multiplier(self):
        """获取移动速度倍率"""
        if self.stealth_mode:
            return 0.4  # 静步时速度降低到40%
        elif self.in_combat:
            return 1.2  # 战斗中速度提高20%
        else:
            return 1.0  # 正常速度
    
    def update_pathfinding(self, target_pos):
        """更新路径规划"""
        current_time = time.time()
        
        # 定期重新计算路径或者当前路径已完成
        if (current_time - self.last_pathfind_time > self.pathfind_interval or 
            self.path_index >= len(self.current_path)):
            
            self.current_path = self.find_path_to_target(target_pos)
            self.path_index = 0
            self.last_pathfind_time = current_time
            
            # 检查新路径是否经过关闭的门
            doors_on_path = self.check_path_for_doors()
            if doors_on_path:
                print(f"[AI路径规划] AI{self.id}的路径将经过{len(doors_on_path)}个关闭的门")
    
    def get_next_move_direction(self):
        """获取下一个移动方向"""
        if not self.current_path or self.path_index >= len(self.current_path):
            return pygame.Vector2(0, 0)
        
        # 获取当前目标点
        target = self.current_path[self.path_index]
        direction = target - self.pos
        
        # 检查从当前位置到目标点的路径上是否有关闭的门
        self.check_doors_on_movement_path(self.pos, target)
        
        # 如果接近当前目标点，移动到下一个点
        if direction.length() < self.grid_size * 0.7:
            self.path_index += 1
            if self.path_index < len(self.current_path):
                target = self.current_path[self.path_index]
                direction = target - self.pos
                # 检查新的移动段是否有门
                self.check_doors_on_movement_path(self.pos, target)
        
        # 返回标准化的方向向量
        if direction.length() > 0:
            return direction.normalize()
        else:
            return pygame.Vector2(0, 0)
    
    def check_doors_on_movement_path(self, start_pos, end_pos):
        """检查从起点到终点的直线路径上是否有关闭的门"""
        for door_info in self.door_positions:
            door = door_info['door']
            door_rect = door_info['rect']
            
            if not door.is_open:
                # 检查移动路径是否与门矩形相交
                if self.line_intersects_rect(start_pos, end_pos, door_rect):
                    # 如果路径经过关闭的门，记录需要开启
                    door_center = door_info['center']
                    distance_to_door = start_pos.distance_to(door_center)
                    
                    # 如果AI足够接近门，标记为需要开启
                    if distance_to_door < 100:
                        self.target_door = door
    
    def line_intersects_rect(self, start, end, rect):
        """检查线段是否与矩形相交"""
        # 简化的线段-矩形相交检测
        # 检查线段端点是否在矩形内
        if rect.collidepoint(start) or rect.collidepoint(end):
            return True
        
        # 检查线段是否与矩形边界相交
        # 这里使用简化的检测：检查线段是否经过矩形区域
        min_x = min(start.x, end.x)
        max_x = max(start.x, end.x)
        min_y = min(start.y, end.y)
        max_y = max(start.y, end.y)
        
        # 检查矩形是否与线段的包围盒相交
        return not (rect.right < min_x or rect.left > max_x or 
                   rect.bottom < min_y or rect.top > max_y)
    
    def detect_sounds(self, players, game_map):
        """通过声音检测其他玩家"""
        current_time = time.time()
        detected_sounds = []
        
        for player_id, player_data in players.items():
            if player_id == self.id or player_data.get('is_dead', False):
                continue
            
            player_pos = pygame.Vector2(player_data['pos'])
            distance = self.pos.distance_to(player_pos)
            
            # 在声音检测范围内
            if distance <= self.sound_detection_range:
                sounds_detected = []
                
                # 射击声音（最优先检测）
                if player_data.get('shooting', False):
                    sounds_detected.append({
                        'type': 'gunshot',
                        'volume': 1.5,
                        'priority': 3
                    })
                
                # 装填声音
                if player_data.get('is_reloading', False):
                    sounds_detected.append({
                        'type': 'reload',
                        'volume': 0.8,
                        'priority': 2
                    })
                
                # 移动声音（脚步声）- 修复检测逻辑
                # 检查玩家的移动状态
                is_walking = player_data.get('is_walking', False)
                
                # 假设玩家总是可能在移动（除非明确静止）
                # 这里我们简化处理：如果玩家存在就可能有脚步声
                if is_walking:
                    # 静步声音
                    sounds_detected.append({
                        'type': 'footstep_quiet',
                        'volume': 0.3,
                        'priority': 1
                    })
                else:
                    # 正常移动声音（假设玩家在移动）
                    sounds_detected.append({
                        'type': 'footstep',
                        'volume': 1.0,
                        'priority': 1
                    })
                
                # 处理检测到的声音
                for sound in sounds_detected:
                    # 距离影响声音强度
                    distance_factor = 1.0 - (distance / self.sound_detection_range)
                    final_volume = sound['volume'] * distance_factor
                    
                    if final_volume > 0.1:  # 最小可听阈值
                        sound_info = {
                            'player_id': player_id,
                            'position': player_pos,
                            'type': sound['type'],
                            'volume': final_volume,
                            'distance': distance,
                            'time': current_time,
                            'priority': sound['priority']
                        }
                        detected_sounds.append(sound_info)
                        
                        # 调试输出
                        print(f"[AI声音检测] AI{self.id}听到玩家{player_id}的{sound['type']}，距离{distance:.1f}，音量{final_volume:.2f}")
        
        # 更新声音记忆
        self.last_heard_sounds = [s for s in self.last_heard_sounds 
                                 if current_time - s['time'] < self.sound_memory_duration]
        self.last_heard_sounds.extend(detected_sounds)
        
        return detected_sounds
    
    def detect_visual_enemies(self, players, game_map):
        """通过视线检测敌人"""
        visual_contacts = []
        
        for player_id, player_data in players.items():
            if player_id == self.id or player_data.get('is_dead', False):
                continue
            
            player_pos = pygame.Vector2(player_data['pos'])
            distance = self.pos.distance_to(player_pos)
            
            # 视线检测范围（比声音检测稍远）
            if distance <= 300:  # 视线范围
                # 检查是否有直接视线
                if self.has_line_of_sight(player_pos, game_map):
                    visual_contact = {
                        'player_id': player_id,
                        'position': player_pos,
                        'distance': distance,
                        'time': time.time()
                    }
                    visual_contacts.append(visual_contact)
                    print(f"[AI视觉检测] AI{self.id}看到玩家{player_id}，距离{distance:.1f}")
        
        return visual_contacts
    
    def has_line_of_sight(self, target_pos, game_map):
        """检查是否有视线到目标位置"""
        # 检查墙壁遮挡
        for wall in game_map.walls:
            if self.line_intersects_rect(self.pos, target_pos, wall):
                return False
        
        # 检查关闭的门遮挡
        for door_info in self.door_positions:
            door = door_info['door']
            if not door.is_open:
                if self.line_intersects_rect(self.pos, target_pos, door.rect):
                    return False
        
        return True
    
    def can_shoot_at_target(self, target_pos, game_map):
        """检查是否可以向目标射击（不会打到墙）"""
        return self.has_line_of_sight(target_pos, game_map)
    
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
        
        # 更新静步模式决策
        self.update_stealth_mode(players, game_map)
        
        # 决策更新
        if current_time - self.last_decision_time >= self.decision_interval:
            self.last_decision_time = current_time
            self.make_decision(players, game_map)
        
        # 检查门交互
        door_to_open = self.check_door_interaction()
        
        # 执行当前状态的行为
        action = self.execute_state(dt, players, game_map, bullets)
        
        # 更新声音产生
        move_vector = action.get('move', pygame.Vector2(0, 0))
        is_shooting = action.get('shoot', False)
        is_reloading = action.get('reload', False)
        self.update_sound_generation(move_vector, is_shooting, is_reloading)
        
        # 添加门交互动作
        if door_to_open:
            action['interact_door'] = door_to_open
        
        # 添加静步状态
        action['is_walking'] = self.stealth_mode
        
        # 添加声音状态
        action['is_making_sound'] = self.is_making_sound
        action['sound_volume'] = self.sound_volume
        
        return action
    
    def make_decision(self, players, game_map):
        """AI决策逻辑 - 综合视线和声音感知"""
        current_time = time.time()
        
        # 检测声音和视线
        detected_sounds = self.detect_sounds(players, game_map)
        visual_contacts = self.detect_visual_enemies(players, game_map)
        
        # 优先处理视觉接触（更可靠）
        closest_visual = None
        closest_sound = None
        min_visual_distance = float('inf')
        min_sound_distance = float('inf')
        
        # 分析视觉接触
        for contact in visual_contacts:
            if contact['distance'] < min_visual_distance:
                min_visual_distance = contact['distance']
                closest_visual = contact
        
        # 分析声音接触
        for sound in detected_sounds:
            if sound['distance'] < min_sound_distance:
                min_sound_distance = sound['distance']
                closest_sound = sound
        
        # 决策优先级：视觉 > 声音 > 记忆
        target_updated = False
        
        if closest_visual:
            # 视觉接触优先级最高
            self.target_player = closest_visual['player_id']
            self.target_pos = pygame.Vector2(closest_visual['position'])
            self.last_known_enemy_pos = self.target_pos
            self.last_sound_time = current_time  # 更新最后接触时间
            target_updated = True
            
            print(f"[AI决策] AI{self.id}通过视觉锁定玩家{self.target_player}")
            
            # 基于视觉距离决定行为
            if min_visual_distance < 100:
                self.state = 'attack' if self.health > 30 else 'retreat'
            elif min_visual_distance < 200:
                self.state = 'attack'
            else:
                self.state = 'chase'
                
        elif closest_sound:
            # 声音接触次优先级
            self.target_player = closest_sound['player_id']
            self.target_pos = pygame.Vector2(closest_sound['position'])
            self.last_known_enemy_pos = self.target_pos
            self.last_sound_time = current_time
            target_updated = True
            
            print(f"[AI决策] AI{self.id}通过声音({closest_sound['type']})锁定玩家{self.target_player}")
            
            # 根据声音类型和距离决定行为
            if closest_sound['type'] == 'gunshot':
                # 听到枪声，立即进入战斗状态
                if min_sound_distance < 100:
                    self.state = 'attack' if self.health > 30 else 'retreat'
                else:
                    self.state = 'chase'
            elif closest_sound['type'] in ['footstep', 'footstep_quiet']:
                # 听到脚步声
                if min_sound_distance < 80:
                    self.state = 'attack' if self.health > 30 else 'retreat'
                elif min_sound_distance < 150:
                    self.state = 'chase'
                else:
                    # 远距离脚步声，谨慎接近
                    self.state = 'chase'
            elif closest_sound['type'] == 'reload':
                # 听到装填声，这是攻击的好机会
                if min_sound_distance < 200:
                    self.state = 'chase'  # 快速接近
        
        # 如果没有新的接触，使用记忆
        if not target_updated:
            if self.last_known_enemy_pos and current_time - self.last_sound_time < 15.0:
                # 15秒内有过接触，去最后已知位置搜索
                self.target_pos = self.last_known_enemy_pos
                self.state = 'chase'
                print(f"[AI决策] AI{self.id}前往最后已知位置搜索")
            else:
                # 很久没有接触，继续巡逻
                self.state = 'patrol'
                self.target_player = None
                self.target_pos = None
                self.last_known_enemy_pos = None
                print(f"[AI决策] AI{self.id}进入巡逻模式")
    
    def execute_state(self, dt, players, game_map, bullets):
        """执行当前状态"""
        action = {
            'move': pygame.Vector2(0, 0),
            'angle': self.angle,
            'shoot': False,
            'reload': False
        }
        
        if self.state == 'patrol':
            action = self._patrol(dt, game_map)
        elif self.state == 'chase':
            action = self._chase(dt, game_map)
        elif self.state == 'attack':
            action = self._attack(dt, game_map)
        elif self.state == 'retreat':
            action = self._retreat(dt, game_map)
        
        # 自动装填（弹药用完时立即装填）
        if self.ammo == 0 and not self.is_reloading:
            action['reload'] = True
            self.is_reloading = True
            self.reload_start_time = time.time()
        # 或者在安全时提前装填
        elif self.ammo <= 5 and not self.is_reloading and self.state == 'patrol':
            action['reload'] = True
            self.is_reloading = True
            self.reload_start_time = time.time()
        
        return action
    
    def _patrol(self, dt, game_map):
        """巡逻行为 - 使用智能路径规划"""
        if not self.patrol_points:
            self.generate_patrol_points(game_map)
        
        target = self.patrol_points[self.current_patrol_index]
        
        # 检查是否到达当前巡逻点
        if (target - self.pos).length() < 50:
            # 到达巡逻点，前往下一个
            self.current_patrol_index = (self.current_patrol_index + 1) % len(self.patrol_points)
            target = self.patrol_points[self.current_patrol_index]
            # 清空当前路径，强制重新规划
            self.current_path = []
            self.path_index = 0
        
        # 更新路径规划
        self.update_pathfinding(target)
        
        # 获取智能移动方向
        move_direction = self.get_next_move_direction()
        
        # 计算朝向角度
        if move_direction.length() > 0:
            dx = move_direction.x
            dy = move_direction.y
            self.angle = math.degrees(math.atan2(-dy, dx))
        
        # 应用移动速度倍率（巡逻时可能使用静步）
        speed_multiplier = self.get_movement_speed_multiplier()
        
        return {
            'move': move_direction * PLAYER_SPEED * speed_multiplier,
            'angle': self.angle,
            'shoot': False,
            'reload': False
        }
    
    def _chase(self, dt, game_map):
        """追击行为 - 使用智能路径规划"""
        if not self.target_pos:
            return self._patrol(dt, game_map)
        
        # 更新路径规划到目标位置
        self.update_pathfinding(self.target_pos)
        
        # 获取智能移动方向
        move_direction = self.get_next_move_direction()
        
        # 如果路径规划失败，使用直线移动作为后备
        if move_direction.length() == 0:
            direction = self.target_pos - self.pos
            if direction.length() > 0:
                move_direction = direction.normalize()
        
        # 计算朝向角度
        if move_direction.length() > 0:
            dx = move_direction.x
            dy = move_direction.y
            self.angle = math.degrees(math.atan2(-dy, dx))
        
        # 应用移动速度倍率（追击时可能使用静步接近）
        speed_multiplier = self.get_movement_speed_multiplier()
        
        return {
            'move': move_direction * PLAYER_SPEED * speed_multiplier,
            'angle': self.angle,
            'shoot': False,
            'reload': False
        }
    
    def _attack(self, dt, game_map):
        """攻击行为 - 智能定位和射击"""
        if not self.target_pos:
            return self._patrol(dt, game_map)
        
        # 计算到目标的距离
        direction = self.target_pos - self.pos
        distance = direction.length()
        
        # 计算朝向目标的角度（用于射击）
        if distance > 0:
            dx = direction.x
            dy = direction.y
            target_angle = math.degrees(math.atan2(-dy, dx))
            self.angle = target_angle
        
        # 智能定位：保持最佳攻击距离
        move_direction = pygame.Vector2(0, 0)
        optimal_distance = 180  # 最佳攻击距离
        
        if distance < 120:  # 太近了，需要后退
            # 寻找后退路径
            retreat_pos = self.pos + (self.pos - self.target_pos).normalize() * 100
            self.update_pathfinding(retreat_pos)
            move_direction = self.get_next_move_direction()
            
        elif distance > 250:  # 太远了，需要前进
            # 使用路径规划接近目标
            self.update_pathfinding(self.target_pos)
            move_direction = self.get_next_move_direction()
            
        # 在最佳距离范围内时，进行侧向移动以避免被击中
        elif 120 <= distance <= 250:
            # 计算垂直于目标方向的侧向移动
            if distance > 0:
                perpendicular = pygame.Vector2(-direction.y, direction.x).normalize()
                # 随机选择左右移动方向
                if random.random() > 0.5:
                    perpendicular = -perpendicular
                move_direction = perpendicular * 0.5  # 较慢的侧向移动
        
        # 射击判断 - 必须有视线且不会打到墙
        can_shoot = (not self.is_reloading and 
                    self.ammo > 0 and 
                    time.time() - self.last_shot_time >= BULLET_COOLDOWN and
                    self.target_pos and
                    self.can_shoot_at_target(self.target_pos, game_map))
        
        # 如果没有视线到目标，尝试移动到更好的位置
        if (not can_shoot and self.target_pos and 
            not self.is_reloading and self.ammo > 0):
            if not self.has_line_of_sight(self.target_pos, game_map):
                # 没有视线，需要移动到更好的位置
                # 尝试侧向移动寻找射击角度
                if distance > 0:
                    perpendicular = pygame.Vector2(-direction.y, direction.x).normalize()
                    if random.random() > 0.5:
                        perpendicular = -perpendicular
                    move_direction = perpendicular * 0.8  # 更积极的侧向移动
        
        # 应用移动速度倍率（攻击时通常不使用静步）
        speed_multiplier = self.get_movement_speed_multiplier()
        
        return {
            'move': move_direction * PLAYER_SPEED * 0.7 * speed_multiplier,
            'angle': self.angle,
            'shoot': can_shoot,
            'reload': False
        }
    
    def _retreat(self, dt, game_map):
        """撤退行为 - 智能寻找掩体和撤退路径"""
        if not self.target_pos:
            return self._patrol(dt, game_map)
        
        # 计算撤退目标位置（远离敌人的安全位置）
        retreat_direction = (self.pos - self.target_pos).normalize()
        retreat_distance = 300  # 撤退距离
        retreat_target = self.pos + retreat_direction * retreat_distance
        
        # 确保撤退目标在地图范围内
        map_size = ROOM_SIZE * 3
        retreat_target.x = max(50, min(map_size - 50, retreat_target.x))
        retreat_target.y = max(50, min(map_size - 50, retreat_target.y))
        
        # 使用路径规划找到安全的撤退路径
        self.update_pathfinding(retreat_target)
        move_direction = self.get_next_move_direction()
        
        # 如果路径规划失败，使用直接撤退
        if move_direction.length() == 0:
            direction = self.pos - self.target_pos
            if direction.length() > 0:
                move_direction = direction.normalize()
        
        # 保持面向敌人（边撤退边射击）
        to_enemy = self.target_pos - self.pos
        if to_enemy.length() > 0:
            dx = to_enemy.x
            dy = to_enemy.y
            self.angle = math.degrees(math.atan2(-dy, dx))
        
        # 撤退时也可以射击
        can_shoot = (not self.is_reloading and 
                    self.ammo > 0 and 
                    time.time() - self.last_shot_time >= BULLET_COOLDOWN)
        
        # 应用移动速度倍率（撤退时可能使用静步）
        speed_multiplier = self.get_movement_speed_multiplier()
        
        return {
            'move': move_direction * PLAYER_SPEED * speed_multiplier,
            'angle': self.angle,
            'shoot': can_shoot,
            'reload': False
        }
    
    def _has_line_of_sight(self, start_pos, end_pos, game_map):
        """检查两点之间是否有视线"""
        # 简化的视线检测
        for wall in game_map.walls:
            if self._line_intersects_rect(start_pos, end_pos, wall):
                return False
        
        for door in game_map.doors:
            if not door.is_open and self._line_intersects_rect(start_pos, end_pos, door.rect):
                return False
        
        return True
    
    def _line_intersects_rect(self, start, end, rect):
        """检查线段是否与矩形相交"""
        return rect.clipline(start, end)
    
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
        self.state = 'patrol'
        self.target_player = None
