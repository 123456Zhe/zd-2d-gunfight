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
    """游戏地图类"""
    def __init__(self):
        self.walls = []
        self.doors = []
        self.initialize_map()
    
    def initialize_map(self):
        """初始化地图"""
        # 创建九宫格地图
        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2
        
        # 创建墙壁
        # 外框墙壁
        self.walls.append(pygame.Rect(center_x - ROOM_SIZE//2, center_y - ROOM_SIZE//2, ROOM_SIZE, WALL_THICKNESS))  # 上
        self.walls.append(pygame.Rect(center_x - ROOM_SIZE//2, center_y + ROOM_SIZE//2 - WALL_THICKNESS, ROOM_SIZE, WALL_THICKNESS))  # 下
        self.walls.append(pygame.Rect(center_x - ROOM_SIZE//2, center_y - ROOM_SIZE//2, WALL_THICKNESS, ROOM_SIZE))  # 左
        self.walls.append(pygame.Rect(center_x + ROOM_SIZE//2 - WALL_THICKNESS, center_y - ROOM_SIZE//2, WALL_THICKNESS, ROOM_SIZE))  # 右
        
        # 创建门
        # 上边门
        self.doors.append(Door(center_x - DOOR_SIZE//2, center_y - ROOM_SIZE//2, DOOR_SIZE, WALL_THICKNESS))
        # 下边门
        self.doors.append(Door(center_x - DOOR_SIZE//2, center_y + ROOM_SIZE//2 - WALL_THICKNESS, DOOR_SIZE, WALL_THICKNESS))
        # 左边门
        self.doors.append(Door(center_x - ROOM_SIZE//2, center_y - DOOR_SIZE//2, WALL_THICKNESS, DOOR_SIZE, True))
        # 右边门
        self.doors.append(Door(center_x + ROOM_SIZE//2 - WALL_THICKNESS, center_y - DOOR_SIZE//2, WALL_THICKNESS, DOOR_SIZE, True))
    
    def update(self, dt):
        """更新地图状态"""
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