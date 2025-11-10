import pygame
import math
import time
from constants import *
from utils import is_visible, normalize_angle, angle_difference, is_in_melee_range

def ray_cast(start_pos, direction, max_distance, obstacles):
    """射线检测函数"""
    # 创建射线终点
    end_pos = pygame.Vector2(
        start_pos.x + math.cos(math.radians(direction)) * max_distance,
        start_pos.y - math.sin(math.radians(direction)) * max_distance
    )
    
    # 检查与障碍物的碰撞
    for obstacle in obstacles:
        if obstacle.clipline((start_pos, end_pos)):
            return True
    
    return False


class Ray:
    """射线类 - 用于即时命中检测"""
    def __init__(self, start_pos, direction, owner_id, game_map, players, custom_speed=None):
        self.start_pos = pygame.Vector2(start_pos)
        self.direction = pygame.Vector2(direction).normalize()
        self.owner_id = owner_id
        self.game_map = game_map
        self.players = players
        # 使用自定义速度或默认值
        self.speed = custom_speed if custom_speed is not None else BULLET_SPEED
        self.damage = BULLET_DAMAGE
        self.max_distance = 500  # 射线最大距离
        self.distance_traveled = 0
        self.end_pos = self.start_pos  # 射线终点
        self.hit_player = None  # 被击中的玩家
        self.hit_wall = False  # 是否击中墙壁
        
        # 曳光弹效果
        self.trail_points = [self.start_pos]  # 轨迹点
        self.trail_lifetime = 0.5  # 轨迹持续时间
        self.trail_creation_time = time.time()
        
        # 执行射线检测
        self.cast_ray()
    
    def cast_ray(self):
        """执行射线检测"""
        # 计算射线终点
        self.end_pos = self.start_pos + self.direction * self.max_distance
        
        # 检查与玩家的碰撞
        closest_hit = None
        closest_distance = float('inf')
        
        for player in self.players.values():
            if player.id != self.owner_id and not player.is_dead:
                # 计算射线与玩家的交点
                player_center = player.pos
                player_radius = PLAYER_RADIUS
                
                # 使用向量投影计算最近点
                to_player = player_center - self.start_pos
                projection = to_player.dot(self.direction)
                
                # 确保交点在射线上
                if 0 <= projection <= self.max_distance:
                    closest_point = self.start_pos + self.direction * projection
                    distance_to_player = closest_point.distance_to(player_center)
                    
                    # 检查是否击中玩家
                    if distance_to_player <= player_radius:
                        if projection < closest_distance:
                            closest_distance = projection
                            closest_hit = player
        
        # 检查与墙壁的碰撞
        for wall in self.game_map.walls:
            if self.line_intersects_rect(self.start_pos, self.end_pos, wall):
                # 计算交点
                intersection = self.get_line_rect_intersection(self.start_pos, self.end_pos, wall)
                if intersection:
                    distance = self.start_pos.distance_to(intersection)
                    if distance < closest_distance:
                        closest_distance = distance
                        closest_hit = None  # 击中墙壁
        
        # 检查与门的碰撞
        for door in self.game_map.doors:
            if not door.is_open and self.line_intersects_rect(self.start_pos, self.end_pos, door.rect):
                intersection = self.get_line_rect_intersection(self.start_pos, self.end_pos, door.rect)
                if intersection:
                    distance = self.start_pos.distance_to(intersection)
                    if distance < closest_distance:
                        closest_distance = distance
                        closest_hit = None  # 击中门
        
        # 设置射线终点
        if closest_distance < float('inf'):
            self.end_pos = self.start_pos + self.direction * closest_distance
            if closest_hit:
                self.hit_player = closest_hit
        else:
            self.hit_wall = True
        
        # 更新轨迹点
        self.trail_points = [self.start_pos, self.end_pos]
    
    def line_intersects_rect(self, start, end, rect):
        """检查线段是否与矩形相交"""
        # 获取矩形的四条边
        left = rect.left
        right = rect.right
        top = rect.top
        bottom = rect.bottom
        
        # 检查线段是否与矩形的四条边相交
        # 左边
        if self.line_intersects_line(start, end, (left, top), (left, bottom)):
            return True
        # 右边
        if self.line_intersects_line(start, end, (right, top), (right, bottom)):
            return True
        # 上边
        if self.line_intersects_line(start, end, (left, top), (right, top)):
            return True
        # 下边
        if self.line_intersects_line(start, end, (left, bottom), (right, bottom)):
            return True
        
        return False
    
    def line_intersects_line(self, p1, p2, p3, p4):
        """检查两条线段是否相交"""
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4
        
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 0.0001:
            return False
        
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
        
        return 0 <= t <= 1 and 0 <= u <= 1
    
    def get_line_rect_intersection(self, start, end, rect):
        """获取线段与矩形的交点"""
        # 检查与四条边的交点
        edges = [
            ((rect.left, rect.top), (rect.left, rect.bottom)),  # 左边
            ((rect.right, rect.top), (rect.right, rect.bottom)),  # 右边
            ((rect.left, rect.top), (rect.right, rect.top)),  # 上边
            ((rect.left, rect.bottom), (rect.right, rect.bottom))  # 下边
        ]
        
        closest_point = None
        min_distance = float('inf')
        
        for edge in edges:
            intersection = self.get_line_line_intersection(start, end, edge[0], edge[1])
            if intersection:
                distance = start.distance_to(intersection)
                if distance < min_distance:
                    min_distance = distance
                    closest_point = intersection
        
        return closest_point
    
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
    
    def get_hit_player(self):
        """获取被击中的玩家"""
        return self.hit_player
    
    def is_expired(self):
        """检查轨迹是否过期"""
        return time.time() - self.trail_creation_time > self.trail_lifetime
    
    def draw(self, surface, camera_offset, player_pos=None, player_angle=None, walls=None, doors=None, is_aiming=False):
        """绘制射线和曳光弹效果"""
        # 计算屏幕坐标
        start_screen = pygame.Vector2(
            self.start_pos.x - camera_offset.x,
            self.start_pos.y - camera_offset.y
        )
        end_screen = pygame.Vector2(
            self.end_pos.x - camera_offset.x,
            self.end_pos.y - camera_offset.y
        )
        
        # 根据瞄准状态选择视野角度
        current_fov = 30 if is_aiming else 120
        
        # 检查射线是否可见（在视野内且无遮挡）
        if player_pos and player_angle and walls and doors:
            if not is_visible(player_pos, player_angle, self.start_pos, current_fov, walls, doors):
                return  # 不可见，不绘制
        
        # 绘制曳光弹轨迹
        if len(self.trail_points) >= 2:
            # 计算轨迹点的屏幕坐标
            screen_points = []
            for point in self.trail_points:
                screen_point = pygame.Vector2(
                    point.x - camera_offset.x,
                    point.y - camera_offset.y
                )
                screen_points.append(screen_point)
            
            # 绘制轨迹线
            pygame.draw.lines(surface, YELLOW, False, [(int(p.x), int(p.y)) for p in screen_points], 3)
        
        # 绘制射线终点的光晕效果
        pygame.draw.circle(surface, YELLOW, (int(end_screen.x), int(end_screen.y)), 8, 1)
        pygame.draw.circle(surface, (255, 255, 200), (int(end_screen.x), int(end_screen.y)), 4)


class MeleeWeapon:
    """近战武器类"""
    def __init__(self, owner_id):
        self.owner_id = owner_id
        self.damage = MELEE_DAMAGE
        self.range = MELEE_RANGE
        self.angle = MELEE_ANGLE
        self.cooldown = MELEE_COOLDOWN
        self.animation_time = MELEE_ANIMATION_TIME
        
        # 重击属性
        self.heavy_damage = HEAVY_MELEE_DAMAGE  # 使用专门的重击伤害
        self.heavy_range = HEAVY_MELEE_RANGE    # 重击范围
        self.heavy_angle = HEAVY_MELEE_ANGLE    # 重击角度
        self.heavy_cooldown = HEAVY_MELEE_COOLDOWN  # 使用专门的重击冷却时间
        self.heavy_animation_time = HEAVY_MELEE_ANIMATION_TIME  # 使用专门的重击动画时间
        
        # 攻击状态
        self.is_attacking = False
        self.is_heavy_attack = False  # 是否为重击
        self.attack_start_time = 0
        self.last_attack_time = 0
        self.attack_direction = 0  # 攻击方向
        
        # 已击中的目标（防止一次攻击击中多次）
        self.hit_targets = set()
    
    def can_attack(self, is_heavy=False):
        """检查是否可以攻击"""
        current_time = time.time()
        # 重击使用更长的冷却时间
        cooldown = self.heavy_cooldown if is_heavy else self.cooldown
        return current_time - self.last_attack_time >= cooldown
    
    def start_attack(self, direction, is_heavy=False):
        """开始攻击"""
        if not self.can_attack(is_heavy):
            return False
        
        current_time = time.time()
        self.is_attacking = True
        self.is_heavy_attack = is_heavy  # 记录是否为重击
        self.attack_start_time = current_time
        self.last_attack_time = current_time
        self.attack_direction = direction
        
        # 根据攻击类型设置属性
        if is_heavy:
            self.animation_time = self.heavy_animation_time
            self.range = self.heavy_range
            self.angle = self.heavy_angle
        else:
            self.animation_time = MELEE_ANIMATION_TIME
            self.range = MELEE_RANGE
            self.angle = MELEE_ANGLE
        
        self.hit_targets.clear()
        return True
    
    def update(self, dt):
        """更新武器状态"""
        if self.is_attacking:
            current_time = time.time()
            if current_time - self.attack_start_time >= self.animation_time:
                self.is_attacking = False
    
    def get_attack_progress(self):
        """获取攻击动画进度 (0.0 - 1.0)"""
        if not self.is_attacking:
            return 0.0
        
        current_time = time.time()
        elapsed = current_time - self.attack_start_time
        return min(elapsed / self.animation_time, 1.0)
    
    def get_damage(self):
        """获取当前攻击的伤害值"""
        if self.is_heavy_attack:
            return self.heavy_damage
        else:
            return self.damage
    
    def _get_current_attack_params(self):
        """获取当前攻击的参数（范围和角度）"""
        if self.is_heavy_attack:
            return self.heavy_range, self.heavy_angle
        else:
            return self.range, self.angle
    
    def check_hit(self, attacker_pos, targets, obstacles=None):
        """检查攻击是否击中目标"""
        if not self.is_attacking:
            return []
        
        # 根据是否为重击选择相应的范围和角度
        current_range, current_angle = self._get_current_attack_params()
        
        hit_list = []
        for target_id, target_pos in targets.items():
            if (target_id != self.owner_id and 
                target_id not in self.hit_targets):
                
                # 首先检查角度和距离
                if is_in_melee_range(attacker_pos, self.attack_direction, target_pos, current_range, current_angle):
                    # 如果有障碍物，进行射线检测
                    if obstacles is not None:
                        # 计算到目标的角度
                        dx = target_pos.x - attacker_pos.x
                        dy = target_pos.y - attacker_pos.y
                        target_angle = math.degrees(math.atan2(-dy, dx))
                        
                        # 进行射线检测
                        if not ray_cast(attacker_pos, target_angle, current_range, obstacles):
                            self.hit_targets.add(target_id)
                            hit_list.append(target_id)
                    else:
                        # 没有障碍物时直接命中
                        self.hit_targets.add(target_id)
                        hit_list.append(target_id)
        
        return hit_list
    
    def get_attack_arc_points(self, attacker_pos, screen_offset):
        """获取攻击弧形的绘制点"""
        if not self.is_attacking:
            return []
        
        # 根据是否为重击选择相应的范围和角度
        current_range, current_angle = self._get_current_attack_params()
        
        progress = self.get_attack_progress()
        actual_angle = current_angle * progress  # 随着动画进度增加攻击角度
        
        points = []
        half_angle = actual_angle / 2
        
        # 生成攻击弧形的点
        for i in range(int(actual_angle) + 1):
            angle = self.attack_direction - half_angle + i
            angle_rad = math.radians(angle)
            
            # 计算弧形上的点
            end_x = attacker_pos.x + math.cos(angle_rad) * current_range
            end_y = attacker_pos.y - math.sin(angle_rad) * current_range
            
            # 转换为屏幕坐标
            screen_x = end_x - screen_offset.x
            screen_y = end_y - screen_offset.y
            points.append((screen_x, screen_y))
        
        return points

class Bullet:
    """子弹类 - 用于网络同步的子弹"""
    def __init__(self, bullet_data, custom_speed=None):
        self.id = bullet_data['id']
        self.pos = pygame.Vector2(bullet_data['pos'])
        self.direction = pygame.Vector2(bullet_data['dir']).normalize()
        self.owner_id = bullet_data['owner']
        # 使用自定义速度或默认值
        self.speed = custom_speed if custom_speed is not None else BULLET_SPEED
        self.radius = BULLET_RADIUS
        self.creation_time = bullet_data['time']
        self.has_hit = set()

    def update(self, dt, game_map, players, network_manager=None):
        """更新子弹位置并检测碰撞"""
        self.pos += self.direction * self.speed * dt
        
        bullet_rect = pygame.Rect(
            self.pos.x - self.radius,
            self.pos.y - self.radius,
            self.radius * 2,
            self.radius * 2
        )
        
        # 检查与其他玩家的碰撞
        for player in players.values():
            if (player.id != self.owner_id and 
                not player.is_dead and 
                player.id not in self.has_hit):
                
                # 检查是否是队友（团队系统）
                if network_manager:
                    game_instance = getattr(network_manager, 'game_instance', None)
                    # 先用团队管理器判定
                    if game_instance and hasattr(game_instance, 'team_manager'):
                        if game_instance.team_manager.are_teammates(self.owner_id, player.id):
                            continue
                    # 回退：直接比较双方的team_id（网络数据或对象属性）
                    try:
                        owner_team_id = None
                        target_team_id = None
                        if hasattr(network_manager, 'players'):
                            owner_team_id = network_manager.players.get(self.owner_id, {}).get('team_id', None)
                            target_team_id = network_manager.players.get(player.id, {}).get('team_id', None)
                        if owner_team_id is None and game_instance:
                            # 从游戏实例对象获取（玩家或AI）
                            if hasattr(game_instance, 'players') and self.owner_id in getattr(game_instance, 'players', {}):
                                owner_team_id = getattr(game_instance.players[self.owner_id], 'team_id', None)
                            if hasattr(game_instance, 'ai_players') and self.owner_id in getattr(game_instance, 'ai_players', {}):
                                owner_team_id = getattr(game_instance.ai_players[self.owner_id], 'team_id', None)
                        if target_team_id is None:
                            target_team_id = getattr(player, 'team_id', None)
                        if owner_team_id is not None and target_team_id is not None and owner_team_id == target_team_id:
                            continue
                    except Exception:
                        pass
                
                player_rect = pygame.Rect(
                    player.pos.x - PLAYER_RADIUS,
                    player.pos.y - PLAYER_RADIUS,
                    PLAYER_RADIUS * 2,
                    PLAYER_RADIUS * 2
                )
                if bullet_rect.colliderect(player_rect):
                    self.has_hit.add(player.id)
                    
                    print(f"[子弹碰撞] 子弹{self.id}击中玩家{player.id}，所有者{self.owner_id}")
                    
                    if network_manager:
                        damage_data = {
                            'target_id': player.id,
                            'damage': BULLET_DAMAGE,
                            'attacker_id': self.owner_id,
                            'type': 'bullet'
                        }
                        
                        # 服务端直接处理伤害
                        if network_manager.is_server:
                            print(f"[服务端] 直接处理伤害: 玩家{player.id}受到{BULLET_DAMAGE}伤害")
                            network_manager._handle_damage(damage_data)
                        else:
                            # 客户端发送伤害请求
                            print(f"[客户端] 发送伤害请求: 玩家{player.id}受到{BULLET_DAMAGE}伤害")
                            network_manager.send_data({
                                'type': 'hit_damage',
                                'data': damage_data
                            })
                    
                    return True
        
        # 碰撞墙壁检测
        for wall in game_map.walls:
            if bullet_rect.colliderect(wall):
                return True
                
        # 检测门碰撞
        for door in game_map.doors:
            if door.check_collision(bullet_rect):
                return True
                
        return False

    def draw(self, surface, camera_offset, player_pos=None, player_angle=None, walls=None, doors=None, is_aiming=False):
        """绘制子弹（考虑视线遮挡）"""
        bullet_screen_pos = pygame.Vector2(
            self.pos.x - camera_offset.x,
            self.pos.y - camera_offset.y
        )
        
        # 根据瞄准状态选择视野角度
        current_fov = 30 if is_aiming else 120
        
        # 检查子弹是否可见（在视野内且无遮挡）
        if player_pos and player_angle and walls and doors:
            if not is_visible(player_pos, player_angle, self.pos, current_fov, walls, doors):
                return  # 不可见，不绘制
        
        pygame.draw.circle(
            surface, YELLOW,
            (int(bullet_screen_pos.x), int(bullet_screen_pos.y)),
            self.radius
        )