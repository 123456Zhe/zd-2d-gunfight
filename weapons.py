import pygame
import math
import time
from constants import *
from utils import is_visible, normalize_angle, angle_difference, is_in_melee_range, friendly_fire_enabled

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
            if player.id != self.owner_id and not player.is_dead:
                
                # 检查是否是队友（友军伤害开启时不跳过）
                if network_manager and not friendly_fire_enabled(
                    getattr(getattr(network_manager, 'game_instance', None), 'game_rules', None)
                ):
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
                    # 命中判定由服务端权威处理，客户端只做本地视觉移除
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

    def draw(self, surface, camera, player_pos=None, player_angle=None, walls=None, doors=None, is_aiming=False):
        """绘制子弹（考虑视线遮挡）"""
        bullet_screen_pos = camera.to_screen_vec(self.pos)
        
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