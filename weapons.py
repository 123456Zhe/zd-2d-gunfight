import pygame
import math
import time
from constants import *

def normalize_angle(angle):
    """将角度标准化到-180到180度范围"""
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return angle

def angle_difference(angle1, angle2):
    """计算两个角度之间的最小差值"""
    diff = abs(normalize_angle(angle1) - normalize_angle(angle2))
    return min(diff, 360 - diff)

def is_in_melee_range(attacker_pos, attacker_angle, target_pos, melee_range, melee_angle):
    """检查目标是否在近战攻击范围内"""
    # 计算距离
    distance = (target_pos - attacker_pos).length()
    if distance > melee_range:
        return False
    
    # 计算角度
    dx = target_pos.x - attacker_pos.x
    dy = target_pos.y - attacker_pos.y
    target_angle = math.degrees(math.atan2(-dy, dx))
    
    # 检查是否在攻击角度范围内
    angle_diff = angle_difference(attacker_angle, target_angle)
    return angle_diff <= melee_angle / 2

class MeleeWeapon:
    """近战武器类"""
    def __init__(self, owner_id):
        self.owner_id = owner_id
        self.damage = MELEE_DAMAGE
        self.range = MELEE_RANGE
        self.angle = MELEE_ANGLE
        self.cooldown = MELEE_COOLDOWN
        self.animation_time = MELEE_ANIMATION_TIME
        
        # 攻击状态
        self.is_attacking = False
        self.attack_start_time = 0
        self.last_attack_time = 0
        self.attack_direction = 0  # 攻击方向
        
        # 已击中的目标（防止一次攻击击中多次）
        self.hit_targets = set()
    
    def can_attack(self):
        """检查是否可以攻击"""
        current_time = time.time()
        return current_time - self.last_attack_time >= self.cooldown
    
    def start_attack(self, direction):
        """开始攻击"""
        if not self.can_attack():
            return False
        
        current_time = time.time()
        self.is_attacking = True
        self.attack_start_time = current_time
        self.last_attack_time = current_time
        self.attack_direction = direction
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
    
    def check_hit(self, attacker_pos, targets):
        """检查攻击是否击中目标"""
        if not self.is_attacking:
            return []
        
        hit_list = []
        for target_id, target_pos in targets.items():
            if (target_id != self.owner_id and 
                target_id not in self.hit_targets and
                is_in_melee_range(attacker_pos, self.attack_direction, target_pos, self.range, self.angle)):
                
                self.hit_targets.add(target_id)
                hit_list.append(target_id)
        
        return hit_list
    
    def get_attack_arc_points(self, attacker_pos, screen_offset):
        """获取攻击弧形的绘制点"""
        if not self.is_attacking:
            return []
        
        progress = self.get_attack_progress()
        current_angle = self.angle * progress  # 随着动画进度增加攻击角度
        
        points = []
        half_angle = current_angle / 2
        
        # 生成攻击弧形的点
        for i in range(int(current_angle) + 1):
            angle = self.attack_direction - half_angle + i
            angle_rad = math.radians(angle)
            
            # 计算弧形上的点
            end_x = attacker_pos.x + math.cos(angle_rad) * self.range
            end_y = attacker_pos.y - math.sin(angle_rad) * self.range
            
            # 转换为屏幕坐标
            screen_x = end_x - screen_offset.x
            screen_y = end_y - screen_offset.y
            points.append((screen_x, screen_y))
        
        return points

class Bullet:
    """子弹类"""
    def __init__(self, owner_id, x, y, angle):
        self.owner_id = owner_id
        self.position = pygame.Vector2(x, y)
        self.velocity = pygame.Vector2(
            math.cos(math.radians(angle)) * BULLET_SPEED,
            -math.sin(math.radians(angle)) * BULLET_SPEED
        )
        self.creation_time = time.time()
    
    def update(self, dt):
        """更新子弹位置"""
        self.position += self.velocity * dt
    
    def draw(self, screen, screen_offset):
        """绘制子弹"""
        screen_x = self.position.x - screen_offset.x
        screen_y = self.position.y - screen_offset.y
        pygame.draw.circle(screen, YELLOW, (int(screen_x), int(screen_y)), BULLET_RADIUS)