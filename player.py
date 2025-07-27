import pygame
import math
import time
from pygame.locals import *
from constants import *

class Player:
    def __init__(self, player_id, x, y, is_local=False):
        self.id = player_id
        self.position = pygame.Vector2(x, y)
        self.velocity = pygame.Vector2(0, 0)
        self.angle = 0  # 角度（度）
        self.is_local = is_local
        
        # 玩家状态
        self.health = 100
        self.is_dead = False
        self.is_respawning = False
        self.respawn_time = 0
        self.last_damage_time = 0
        self.damage_cooldown = 0.5  # 伤害冷却时间
        
        # 被击中减速效果
        self.hit_slowdown_end_time = 0  # 减速结束时间
        
        # 武器系统
        self.current_weapon = 0  # 0: 主武器, 1: 近战武器
        self.weapons = [
            {
                'ammo': 30,
                'max_ammo': 30,
                'reloading': False,
                'reload_start_time': 0,
                'last_shot_time': 0
            },
            {
                'ammo': 1,
                'max_ammo': 1,
                'reloading': False,
                'reload_start_time': 0,
                'last_shot_time': 0
            }
        ]
        
        # 瞄准状态
        self.is_aiming = False
        self.aim_direction = pygame.Vector2(0, 0)
        
        # 动画状态
        self.walking = False
        self.last_walking_time = 0
        self.walking_animation_speed = 0.2  # 行走动画速度
        
        # 近战武器
        self.melee_weapon = MeleeWeapon(self.id)
    
    def update(self, dt):
        """更新玩家状态"""
        if not self.is_dead:
            # 检查是否处于被击中减速状态
            current_time = time.time()
            is_slowed = current_time < self.hit_slowdown_end_time
            
            # 计算实际速度
            actual_velocity = pygame.Vector2(self.velocity)
            if is_slowed:
                actual_velocity *= HIT_SLOWDOWN_FACTOR
            
            # 更新位置
            self.position += actual_velocity * dt
            
            # 更新武器状态
            self.update_weapons(dt)
            
            # 更新近战武器
            self.melee_weapon.update(dt)
            
            # 更新行走动画状态
            if self.velocity.length() > 0:
                self.walking = True
                self.last_walking_time = time.time()
            elif time.time() - self.last_walking_time > self.walking_animation_speed:
                self.walking = False
    
    def update_weapons(self, dt):
        """更新武器状态"""
        for weapon in self.weapons:
            if weapon['reloading']:
                current_time = time.time()
                if current_time - weapon['reload_start_time'] >= RELOAD_TIME:
                    weapon['reloading'] = False
                    weapon['ammo'] = weapon['max_ammo']
    
    def switch_weapon(self):
        """切换武器"""
        if self.is_dead:
            return
            
        self.current_weapon = (self.current_weapon + 1) % len(self.weapons)
    
    def take_damage(self, damage):
        """玩家受到伤害"""
        current_time = time.time()
        if current_time - self.last_damage_time < self.damage_cooldown:
            return False
            
        self.last_damage_time = current_time
        self.health -= damage
        
        # 触发被击中减速效果
        self.hit_slowdown_end_time = current_time + HIT_SLOWDOWN_DURATION
        
        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            self.respawn_time = time.time() + RESPAWN_TIME
            return True
        
        return False
    
    def respawn(self, x, y):
        """玩家复活"""
        self.position.x = x
        self.position.y = y
        self.health = 100
        self.is_dead = False
        self.is_respawning = False
        
        # 重置武器状态
        for weapon in self.weapons:
            weapon['ammo'] = weapon['max_ammo']
            weapon['reloading'] = False
    
    def start_melee_attack(self, is_heavy=False):
        """开始近战攻击"""
        if self.is_dead or self.current_weapon != 1:
            return False
            
        return self.melee_weapon.start_attack(self.angle, is_heavy)
    
    def check_melee_hit(self, targets):
        """检查近战攻击是否击中目标"""
        return self.melee_weapon.check_hit(self.position, targets)
    
    def get_melee_arc_points(self, screen_offset):
        """获取近战攻击弧形的绘制点"""
        return self.melee_weapon.get_attack_arc_points(self.position, screen_offset)
    
    def draw(self, screen, screen_offset, debug_mode=False):
        """绘制玩家"""
        screen_x = self.position.x - screen_offset.x
        screen_y = self.position.y - screen_offset.y
        
        # 绘制玩家
        color = RED if self.is_local else BLUE
        if self.is_dead:
            color = DEAD_COLOR
        
        pygame.draw.circle(screen, color, (int(screen_x), int(screen_y)), PLAYER_RADIUS)
        
        # 绘制方向指示器
        end_x = screen_x + math.cos(math.radians(self.angle)) * PLAYER_RADIUS
        end_y = screen_y - math.sin(math.radians(self.angle)) * PLAYER_RADIUS
        pygame.draw.line(screen, WHITE, (screen_x, screen_y), (end_x, end_y), 2)
        
        # 绘制生命值
        health_width = 40
        health_height = 5
        health_x = screen_x - health_width // 2
        health_y = screen_y - PLAYER_RADIUS - 10
        
        pygame.draw.rect(screen, RED, (health_x, health_y, health_width, health_height))
        pygame.draw.rect(screen, GREEN, (health_x, health_y, health_width * (self.health / 100), health_height))
        
        # 调试信息
        if debug_mode:
            debug_text = f"ID: {self.id} HP: {self.health}"
            debug_surface = small_font.render(debug_text, True, WHITE)
            screen.blit(debug_surface, (screen_x - debug_surface.get_width() // 2, screen_y + PLAYER_RADIUS + 5))