
import pygame
import math
import random
import sys
import socket
import threading
import json
import time
from pygame.locals import *

# 初始化pygame
pygame.init()
pygame.font.init()

# 尝试加载中文字体
try:
    font = pygame.font.SysFont('Microsoft YaHei', 24)
except:
    try:
        font = pygame.font.SysFont('SimHei', 24)
    except:
        font = pygame.font.Font(None, 24)

# 游戏配置
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
FPS = 60
PLAYER_SPEED = 200
BULLET_SPEED = 500
BULLET_COOLDOWN = 0.15  # 连发间隔
RELOAD_TIME = 2.0
MAGAZINE_SIZE = 30
PLAYER_RADIUS = 20
BULLET_RADIUS = 5
ROOM_SIZE = 600
WALL_THICKNESS = 20
DOOR_SIZE = 80
DOOR_ANIMATION_SPEED = 2.0  # 门动画速度
SERVER_PORT = 5555
BUFFER_SIZE = 4096

# 颜色定义
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
YELLOW = (255, 255, 0)
DOOR_COLOR = (139, 69, 19)

class GameMap:
    def __init__(self):
        self.walls = []
        self.doors = []
        self.create_map()
    
    def create_map(self):
        # 创建房间墙壁
        room_rect = pygame.Rect(
            (SCREEN_WIDTH - ROOM_SIZE) // 2,
            (SCREEN_HEIGHT - ROOM_SIZE) // 2,
            ROOM_SIZE,
            ROOM_SIZE
        )
        
        # 添加四周墙壁
        self.walls.append(pygame.Rect(room_rect.left, room_rect.top, WALL_THICKNESS, ROOM_SIZE))  # 左墙
        self.walls.append(pygame.Rect(room_rect.right - WALL_THICKNESS, room_rect.top, WALL_THICKNESS, ROOM_SIZE))  # 右墙
        self.walls.append(pygame.Rect(room_rect.left, room_rect.top, ROOM_SIZE, WALL_THICKNESS))  # 上墙
        self.walls.append(pygame.Rect(room_rect.left, room_rect.bottom - WALL_THICKNESS, ROOM_SIZE, WALL_THICKNESS))  # 下墙
        
        # 添加门(修正位置在房间内部)
        self.doors.append({
            'rect': pygame.Rect(room_rect.centerx - DOOR_SIZE//2, room_rect.top, DOOR_SIZE, WALL_THICKNESS),
            'fully_open': False,
            'opening': False,
            'vertical': False,
            'animation_progress': 0,
            'original_rect': pygame.Rect(room_rect.centerx - DOOR_SIZE//2, room_rect.top, DOOR_SIZE, WALL_THICKNESS)
        })
    
    def update_doors(self, dt):
        for door in self.doors:
            if door['opening'] and not door['fully_open']:
                door['animation_progress'] += dt * DOOR_ANIMATION_SPEED
                if door['animation_progress'] >= 1:
                    door['fully_open'] = True
                    door['opening'] = False
                    door['animation_progress'] = 1
                
                if door['vertical']:
                    door['rect'].height = int(door['original_rect'].height * (1 - door['animation_progress']))
                else:
                    door['rect'].width = int(door['original_rect'].width * (1 - door['animation_progress']))
    
    def draw(self, surface, camera_offset):
        # 绘制墙壁
        for wall in self.walls:
            pygame.draw.rect(surface, GRAY, 
                           (wall.x - camera_offset.x, wall.y - camera_offset.y, 
                            wall.width, wall.height))
        
        # 绘制门
        for door in self.doors:
            if not door['fully_open']:
                pygame.draw.rect(surface, DOOR_COLOR,
                               (door['rect'].x - camera_offset.x, door['rect'].y - camera_offset.y,
                                door['rect'].width, door['rect'].height))

class NetworkManager:
    def __init__(self, player_id, server_address=None):
        self.player_id = player_id
        self.is_server = (player_id == 1)  # 判断是否是服务器
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.players = {}
        self.bullets = []
        self.doors = []
        self.lock = threading.Lock()
        self.running = True
        self.clients = set()  # 存储连接的客户端地址
        
        if self.is_server:
            self.socket.bind(('0.0.0.0', SERVER_PORT))
            self.server_address = ('0.0.0.0', SERVER_PORT)  # 服务端也需要设置server_address
            print("服务器已启动，等待连接...")
            # 初始化服务端玩家数据
            self.players[player_id] = {
                'pos': [SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2],
                'angle': 0,
                'health': 100,
                'ammo': MAGAZINE_SIZE,
                'is_reloading': False,
                'shooting': False
            }
        else:
            self.server_address = server_address
            self.socket.sendto(f"connect:{player_id}".encode(), (self.server_address, SERVER_PORT))
            print(f"玩家{player_id}已连接服务器")
        
        # 启动接收线程
        self.receive_thread = threading.Thread(target=self.receive_data)
        self.receive_thread.daemon = True
        self.receive_thread.start()
    
    def receive_data(self):
        while self.running:
            try:
                data, addr = self.socket.recvfrom(BUFFER_SIZE)
                try:
                    message = json.loads(data.decode())
                    if not isinstance(message, dict) or 't' not in message:
                        continue
                except:
                    continue
                
                with self.lock:
                    # 消息类型映射
                    msg_handlers = {
                        'c': lambda: self._handle_connect(int(message['d'])) if 'd' in message else None,
                        'p': lambda: self._update_players(message['d']) if isinstance(message.get('d'), dict) else None,
                        'i': lambda: self._init_players(message['d']) if isinstance(message.get('d'), dict) else None,
                        'b': lambda: self._update_bullets(message['d']) if isinstance(message.get('d'), list) else None,
                        'd': lambda: self._update_door(message['d']) if isinstance(message.get('d'), dict) else None
                    }
                    
                    if message['t'] in msg_handlers:
                        msg_handlers[message['t']]()
                        
                    # 记录新客户端
                    if self.is_server and addr not in self.clients:
                        self.clients.add(addr)
                        
            except Exception:
                continue  # 忽略无效数据包

    def _handle_connect(self, player_id):
        if self.is_server:
            self.send_data({
                'type': 'init_players',
                'data': self.players
            })

    def _update_bullets(self, bullet_data):
        """处理子弹数据更新"""
        valid_bullets = []
        for bullet in bullet_data:
            try:
                if all(key in bullet for key in ['pos', 'direction', 'owner_id']):
                    valid_bullets.append({
                        'pos': bullet['pos'],
                        'direction': bullet['direction'],
                        'owner_id': int(bullet['owner_id'])
                    })
            except (ValueError, TypeError):
                continue
        self.bullets = valid_bullets

    def _update_players(self, player_data):
        """更新玩家数据"""
        if not isinstance(player_data, dict):
            return
            
        valid_players = {}
        for pid, pdata in player_data.items():
            try:
                pid = int(pid)
                if all(key in pdata for key in ['pos', 'angle', 'health', 'ammo', 'is_reloading', 'shooting']):
                    valid_players[pid] = pdata
            except (ValueError, TypeError):
                continue
        self.players.update(valid_players)

    def _init_players(self, player_data):
        """初始化玩家数据"""
        if not self.is_server and isinstance(player_data, dict):
            self._update_players(player_data)

    def _update_door(self, door_data):
        """更新门状态"""
        if isinstance(door_data, dict) and all(key in door_data for key in ['i', 'r', 'f', 'o', 'p']):
            if door_data['i'] < len(self.doors):
                try:
                    door = self.doors[door_data['i']]
                    door.update({
                        'rect': pygame.Rect(*door_data['r']),
                        'fully_open': bool(door_data['f']),
                        'opening': bool(door_data['o']),
                        'animation_progress': float(door_data['p'])
                    })
                except (TypeError, ValueError):
                    pass
    
    def send_data(self, data):
        # 精简数据格式
        packet = {
            't': data['type'][0],  # 消息类型首字母
            'd': data['data']      # 原始数据
        }

        # 服务端强制包含自身数据
        if self.is_server and packet['t'] == 'p' and 1 not in packet['d']:
            packet['d'][1] = self.players[1]

        # 统一发送逻辑
        try:
            serialized = json.dumps(packet).encode()
            if self.is_server:
                for addr in self.clients:
                    self.socket.sendto(serialized, addr)
            else:
                self.socket.sendto(serialized, (self.server_address, SERVER_PORT))
        except Exception:
            pass  # 静默失败，依赖上层重试
            # 重连逻辑
            if not self.running:
                return
            time.sleep(1)
            try:
                if self.is_server:
                    self.socket.bind(('0.0.0.0', SERVER_PORT))
                else:
                    self.socket.sendto(f"reconnect:{self.player_id}".encode(), (self.server_address, SERVER_PORT))
            except:
                pass
    
    def stop(self):
        self.running = False
        self.socket.close()

class Bullet:
    def __init__(self, pos, direction, owner_id):
        self.pos = pygame.Vector2(pos)
        self.direction = pygame.Vector2(direction).normalize()
        self.owner_id = owner_id
        self.speed = BULLET_SPEED
        self.radius = BULLET_RADIUS
        self.lifetime = 3.0  # 子弹存在时间(秒)

    def update(self, dt, game_map):
        self.pos += self.direction * self.speed * dt
        self.lifetime -= dt
        
        if self.lifetime <= 0:
            return True
            
        bullet_rect = pygame.Rect(
            self.pos.x - self.radius,
            self.pos.y - self.radius,
            self.radius * 2,
            self.radius * 2
        )
        
        # 碰撞墙壁检测
        for wall in game_map.walls:
            if bullet_rect.colliderect(wall):
                return True
        return False

    def draw(self, surface, camera_offset):
        pygame.draw.circle(
            surface, YELLOW,
            (int(self.pos.x - camera_offset.x), int(self.pos.y - camera_offset.y)),
            self.radius
        )

class Player:
    def __init__(self, player_id, x, y):
        self.id = player_id
        self.pos = pygame.Vector2(x, y)
        self.velocity = pygame.Vector2(0, 0)
        self.angle = 0
        self.health = 100
        self.max_health = 100
        self.ammo = MAGAZINE_SIZE
        self.is_reloading = False
        self.reload_start = 0
        self.last_shot = 0
        self.color = (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
        self.name = f"玩家{player_id}"
        self.shooting = False

    def update(self, dt, game_map, bullets, network_manager=None):
        # 只有本地玩家才处理输入
        if network_manager is None or network_manager.player_id == self.id:
            # 鼠标控制旋转
            mouse_x, mouse_y = pygame.mouse.get_pos()
            rel_x = mouse_x - SCREEN_WIDTH / 2
            rel_y = mouse_y - SCREEN_HEIGHT / 2
            self.angle = (180 / math.pi) * -math.atan2(rel_y, rel_x)
            
            # 键盘控制移动
            keys = pygame.key.get_pressed()
            move_dir = pygame.Vector2(0, 0)
            if keys[K_w]: move_dir.y -= 1
            if keys[K_s]: move_dir.y += 1
            if keys[K_a]: move_dir.x -= 1
            if keys[K_d]: move_dir.x += 1
            
            if move_dir.length() > 0:
                move_dir = move_dir.normalize() * PLAYER_SPEED
                self.velocity += move_dir * dt * 5
            else:
                self.velocity *= 0.9  # 摩擦力，减少速度
                
            # 限制最大速度
            if self.velocity.length() > PLAYER_SPEED:
                self.velocity = self.velocity.normalize() * PLAYER_SPEED

            # 射击控制
            current_time = pygame.time.get_ticks() / 1000
            if self.shooting and not self.is_reloading and self.ammo > 0:
                if current_time - self.last_shot > BULLET_COOLDOWN:
                    bullet_dir = pygame.Vector2(math.cos(math.radians(self.angle)),
                                              -math.sin(math.radians(self.angle)))
                    bullet_pos = self.pos + bullet_dir * (PLAYER_RADIUS + BULLET_RADIUS)
                    bullets.append(Bullet(bullet_pos, bullet_dir, self.id))
                    self.ammo -= 1
                    self.last_shot = current_time
                    
                    # 发送子弹信息给服务器
                    if network_manager:
                        bullet_data = {
                            'pos': [bullet_pos.x, bullet_pos.y],
                            'direction': [bullet_dir.x, bullet_dir.y],
                            'owner_id': self.id
                        }
                        network_manager.send_data({
                            'type': 'bullet_create',
                            'data': bullet_data
                        })
            
            # 换弹控制
            if (keys[K_r] or self.ammo <= 0) and not self.is_reloading and self.ammo < MAGAZINE_SIZE:
                self.is_reloading = True
                self.reload_start = current_time
                
            if self.is_reloading and (current_time - self.reload_start) >= RELOAD_TIME:
                self.ammo = MAGAZINE_SIZE
                self.is_reloading = False
        
        # 更新位置
        if self.velocity.length() > 0:
            new_pos = self.pos + self.velocity * dt
            player_rect = pygame.Rect(
                new_pos.x - PLAYER_RADIUS,
                new_pos.y - PLAYER_RADIUS,
                PLAYER_RADIUS * 2,
                PLAYER_RADIUS * 2
            )
            
            can_move = True
            # 墙壁碰撞检测
            for wall in game_map.walls:
                if player_rect.colliderect(wall):
                    can_move = False
                    # 从碰撞的墙壁反弹
                    if wall.left < player_rect.left < wall.right or wall.left < player_rect.right < wall.right:
                        self.velocity.x *= -0.5
                    if wall.top < player_rect.top < wall.bottom or wall.top < player_rect.bottom < wall.bottom:
                        self.velocity.y *= -0.5
                    break
            if can_move:
                self.pos = new_pos

        # 门交互检测
        if network_manager and network_manager.player_id == self.id and hasattr(game_map, 'doors'):
            player_rect = pygame.Rect(
                self.pos.x - PLAYER_RADIUS,
                self.pos.y - PLAYER_RADIUS,
                PLAYER_RADIUS * 2,
                PLAYER_RADIUS * 2
            )
            
            # 检查与所有门的碰撞
            closest_door = None
            min_distance = float('inf')
            
            for door in game_map.doors:
                if player_rect.colliderect(door['original_rect']):
                    distance = math.sqrt((self.pos.x - door['original_rect'].centerx)**2 + 
                                       (self.pos.y - door['original_rect'].centery)**2)
                    if distance < min_distance:
                        min_distance = distance
                        closest_door = door
            
            # 门交互检测 - 直接处理E键状态
            if closest_door and not closest_door['fully_open'] and not closest_door['opening']:
                keys = pygame.key.get_pressed()
                if keys[K_e]:  # 检测E键是否按下
                    closest_door['opening'] = True
                    # 确保发送完整的门状态更新
                    door_index = game_map.doors.index(closest_door)
                    door_data = {
                        'i': door_index,
                        'r': [closest_door['rect'].x, closest_door['rect'].y, 
                             closest_door['rect'].width, closest_door['rect'].height],
                        'o': 1,  # opening=True
                        'f': 0,  # fully_open=False
                        'p': closest_door['animation_progress']
                    }
                    network_manager.send_data({
                        'type': 'door_update',
                        'data': door_data
                    })

        # 发送玩家更新
        if network_manager and network_manager.player_id == self.id:
            player_data = {
                'pos': [self.pos.x, self.pos.y],
                'angle': self.angle,
                'health': self.health,
                'ammo': self.ammo,
                'is_reloading': self.is_reloading,
                'shooting': self.shooting
            }
            # 如果是服务端，发送所有玩家数据
            if network_manager.is_server:
                all_player_data = {self.id: player_data}
                # 添加其他玩家数据
                for pid, player in network_manager.players.items():
                    all_player_data[pid] = {
                        'pos': player['pos'],
                        'angle': player['angle'],
                        'health': player['health'],
                        'ammo': player['ammo'],
                        'is_reloading': player['is_reloading'],
                        'shooting': player['shooting']
                    }
                network_manager.send_data({
                    'type': 'player_update',
                    'data': all_player_data
                })
            else:
                # 客户端只发送自己的数据
                network_manager.send_data({
                    'type': 'player_update',
                    'data': {self.id: player_data}
                })

    def draw(self, surface, camera_offset):
        points = [
            self.pos + pygame.Vector2(math.cos(math.radians(self.angle)) * PLAYER_RADIUS,
                                    -math.sin(math.radians(self.angle)) * PLAYER_RADIUS),
            self.pos + pygame.Vector2(math.cos(math.radians(self.angle + 120)) * PLAYER_RADIUS / 2,
                                    -math.sin(math.radians(self.angle + 120)) * PLAYER_RADIUS / 2),
            self.pos + pygame.Vector2(math.cos(math.radians(self.angle - 120)) * PLAYER_RADIUS / 2,
                                    -math.sin(math.radians(self.angle - 120)) * PLAYER_RADIUS / 2)
        ]
        
        screen_points = [(p.x - camera_offset.x, p.y - camera_offset.y) for p in points]
        pygame.draw.polygon(surface, self.color, screen_points)
        
        # 绘制血条和名字
        health_bar_width = 40
        health_ratio = self.health / self.max_health
        pygame.draw.rect(surface, RED, (screen_points[0][0] - health_bar_width / 2,
                                      screen_points[0][1] - 15,
                                      health_bar_width, 5))
        pygame.draw.rect(surface, GREEN, (screen_points[0][0] - health_bar_width / 2,
                                        screen_points[0][1] - 15,
                                        health_bar_width * health_ratio, 5))
        
        name_surface = font.render(self.name, True, WHITE)
        surface.blit(name_surface, (screen_points[0][0] - name_surface.get_width() // 2,
                                   screen_points[0][1] - 35))

class Map:
    def __init__(self):
        self.rooms = []
        self.doors = []
        self.walls = []
        self.generate_map()
    
    def generate_map(self):
        # 创建3x3房间网格
        for row in range(3):
            for col in range(3):
                x = col * ROOM_SIZE
                y = row * ROOM_SIZE
                self.rooms.append(pygame.Rect(x, y, ROOM_SIZE, ROOM_SIZE))
        
        # 边界墙
        self.walls.append(pygame.Rect(0, 0, ROOM_SIZE * 3, WALL_THICKNESS))
        self.walls.append(pygame.Rect(0, ROOM_SIZE * 3 - WALL_THICKNESS, ROOM_SIZE * 3, WALL_THICKNESS))
        self.walls.append(pygame.Rect(0, 0, WALL_THICKNESS, ROOM_SIZE * 3))
        self.walls.append(pygame.Rect(ROOM_SIZE * 3 - WALL_THICKNESS, 0, WALL_THICKNESS, ROOM_SIZE * 3))
        
        # 水平方向的门（左右连接）  
        for row in range(3):
            for col in range(2):
                door_x = (col + 1) * ROOM_SIZE - WALL_THICKNESS
                door_y = row * ROOM_SIZE + (ROOM_SIZE - DOOR_SIZE) // 2
                self.doors.append({
                    'rect': pygame.Rect(door_x, door_y, WALL_THICKNESS, DOOR_SIZE),
                    'fully_open': False,
                    'opening': False,
                    'vertical': False,
                    'animation_progress': 0.0,
                    'original_rect': pygame.Rect(door_x, door_y, WALL_THICKNESS, DOOR_SIZE)
                })
                
                # 添加上下部分墙
                self.walls.append(pygame.Rect(
                    (col + 1) * ROOM_SIZE - WALL_THICKNESS,
                    row * ROOM_SIZE,
                    WALL_THICKNESS,
                    (ROOM_SIZE - DOOR_SIZE) // 2
                ))
                self.walls.append(pygame.Rect(
                    (col + 1) * ROOM_SIZE - WALL_THICKNESS,
                    row * ROOM_SIZE + (ROOM_SIZE + DOOR_SIZE) // 2,
                    WALL_THICKNESS,
                    (ROOM_SIZE - DOOR_SIZE) // 2
                ))
        
        # 垂直方向的门（上下连接）  
        for row in range(2):
            for col in range(3):
                door_x = col * ROOM_SIZE + (ROOM_SIZE - DOOR_SIZE) // 2
                door_y = (row + 1) * ROOM_SIZE - WALL_THICKNESS
                self.doors.append({
                    'rect': pygame.Rect(door_x, door_y, DOOR_SIZE, WALL_THICKNESS),
                    'fully_open': False,
                    'opening': False,
                    'vertical': True,
                    'animation_progress': 0.0,
                    'original_rect': pygame.Rect(door_x, door_y, DOOR_SIZE, WALL_THICKNESS)
                })
                
                # 添加左右部分墙
                self.walls.append(pygame.Rect(
                    col * ROOM_SIZE,
                    (row + 1) * ROOM_SIZE - WALL_THICKNESS,
                    (ROOM_SIZE - DOOR_SIZE) // 2,
                    WALL_THICKNESS
                ))
                self.walls.append(pygame.Rect(
                    col * ROOM_SIZE + (ROOM_SIZE + DOOR_SIZE) // 2,
                    (row + 1) * ROOM_SIZE - WALL_THICKNESS,
                    (ROOM_SIZE - DOOR_SIZE) // 2,
                    WALL_THICKNESS
                ))

    def update_doors(self, dt):
        for door in self.doors:
            if door['opening']:
                door['animation_progress'] += dt * DOOR_ANIMATION_SPEED
                if door['animation_progress'] >= 1.0:
                    door['animation_progress'] = 1.0
                    door['opening'] = False
                    door['fully_open'] = True
                
                # 更新门的矩形
                if door['vertical']:
                    # 垂直门 - 上下打开
                    new_height = int(door['original_rect'].height * (1 - door['animation_progress']))
                    door['rect'].height = max(1, new_height)
                    door['rect'].y = door['original_rect'].y + (door['original_rect'].height - new_height) // 2
                else:
                    # 水平门 - 左右打开
                    new_width = int(door['original_rect'].width * (1 - door['animation_progress']))
                    door['rect'].width = max(1, new_width)
                    door['rect'].x = door['original_rect'].x + (door['original_rect'].width - new_width) // 2
    
    def draw(self, surface, camera_offset):
        # 绘制墙壁
        for wall in self.walls:
            wall_rect = (wall.x - camera_offset.x, wall.y - camera_offset.y, wall.width, wall.height)
            pygame.draw.rect(surface, GRAY, wall_rect)
        
        # 绘制门
        for door in self.doors:
            door_rect = (door['rect'].x - camera_offset.x,
                         door['rect'].y - camera_offset.y,
                         door['rect'].width,
                         door['rect'].height)
            
            # 根据门的动画状态选择颜色
            if door['fully_open']:
                color = GREEN
            elif door['opening']:
                # 动画过程中使用渐变颜色
                progress = door['animation_progress']
                r = int(DOOR_COLOR[0] * (1 - progress) + GREEN[0] * progress)
                g = int(DOOR_COLOR[1] * (1 - progress) + GREEN[1] * progress)
                b = int(DOOR_COLOR[2] * (1 - progress) + GREEN[2] * progress)
                color = (r, g, b)
            else:
                color = DOOR_COLOR
                
            pygame.draw.rect(surface, color, door_rect)

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("射击游戏")
        self.clock = pygame.time.Clock()
        self.running = True
        self.bullets = []
        self.game_map = Map()
        self.camera_offset = pygame.Vector2(0, 0)
        
        # 获取玩家ID
        self.player_id = self.get_player_id()
        self.server_address = input("请输入服务器IP地址: ") if self.player_id != 1 else None
        self.network_manager = NetworkManager(self.player_id, self.server_address)
        
        # 初始化玩家
        spawn_room = random.choice(self.game_map.rooms)
        spawn_x = random.randint(spawn_room.left + 50, spawn_room.right - 50)
        spawn_y = random.randint(spawn_room.top + 50, spawn_room.bottom - 50)
        self.player = Player(self.player_id, spawn_x, spawn_y)
        
        # 其他玩家
        self.other_players = {}
        
        # 如果是客户端，立即创建服务端玩家
        if not self.network_manager.is_server and 1 in self.network_manager.players:
            server_data = self.network_manager.players[1]
            self.other_players[1] = Player(1, server_data['pos'][0], server_data['pos'][1])
            self.other_players[1].color = RED
            print("初始化时创建服务端玩家")  # 调试日志
    
    def get_player_id(self):
        input_text = ""
        input_active = True
        font_large = pygame.font.SysFont('Microsoft YaHei', 32)
        
        while input_active:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == KEYDOWN:
                    if event.key == K_RETURN:
                        input_active = False
                    elif event.key == K_BACKSPACE:
                        input_text = input_text[:-1]
                    else:
                        input_text += event.unicode
            
            self.screen.fill(BLACK)
            prompt = font_large.render("请输入你的玩家ID(1=服务器):", True, WHITE)
            input_surface = font_large.render(input_text, True, WHITE)
            
            self.screen.blit(prompt, (SCREEN_WIDTH//2 - prompt.get_width()//2, SCREEN_HEIGHT//2 - 50))
            self.screen.blit(input_surface, (SCREEN_WIDTH//2 - input_surface.get_width()//2, SCREEN_HEIGHT//2 + 20))
            
            pygame.display.flip()
            self.clock.tick(FPS)
        
        try:
            return int(input_text)
        except ValueError:
            return 1  # 默认服务器
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False
                elif event.key == K_r and not self.player.is_reloading:
                    self.player.is_reloading = True
                    self.player.reload_start = pygame.time.get_ticks() / 1000
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:  # 左键按下
                    self.player.shooting = True
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1:  # 左键释放
                    self.player.shooting = False
    
    def __init__(self):
        self.running = True  # 添加running属性初始化
        self.clock = pygame.time.Clock()  # 添加clock属性初始化
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("多人射击游戏")
        
        # 初始化玩家
        self.player_id = self.get_player_id()  # 保存player_id属性
        server_address = None if self.player_id == 1 else input("请输入服务器IP地址: ")
        self.network_manager = NetworkManager(self.player_id, server_address)
        
        # 创建本地玩家
        self.player = Player(self.player_id, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.other_players = {}  # 存储其他玩家
        
        # 初始化游戏地图
        self.game_map = GameMap()
        self.bullets = []
        self.camera_offset = pygame.Vector2(0, 0)
        
        self.last_sync_time = 0
        self.sync_interval = 0.05  # 同步间隔50ms

    def update(self, dt):
        current_time = pygame.time.get_ticks() / 1000
        
        # 更新本地玩家
        self.player.update(dt, self.game_map, self.bullets, self.network_manager)
        
        # 控制网络同步频率
        if current_time - self.last_sync_time > self.sync_interval:
            self.last_sync_time = current_time
            
            # 确保更新所有玩家(包括服务端玩家)
            with self.network_manager.lock:
                print(f"[DEBUG] 当前玩家数据: {self.network_manager.players}")
                
                # 确保服务端玩家(pid=1)数据存在
                if self.network_manager.is_server and 1 not in self.network_manager.players:
                    self.network_manager.players[1] = {
                        'pos': [SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2],
                        'angle': 0,
                        'health': 100,
                        'ammo': MAGAZINE_SIZE,
                        'is_reloading': False,
                        'shooting': False
                    }
                    print("[DEBUG] 强制添加服务端玩家数据")
                
                for pid, pdata in self.network_manager.players.items():
                    # 跳过本地玩家
                    if pid == self.player_id:
                        continue
                        
                    # 创建或更新其他玩家
                    if pid not in self.other_players:
                        print(f"[DEBUG] 创建新玩家: {pid}")
                        self.other_players[pid] = Player(pid, pdata['pos'][0], pdata['pos'][1])
                        # 服务端玩家使用固定颜色(红色)
                        if pid == 1:
                            self.other_players[pid].color = RED
                            print("[DEBUG] 服务端玩家已创建并设置为红色")
                    
                    # 强制更新所有玩家数据
                    other_player = self.other_players[pid]
                    other_player.pos.update(pdata['pos'])
                    other_player.angle = pdata['angle']
                    other_player.health = pdata['health']
                    other_player.ammo = pdata['ammo']
                    other_player.is_reloading = pdata['is_reloading']
                    other_player.shooting = pdata['shooting']
                    print(f"[DEBUG] 更新玩家{pid}数据: 位置={pdata['pos']}, 角度={pdata['angle']}")
                        
                        # 更新玩家数据
                    other_player = self.other_players[pid]
                    other_player.pos.update(pdata['pos'])
                    other_player.angle = pdata['angle']
                    other_player.health = pdata['health']
                    other_player.ammo = pdata['ammo']
                    other_player.is_reloading = pdata['is_reloading']
                    other_player.shooting = pdata['shooting']
        
        # 更新子弹
        for bullet in self.bullets[:]:
            if bullet.update(dt, self.game_map):
                self.bullets.remove(bullet)
        
        # 同步网络子弹
        with self.network_manager.lock:
            network_bullets = []
            for bullet_data in self.network_manager.bullets:
                # 只添加不是自己创建的子弹
                if bullet_data['owner_id'] != self.player_id:
                    bullet = Bullet(bullet_data['pos'], bullet_data['direction'], bullet_data['owner_id'])
                    network_bullets.append(bullet)
            
            # 合并子弹列表，避免重复
            existing_bullets = {(b.pos.x, b.pos.y, b.owner_id) for b in self.bullets}
            for bullet in network_bullets:
                if (bullet.pos.x, bullet.pos.y, bullet.owner_id) not in existing_bullets:
                    self.bullets.append(bullet)
        
        # 更新门
        self.game_map.update_doors(dt)
        
        # 更新相机
        target_offset = pygame.Vector2(
            self.player.pos.x - SCREEN_WIDTH / 2,
            self.player.pos.y - SCREEN_HEIGHT / 2
        )
        self.camera_offset += (target_offset - self.camera_offset) * 0.1
    
    def render(self):
        self.screen.fill(BLACK)
        self.game_map.draw(self.screen, self.camera_offset)
        
        # 绘制子弹
        for bullet in self.bullets:
            bullet.draw(self.screen, self.camera_offset)
        
        # 绘制其他玩家
        for player in self.other_players.values():
            player.draw(self.screen, self.camera_offset)
        
        # 绘制本地玩家
        self.player.draw(self.screen, self.camera_offset)
        
        # 绘制UI
        health_text = f"生命: {self.player.health}/{self.player.max_health}"
        ammo_text = f"弹药: {self.player.ammo}/{MAGAZINE_SIZE}"
        self.screen.blit(font.render(health_text, True, WHITE), (20, 20))
        self.screen.blit(font.render(ammo_text, True, WHITE), (20, 50))
        
        if self.player.is_reloading:
            reload_time = max(0, RELOAD_TIME - (pygame.time.get_ticks() / 1000 - self.player.reload_start))
            reload_text = f"换弹中: {reload_time:.1f}s"
            self.screen.blit(font.render(reload_text, True, YELLOW), (20, 80))
        
        player_count = len(self.other_players) + 1
        count_text = f"玩家数: {player_count}"
        self.screen.blit(font.render(count_text, True, WHITE), (SCREEN_WIDTH - 150, 20))
        
        interact_text = "按E键开门"
        self.screen.blit(font.render(interact_text, True, WHITE),
                         (SCREEN_WIDTH - 150, SCREEN_HEIGHT - 30))
        
        # 小地图
        self.render_minimap()
        
        pygame.display.flip()

    def render_minimap(self):
        # 绘制小地图
        minimap_width, minimap_height = 200, 150
        minimap_surface = pygame.Surface((minimap_width, minimap_height))
        minimap_surface.fill(BLACK)
        
        # 绘制游戏区域的房间和墙壁
        for wall in self.game_map.walls:
            pygame.draw.rect(minimap_surface, GRAY, 
                             (wall.x / ROOM_SIZE * minimap_width, wall.y / ROOM_SIZE * minimap_height,
                              wall.width / ROOM_SIZE * minimap_width, wall.height / ROOM_SIZE * minimap_height))
        
        # 绘制玩家
        for player in self.other_players.values():
            pygame.draw.circle(minimap_surface, player.color,
                               (player.pos.x / ROOM_SIZE * minimap_width, player.pos.y / ROOM_SIZE * minimap_height),
                               PLAYER_RADIUS / ROOM_SIZE * minimap_width)

        pygame.draw.circle(minimap_surface, self.player.color,
                           (self.player.pos.x / ROOM_SIZE * minimap_width, self.player.pos.y / ROOM_SIZE * minimap_height),
                           PLAYER_RADIUS / ROOM_SIZE * minimap_width)

        self.screen.blit(minimap_surface, (SCREEN_WIDTH - minimap_width - 10, SCREEN_HEIGHT - minimap_height - 10))
    
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.render()
        
        self.network_manager.stop()
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
