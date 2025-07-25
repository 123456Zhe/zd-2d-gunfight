import pygame
import math
import random
import sys
import socket
import threading
import json
import time
import uuid
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
BULLET_DAMAGE = 20  # 子弹伤害
RESPAWN_TIME = 3.0  # 复活时间（秒）
SERVER_PORT = 5555
BUFFER_SIZE = 4096
MAX_BULLETS = 100  # 最大子弹数量限制

# 颜色定义
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
YELLOW = (255, 255, 0)
DOOR_COLOR = (139, 69, 19)
DEAD_COLOR = (128, 128, 128)  # 死亡状态颜色

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
        self.last_update_time = 0  # 上次更新时间
        self.door_id = f"door_{x}_{y}"  # 门的唯一ID
    
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
        self.last_update_time = time.time()
    
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
        interaction_range = PLAYER_RADIUS * 3  # 增大交互范围
        door_center = pygame.Vector2(self.original_rect.centerx, self.original_rect.centery)
        distance = (door_center - player_pos).length()
        
        if distance <= interaction_range + max(self.original_rect.width, self.original_rect.height) / 2:
            self.last_interaction_time = current_time
            
            # 切换门的状态
            if self.is_open or self.is_opening:
                self.close()
            else:
                self.open()
            
            return True
        
        return False
    
    def open(self):
        """打开门"""
        if not self.is_open and not self.is_opening:
            self.is_opening = True
            self.is_closing = False
            print(f"[门操作] 打开门 {self.door_id}")
            return True
        return False
    
    def close(self):
        """关闭门"""
        if self.is_open and not self.is_closing:
            self.is_closing = True
            self.is_opening = False
            print(f"[门操作] 关闭门 {self.door_id}")
            return True
        return False
    
    def get_color(self):
        """根据门的状态返回颜色"""
        if self.is_open:
            return GREEN
        elif self.is_opening or self.is_closing:
            # 动画过程中使用渐变颜色
            progress = self.animation_progress
            r = int(DOOR_COLOR[0] * (1 - progress) + GREEN[0] * progress)
            g = int(DOOR_COLOR[1] * (1 - progress) + GREEN[1] * progress)
            b = int(DOOR_COLOR[2] * (1 - progress) + GREEN[2] * progress)
            return (r, g, b)
        else:
            return DOOR_COLOR
    
    def draw(self, surface, camera_offset):
        """绘制门"""
        if self.animation_progress < 1.0:  # 只绘制未完全打开的门
            door_rect = (
                self.rect.x - camera_offset.x,
                self.rect.y - camera_offset.y,
                self.rect.width,
                self.rect.height
            )
            pygame.draw.rect(surface, self.get_color(), door_rect)
    
    def to_network_data(self, door_index):
        """将门状态转换为网络传输格式"""
        return {
            'i': door_index,
            'did': self.door_id,
            'o': int(self.is_opening),
            'c': int(self.is_closing),
            'f': int(self.is_open),
            'p': self.animation_progress,
            't': time.time()  # 添加时间戳
        }
    
    def from_network_data(self, data):
        """从网络数据更新门状态"""
        # 检查时间戳，只接受更新的数据
        if 't' in data and data['t'] <= self.last_update_time:
            return False  # 拒绝旧数据
            
        if 'o' in data:
            self.is_opening = bool(data['o'])
        if 'c' in data:
            self.is_closing = bool(data['c'])
        if 'f' in data:
            self.is_open = bool(data['f'])
        if 'p' in data:
            self.animation_progress = float(data['p'])
            
        # 立即更新门的大小和位置，确保视觉上同步
        self.update_rect()
        
        # 更新时间戳
        if 't' in data:
            self.last_update_time = data['t']
        else:
            self.last_update_time = time.time()
            
        return True  # 成功应用更新
    
    def check_collision(self, rect):
        """检查与门的碰撞，如果门打开则不碰撞"""
        if self.is_open:
            return False
        return self.rect.colliderect(rect)

class NetworkManager:
    def __init__(self, player_id, server_address=None):
        self.player_id = player_id
        self.is_server = (player_id == 1)  # 判断是否是服务器
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.players = {}
        self.bullets = []
        self.doors = {}  # 改为字典存储门状态
        self.lock = threading.Lock()
        self.running = True
        self.clients = set()  # 存储连接的客户端地址
        self.client_addresses = {}  # 玩家ID到地址的映射
        self.last_damage_time = {}  # 防止重复处理伤害
        self.last_broadcast = 0  # 上次广播时间
        self.door_last_update = {}  # 门状态最后更新时间
        self.bullet_ids = set()  # 已处理的子弹ID集合
        self.door_sync_timer = 0  # 门状态同步计时器
        
        if self.is_server:
            self.socket.bind(('0.0.0.0', SERVER_PORT))
            self.server_address = ('0.0.0.0', SERVER_PORT)
            print("服务器已启动，等待连接...")
            # 初始化服务端玩家数据
            self.players[player_id] = {
                'pos': [ROOM_SIZE + ROOM_SIZE // 2, ROOM_SIZE + ROOM_SIZE // 2],  # 中央房间
                'angle': 0,
                'health': 100,
                'ammo': MAGAZINE_SIZE,
                'is_reloading': False,
                'shooting': False,
                'is_dead': False,
                'respawn_time': 0,
                'is_respawning': False
            }
        else:
            self.server_address = server_address
            try:
                self.socket.sendto(f"connect:{player_id}".encode(), (self.server_address, SERVER_PORT))
                print(f"玩家{player_id}已连接服务器 {self.server_address}:{SERVER_PORT}")
            except Exception as e:
                print(f"连接服务器失败: {e}")
                sys.exit(1)
        
        # 启动接收线程
        self.receive_thread = threading.Thread(target=self.receive_data)
        self.receive_thread.daemon = True
        self.receive_thread.start()
    
    def receive_data(self):
        while self.running:
            try:
                data, addr = self.socket.recvfrom(BUFFER_SIZE)
                message_str = data.decode()
                
                # 处理连接消息（非JSON格式）
                if message_str.startswith("connect:"):
                    _, player_id = message_str.split(":")
                    self._handle_connect(player_id, addr)
                    continue
                    
                try:
                    message = json.loads(message_str)
                    if not isinstance(message, dict) or 't' not in message:
                        continue
                except json.JSONDecodeError:
                    print(f"无效的JSON数据: {message_str[:50]}...")
                    continue
                
                with self.lock:
                    # 消息类型映射
                    msg_handlers = {
                        'c': lambda: self._handle_connect(message['d'], addr) if 'd' in message else None,
                        'p': lambda: self._update_players(message['d']) if isinstance(message.get('d'), dict) else None,
                        'i': lambda: self._init_players(message['d']) if isinstance(message.get('d'), dict) else None,
                        'b': lambda: self._update_bullets(message['d']) if isinstance(message.get('d'), list) else None,
                        'd': lambda: self._update_door(message['d']) if isinstance(message.get('d'), dict) else None,
                        'r': lambda: self._handle_respawn(message['d']) if isinstance(message.get('d'), dict) else None,
                        'h': lambda: self._handle_damage(message['d']) if isinstance(message.get('d'), dict) else None
                    }
                    
                    if message['t'] in msg_handlers:
                        msg_handlers[message['t']]()
                        
                    # 记录新客户端
                    if self.is_server and addr not in self.clients:
                        self.clients.add(addr)
                        print(f"[服务端] 新客户端已添加: {addr}")
                        
            except Exception as e:
                print(f"接收数据错误: {e}")
                continue  # 忽略无效数据包

    def _handle_connect(self, data, addr):
        """处理新客户端连接"""
        if self.is_server:
            try:
                player_id = int(data)
                self.client_addresses[player_id] = addr
                self.clients.add(addr)
                print(f"[服务端] 玩家{player_id}已连接，地址：{addr}")
                
                # 初始化新玩家
                if player_id not in self.players:
                    spawn_pos = self.get_random_spawn_pos()
                    self.players[player_id] = {
                        'pos': spawn_pos,
                        'angle': 0,
                        'health': 100,
                        'ammo': MAGAZINE_SIZE,
                        'is_reloading': False,
                        'shooting': False,
                        'is_dead': False,
                        'respawn_time': 0,
                        'is_respawning': False
                    }
                
                # 立即发送当前游戏状态给新玩家
                init_packet = {
                    't': 'i',  # init_players
                    'd': self.players
                }
                self.socket.sendto(json.dumps(init_packet).encode(), addr)
                print(f"[服务端] 发送初始玩家数据到 {addr}")
                
                # 发送门状态
                for door_id, door_state in self.doors.items():
                    door_packet = {
                        't': 'd',  # door_update
                        'd': door_state
                    }
                    self.socket.sendto(json.dumps(door_packet).encode(), addr)
                    print(f"[服务端] 发送门{door_id}状态到 {addr}")
                    
            except ValueError as e:
                print(f"处理连接失败: {e}")
                
    def _update_bullets(self, bullet_data):
        """处理子弹数据更新"""
        if not isinstance(bullet_data, list):
            return
            
        valid_bullets = []
        for bullet in bullet_data:
            try:
                if all(key in bullet for key in ['pos', 'direction', 'owner_id']):
                    # 检查子弹ID是否存在，防止重复处理
                    bullet_id = bullet.get('id', f"{bullet['owner_id']}_{bullet['pos'][0]}_{bullet['pos'][1]}")
                    
                    # 如果没有处理过这个子弹，添加到列表
                    if bullet_id not in self.bullet_ids:
                        self.bullet_ids.add(bullet_id)
                        valid_bullets.append({
                            'id': bullet_id,
                            'pos': bullet['pos'],
                            'direction': bullet['direction'],
                            'owner_id': int(bullet['owner_id']),
                            'time': bullet.get('time', time.time())
                        })
            except (ValueError, TypeError) as e:
                print(f"子弹数据无效: {e}")
                continue
                
        # 合并有效子弹到当前列表
        if valid_bullets:
            # 限制子弹总数，防止过多
            self.bullets.extend(valid_bullets)
            if len(self.bullets) > MAX_BULLETS:
                # 保留最新的子弹
                self.bullets = self.bullets[-MAX_BULLETS:]
                
            # 如果是服务端，广播新子弹给所有客户端
            if self.is_server:
                self.send_data({
                    'type': 'bullet_create',
                    'data': valid_bullets
                })

    def _update_players(self, player_data):
        """更新玩家数据 - 修复服务端玩家移动问题"""
        if not isinstance(player_data, dict):
            return
            
        for pid_str, pdata in player_data.items():
            try:
                pid = int(pid_str)
                required_keys = ['pos', 'angle', 'health', 'ammo', 'is_reloading', 'shooting', 'is_dead']
                if not all(key in pdata for key in required_keys):
                    continue
                    
                # 确保有复活相关字段
                if 'respawn_time' not in pdata:
                    pdata['respawn_time'] = 0
                if 'is_respawning' not in pdata:
                    pdata['is_respawning'] = False
                
                if self.is_server:
                    # 服务端：接受客户端的位置和输入数据，但保持权威生命值
                    if pid in self.players:
                        # 保存当前权威数据
                        current_health = self.players[pid]['health']
                        current_is_dead = self.players[pid]['is_dead']
                        current_respawn_time = self.players[pid]['respawn_time']
                        current_is_respawning = self.players[pid]['is_respawning']
                        
                        # 更新客户端发来的数据
                        self.players[pid].update(pdata)
                        
                        # 恢复服务端权威数据
                        self.players[pid]['health'] = current_health
                        self.players[pid]['is_dead'] = current_is_dead
                        self.players[pid]['respawn_time'] = current_respawn_time
                        self.players[pid]['is_respawning'] = current_is_respawning
                    else:
                        self.players[pid] = pdata
                else:
                    # 客户端：完全接受服务端数据
                    self.players[pid] = pdata
            except (ValueError, TypeError) as e:
                print(f"更新玩家数据错误: {e}")
                continue

    def _init_players(self, player_data):
        """初始化玩家数据"""
        if not self.is_server and isinstance(player_data, dict):
            print(f"[客户端] 接收到初始玩家数据: {player_data}")
            self.players = {}
            for pid_str, pdata in player_data.items():
                try:
                    pid = int(pid_str)
                    self.players[pid] = pdata
                except ValueError:
                    continue

    def _update_door(self, door_data):
        """更新门状态"""
        if isinstance(door_data, dict) and 'i' in door_data:
            door_index = door_data['i']
            current_time = time.time()
            
            # 检查是否是更新的门状态
            is_newer = True
            if door_index in self.door_last_update:
                if current_time - self.door_last_update[door_index] < 0.1:
                    is_newer = False
            
            if is_newer:
                # 为数据添加时间戳
                if 't' not in door_data:
                    door_data['t'] = current_time
                    
                self.door_last_update[door_index] = current_time
                self.doors[door_index] = door_data
                print(f"[门同步] 更新门{door_index}状态: {door_data}")
                
                # 服务端收到门状态更新后，直接广播给所有客户端
                if self.is_server:
                    self._broadcast_door_state(door_data)
    
    def _broadcast_door_state(self, door_data):
        """广播门状态到所有客户端"""
        try:
            # 确保时间戳存在
            if 't' not in door_data:
                door_data['t'] = time.time()
                
            # 直接使用原始数据包格式广播
            door_packet = {
                't': 'd',  # door_update
                'd': door_data
            }
            packet_data = json.dumps(door_packet).encode()
            
            # 发送到所有客户端
            for addr in self.clients:
                try:
                    self.socket.sendto(packet_data, addr)
                except Exception as e:
                    print(f"发送门状态到 {addr} 失败: {e}")
            
            print(f"[服务端] 广播门{door_data['i']}状态到所有客户端")
        except Exception as e:
            print(f"广播门状态失败: {e}")
    
    def _handle_respawn(self, respawn_data):
        """处理复活事件"""
        if isinstance(respawn_data, dict) and 'player_id' in respawn_data and 'pos' in respawn_data:
            player_id = respawn_data['player_id']
            if player_id in self.players:
                print(f"[复活] 玩家{player_id}复活到位置{respawn_data['pos']}")
                self.players[player_id].update({
                    'pos': respawn_data['pos'],
                    'health': 100,
                    'ammo': MAGAZINE_SIZE,
                    'is_dead': False,
                    'respawn_time': 0,
                    'is_reloading': False,
                    'is_respawning': False
                })
                
                # 如果是服务端，广播复活事件给所有客户端
                if self.is_server:
                    self.send_data({
                        'type': 'player_update',
                        'data': {str(player_id): self.players[player_id]}
                    })

    def _handle_damage(self, damage_data):
        """处理伤害事件 - 只有服务端处理"""
        if not self.is_server:
            return
            
        if isinstance(damage_data, dict) and all(key in damage_data for key in ['target_id', 'damage', 'attacker_id']):
            try:
                target_id = int(damage_data['target_id'])
                damage = damage_data['damage']
                attacker_id = int(damage_data['attacker_id'])
                
                # 防止重复处理相同的伤害事件
                damage_key = f"{attacker_id}_{target_id}_{pygame.time.get_ticks()//100}"
                current_time = pygame.time.get_ticks() / 1000
                
                if damage_key in self.last_damage_time and current_time - self.last_damage_time[damage_key] < 0.1:
                    return
                
                self.last_damage_time[damage_key] = current_time
                
                if target_id in self.players and not self.players[target_id]['is_dead']:
                    old_health = self.players[target_id]['health']
                    self.players[target_id]['health'] = max(0, old_health - damage)
                    print(f"[伤害处理] 玩家{target_id}被玩家{attacker_id}击中，{old_health}->{self.players[target_id]['health']}")
                    
                    if self.players[target_id]['health'] <= 0:
                        self.players[target_id]['health'] = 0
                        self.players[target_id]['is_dead'] = True
                        self.players[target_id]['respawn_time'] = current_time + RESPAWN_TIME
                        print(f"[死亡] 玩家{target_id}死亡，{RESPAWN_TIME}秒后复活")
                    
                    # 立即广播更新后的玩家状态
                    self.send_data({
                        'type': 'player_update',
                        'data': {str(target_id): self.players[target_id]}
                    })
            except ValueError as e:
                print(f"处理伤害数据错误: {e}")
    
    def send_data(self, data):
        """发送数据"""
        # 精简数据格式
        packet = {
            't': data['type'][0],  # 消息类型首字母
            'd': data['data']      # 原始数据
        }

        try:
            serialized = json.dumps(packet).encode()
            if self.is_server:
                # 服务端广播
                for addr in list(self.clients):
                    try:
                        self.socket.sendto(serialized, addr)
                    except:
                        self.clients.discard(addr)
                        print(f"[服务端] 客户端 {addr} 连接失败，已移除")
            else:
                # 客户端发送到服务端
                self.socket.sendto(serialized, (self.server_address, SERVER_PORT))
        except Exception as e:
            print(f"[网络错误] 发送数据失败: {e}")

    def update_and_broadcast(self):
        """服务端定期广播游戏状态"""
        if self.is_server:
            current_time = time.time()
            
            # 广播玩家状态
            if current_time - self.last_broadcast > 0.05:  # 20Hz
                self.send_data({
                    'type': 'player_update', 
                    'data': {str(pid): pdata for pid, pdata in self.players.items()}
                })
                self.last_broadcast = current_time
            
            # 定期同步所有门状态(每5秒一次)
            if current_time - self.door_sync_timer > 5.0:
                self.door_sync_timer = current_time
                for door_id, door_state in self.doors.items():
                    # 更新时间戳
                    door_state['t'] = current_time
                    self._broadcast_door_state(door_state)
                print(f"[服务端] 执行完整门状态同步")

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
    
    def clear_old_bullets(self):
        """清理旧子弹"""
        current_time = time.time()
        # 子弹存在超过3秒就清理
        self.bullets = [b for b in self.bullets if 'time' not in b or current_time - b['time'] < 3.0]
        
        # 限制子弹数量
        if len(self.bullets) > MAX_BULLETS:
            self.bullets = self.bullets[-MAX_BULLETS:]
        
        # 超过1000个的子弹ID清理
        if len(self.bullet_ids) > 1000:
            self.bullet_ids = set(list(self.bullet_ids)[-1000:])
    
    def stop(self):
        self.running = False
        try:
            self.socket.close()
        except:
            pass

class Bullet:
    def __init__(self, pos, direction, owner_id, bullet_id=None):
        self.pos = pygame.Vector2(pos)
        self.direction = pygame.Vector2(direction).normalize()
        self.owner_id = owner_id
        self.speed = BULLET_SPEED
        self.radius = BULLET_RADIUS
        self.lifetime = 3.0
        self.has_hit = set()
        self.creation_time = time.time()
        self.bullet_id = bullet_id or f"{owner_id}_{self.creation_time}_{uuid.uuid4().hex[:8]}"

    def update(self, dt, game_map, players, network_manager=None):
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
        
        # 检查与其他玩家的碰撞
        for player in players.values():
            if (player.id != self.owner_id and 
                not player.is_dead and 
                player.id not in self.has_hit):
                
                player_rect = pygame.Rect(
                    player.pos.x - PLAYER_RADIUS,
                    player.pos.y - PLAYER_RADIUS,
                    PLAYER_RADIUS * 2,
                    PLAYER_RADIUS * 2
                )
                if bullet_rect.colliderect(player_rect):
                    print(f"[子弹击中] 玩家{player.id}被玩家{self.owner_id}的子弹击中")
                    self.has_hit.add(player.id)
                    
                    if network_manager:
                        # 无论是服务器还是客户端，都发送伤害事件
                        damage_data = {
                            'target_id': player.id,
                            'damage': BULLET_DAMAGE,
                            'attacker_id': self.owner_id
                        }
                        # 记录发送的伤害数据
                        print(f"[发送伤害事件] 从{self.owner_id}到{player.id}, 伤害:{BULLET_DAMAGE}")
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

    def draw(self, surface, camera_offset):
        pygame.draw.circle(
            surface, YELLOW,
            (int(self.pos.x - camera_offset.x), int(self.pos.y - camera_offset.y)),
            self.radius
        )
        
    def to_network_data(self):
        """转换为网络数据格式"""
        return {
            'id': self.bullet_id,
            'pos': [self.pos.x, self.pos.y],
            'direction': [self.direction.x, self.direction.y],
            'owner_id': self.owner_id,
            'time': self.creation_time
        }

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
        self.color = RED if player_id == 1 else (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
        self.name = f"玩家{player_id}"
        self.shooting = False
        self.is_dead = False
        self.death_time = 0
        self.respawn_time = 0
        self.is_respawning = False
        self.last_respawn_check = 0
        self.last_door_interaction = 0

    def take_damage(self, damage):
        """受到伤害 - 现在主要用于本地显示，实际伤害由服务端处理"""
        if not self.is_dead:
            print(f"本地玩家{self.id}受到{damage}点伤害")

    def die(self):
        """死亡"""
        self.is_dead = True
        self.death_time = pygame.time.get_ticks() / 1000
        self.respawn_time = self.death_time + RESPAWN_TIME
        self.velocity = pygame.Vector2(0, 0)
        print(f"玩家{self.id}死亡，将在{RESPAWN_TIME}秒后复活")

    def get_random_spawn_pos(self):
        """获取随机出生位置"""
        room_id = random.randint(0, 8)  # 0-8九个房间
        room_row = room_id // 3
        room_col = room_id % 3
        
        # 在房间中心附近随机位置
        spawn_x = room_col * ROOM_SIZE + ROOM_SIZE // 2 + random.randint(-100, 100)
        spawn_y = room_row * ROOM_SIZE + ROOM_SIZE // 2 + random.randint(-100, 100)
        
        # 确保在房间边界内
        spawn_x = max(room_col * ROOM_SIZE + 50, min(spawn_x, (room_col + 1) * ROOM_SIZE - 50))
        spawn_y = max(room_row * ROOM_SIZE + 50, min(spawn_y, (room_row + 1) * ROOM_SIZE - 50))
        
        return pygame.Vector2(spawn_x, spawn_y)

    def respawn(self, network_manager=None):
        """复活"""
        if self.is_respawning:
            return
            
        self.is_respawning = True
        new_pos = self.get_random_spawn_pos()
        self.pos = new_pos
        self.health = self.max_health
        self.ammo = MAGAZINE_SIZE
        self.is_dead = False
        self.is_reloading = False
        self.death_time = 0
        self.respawn_time = 0
        self.velocity = pygame.Vector2(0, 0)
        self.last_door_interaction = 0  # 重置门交互冷却
        
        print(f"玩家{self.id}在位置({new_pos.x:.0f}, {new_pos.y:.0f})复活")
        
        if network_manager:
            # 发送复活事件
            respawn_data = {
                'player_id': self.id,
                'pos': [new_pos.x, new_pos.y]
            }
            network_manager.send_data({
                'type': 'respawn',
                'data': respawn_data
            })
            
            # 如果是服务端，立即更新服务端玩家数据
            if network_manager.is_server and self.id in network_manager.players:
                network_manager.players[self.id].update({
                    'pos': [new_pos.x, new_pos.y],
                    'health': self.max_health,
                    'ammo': MAGAZINE_SIZE,
                    'is_dead': False,
                    'respawn_time': 0,
                    'is_reloading': False,
                    'is_respawning': False
                })
        
        self.last_respawn_check = pygame.time.get_ticks() / 1000

    def update(self, dt, game_map, bullets, network_manager=None, all_players=None):
        current_time = pygame.time.get_ticks() / 1000
        
        # 重置复活状态
        if self.is_respawning and current_time - self.last_respawn_check > 1.0:
            self.is_respawning = False
            self.last_door_interaction = 0  # 确保复活后可以与门交互
        
        # 只有本地玩家才处理输入
        is_local_player = network_manager and network_manager.player_id == self.id
        
        if is_local_player:
            # 检查是否需要复活
            if self.is_dead and not self.is_respawning:
                if current_time >= self.respawn_time:
                    self.respawn(network_manager)
                return
            
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
                self.velocity *= 0.9
                
            if self.velocity.length() > PLAYER_SPEED:
                self.velocity = self.velocity.normalize() * PLAYER_SPEED

            # 射击控制
            if self.shooting and not self.is_reloading and self.ammo > 0:
                if current_time - self.last_shot > BULLET_COOLDOWN:
                    bullet_dir = pygame.Vector2(math.cos(math.radians(self.angle)),
                                              -math.sin(math.radians(self.angle)))
                    bullet_pos = self.pos + bullet_dir * (PLAYER_RADIUS + BULLET_RADIUS)
                    
                    # 创建新子弹
                    new_bullet = Bullet(bullet_pos, bullet_dir, self.id)
                    bullets.append(new_bullet)
                    
                    self.ammo -= 1
                    self.last_shot = current_time
                    
                    if network_manager:
                        # 发送子弹创建事件
                        bullet_data = new_bullet.to_network_data()
                        network_manager.send_data({
                            'type': 'bullet_create',
                            'data': [bullet_data]  # 修改为列表包装
                        })
            
            # 换弹控制
            if (keys[K_r] or self.ammo <= 0) and not self.is_reloading and self.ammo < MAGAZINE_SIZE:
                self.is_reloading = True
                self.reload_start = current_time
                
            if self.is_reloading and (current_time - self.reload_start) >= RELOAD_TIME:
                self.ammo = MAGAZINE_SIZE
                self.is_reloading = False
        
        # 更新位置（所有玩家）
        if self.velocity.length() > 0 and not self.is_respawning and not self.is_dead:
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
                    if wall.left < player_rect.left < wall.right or wall.left < player_rect.right < wall.right:
                        self.velocity.x *= -0.5
                    if wall.top < player_rect.top < wall.bottom or wall.top < player_rect.bottom < wall.bottom:
                        self.velocity.y *= -0.5
                    break
                    
            # 检查门碰撞
            for door in game_map.doors:
                if door.check_collision(player_rect):
                    can_move = False
                    if door.rect.left < player_rect.left < door.rect.right or door.rect.left < player_rect.right < door.rect.right:
                        self.velocity.x *= -0.5
                    if door.rect.top < player_rect.top < door.rect.bottom or door.rect.top < player_rect.bottom < door.rect.bottom:
                        self.velocity.y *= -0.5
                    break
                    
            if can_move:
                self.pos = new_pos

        # 门交互检测（只有本地玩家）
        if (is_local_player and not self.is_dead and not self.is_respawning):
            keys = pygame.key.get_pressed()
            if keys[K_e] and current_time - self.last_door_interaction > 0.5:  # 添加交互冷却
                self.last_door_interaction = current_time
                for i, door in enumerate(game_map.doors):
                    if door.try_interact(self.pos):
                        door_data = door.to_network_data(i)
                        print(f"[门交互] 玩家{self.id}与门{i}交互，发送数据: {door_data}")
                        network_manager.send_data({
                            'type': 'door_update',
                            'data': door_data
                        })
                        break

        # 从网络同步健康状态（只有本地玩家）
        if is_local_player and self.id in network_manager.players:
            server_data = network_manager.players[self.id]
            
            # 健康同步
            if self.health != server_data['health']:
                old_health = self.health
                self.health = server_data['health']
                if old_health > self.health:
                    print(f"[同步] 玩家{self.id}生命值从{old_health}同步为{self.health}")
            
            # 死亡状态同步
            if self.is_dead != server_data['is_dead']:
                self.is_dead = server_data['is_dead']
                if self.is_dead:
                    print(f"[同步] 玩家{self.id}死亡状态同步")
                    self.respawn_time = server_data['respawn_time']

        # 发送玩家更新（只有本地玩家）
        if is_local_player:
            player_data = {
                'pos': [self.pos.x, self.pos.y],
                'angle': self.angle,
                'health': self.health,
                'ammo': self.ammo,
                'is_reloading': self.is_reloading,
                'shooting': self.shooting,
                'is_dead': self.is_dead,
                'respawn_time': self.respawn_time,
                'is_respawning': self.is_respawning
            }
            
            # 更新网络管理器中的玩家数据
            if network_manager.is_server:
                # 服务端：从网络数据同步权威状态
                if self.id in network_manager.players:
                    server_data = network_manager.players[self.id]
                    self.health = server_data.get('health', self.health)
                    self.is_dead = server_data.get('is_dead', self.is_dead)
                    self.respawn_time = server_data.get('respawn_time', self.respawn_time)
                    
                    # 更新服务端数据（位置等输入数据）
                    network_manager.players[self.id].update(player_data)
                    # 保持权威数据
                    network_manager.players[self.id]['health'] = self.health
                    network_manager.players[self.id]['is_dead'] = self.is_dead
                    network_manager.players[self.id]['respawn_time'] = self.respawn_time
                else:
                    network_manager.players[self.id] = player_data
            else:
                # 客户端发送数据
                network_manager.send_data({
                    'type': 'player_update',
                    'data': {str(self.id): player_data}
                })

    def draw(self, surface, camera_offset):
        if self.is_dead:
            # 死亡状态绘制灰色圆圈和复活倒计时
            pygame.draw.circle(
                surface, DEAD_COLOR,
                (int(self.pos.x - camera_offset.x), int(self.pos.y - camera_offset.y)),
                PLAYER_RADIUS
            )
            
            # 显示复活倒计时
            current_time = pygame.time.get_ticks() / 1000
            remaining_time = max(0, self.respawn_time - current_time)
            if remaining_time > 0:
                respawn_text = f"{remaining_time:.1f}s"
                text_surface = font.render(respawn_text, True, WHITE)
                surface.blit(text_surface, 
                           (int(self.pos.x - camera_offset.x - text_surface.get_width() // 2),
                            int(self.pos.y - camera_offset.y - PLAYER_RADIUS - 40)))
            
            return
        
        # 正常绘制
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
        self.door_positions = []
        self.generate_map()
    
    def generate_map(self):
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

    def update_doors(self, dt, network_manager):
        """更新门状态"""
        for i, door in enumerate(self.doors):
            door.update(dt)
            
            # 从网络管理器同步门状态
            if i in network_manager.doors:
                door_updated = door.from_network_data(network_manager.doors[i])
                if door_updated:
                    print(f"[门更新] 门{i}状态从网络同步成功")
    
    def draw(self, surface, camera_offset):
        # 绘制墙壁
        for wall in self.walls:
            wall_rect = (wall.x - camera_offset.x, wall.y - camera_offset.y, wall.width, wall.height)
            pygame.draw.rect(surface, GRAY, wall_rect)
        
        # 绘制门
        for door in self.doors:
            door.draw(surface, camera_offset)

class Game:
    def __init__(self):
        self.running = True  
        self.clock = pygame.time.Clock()  
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("多人射击游戏")
        
        # 初始化玩家
        self.player_id = self.get_player_id()  
        server_address = None if self.player_id == 1 else input("请输入服务器IP地址: ")
        self.network_manager = NetworkManager(self.player_id, server_address)
        
        # 随机选择一个房间作为出生点
        spawn_room = random.choice(range(9))
        spawn_row = spawn_room // 3
        spawn_col = spawn_room % 3
        spawn_x = spawn_col * ROOM_SIZE + ROOM_SIZE // 2
        spawn_y = spawn_row * ROOM_SIZE + ROOM_SIZE // 2
        
        # 创建本地玩家
        self.player = Player(self.player_id, spawn_x, spawn_y)
        self.other_players = {}  # 存储其他玩家
        
        # 初始化游戏地图（使用九宫格地图）
        self.game_map = Map()
        self.bullets = []
        self.camera_offset = pygame.Vector2(0, 0)
        
        self.last_sync_time = 0
        self.sync_interval = 0.05  # 同步间隔50ms
        
        # 调试模式
        self.debug_mode = True
        
        # 初始化子弹清理计时器
        self.bullet_cleanup_timer = 0

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
                elif event.key == K_r and not self.player.is_reloading and not self.player.is_dead:
                    self.player.is_reloading = True
                    self.player.reload_start = pygame.time.get_ticks() / 1000
                elif event.key == K_F3:  # 切换调试模式
                    self.debug_mode = not self.debug_mode
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1 and not self.player.is_dead:  # 左键按下且未死亡
                    self.player.shooting = True
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1:  # 左键释放
                    self.player.shooting = False
    
    def update(self, dt):
        current_time = time.time()
        
        # 合并所有玩家（本地+网络）
        all_players = {self.player.id: self.player}
        all_players.update(self.other_players)
        
        # 更新本地玩家
        self.player.update(dt, self.game_map, self.bullets, self.network_manager, all_players)
        
        # 控制网络同步频率
        if current_time - self.last_sync_time > self.sync_interval:
            self.last_sync_time = current_time
            
            # 同步网络玩家数据
            with self.network_manager.lock:
                for pid, pdata in self.network_manager.players.items():
                    # 跳过本地玩家
                    if pid == self.player_id:
                        continue
                        
                    # 创建或更新其他玩家
                    if pid not in self.other_players:
                        self.other_players[pid] = Player(pid, pdata['pos'][0], pdata['pos'][1])
                    
                    # 更新玩家数据
                    other_player = self.other_players[pid]
                    # 只在非复活状态下更新位置
                    if not pdata.get('is_respawning', False):
                        other_player.pos.update(pdata['pos'])
                    other_player.angle = pdata['angle']
                    other_player.health = pdata['health']
                    other_player.ammo = pdata['ammo']
                    other_player.is_reloading = pdata['is_reloading']
                    other_player.shooting = pdata['shooting']
                    other_player.is_dead = pdata.get('is_dead', False)
                    other_player.respawn_time = pdata.get('respawn_time', 0)
                    other_player.is_respawning = pdata.get('is_respawning', False)
            
            # 服务端定期广播
            self.network_manager.update_and_broadcast()
        
        # 更新子弹
        for bullet in self.bullets[:]:
            if bullet.update(dt, self.game_map, all_players, self.network_manager):
                self.bullets.remove(bullet)
        
        # 同步网络子弹
        with self.network_manager.lock:
            network_bullets = []
            existing_bullet_ids = {b.bullet_id for b in self.bullets}
            
            for bullet_data in self.network_manager.bullets:
                # 只添加不是自己创建的子弹且不重复的子弹
                bullet_id = bullet_data.get('id', f"{bullet_data['owner_id']}_{bullet_data['pos'][0]}_{bullet_data['pos'][1]}")
                
                if bullet_data['owner_id'] != self.player_id and bullet_id not in existing_bullet_ids:
                    bullet = Bullet(
                        bullet_data['pos'], 
                        bullet_data['direction'], 
                        bullet_data['owner_id'],
                        bullet_id
                    )
                    network_bullets.append(bullet)
            
            # 添加新子弹
            if network_bullets:
                self.bullets.extend(network_bullets)
                print(f"[子弹同步] 从网络添加了{len(network_bullets)}个子弹")
                
            # 限制子弹数量
            if len(self.bullets) > MAX_BULLETS:
                old_count = len(self.bullets)
                self.bullets = self.bullets[-MAX_BULLETS:]
                print(f"[子弹限制] 子弹数量超限，从{old_count}减至{len(self.bullets)}")
        
        # 定期清理子弹
        if current_time - self.bullet_cleanup_timer > 1.0:
            self.bullet_cleanup_timer = current_time
            self.network_manager.clear_old_bullets()
            
            # 清理超时的本地子弹
            old_count = len(self.bullets)
            self.bullets = [b for b in self.bullets if b.lifetime > 0]
            if old_count > len(self.bullets):
                print(f"[子弹清理] 清理了{old_count - len(self.bullets)}个过期子弹")
        
        # 更新门
        self.game_map.update_doors(dt, self.network_manager)
        
        # 更新相机（死亡或复活时不移动相机）
        if not self.player.is_dead and not self.player.is_respawning:
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
        
        if self.player.is_dead:
            # 显示死亡状态
            current_time = pygame.time.get_ticks() / 1000
            remaining_time = max(0, self.player.respawn_time - current_time)
            death_text = f"已死亡 - 复活倒计时: {remaining_time:.1f}s"
            death_surface = font.render(death_text, True, RED)
            self.screen.blit(death_surface, (SCREEN_WIDTH//2 - death_surface.get_width()//2, SCREEN_HEIGHT//2))
        elif self.player.is_reloading:
            reload_time = max(0, RELOAD_TIME - (pygame.time.get_ticks() / 1000 - self.player.reload_start))
            reload_text = f"换弹中: {reload_time:.1f}s"
            self.screen.blit(font.render(reload_text, True, YELLOW), (20, 80))
        
        player_count = len(self.other_players) + 1
        count_text = f"玩家数: {player_count}"
        self.screen.blit(font.render(count_text, True, WHITE), (SCREEN_WIDTH - 150, 20))
        
        if not self.player.is_dead and not self.player.is_respawning:
            interact_text = "按E键开/关门"
            self.screen.blit(font.render(interact_text, True, WHITE),
                             (SCREEN_WIDTH - 150, SCREEN_HEIGHT - 30))
        
        # 显示伤害信息
        damage_text = f"子弹伤害: {BULLET_DAMAGE}"
        self.screen.blit(font.render(damage_text, True, WHITE), (20, 110))
        
        # 调试信息
        if self.debug_mode:
            debug_y = 140
            self.screen.blit(font.render(f"玩家ID: {self.player_id}", True, YELLOW), (20, debug_y))
            debug_y += 25
            self.screen.blit(font.render(f"服务器: {'是' if self.network_manager.is_server else '否'}", True, YELLOW), (20, debug_y))
            debug_y += 25
            self.screen.blit(font.render(f"门状态: {len(self.network_manager.doors)}个已同步", True, YELLOW), (20, debug_y))
            debug_y += 25
            self.screen.blit(font.render(f"子弹数: {len(self.bullets)} (网络:{len(self.network_manager.bullets)})", True, YELLOW), (20, debug_y))
            debug_y += 25
            self.screen.blit(font.render(f"按F3切换调试模式", True, YELLOW), (20, debug_y))
        
        # 小地图
        self.render_minimap()
        
        pygame.display.flip()

    def render_minimap(self):
        # 绘制小地图
        minimap_width, minimap_height = 200, 150
        minimap_surface = pygame.Surface((minimap_width, minimap_height))
        minimap_surface.fill(BLACK)
        
        # 设置小地图的缩放比例
        minimap_scale = 0.08  # 调整比例以适应九宫格
        # 使玩家位于小地图中心
        minimap_center_x = minimap_width / 2
        minimap_center_y = minimap_height / 2
        
        # 绘制游戏区域的房间和墙壁，以玩家为中心
        for wall in self.game_map.walls:
            rel_x = (wall.x - self.player.pos.x) * minimap_scale + minimap_center_x
            rel_y = (wall.y - self.player.pos.y) * minimap_scale + minimap_center_y
            rel_width = wall.width * minimap_scale
            rel_height = wall.height * minimap_scale
            
            # 只绘制在小地图区域内的墙壁
            if (rel_x + rel_width > 0 and rel_x < minimap_width and 
                rel_y + rel_height > 0 and rel_y < minimap_height):
                pygame.draw.rect(minimap_surface, GRAY, (rel_x, rel_y, rel_width, rel_height))
        
        # 绘制门
        for door in self.game_map.doors:
            if not door.is_open:  # 只绘制未完全打开的门
                rel_x = (door.rect.x - self.player.pos.x) * minimap_scale + minimap_center_x
                rel_y = (door.rect.y - self.player.pos.y) * minimap_scale + minimap_center_y
                rel_width = door.rect.width * minimap_scale
                rel_height = door.rect.height * minimap_scale
                
                if (rel_x + rel_width > 0 and rel_x < minimap_width and 
                    rel_y + rel_height > 0 and rel_y < minimap_height):
                    pygame.draw.rect(minimap_surface, door.get_color(), (rel_x, rel_y, rel_width, rel_height))
        
        # 绘制房间边界（可选）
        for room in self.game_map.rooms:
            rel_x = (room.x - self.player.pos.x) * minimap_scale + minimap_center_x
            rel_y = (room.y - self.player.pos.y) * minimap_scale + minimap_center_y
            rel_width = room.width * minimap_scale
            rel_height = room.height * minimap_scale
            
            if (rel_x + rel_width > 0 and rel_x < minimap_width and 
                rel_y + rel_height > 0 and rel_y < minimap_height):
                pygame.draw.rect(minimap_surface, (50, 50, 50), (rel_x, rel_y, rel_width, rel_height), 1)
        
        # 绘制其他玩家
        for player in self.other_players.values():
            rel_x = (player.pos.x - self.player.pos.x) * minimap_scale + minimap_center_x
            rel_y = (player.pos.y - self.player.pos.y) * minimap_scale + minimap_center_y
            
            if 0 <= rel_x < minimap_width and 0 <= rel_y < minimap_height:
                color = DEAD_COLOR if player.is_dead else player.color
                pygame.draw.circle(minimap_surface, color, (int(rel_x), int(rel_y)), 3)

        # 绘制本地玩家 - 始终在小地图中心
        player_color = DEAD_COLOR if self.player.is_dead else self.player.color
        pygame.draw.circle(minimap_surface, player_color, (int(minimap_center_x), int(minimap_center_y)), 4)

        # 绘制小地图边框
        pygame.draw.rect(minimap_surface, WHITE, (0, 0, minimap_width, minimap_height), 2)
        
        # 将小地图绘制到屏幕上
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