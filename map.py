import pygame
import random
from pygame.locals import *
from constants import *

class Door:
    """门类，管理门的状态、动画和交互"""
    def __init__(self, x, y, width, height, is_vertical=False):
        self.original_rect = pygame.Rect(x, y, width, height)
        self.rect = pygame.Rect(x, y, width, height)
        self.is_vertical = is_vertical  # 是否是垂直门
        self.is_open = False  # 门是否完全打开
        self.is_opening = False  # 门是否正在打开
        self.is_closing = False  # 门是否正在关闭
        self.animation_progress = 0.0  # 动画进度 (0.0 - 1.0)
        self.interaction_cooldown = 0.5  # 交互冷却时间(秒)
        self.last_interaction_time = 0  # 上次交互时间
        self.state_version = 0  # 门状态版本号，用于同步
    
    def update(self, dt):
        """更新门的状态和动画"""
        # 处理动画
        if self.is_opening:
            self.animation_progress += dt * DOOR_ANIMATION_SPEED
            if self.animation_progress >= 1.0:
                self.animation_progress = 1.0
                self.is_opening = False
                self.is_open = True
        elif self.is_closing:
            self.animation_progress -= dt * DOOR_ANIMATION_SPEED
            if self.animation_progress <= 0.0:
                self.animation_progress = 0.0
                self.is_closing = False
                self.is_open = False
        
        # 更新门的大小和位置
        self.update_rect()
    
    def update_rect(self):
        """根据动画进度更新门的矩形"""
        if self.is_vertical:
            # 垂直门 - 上下方向打开
            new_height = int(self.original_rect.height * (1 - self.animation_progress))
            self.rect.height = max(1, new_height)
            self.rect.y = self.original_rect.y + (self.original_rect.height - new_height) // 2
        else:
            # 水平门 - 左右方向打开
            new_width = int(self.original_rect.width * (1 - self.animation_progress))
            self.rect.width = max(1, new_width)
            self.rect.x = self.original_rect.x + (self.original_rect.width - new_width) // 2
    
    def try_interact(self, player_pos):
        """尝试与门交互，返回是否成功交互"""
        current_time = pygame.time.get_ticks() / 1000
        
        # 检查是否在冷却时间内
        if current_time - self.last_interaction_time < self.interaction_cooldown:
            return False
        
        # 检查玩家是否在交互区域内
        interaction_range = PLAYER_RADIUS * 3  # 交互范围
        door_center = pygame.Vector2(self.original_rect.centerx, self.original_rect.centery)
        distance = (door_center - player_pos).length()
        
        if distance <= interaction_range + max(self.original_rect.width, self.original_rect.height) / 2:
            self.last_interaction_time = current_time
            
            # 切换门的状态
            if self.is_open or self.is_opening:
                self.close()
            else:
                self.open()
            
            self.state_version += 1  # 增加版本号
            return True
        
        return False
    
    def open(self):
        """打开门"""
        if not self.is_open and not self.is_opening:
            self.is_opening = True
            self.is_closing = False
            return True
        return False
    
    def close(self):
        """关闭门"""
        if self.is_open and not self.is_closing:
            self.is_closing = True
            self.is_opening = False
            return True
        return False
    
    def check_collision(self, rect):
        """检查与门的碰撞，如果门打开则不碰撞"""
        if self.is_open:
            return False
        return self.rect.colliderect(rect)
    
    def get_state(self):
        """获取当前门状态"""
        return {
            'is_open': self.is_open,
            'is_opening': self.is_opening,
            'is_closing': self.is_closing,
            'animation_progress': self.animation_progress,
            'version': self.state_version
        }
    
    def set_state(self, state):
        """设置门状态"""
        # 只有版本号更高的状态才会被应用
        if 'version' in state and state['version'] > self.state_version:
            self.is_open = state.get('is_open', False)
            self.is_opening = state.get('is_opening', False)
            self.is_closing = state.get('is_closing', False)
            self.animation_progress = state.get('animation_progress', 0.0)
            self.state_version = state['version']
            self.update_rect()
            return True
        return False
    
    def get_color(self, in_fog=False):
        """根据门的状态返回颜色"""
        base_color = DOOR_COLOR
        bright_color = GREEN
        
        if self.is_open:
            return bright_color
        elif in_fog:
            return DARK_DOOR_COLOR
        else:
            return base_color

class Map:
    """游戏地图类 - 3x3房间网格系统"""
    def __init__(self):
        self.rooms = []
        self.doors = []
        self.walls = []
        self.door_positions = []
        self.generate_map()
    
    def generate_map(self):
        """生成3x3房间网格地图"""
        # 创建3x3房间网格
        for row in range(3):
            for col in range(3):
                x = col * ROOM_SIZE
                y = row * ROOM_SIZE
                self.rooms.append(pygame.Rect(x, y, ROOM_SIZE, ROOM_SIZE))
        
        self.generate_doors()
        self.generate_walls()
    
    def generate_doors(self):
        """生成门并记录位置"""
        # 水平方向的门（左右连接房间）
        for row in range(3):
            for col in range(2):
                door_x = (col + 1) * ROOM_SIZE - WALL_THICKNESS
                door_y = row * ROOM_SIZE + (ROOM_SIZE - DOOR_SIZE) // 2
                
                door = Door(door_x, door_y, WALL_THICKNESS, DOOR_SIZE, is_vertical=False)
                self.doors.append(door)
                self.door_positions.append(door.original_rect)
        
        # 垂直方向的门（上下连接房间）
        for row in range(2):
            for col in range(3):
                door_x = col * ROOM_SIZE + (ROOM_SIZE - DOOR_SIZE) // 2
                door_y = (row + 1) * ROOM_SIZE - WALL_THICKNESS
                
                door = Door(door_x, door_y, DOOR_SIZE, WALL_THICKNESS, is_vertical=True)
                self.doors.append(door)
                self.door_positions.append(door.original_rect)
    
    def generate_walls(self):
        """生成墙壁，避开门的位置"""
        # 外边界墙
        self.walls.append(pygame.Rect(0, 0, ROOM_SIZE * 3, WALL_THICKNESS))
        self.walls.append(pygame.Rect(0, ROOM_SIZE * 3 - WALL_THICKNESS, ROOM_SIZE * 3, WALL_THICKNESS))
        self.walls.append(pygame.Rect(0, 0, WALL_THICKNESS, ROOM_SIZE * 3))
        self.walls.append(pygame.Rect(ROOM_SIZE * 3 - WALL_THICKNESS, 0, WALL_THICKNESS, ROOM_SIZE * 3))
        
        self.generate_internal_walls()
    
    def generate_internal_walls(self):
        """生成内部墙壁，智能避开门的位置"""
        # 垂直内部墙
        for col in range(1, 3):
            wall_x = col * ROOM_SIZE - WALL_THICKNESS
            
            for row in range(3):
                wall_segments = self.get_wall_segments_avoiding_doors(
                    wall_x, row * ROOM_SIZE, WALL_THICKNESS, ROOM_SIZE, is_vertical=True
                )
                self.walls.extend(wall_segments)
        
        # 水平内部墙
        for row in range(1, 3):
            wall_y = row * ROOM_SIZE - WALL_THICKNESS
            
            for col in range(3):
                wall_segments = self.get_wall_segments_avoiding_doors(
                    col * ROOM_SIZE, wall_y, ROOM_SIZE, WALL_THICKNESS, is_vertical=False
                )
                self.walls.extend(wall_segments)
    
    def get_wall_segments_avoiding_doors(self, x, y, width, height, is_vertical):
        """获取避开门的墙壁段"""
        wall_rect = pygame.Rect(x, y, width, height)
        segments = []
        
        overlapping_doors = []
        for door_rect in self.door_positions:
            if wall_rect.colliderect(door_rect):
                overlapping_doors.append(door_rect)
        
        if not overlapping_doors:
            segments.append(wall_rect)
            return segments
        
        if is_vertical:
            overlapping_doors.sort(key=lambda door: door.y)
        else:
            overlapping_doors.sort(key=lambda door: door.x)
        
        if is_vertical:
            current_y = y
            for door in overlapping_doors:
                if current_y < door.y:
                    segments.append(pygame.Rect(x, current_y, width, door.y - current_y))
                current_y = door.y + door.height
            
            if current_y < y + height:
                segments.append(pygame.Rect(x, current_y, width, y + height - current_y))
        else:
            current_x = x
            for door in overlapping_doors:
                if current_x < door.x:
                    segments.append(pygame.Rect(current_x, y, door.x - current_x, height))
                current_x = door.x + door.width
            
            if current_x < x + width:
                segments.append(pygame.Rect(current_x, y, x + width - current_x, height))
        
        return segments
    
    def get_random_spawn_pos(self):
        """获取随机出生位置"""
        room_id = random.randint(0, 8)
        room_row = room_id // 3
        room_col = room_id % 3
        
        spawn_x = room_col * ROOM_SIZE + ROOM_SIZE // 2 + random.randint(-100, 100)
        spawn_y = room_row * ROOM_SIZE + ROOM_SIZE // 2 + random.randint(-100, 100)
        
        spawn_x = max(room_col * ROOM_SIZE + 50, min(spawn_x, (room_col + 1) * ROOM_SIZE - 50))
        spawn_y = max(room_row * ROOM_SIZE + 50, min(spawn_y, (room_row + 1) * ROOM_SIZE - 50))
        
        return [spawn_x, spawn_y]
    
    def update_doors(self, dt, network_manager):
        """更新门状态"""
        for i, door in enumerate(self.doors):
            door.update(dt)
            
            # 从网络管理器同步门状态
            if i in network_manager.doors:
                door_state = network_manager.doors[i]
                door.set_state(door_state)
    
    def update(self, dt):
        """更新地图状态（不包含网络同步）"""
        for door in self.doors:
            door.update(dt)
    
    def draw(self, screen, screen_offset, in_fog=False):
        """绘制地图"""
        # 绘制墙壁
        for wall in self.walls:
            wall_rect = pygame.Rect(wall.x - screen_offset.x, wall.y - screen_offset.y, wall.width, wall.height)
            pygame.draw.rect(screen, DARK_GRAY if in_fog else GRAY, wall_rect)
        
        # 绘制门
        for door in self.doors:
            door_rect = pygame.Rect(door.rect.x - screen_offset.x, door.rect.y - screen_offset.y, 
                                   door.rect.width, door.rect.height)
            pygame.draw.rect(screen, door.get_color(in_fog), door_rect)