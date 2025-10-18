import pygame
import math
import random
import time
from constants import *

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
    
    def _get_decision_interval(self):
        """根据难度获取决策间隔"""
        if self.difficulty == 'easy':
            return random.uniform(0.8, 1.2)
        elif self.difficulty == 'normal':
            return random.uniform(0.4, 0.8)
        else:  # hard
            return random.uniform(0.2, 0.4)
    
    def _get_reaction_time(self):
        """根据难度获取反应时间"""
        if self.difficulty == 'easy':
            return random.uniform(0.5, 1.0)
        elif self.difficulty == 'normal':
            return random.uniform(0.2, 0.5)
        else:  # hard
            return random.uniform(0.1, 0.2)
    
    def _get_accuracy(self):
        """根据难度获取射击精度（角度偏差）"""
        if self.difficulty == 'easy':
            return random.uniform(15, 30)
        elif self.difficulty == 'normal':
            return random.uniform(5, 15)
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
        
        # 决策更新
        if current_time - self.last_decision_time >= self.decision_interval:
            self.last_decision_time = current_time
            self.make_decision(players, game_map)
        
        # 执行当前状态的行为
        action = self.execute_state(dt, players, game_map, bullets)
        
        return action
    
    def make_decision(self, players, game_map):
        """AI决策逻辑"""
        # 查找最近的敌人
        closest_enemy = None
        min_distance = float('inf')
        
        for player_id, player_data in players.items():
            if player_id == self.id or player_data.get('is_dead', False):
                continue
            
            player_pos = pygame.Vector2(player_data['pos'])
            distance = self.pos.distance_to(player_pos)
            
            # 检查视线（简化：只检查距离，不检查墙壁）
            # 这样AI会更积极地寻找敌人
            if distance < 600:  # 视野范围
                if distance < min_distance:
                    min_distance = distance
                    closest_enemy = (player_id, player_pos)
        
        # 根据距离和状态决定行为
        if closest_enemy:
            self.target_player = closest_enemy[0]
            self.target_pos = pygame.Vector2(closest_enemy[1])  # 确保是Vector2
            self.last_seen_enemy_time = time.time()
            
            if min_distance < 150:  # 近距离
                if self.health < 30:
                    self.state = 'retreat'
                else:
                    self.state = 'attack'
            elif min_distance < 400:  # 中距离
                self.state = 'attack'  # 改为直接攻击
            else:  # 远距离
                self.state = 'chase'
        else:
            # 没有发现敌人，继续巡逻
            if time.time() - self.last_seen_enemy_time > 3.0:
                self.state = 'patrol'
                self.target_player = None
                self.target_pos = None
    
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
        """巡逻行为"""
        if not self.patrol_points:
            self.generate_patrol_points(game_map)
        
        target = self.patrol_points[self.current_patrol_index]
        direction = target - self.pos
        
        if direction.length() < 50:
            # 到达巡逻点，前往下一个
            self.current_patrol_index = (self.current_patrol_index + 1) % len(self.patrol_points)
            target = self.patrol_points[self.current_patrol_index]
            direction = target - self.pos
        
        move_direction = pygame.Vector2(0, 0)
        if direction.length() > 0:
            move_direction = direction.normalize()
            # 正确计算角度
            dx = direction.x
            dy = direction.y
            self.angle = math.degrees(math.atan2(-dy, dx))
        
        return {
            'move': move_direction * PLAYER_SPEED,
            'angle': self.angle,
            'shoot': False,
            'reload': False
        }
    
    def _chase(self, dt, game_map):
        """追击行为"""
        if not self.target_pos:
            return self._patrol(dt, game_map)
        
        direction = self.target_pos - self.pos
        move_direction = pygame.Vector2(0, 0)
        if direction.length() > 0:
            move_direction = direction.normalize()
            # 正确计算角度
            dx = direction.x
            dy = direction.y
            self.angle = math.degrees(math.atan2(-dy, dx))
        
        return {
            'move': move_direction * PLAYER_SPEED,
            'angle': self.angle,
            'shoot': False,
            'reload': False
        }
    
    def _attack(self, dt, game_map):
        """攻击行为"""
        if not self.target_pos:
            return self._patrol(dt, game_map)
        
        # 计算朝向目标的角度
        direction = self.target_pos - self.pos
        distance = direction.length()
        
        if distance > 0:
            # 正确计算角度：atan2(dy, dx)，注意Y轴方向
            dx = direction.x
            dy = direction.y
            target_angle = math.degrees(math.atan2(-dy, dx))
            self.angle = target_angle
        
        # 保持距离并射击
        move_direction = pygame.Vector2(0, 0)
        
        if distance < 120:  # 太近了，后退
            if distance > 0:
                move_direction = -direction.normalize()
        elif distance > 250:  # 太远了，前进
            if distance > 0:
                move_direction = direction.normalize()
        # 在120-250之间保持位置，只射击
        
        # 射击（只有在有弹药且不在装填时才射击）
        can_shoot = (not self.is_reloading and 
                    self.ammo > 0 and 
                    time.time() - self.last_shot_time >= BULLET_COOLDOWN)
        
        return {
            'move': move_direction * PLAYER_SPEED * 0.6,  # 攻击时移动速度
            'angle': self.angle,
            'shoot': can_shoot,
            'reload': False
        }
    
    def _retreat(self, dt, game_map):
        """撤退行为"""
        if not self.target_pos:
            return self._patrol(dt, game_map)
        
        # 远离目标
        direction = self.pos - self.target_pos
        move_direction = pygame.Vector2(0, 0)
        if direction.length() > 0:
            move_direction = direction.normalize()
        
        # 朝向敌人（保持面向敌人边撤退边射击）
        to_enemy = self.target_pos - self.pos
        if to_enemy.length() > 0:
            dx = to_enemy.x
            dy = to_enemy.y
            self.angle = math.degrees(math.atan2(-dy, dx))
        
        # 撤退时也可以射击
        can_shoot = (not self.is_reloading and 
                    self.ammo > 0 and 
                    time.time() - self.last_shot_time >= BULLET_COOLDOWN)
        
        if can_shoot:
            self.last_shot_time = time.time()
        
        return {
            'move': move_direction * PLAYER_SPEED,
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
