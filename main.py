import pygame
import math
import random
import sys
import socket
import threading
import json
import time
import subprocess
import ipaddress
from pygame.locals import *
from constants import *
from player import Player
from map import Map, Door
from network import NetworkManager
from weapons import MeleeWeapon, Bullet

# 初始化pygame
pygame.init()
pygame.font.init()

# 尝试加载中文字体
try:
    font = pygame.font.SysFont('Microsoft YaHei', 24)
    small_font = pygame.font.SysFont('Microsoft YaHei', 18)
    large_font = pygame.font.SysFont('Microsoft YaHei', 32)
    title_font = pygame.font.SysFont('Microsoft YaHei', 48)
except:
    try:
        font = pygame.font.SysFont('SimHei', 24)
        small_font = pygame.font.SysFont('SimHei', 18)
        large_font = pygame.font.SysFont('SimHei', 32)
        title_font = pygame.font.SysFont('SimHei', 48)
    except:
        font = pygame.font.Font(None, 24)
        small_font = pygame.font.Font(None, 18)
        large_font = pygame.font.Font(None, 32)
        title_font = pygame.font.Font(None, 48)

# 射线类
class Ray:
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

def get_local_ip():
    """获取本机内网IP"""
    try:
        # 连接一个外部地址来获取本机IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

def get_network_range():
    """获取当前网络的IP段 - 改进版"""
    local_ip = get_local_ip()
    try:
        # 尝试多种常见的子网掩码
        for prefix in [24, 16, 8]:
            try:
                network = ipaddress.IPv4Network(f"{local_ip}/{prefix}", strict=False)
                # 如果网络不是太大（小于65536个主机），就使用这个
                if network.num_addresses <= 65536:
                    return str(network.network_address), str(network.broadcast_address)
            except:
                continue
        # 默认使用/24
        network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
        return str(network.network_address), str(network.broadcast_address)
    except:
        return "192.168.1.1", "192.168.1.254"

def scan_for_servers():
    """扫描局域网中的游戏服务器 - 改进版"""
    found_servers = []
    local_ip = get_local_ip()
    
    print(f"开始扫描，本机IP: {local_ip}")
    
    # 获取网络段 - 尝试多种方法
    ip_lists = []
    
    # 方法1：基于网络段检测
    try:
        # 尝试/24网段
        network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
        ip_list_24 = list(network.hosts())
        ip_lists.append(("24位网段", ip_list_24))
        print(f"检测到/24网段: {network}, 包含{len(ip_list_24)}个IP")
        
        # 如果IP是10.x.x.x，也尝试/16网段
        if local_ip.startswith("10."):
            try:
                network_16 = ipaddress.IPv4Network(f"{local_ip}/16", strict=False)
                if network_16.num_addresses <= 10000:  # 限制扫描范围
                    ip_list_16 = list(network_16.hosts())
                    ip_lists.append(("16位网段", ip_list_16))
                    print(f"检测到/16网段: {network_16}, 包含{len(ip_list_16)}个IP")
            except:
                pass
                
    except Exception as e:
        print(f"网络段检测失败: {e}")
    
    # 方法2：扫描当前子网的邻近IP
    try:
        base_ip = ".".join(local_ip.split('.')[:-1])
        nearby_ips = [ipaddress.IPv4Address(f"{base_ip}.{i}") for i in range(1, 255)]
        ip_lists.append(("当前子网", nearby_ips))
        print(f"添加当前子网扫描: {base_ip}.1-254")
    except:
        pass
    
    # 如果没有任何IP列表，使用默认
    if not ip_lists:
        print("使用默认IP范围")
        ip_lists.append(("默认范围", [ipaddress.IPv4Address(f"192.168.1.{i}") for i in range(1, 255)]))
    
    # 合并所有IP并去重
    all_ips = set()
    for list_name, ip_list in ip_lists:
        all_ips.update(ip_list)
        print(f"{list_name}: {len(ip_list)}个IP")
    
    print(f"总共需要扫描 {len(all_ips)} 个唯一IP地址")
    
    def check_server(ip):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(SCAN_TIMEOUT)
            
            # 发送服务器探测消息
            probe_msg = "server_probe"
            sock.sendto(probe_msg.encode(), (str(ip), SERVER_PORT))
            
            # 等待响应
            try:
                data, addr = sock.recvfrom(1024)
                response = data.decode()
                if response.startswith("server_info:"):
                    # 解析服务器信息
                    _, info = response.split(":", 1)
                    server_info = json.loads(info)
                    server_info['ip'] = str(ip)
                    found_servers.append(server_info)
                    print(f"找到服务器: {ip} - {server_info.get('name', '未知')}")
            except socket.timeout:
                pass
            except Exception as e:
                # 调试：打印解析错误
                if str(ip) == local_ip:
                    print(f"本机IP {ip} 响应解析失败: {e}")
            
            sock.close()
        except Exception as e:
            # 调试：打印连接错误
            if str(ip) == local_ip:
                print(f"本机IP {ip} 连接失败: {e}")
    
    # 优先扫描本机IP
    local_ip_addr = ipaddress.IPv4Address(local_ip)
    if local_ip_addr in all_ips:
        print(f"优先扫描本机IP: {local_ip}")
        check_server(local_ip_addr)
        all_ips.remove(local_ip_addr)
    
    # 使用线程池扫描其他IP
    threads = []
    for ip in all_ips:
        thread = threading.Thread(target=check_server, args=(ip,))
        thread.daemon = True
        thread.start()
        threads.append(thread)
        
        # 限制并发线程数
        if len(threads) >= 50:  # 增加并发数
            for t in threads:
                t.join()
            threads = []
    
    # 等待剩余线程完成
    for thread in threads:
        thread.join()
    
    print(f"扫描完成，找到 {len(found_servers)} 个服务器")
    return found_servers

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

def is_in_field_of_view(player_pos, player_angle, target_pos, fov_degrees):
    """检查目标位置是否在玩家的视野范围内"""
    if player_pos == target_pos:
        return True
    
    # 计算从玩家到目标的角度
    dx = target_pos.x - player_pos.x
    dy = target_pos.y - player_pos.y
    target_angle = math.degrees(math.atan2(-dy, dx))  # 注意Y轴方向
    
    # 计算角度差
    angle_diff = angle_difference(player_angle, target_angle)
    
    # 检查是否在视野范围内
    return angle_diff <= fov_degrees / 2

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

def line_intersects_rect(start, end, rect):
    """检查线段是否与矩形相交"""
    # 获取矩形的四条边
    left = rect.left
    right = rect.right
    top = rect.top
    bottom = rect.bottom
    
    # 检查线段是否与矩形的四条边相交
    # 左边
    if line_intersects_line(start, end, (left, top), (left, bottom)):
        return True
    # 右边
    if line_intersects_line(start, end, (right, top), (right, bottom)):
        return True
    # 上边
    if line_intersects_line(start, end, (left, top), (right, top)):
        return True
    # 下边
    if line_intersects_line(start, end, (left, bottom), (right, bottom)):
        return True
    
    return False

def line_intersects_line(p1, p2, p3, p4):
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

def has_line_of_sight(start_pos, end_pos, walls, doors):
    """检查两点之间是否有视线（不被墙壁或关闭的门阻挡）"""
    # 检查与墙壁的碰撞
    for wall in walls:
        if line_intersects_rect(start_pos, end_pos, wall):
            return False
    
    # 检查与关闭的门的碰撞
    for door in doors:
        if not door.is_open and line_intersects_rect(start_pos, end_pos, door.rect):
            return False
    
    return True

def is_visible(player_pos, player_angle, target_pos, fov_degrees, walls, doors):
    """检查目标是否可见（在视野内且有视线）"""
    # 首先检查是否在视野角度内
    if not is_in_field_of_view(player_pos, player_angle, target_pos, fov_degrees):
        return False
    
    # 然后检查是否有视线
    return has_line_of_sight(player_pos, target_pos, walls, doors)

def create_vision_fan_points(player_pos, player_angle, fov_degrees, vision_range, num_points=30):
    """创建视角扇形的点集合 - 优化版本"""
    points = [player_pos]  # 扇形的中心点
    
    half_fov = fov_degrees / 2
    angle_step = fov_degrees / num_points
    
    # 生成扇形边界上的点
    for i in range(num_points + 1):
        angle = player_angle - half_fov + (angle_step * i)
        angle_rad = math.radians(angle)
        end_x = player_pos[0] + math.cos(angle_rad) * vision_range
        end_y = player_pos[1] - math.sin(angle_rad) * vision_range
        points.append((end_x, end_y))
    
    return points

class ChatMessage:
    """聊天消息类"""
    def __init__(self, player_id, player_name, message, timestamp=None):
        self.player_id = player_id
        self.player_name = player_name
        self.message = message
        self.timestamp = timestamp or time.time()
        self.color = self.get_player_color(player_id)
    
    def get_player_color(self, player_id):
        """根据玩家ID获取颜色"""
        # 系统消息使用白色
        if player_id == 0:
            return WHITE
            
        colors = [RED, BLUE, GREEN, YELLOW, ORANGE, PURPLE, (0, 255, 255)]
        return colors[player_id % len(colors)]
    
    def is_expired(self, current_time):
        """检查消息是否过期"""
        return current_time - self.timestamp > CHAT_DISPLAY_TIME
        """关闭门"""
        if self.is_open and not self.is_closing:
            self.is_closing = True
            self.is_opening = False
            return True
        return False
    
    def get_color(self, in_fog=False):
        """根据门的状态返回颜色"""
        base_color = DOOR_COLOR
        bright_color = GREEN
        
        if self.is_open:
            return bright_color
        elif self.is_opening or self.is_closing:
            # 动画过程中使用渐变颜色
            progress = self.animation_progress
            r = int(base_color[0] * (1 - progress) + bright_color[0] * progress)
            g = int(base_color[1] * (1 - progress) + bright_color[1] * progress)
            b = int(base_color[2] * (1 - progress) + bright_color[2] * progress)
            return (r, g, b)
        else:
            return base_color
    
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
    
    def check_collision(self, rect):
        """检查与门的碰撞，如果门打开则不碰撞"""
        if self.is_open:
            return False
        return self.rect.colliderect(rect)

class NetworkManager:
    def __init__(self, is_server=False, server_address=None, game_instance=None):
        self.is_server = is_server
        self.player_id = None  # 将在连接时分配
        # 玩家自定义名称（客户端使用，服务端同样保留以便本地显示）
        self.player_name = f"Player{random.randint(100, 999)}"
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(1.0)  # 设置超时
        self.players = {}
        self.doors = {}  # 存储门状态
        self.chat_messages = []  # 存储聊天消息
        self.lock = threading.Lock()
        self.running = True
        self.connected = False
        self.connection_error = None
        self.game_instance = game_instance  # 添加game_instance属性
        
        # 服务端特有属性 - 改进的ID管理
        self.clients = {}  # 客户端地址到玩家ID的映射
        self.client_last_seen = {}  # 客户端最后活跃时间
        self.recycled_ids = set()  # 回收的玩家ID池
        self.next_new_id = 2  # 下一个全新的玩家ID（服务端是1）
        
        # 客户端特有属性
        self.server_address = server_address
        self.last_heartbeat = 0
        self.last_server_response = 0
        
        self.last_damage_time = {}  # 防止重复处理伤害
        self.last_broadcast = 0  # 上次广播时间
        
        # 简化的子弹管理
        self.active_bullets = []  # 当前活动的子弹
        self.next_bullet_id = 1
        
        if self.is_server:
            try:
                self.socket.bind(('0.0.0.0', SERVER_PORT))
                self.player_id = 1  # 服务端始终是玩家1
                print("服务器已启动，等待连接...")
                
                # 初始化服务端玩家数据
                self.players[self.player_id] = {
                    'pos': [ROOM_SIZE + ROOM_SIZE // 2, ROOM_SIZE + ROOM_SIZE // 2],  # 中央房间
                    'angle': 0,
                    'health': 100,
                    'ammo': MAGAZINE_SIZE,
                    'is_reloading': False,
                    'shooting': False,
                    'is_dead': False,
                    'death_time': 0,
                    'respawn_time': 0,
                    'is_respawning': False,
                    'name': f'玩家{self.player_id}',
                    'melee_attacking': False,
                    'melee_direction': 0,
                    'weapon_type': 'gun',  # 新增：武器类型
                    'is_aiming': False  # 新增：瞄准状态
                }
                self.connected = True
                
                # 启动清理线程
                self.cleanup_thread = threading.Thread(target=self.cleanup_disconnected_clients)
                self.cleanup_thread.daemon = True
                self.cleanup_thread.start()
                
            except Exception as e:
                self.connection_error = f"无法启动服务器: {e}"
                self.running = False
                return
        else:
            # 客户端连接到服务器
            if not self.connect_to_server():
                return
        
        # 启动接收线程
        self.receive_thread = threading.Thread(target=self.receive_data)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        
        # 启动心跳线程
        if not self.is_server:
            self.heartbeat_thread = threading.Thread(target=self.heartbeat_loop)
            self.heartbeat_thread.daemon = True
            self.heartbeat_thread.start()
    
    def allocate_player_id(self):
        """分配玩家ID（优先使用回收的ID）"""
        if self.recycled_ids:
            # 优先使用回收的ID
            player_id = min(self.recycled_ids)  # 使用最小的回收ID
            self.recycled_ids.remove(player_id)
            print(f"[服务端] 分配回收ID: {player_id}")
            return player_id
        else:
            # 使用新的ID
            player_id = self.next_new_id
            self.next_new_id += 1
            print(f"[服务端] 分配新ID: {player_id}")
            return player_id
    
    def recycle_player_id(self, player_id):
        """回收玩家ID"""
        if player_id != 1:  # 服务端ID不回收
            self.recycled_ids.add(player_id)
            print(f"[服务端] 回收ID: {player_id}，当前回收池: {sorted(self.recycled_ids)}")
    
    def get_server_info(self):
        """获取服务器信息"""
        return {
            'name': '多人射击游戏服务器',
            'players': len(self.players),
            'max_players': 10,
            'version': '1.0'
        }
    
    def connect_to_server(self):
        """客户端连接到服务器"""
        try:
            print(f"正在连接到服务器 {self.server_address}:{SERVER_PORT}...")
            
            # 发送连接请求，包含玩家名称
            connect_msg = {
                'type': 'connect_request',
                'data': {
                    'name': getattr(self, 'player_name', f'玩家{int(time.time() * 1000) % 10000}')
                }
            }
            self.socket.sendto(json.dumps(connect_msg).encode(), (self.server_address, SERVER_PORT))
            
            # 等待服务器响应
            start_time = time.time()
            while time.time() - start_time < CONNECTION_TIMEOUT:
                try:
                    data, addr = self.socket.recvfrom(BUFFER_SIZE)
                    response = data.decode()
                    
                    if response.startswith("connect_accepted:"):
                        _, player_id = response.split(":")
                        self.player_id = int(player_id)
                        self.connected = True
                        self.last_server_response = time.time()
                        print(f"连接成功！分配到玩家ID: {self.player_id}")
                        return True
                    elif response == "connect_rejected":
                        self.connection_error = "服务器拒绝连接（可能已满）"
                        return False
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"连接过程中出错: {e}")
                    continue
            
            self.connection_error = "连接超时"
            return False
            
        except Exception as e:
            self.connection_error = f"连接失败: {e}"
            return False
    
    def cleanup_disconnected_clients(self):
        """清理断开连接的客户端（仅服务端）"""
        while self.running:
            time.sleep(2.0)  # 每2秒检查一次
            
            if not self.is_server:
                continue
                
            current_time = time.time()
            disconnected_clients = []
            
            with self.lock:
                for addr, last_seen in list(self.client_last_seen.items()):
                    if current_time - last_seen > CLIENT_TIMEOUT:
                        disconnected_clients.append(addr)
                
                # 移除断开连接的客户端
                for addr in disconnected_clients:
                    if addr in self.clients:
                        player_id = self.clients[addr]
                        player_name = self.players.get(player_id, {}).get('name', f'玩家{player_id}')
                        print(f"[服务端] 玩家{player_id}({player_name})连接超时，已踢出")
                        
                        # 广播玩家离开消息
                        leave_msg = ChatMessage(
                            0, "系统", 
                            f"{player_name} 离开了游戏", 
                            time.time()
                        )
                        self.chat_messages.append(leave_msg)
                        self.broadcast_chat_message(leave_msg)
                        
                        # 回收玩家ID
                        self.recycle_player_id(player_id)
                        
                        # 清理数据
                        del self.clients[addr]
                        del self.client_last_seen[addr]
                        if player_id in self.players:
                            del self.players[player_id]
                        
                        print(f"[服务端] 已清理玩家{player_id}的数据，当前玩家数: {len(self.players)}")
    
    def heartbeat_loop(self):
        """客户端心跳循环"""
        while self.running and not self.is_server:
            try:
                current_time = time.time()
                
                # 发送心跳
                if current_time - self.last_heartbeat > HEARTBEAT_INTERVAL:
                    heartbeat_msg = {
                        'type': 'heartbeat',
                        'data': {'player_id': self.player_id, 'timestamp': current_time}
                    }
                    self.send_data_raw(heartbeat_msg)
                    self.last_heartbeat = current_time
                
                # 检查服务器连接
                if current_time - self.last_server_response > CLIENT_TIMEOUT:
                    print("[客户端] 服务器连接超时")
                    self.connection_error = "与服务器连接丢失"
                    self.connected = False
                    self.running = False
                    break
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"[客户端] 心跳错误: {e}")
                break
    
    def receive_data(self):
        while self.running:
            try:
                data, addr = self.socket.recvfrom(BUFFER_SIZE)
                message_str = data.decode()
                
                # 更新最后收到数据的时间
                if self.is_server:
                    with self.lock:
                        if addr in self.clients:
                            self.client_last_seen[addr] = time.time()
                else:
                    self.last_server_response = time.time()
                
                # 处理服务器探测（仅服务端）
                if message_str == "server_probe" and self.is_server:
                    try:
                        server_info = self.get_server_info()
                        response = f"server_info:{json.dumps(server_info)}"
                        self.socket.sendto(response.encode(), addr)
                        print(f"[服务端] 响应探测请求来自: {addr}")
                    except Exception as e:
                        print(f"[服务端] 响应探测请求失败: {e}")
                    continue
                
                # 处理连接请求（仅服务端）
                if message_str == "connect_request" and self.is_server:
                    self._handle_connection_request(addr)
                    continue
                
                # 处理包含玩家名称的连接请求（仅服务端）
                try:
                    message = json.loads(message_str)
                    if isinstance(message, dict) and message.get('type') == 'connect_request':
                        self._handle_connection_request(addr, message.get('data', {}))
                        continue
                except json.JSONDecodeError:
                    pass
                
                # 处理连接响应（仅客户端）
                if message_str.startswith("connect_accepted:") and not self.is_server:
                    continue  # 已在connect_to_server中处理
                
                try:
                    message = json.loads(message_str)
                    if not isinstance(message, dict) or 'type' not in message:
                        continue
                except json.JSONDecodeError:
                    continue
                
                with self.lock:
                    msg_type = message['type']
                    msg_data = message.get('data', {})
                    
                    if msg_type == 'player_update':
                        self._update_players(msg_data)
                    elif msg_type == 'init_players':
                        self._init_players(msg_data)
                    elif msg_type == 'door_update':
                        self._update_door(msg_data)
                    elif msg_type == 'request_bullet':
                        self._handle_bullet_request(msg_data)
                    elif msg_type == 'bullets_update':
                        self._update_bullets(msg_data)
                    elif msg_type == 'hit_damage':
                        self._handle_damage(msg_data)
                    elif msg_type == 'melee_attack':
                        self._handle_melee_attack(msg_data)
                    elif msg_type == 'respawn':
                        self._handle_respawn(msg_data)
                    elif msg_type == 'chat_message':
                        self._handle_chat_message(msg_data)
                    elif msg_type == 'chat_history':
                        self._handle_chat_history(msg_data)
                    elif msg_type == 'heartbeat':
                        self._handle_heartbeat(msg_data, addr)
                    elif msg_type == 'kick':
                        self._handle_kick(msg_data)
                        
            except socket.timeout:
                continue
            except Exception as e:
                print(f"接收数据错误: {e}")
                if not self.is_server:
                    self.connection_error = f"网络错误: {e}"
                    self.connected = False
                    self.running = False
                continue

    def _handle_connection_request(self, addr, data=None):
        """处理连接请求（仅服务端）"""
        try:
            # 检查是否已经连接
            if addr in self.clients:
                return
            
            # 分配玩家ID（使用新的ID管理系统）
            new_player_id = self.allocate_player_id()
            
            # 获取玩家名称
            player_name = data.get('name', f'玩家{new_player_id}') if data else f'玩家{new_player_id}'
            
            # 记录客户端
            self.clients[addr] = new_player_id
            self.client_last_seen[addr] = time.time()
            
            # 初始化新玩家
            spawn_pos = self.get_random_spawn_pos()
            self.players[new_player_id] = {
                'pos': spawn_pos,
                'angle': 0,
                'health': 100,
                'ammo': MAGAZINE_SIZE,
                'is_reloading': False,
                'shooting': False,
                'is_dead': False,
                'death_time': 0,
                'respawn_time': 0,
                'is_respawning': False,
                'name': player_name,
                'melee_attacking': False,
                'melee_direction': 0,
                'weapon_type': 'gun',  # 新增：武器类型
                'is_aiming': False  # 新增：瞄准状态
            }
            
            print(f"[服务端] 玩家{new_player_id}({player_name})已连接，地址：{addr}，当前玩家数: {len(self.players)}")
            
            # 发送连接确认
            response = f"connect_accepted:{new_player_id}"
            self.socket.sendto(response.encode(), addr)
            
            # 发送当前游戏状态给新玩家
            self.send_to_client({
                'type': 'init_players',
                'data': self.players
            }, addr)
            
            # 发送门状态
            for door_id, door_state in self.doors.items():
                self.send_to_client({
                    'type': 'door_update',
                    'data': {'door_id': door_id, 'state': door_state}
                }, addr)
            
            # 发送聊天历史
            if self.chat_messages:
                self.send_to_client({
                    'type': 'chat_history',
                    'data': {'messages': [
                        {
                            'player_id': msg.player_id,
                            'player_name': msg.player_name,
                            'message': msg.message,
                            'timestamp': msg.timestamp
                        } for msg in self.chat_messages[-MAX_CHAT_MESSAGES:]
                    ]}
                }, addr)
            
            # 广播新玩家加入消息
            join_msg = ChatMessage(
                0, "系统", 
                f"{player_name} 加入了游戏", 
                time.time()
            )
            self.chat_messages.append(join_msg)
            self.broadcast_chat_message(join_msg)
            
        except Exception as e:
            print(f"处理连接请求失败: {e}")

    def _handle_heartbeat(self, heartbeat_data, addr):
        """处理心跳包"""
        if self.is_server:
            # 服务端：更新客户端最后活跃时间
            if addr in self.clients:
                self.client_last_seen[addr] = time.time()
                
                # 回应心跳
                response = {
                    'type': 'heartbeat_response',
                    'data': {'timestamp': time.time()}
                }
                self.send_to_client(response, addr)
        else:
            # 客户端：收到服务端的心跳回应
            self.last_server_response = time.time()

    def _handle_kick(self, kick_data):
        """处理踢出消息（仅客户端）"""
        if not self.is_server:
            reason = kick_data.get('reason', '未知原因')
            print(f"[客户端] 被服务器踢出: {reason}")
            self.connection_error = f"被服务器踢出: {reason}"
            self.connected = False
            self.running = False

    def _update_players(self, player_data):
        """更新玩家数据"""
        if not isinstance(player_data, dict):
            return
            
        for pid_str, pdata in player_data.items():
            try:
                pid = int(pid_str)
                if self.is_server:
                    # 服务端：接受客户端的位置和输入数据，但保持权威生命值和死亡状态
                    if pid in self.players:
                        # 保存当前权威数据
                        current_health = self.players[pid]['health']
                        current_is_dead = self.players[pid]['is_dead']
                        current_death_time = self.players[pid].get('death_time', 0)
                        current_respawn_time = self.players[pid].get('respawn_time', 0)
                        current_is_respawning = self.players[pid].get('is_respawning', False)
                        current_name = self.players[pid].get('name', f'玩家{pid}')
                        
                        # 更新客户端发来的数据
                        self.players[pid].update(pdata)
                        
                        # 恢复服务端权威数据
                        self.players[pid]['health'] = current_health
                        self.players[pid]['is_dead'] = current_is_dead
                        self.players[pid]['death_time'] = current_death_time
                        self.players[pid]['respawn_time'] = current_respawn_time
                        self.players[pid]['is_respawning'] = current_is_respawning
                        self.players[pid]['name'] = current_name
                    else:
                        self.players[pid] = pdata
                        self.players[pid]['name'] = pdata.get('name', f'玩家{pid}')
                else:
                    # 客户端：完全接受服务端数据
                    self.players[pid] = pdata
            except (ValueError, TypeError) as e:
                continue

    def _init_players(self, player_data):
        """初始化玩家数据"""
        if not self.is_server and isinstance(player_data, dict):
            print(f"[客户端] 接收到初始玩家数据")
            self.players = {}
            for pid_str, pdata in player_data.items():
                try:
                    pid = int(pid_str)
                    self.players[pid] = pdata
                except ValueError:
                    continue

    def _update_door(self, door_data):
        """更新门状态"""
        if isinstance(door_data, dict) and 'door_id' in door_data and 'state' in door_data:
            door_id = door_data['door_id']
            new_state = door_data['state']
            
            # 更新本地门状态
            self.doors[door_id] = new_state
            
            # 如果是服务端，转发给所有客户端
            if self.is_server:
                for addr in list(self.clients.keys()):
                    try:
                        self.send_to_client({
                            'type': 'door_update',
                            'data': door_data
                        }, addr)
                    except:
                        pass

    def _handle_bullet_request(self, bullet_data):
        """处理子弹发射请求 - 只有服务端处理"""
        if self.is_server and isinstance(bullet_data, dict):
            # 创建新子弹
            new_bullet = {
                'id': self.next_bullet_id,
                'pos': bullet_data.get('pos'),
                'dir': bullet_data.get('dir'),  # 简化为dir
                'owner': bullet_data.get('owner'),
                'time': time.time()
            }
            self.next_bullet_id += 1
            self.active_bullets.append(new_bullet)

    def _update_bullets(self, bullets_data):
        """更新子弹数据 - 客户端接收服务端的子弹"""
        if not self.is_server and isinstance(bullets_data, list):
            self.active_bullets = bullets_data

    def _handle_damage(self, damage_data):
        """处理伤害事件"""
        if isinstance(damage_data, dict) and all(key in damage_data for key in ['target_id', 'damage', 'attacker_id']):
            try:
                target_id = int(damage_data['target_id'])
                base_damage = damage_data['damage']
                attacker_id = int(damage_data['attacker_id'])
                damage_type = damage_data.get('type', 'bullet')  # 添加伤害类型
                
                # 应用游戏规则中的伤害倍率
                game_instance = getattr(self, 'game_instance', None)
                damage_multiplier = 1.0
                if game_instance and hasattr(game_instance, 'game_rules'):
                    damage_multiplier = game_instance.game_rules['damage_multiplier']
                
                damage = base_damage * damage_multiplier
                
                # 防止重复处理相同的伤害事件
                damage_key = f"{attacker_id}_{target_id}_{damage_type}_{int(time.time() * 10)}"
                current_time = time.time()
                
                if damage_key in self.last_damage_time and current_time - self.last_damage_time[damage_key] < 0.1:
                    return
                
                self.last_damage_time[damage_key] = current_time
                
                # 如果受伤的是本地玩家，触发红色滤镜效果和减速效果
                if target_id == self.player_id:
                    # 触发红色滤镜效果
                    if hasattr(self, 'game_instance') and self.game_instance:
                        self.game_instance.trigger_hit_effect()
                    
                    # 应用减速效果
                    game_instance = getattr(self, 'game_instance', None)
                    if game_instance and hasattr(game_instance, 'players') and target_id in game_instance.players:
                        player = game_instance.players[target_id]
                        player.take_damage(0)  # 传入0伤害，只触发减速效果
                
                # 服务端处理
                if self.is_server:
                    if target_id in self.players and not self.players[target_id]['is_dead']:
                        # 获取玩家实例
                        game_instance = getattr(self, 'game_instance', None)
                        if game_instance and hasattr(game_instance, 'players') and target_id in game_instance.players:
                            player = game_instance.players[target_id]
                            # 调用玩家的take_damage方法，传入游戏规则中的复活时间
                            respawn_time = RESPAWN_TIME
                            if game_instance and hasattr(game_instance, 'game_rules'):
                                respawn_time = game_instance.game_rules['respawn_time']
                            is_dead = player.take_damage(damage, respawn_time)
                            
                            # 同步玩家状态到网络
                            self.players[target_id]['health'] = player.health
                            self.players[target_id]['is_dead'] = player.is_dead
                            if is_dead:
                                self.players[target_id]['death_time'] = current_time
                                
                                # 使用游戏规则中的复活时间
                                respawn_time = RESPAWN_TIME
                                if game_instance and hasattr(game_instance, 'game_rules'):
                                    respawn_time = game_instance.game_rules['respawn_time']
                                
                                self.players[target_id]['respawn_time'] = current_time + respawn_time
                            
                            print(f"[{damage_type}伤害] 玩家{target_id}被玩家{attacker_id}击中，{player.health + damage}->{player.health}")
                            
                            if is_dead:
                                print(f"[死亡] 玩家{target_id}死亡，将在{respawn_time}秒后复活")
                                
                                # 发送死亡信息到聊天框
                                attacker_name = self.players.get(attacker_id, {}).get('name', f"玩家{attacker_id}")
                                target_name = self.players.get(target_id, {}).get('name', f"玩家{target_id}")
                                death_message = f"{attacker_name} 击杀了 {target_name}！"
                                death_chat = ChatMessage(0, "[系统]", death_message, current_time)
                                self.chat_messages.append(death_chat)
                                if self.is_server:
                                    self.broadcast_chat_message(death_chat)
                        else:
                            # 如果没有玩家实例，使用原来的逻辑
                            old_health = self.players[target_id]['health']
                            self.players[target_id]['health'] = max(0, old_health - damage)
                            print(f"[{damage_type}伤害] 玩家{target_id}被玩家{attacker_id}击中，{old_health}->{self.players[target_id]['health']}")
                            
                            if self.players[target_id]['health'] <= 0:
                                # 服务端计算死亡和复活时间
                                self.players[target_id]['health'] = 0
                                self.players[target_id]['is_dead'] = True
                                self.players[target_id]['death_time'] = current_time
                                
                                # 使用游戏规则中的复活时间
                                respawn_time = RESPAWN_TIME
                                if game_instance and hasattr(game_instance, 'game_rules'):
                                    respawn_time = game_instance.game_rules['respawn_time']
                                
                                self.players[target_id]['respawn_time'] = current_time + respawn_time
                                print(f"[死亡] 玩家{target_id}死亡，将在{respawn_time}秒后复活")
                                
                                # 发送死亡信息到聊天框
                                attacker_name = self.players.get(attacker_id, {}).get('name', f"玩家{attacker_id}")
                                target_name = self.players.get(target_id, {}).get('name', f"玩家{target_id}")
                                death_message = f"{attacker_name} 击杀了 {target_name}！"
                                death_chat = ChatMessage(0, "[系统]", death_message, current_time)
                                self.chat_messages.append(death_chat)
                                if self.is_server:
                                    self.broadcast_chat_message(death_chat)
            except ValueError as e:
                print(f"处理伤害数据错误: {e}")

    def _handle_melee_attack(self, melee_data):
        """处理近战攻击事件 - 只有服务端处理"""
        if not self.is_server:
            return
            
        if isinstance(melee_data, dict) and all(key in melee_data for key in ['attacker_id', 'direction', 'targets']):
            try:
                attacker_id = int(melee_data['attacker_id'])
                direction = melee_data['direction']
                targets = melee_data['targets']
                is_heavy = melee_data.get('is_heavy', False)  # 是否为重击
                
                print(f"[近战攻击] 玩家{attacker_id}发起近战攻击，方向{direction}°，目标{targets}" + (" (重击)" if is_heavy else " (轻击)"))
                
                # 确定伤害值
                damage = MELEE_DAMAGE * 1.5 if is_heavy else MELEE_DAMAGE
                
                # 处理每个被击中的目标
                for target_id in targets:
                    if target_id != attacker_id and target_id in self.players:
                        damage_data = {
                            'target_id': target_id,
                            'damage': damage,
                            'attacker_id': attacker_id,
                            'type': 'melee'
                        }
                        self._handle_damage(damage_data)
                        
            except (ValueError, TypeError) as e:
                print(f"处理近战攻击数据错误: {e}")

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
                    'death_time': 0,
                    'respawn_time': 0,
                    'is_reloading': False,
                    'is_respawning': False,
                    'melee_attacking': False,
                    'melee_direction': 0,
                    'weapon_type': 'gun',  # 重置为枪械
                    'is_aiming': False  # 重置瞄准状态
                })
    
    def _handle_chat_message(self, chat_data):
        """处理聊天消息"""
        if isinstance(chat_data, dict) and all(key in chat_data for key in ['player_id', 'player_name', 'message']):
            message = chat_data['message']
            player_id = chat_data['player_id']
            player_name = chat_data['player_name']
            timestamp = chat_data.get('timestamp', time.time())
            
            # 检查是否是服务端命令
            if self.is_server and message.startswith('.'):
                self._handle_server_command(message, player_id, player_name)
                return
            
            msg = ChatMessage(
                player_id,
                player_name,
                message,
                timestamp
            )
            
            # 添加到聊天历史
            self.chat_messages.append(msg)
            
            # 保持聊天历史不超过最大数量
            if len(self.chat_messages) > MAX_CHAT_MESSAGES * 2:
                self.chat_messages = self.chat_messages[-MAX_CHAT_MESSAGES:]
            
            print(f"[聊天] {msg.player_name}: {msg.message}")
            
            # 如果是服务端，转发给所有客户端
            if self.is_server:
                self.broadcast_chat_message(msg)
                
    def _handle_server_command(self, command, player_id, player_name):
        """处理服务端命令"""
        if not self.is_server:
            return
            
        # 分割命令和参数
        parts = command.strip().split()
        if not parts:
            return
            
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        # 只有服务器管理员（玩家ID为1）可以执行某些命令
        is_admin = (player_id == 1)
        
        # 处理不同的命令
        if cmd == '.kick' and is_admin:
            if len(args) < 1:
                self._send_system_message(f"用法: .kick <玩家ID> [原因]")
                return
                
            try:
                target_id = int(args[0])
                reason = " ".join(args[1:]) if len(args) > 1 else "被管理员踢出"
                
                # 检查玩家是否存在
                if target_id not in self.players:
                    self._send_system_message(f"玩家{target_id}不存在")
                    return
                    
                # 不能踢出自己
                if target_id == player_id:
                    self._send_system_message(f"不能踢出自己")
                    return
                    
                # 查找玩家的地址
                target_addr = None
                for addr, pid in self.clients.items():
                    if pid == target_id:
                        target_addr = addr
                        break
                        
                if target_addr:
                    # 发送踢出消息
                    kick_data = {
                        'type': 'kick',
                        'data': {'reason': reason}
                    }
                    self.send_to_client(kick_data, target_addr)
                    
                    # 从客户端列表中移除
                    with self.lock:
                        if target_addr in self.clients:
                            del self.clients[target_addr]
                        if target_addr in self.client_last_seen:
                            del self.client_last_seen[target_addr]
                        if target_id in self.players:
                            del self.players[target_id]
                            
                    # 回收玩家ID
                    self.recycle_player_id(target_id)
                    
                    # 广播系统消息
                    self._send_system_message(f"玩家{target_id}已被踢出: {reason}")
                    print(f"[服务端] 玩家{target_id}已被踢出: {reason}")
                else:
                    self._send_system_message(f"无法找到玩家{target_id}的连接")
            except ValueError:
                self._send_system_message(f"无效的玩家ID: {args[0]}")
        
        elif cmd == '.list' or cmd == '.players':
            # 显示在线玩家列表
            if not self.players:
                self._send_system_message("当前没有在线玩家")
                return
                
            player_list = []
            for pid, pdata in self.players.items():
                player_name = pdata.get('name', f"玩家{pid}")
                health = pdata.get('health', 0)
                is_dead = pdata.get('is_dead', False)
                status = "死亡" if is_dead else f"生命值:{health}"
                player_list.append(f"ID:{pid} - {player_name} ({status})")
                
            self._send_system_message(f"在线玩家({len(player_list)}):\n" + "\n".join(player_list))
        
        elif cmd == '.broadcast' and is_admin:
            # 广播系统消息
            if not args:
                self._send_system_message("用法: .broadcast <消息>")
                return
                
            message = " ".join(args)
            self._send_system_message(f"[公告] {message}")
        
        elif cmd == '.heal' and is_admin:
            # 治疗玩家
            if len(args) < 1:
                self._send_system_message("用法: .heal <玩家ID|all> [生命值]")
                return
                
            try:
                target = args[0].lower()
                amount = int(args[1]) if len(args) > 1 else 100
                
                if target == "all":
                    # 治疗所有玩家
                    for pid in self.players:
                        if not self.players[pid].get('is_dead', False):
                            self.players[pid]['health'] = min(100, amount)
                    self._send_system_message(f"已将所有玩家的生命值恢复到{amount}")
                else:
                    # 治疗指定玩家
                    target_id = int(target)
                    if target_id not in self.players:
                        self._send_system_message(f"玩家{target_id}不存在")
                        return
                        
                    if self.players[target_id].get('is_dead', False):
                        self._send_system_message(f"玩家{target_id}已死亡，无法治疗")
                        return
                        
                    self.players[target_id]['health'] = min(100, amount)
                    self._send_system_message(f"已将玩家{target_id}的生命值恢复到{amount}")
            except ValueError:
                self._send_system_message(f"无效的参数: {args[0]}")
        
        elif cmd == '.respawn' and is_admin:
            # 复活玩家
            if len(args) < 1:
                self._send_system_message("用法: .respawn <玩家ID|all>")
                return
                
            try:
                target = args[0].lower()
                
                if target == "all":
                    # 复活所有死亡玩家
                    respawned_count = 0
                    for pid in self.players:
                        if self.players[pid].get('is_dead', False):
                            self.players[pid]['is_dead'] = False
                            self.players[pid]['health'] = 100
                            self.players[pid]['respawn_time'] = 0
                            respawned_count += 1
                    
                    if respawned_count > 0:
                        self._send_system_message(f"已复活所有死亡玩家({respawned_count}人)")
                    else:
                        self._send_system_message("当前没有死亡的玩家")
                else:
                    # 复活指定玩家
                    target_id = int(target)
                    if target_id not in self.players:
                        self._send_system_message(f"玩家{target_id}不存在")
                        return
                        
                    if not self.players[target_id].get('is_dead', False):
                        self._send_system_message(f"玩家{target_id}没有死亡，无需复活")
                        return
                        
                    self.players[target_id]['is_dead'] = False
                    self.players[target_id]['health'] = 100
                    self.players[target_id]['respawn_time'] = 0
                    self._send_system_message(f"已复活玩家{target_id}")
            except ValueError:
                self._send_system_message(f"无效的参数: {args[0]}")
        
        elif cmd == '.tp' and is_admin:
            # 传送玩家到指定位置
            if len(args) < 3:
                self._send_system_message("用法: .tp <玩家ID|all> <x> <y>")
                return
                
            try:
                target = args[0].lower()
                x = float(args[1])
                y = float(args[2])
                
                # 确保坐标在地图范围内
                x = max(0, min(x, self.map_width))
                y = max(0, min(y, self.map_height))
                
                if target == "all":
                    # 传送所有玩家
                    for pid in self.players:
                        if not self.players[pid].get('is_dead', False):
                            self.players[pid]['x'] = x
                            self.players[pid]['y'] = y
                    self._send_system_message(f"已将所有玩家传送到坐标({x:.1f}, {y:.1f})")
                else:
                    # 传送指定玩家
                    target_id = int(target)
                    if target_id not in self.players:
                        self._send_system_message(f"玩家{target_id}不存在")
                        return
                        
                    if self.players[target_id].get('is_dead', False):
                        self._send_system_message(f"玩家{target_id}已死亡，无法传送")
                        return
                        
                    self.players[target_id]['x'] = x
                    self.players[target_id]['y'] = y
                    self._send_system_message(f"已将玩家{target_id}传送到坐标({x:.1f}, {y:.1f})")
            except ValueError:
                self._send_system_message(f"无效的坐标参数")
        
        elif cmd == '.kill':
            # 自杀命令
            if player_id not in self.players:
                self._send_system_message(f"玩家{player_id}不存在")
                return
                
            if self.players[player_id].get('is_dead', False):
                self._send_system_message(f"你已经死亡，无法使用此命令")
                return
                
            # 处理自杀
            damage_data = {
                'target_id': player_id,
                'damage': 100,  # 直接致命伤害
                'attacker_id': player_id,  # 自己击杀自己
                'type': 'suicide'
            }
            self._handle_damage(damage_data)
            self._send_system_message(f"玩家{player_id}自杀了")
            
        elif cmd == '.weapon' and is_admin:
            # 切换武器命令（仅管理员可用）
            if player_id not in self.players:
                self._send_system_message(f"玩家{player_id}不存在")
                return
                
            if self.players[player_id].get('is_dead', False):
                self._send_system_message(f"你已经死亡，无法使用此命令")
                return
                
            # 切换武器类型
            current_weapon = self.players[player_id].get('weapon_type', 'gun')
            new_weapon = 'melee' if current_weapon == 'gun' else 'gun'
            self.players[player_id]['weapon_type'] = new_weapon
            self._send_system_message(f"已将武器切换为: {new_weapon}")
            print(f"[服务端] 管理员{player_id}切换了武器类型为{new_weapon}")
            
        elif cmd == '.ammo' and is_admin:
            # 补充弹药命令（仅管理员可用）
            if player_id not in self.players:
                self._send_system_message(f"玩家{player_id}不存在")
                return
                
            if self.players[player_id].get('is_dead', False):
                self._send_system_message(f"你已经死亡，无法使用此命令")
                return
                
            # 补充弹药
            self.players[player_id]['ammo'] = MAGAZINE_SIZE
            self.players[player_id]['is_reloading'] = False
            self._send_system_message(f"已补充弹药")
            print(f"[服务端] 管理员{player_id}补充了弹药")
            
        elif cmd == '.speed' and is_admin:
            # 临时提高移动速度命令（仅管理员可用）
            if player_id not in self.players:
                self._send_system_message(f"玩家{player_id}不存在")
                return
                
            if self.players[player_id].get('is_dead', False):
                self._send_system_message(f"你已经死亡，无法使用此命令")
                return
                
            # 获取速度参数
            speed_multiplier = 1.5  # 默认提高到150%
            if len(args) > 0:
                try:
                    speed_multiplier = float(args[0])
                    # 限制速度倍率在合理范围内
                    speed_multiplier = max(0.5, min(speed_multiplier, 2.0))
                except ValueError:
                    self._send_system_message(f"无效的速度参数，使用默认值1.5")
            
            # 获取持续时间参数
            duration = 10.0  # 默认10秒
            if len(args) > 1:
                try:
                    duration = float(args[1])
                    # 限制持续时间在合理范围内
                    duration = max(1.0, min(duration, 30.0))
                except ValueError:
                    self._send_system_message(f"无效的持续时间参数，使用默认值10秒")
            
            # 应用速度提升
            game_instance = getattr(self, 'game_instance', None)
            if game_instance and hasattr(game_instance, 'players') and player_id in game_instance.players:
                player = game_instance.players[player_id]
                player.speed_boost_end_time = time.time() + duration
                player.speed_boost_multiplier = speed_multiplier
                self._send_system_message(f"已临时提高移动速度至{speed_multiplier:.1f}倍，持续{duration:.1f}秒")
                print(f"[服务端] 管理员{player_id}临时提高了移动速度至{speed_multiplier:.1f}倍，持续{duration:.1f}秒")
            
        elif cmd == '.help':
            # 显示可用命令
            if is_admin:
                commands = [
                    ".kick <玩家ID> [原因] - 踢出玩家",
                    ".list 或 .players - 显示在线玩家列表",
                    ".broadcast <消息> - 广播系统消息",
                    ".heal <玩家ID|all> [生命值] - 治疗玩家",
                    ".respawn <玩家ID|all> - 复活死亡玩家",
                    ".tp <玩家ID|all> <x> <y> - 传送玩家到指定坐标",
                    ".kill - 自杀",
                    ".weapon - 切换武器类型",
                    ".ammo - 补充弹药",
                    ".speed [倍率] [持续时间] - 临时提高移动速度",
                    ".help - 显示此帮助信息"
                ]
                self._send_system_message("可用命令:\n" + "\n".join(commands))
            else:
                commands = [
                    ".list 或 .players - 显示在线玩家列表",
                    ".kill - 自杀",
                    ".help - 显示此帮助信息"
                ]
                self._send_system_message("可用命令:\n" + "\n".join(commands))
        else:
            # 未知命令
            self._send_system_message(f"未知命令: {cmd}")
            self._send_system_message("输入 .help 查看可用命令")
    
    def _send_system_message(self, message):
        """发送系统消息"""
        if not self.is_server:
            return
            
        # 创建系统消息
        msg = ChatMessage(
            0,  # 系统消息使用ID 0
            "系统",
            message,
            time.time()
        )
        
        # 添加到聊天历史
        self.chat_messages.append(msg)
        
        # 保持聊天历史不超过最大数量
        if len(self.chat_messages) > MAX_CHAT_MESSAGES * 2:
            self.chat_messages = self.chat_messages[-MAX_CHAT_MESSAGES:]
        
        print(f"[系统] {message}")
        
        # 广播给所有客户端
        self.broadcast_chat_message(msg)
    
    def _handle_chat_history(self, history_data):
        """处理聊天历史（客户端接收）"""
        if not self.is_server and isinstance(history_data, dict) and 'messages' in history_data:
            self.chat_messages = []
            for msg_data in history_data['messages']:
                msg = ChatMessage(
                    msg_data['player_id'],
                    msg_data['player_name'],
                    msg_data['message'],
                    msg_data['timestamp']
                )
                self.chat_messages.append(msg)

    def send_data(self, data):
        """发送数据到服务端或所有客户端"""
        self.send_data_raw(data)

    def send_data_raw(self, data):
        """原始数据发送方法"""
        try:
            serialized = json.dumps(data).encode()
            if self.is_server:
                # 服务端广播
                for addr in list(self.clients.keys()):
                    try:
                        self.socket.sendto(serialized, addr)
                    except Exception as e:
                        print(f"向{addr}发送数据失败: {e}")
                        # 移除失效的客户端
                        with self.lock:
                            if addr in self.clients:
                                player_id = self.clients[addr]
                                print(f"移除失效客户端 玩家{player_id}")
                                # 回收ID
                                self.recycle_player_id(player_id)
                                del self.clients[addr]
                                if addr in self.client_last_seen:
                                    del self.client_last_seen[addr]
                                if player_id in self.players:
                                    del self.players[player_id]
            else:
                # 客户端发送到服务端
                self.socket.sendto(serialized, (self.server_address, SERVER_PORT))
        except Exception as e:
            print(f"[网络错误] 发送数据失败: {e}")
            if not self.is_server:
                self.connection_error = f"发送数据失败: {e}"
                self.connected = False

    def send_to_client(self, data, addr):
        """发送数据到指定客户端"""
        try:
            serialized = json.dumps(data).encode()
            self.socket.sendto(serialized, addr)
        except Exception as e:
            print(f"[网络错误] 发送到{addr}失败: {e}")

    def send_chat_message(self, message):
        """发送聊天消息"""
        if len(message.strip()) == 0:
            return
            
        player_name = f"玩家{self.player_id}"
        if self.player_id in self.players:
            player_name = self.players[self.player_id].get('name', player_name)
        
        chat_data = {
            'type': 'chat_message',
            'data': {
                'player_id': self.player_id,
                'player_name': player_name,
                'message': message[:MAX_CHAT_LENGTH],
                'timestamp': time.time()
            }
        }
        
        if self.is_server:
            # 服务端：直接处理并广播
            self._handle_chat_message(chat_data['data'])
        else:
            # 客户端：发送给服务端
            self.send_data(chat_data)
    
    def broadcast_chat_message(self, chat_msg):
        """广播聊天消息（仅服务端）"""
        if self.is_server:
            chat_data = {
                'type': 'chat_message',
                'data': {
                    'player_id': chat_msg.player_id,
                    'player_name': chat_msg.player_name,
                    'message': chat_msg.message,
                    'timestamp': chat_msg.timestamp
                }
            }
            
            for addr in list(self.clients.keys()):
                try:
                    self.send_to_client(chat_data, addr)
                except:
                    pass

    def request_fire_bullet(self, pos, direction, owner_id):
        """请求发射子弹"""
        if self.is_server:
            # 服务端直接创建子弹
            new_bullet = {
                'id': self.next_bullet_id,
                'pos': pos,
                'dir': direction,
                'owner': owner_id,
                'time': time.time()
            }
            self.next_bullet_id += 1
            with self.lock:
                self.active_bullets.append(new_bullet)
        else:
            # 客户端发送请求给服务端
            self.send_data({
                'type': 'request_bullet',
                'data': {
                    'pos': pos,
                    'dir': direction,
                    'owner': owner_id
                }
            })

    def request_melee_attack(self, attacker_id, direction, hit_targets, is_heavy=False):
        """请求近战攻击"""
        if self.is_server:
            # 服务端直接处理近战攻击
            melee_data = {
                'attacker_id': attacker_id,
                'direction': direction,
                'targets': hit_targets,
                'is_heavy': is_heavy  # 是否为重击
            }
            self._handle_melee_attack(melee_data)
        else:
            # 客户端发送请求给服务端
            self.send_data({
                'type': 'melee_attack',
                'data': {
                    'attacker_id': attacker_id,
                    'direction': direction,
                    'targets': hit_targets,
                    'is_heavy': is_heavy  # 是否为重击
                }
            })

    def update_door(self, door_id, door_state):
        """更新门状态"""
        self.doors[door_id] = door_state
        self.send_data({
            'type': 'door_update',
            'data': {'door_id': door_id, 'state': door_state}
        })

    def update_and_broadcast(self):
        """服务端定期广播游戏状态"""
        if self.is_server:
            current_time = time.time()
            if current_time - self.last_broadcast > 0.05:  # 20Hz
                # 广播玩家状态
                self.send_data({
                    'type': 'player_update', 
                    'data': {str(pid): pdata for pid, pdata in self.players.items()}
                })
                
                # 清理过期子弹（3秒后）
                with self.lock:
                    self.active_bullets = [
                        b for b in self.active_bullets 
                        if current_time - b['time'] < 3.0
                    ]
                
                # 广播子弹状态
                self.send_data({
                    'type': 'bullets_update',
                    'data': self.active_bullets
                })
                
                self.last_broadcast = current_time

    def get_bullets(self):
        """获取当前活动的子弹"""
        with self.lock:
            return list(self.active_bullets)

    def remove_bullet(self, bullet_id):
        """移除指定子弹"""
        if self.is_server:
            with self.lock:
                self.active_bullets = [b for b in self.active_bullets if b['id'] != bullet_id]

    def get_recent_chat_messages(self):
        """获取最近的聊天消息"""
        current_time = time.time()
        # 返回未过期的消息
        return [msg for msg in self.chat_messages if not msg.is_expired(current_time)]

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
    
    def stop(self):
        self.running = False
        try:
            self.socket.close()
        except:
            pass

class Bullet:
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
                
                player_rect = pygame.Rect(
                    player.pos.x - PLAYER_RADIUS,
                    player.pos.y - PLAYER_RADIUS,
                    PLAYER_RADIUS * 2,
                    PLAYER_RADIUS * 2
                )
                if bullet_rect.colliderect(player_rect):
                    self.has_hit.add(player.id)
                    
                    if network_manager:
                        damage_data = {
                            'target_id': player.id,
                            'damage': BULLET_DAMAGE,
                            'attacker_id': self.owner_id,
                            'type': 'bullet'
                        }
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

class Player:
    def __init__(self, player_id, x, y, is_local=False, name=None):
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
        self.is_local = is_local
        self.name = name if name is not None else f"玩家{player_id}"
        self.shooting = False
        self.is_dead = False
        self.death_time = 0
        self.respawn_time = 0
        self.is_respawning = False
        self.last_respawn_check = 0
        self.last_door_interaction = 0
        
        # 子弹散布相关属性
        self.last_movement_time = 0  # 上次移动时间
        self.shot_count = 0  # 连续射击计数
        self.last_shot_time = 0  # 上次射击时间
        
        # 近战武器
        self.melee_weapon = MeleeWeapon(player_id)
        
        # 新增：武器系统
        self.weapon_type = "gun"  # "gun" 或 "melee"
        self.last_weapon_switch = 0
        self.weapon_switch_cooldown = 0.5  # 武器切换冷却时间
        
        # 新增：瞄准系统
        self.is_aiming = False
        self.aim_offset = pygame.Vector2(0, 0)  # 瞄准时的相机偏移
        
        # 被击中减速效果
        self.hit_slowdown_end_time = 0  # 减速结束时间
        
        # 脚步声系统
        self.last_move_sound_time = 0
        self.move_sound_interval = 0.3  # 移动声音间隔(秒)
        self.is_making_sound = False  # 是否正在发出声音
        self.sound_volume = 0.0  # 声音音量 (0.0-1.0)
        
        # 静步功能
        self.is_walking = False  # 是否静步移动
        self.walk_speed_multiplier = 0.4  # 静步速度倍率（降低至40%）
        
        # 速度提升效果
        self.speed_boost_end_time = 0  # 速度提升结束时间
        self.speed_boost_multiplier = 1.0  # 速度提升倍率
        self.last_speed_warning_time = 0  # 上次速度提升警告时间

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

    def can_switch_weapon(self):
        """检查是否可以切换武器"""
        current_time = time.time()
        return current_time - self.last_weapon_switch >= self.weapon_switch_cooldown

    def switch_weapon(self):
        """切换武器"""
        if not self.can_switch_weapon() or self.is_dead or self.is_respawning:
            return False
        
        current_time = time.time()
        if self.weapon_type == "gun":
            self.weapon_type = "melee"
        else:
            self.weapon_type = "gun"
        
        self.last_weapon_switch = current_time
        print(f"玩家{self.id}切换到{'近战武器' if self.weapon_type == 'melee' else '枪械'}")
        return True

    def update_aim_offset(self, mouse_pos, screen_center):
        """更新瞄准偏移"""
        if self.is_aiming:
            # 计算鼠标相对于屏幕中心的偏移
            mouse_offset = pygame.Vector2(
                mouse_pos[0] - screen_center[0],
                mouse_pos[1] - screen_center[1]
            )
            
            # 限制偏移距离
            if mouse_offset.length() > AIM_CAMERA_RANGE:
                mouse_offset = mouse_offset.normalize() * AIM_CAMERA_RANGE
            
            # 应用灵敏度
            self.aim_offset = mouse_offset * AIM_SENSITIVITY
        else:
            # 平滑回到中心
            self.aim_offset *= 0.9
            if self.aim_offset.length() < 1:
                self.aim_offset = pygame.Vector2(0, 0)

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
        
        # 重置武器和瞄准状态
        self.weapon_type = "gun"
        self.is_aiming = False
        self.aim_offset = pygame.Vector2(0, 0)
        
        # 重置子弹散布相关属性
        self.last_movement_time = 0
        self.shot_count = 0
        self.last_shot_time = 0
        
        # 重置近战武器
        self.melee_weapon = MeleeWeapon(self.id)
        
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
                    'death_time': 0,
                    'respawn_time': 0,
                    'is_reloading': False,
                    'is_respawning': False,
                    'melee_attacking': False,
                    'melee_direction': 0,
                    'weapon_type': 'gun',
                    'is_aiming': False
                })
        
        self.last_respawn_check = time.time()
    
    def calculate_bullet_spread(self):
        """计算子弹散布角度"""
        current_time = time.time()
        spread = 0.0
        
        # 检查是否在移动
        is_moving = self.velocity.length() > 0.1
        if is_moving:
            self.last_movement_time = current_time
        
        # 移动时的散布（根据速度计算，最多15度）
        time_since_movement = current_time - self.last_movement_time
        if time_since_movement < 0.5 and is_moving:  # 移动后0.5秒内有散布
            # 根据速度计算散布，速度越快散布越大
            speed_ratio = min(self.velocity.length() / PLAYER_SPEED, 1.0)
            base_spread = speed_ratio * 15.0  # 基础散布最多15度
            
            # 静步时减少散布
            if self.is_walking:
                spread += base_spread * 0.5  # 静步时散布减半
            else:
                spread += base_spread
        
        # 连续射击散布
        time_since_last_shot = current_time - self.last_shot_time
        if time_since_last_shot < 3.0:  # 3秒内的连续射击
            # 第一发是准的，之后有<=5度的基础散布
            if self.shot_count > 0:
                spread += min(self.shot_count * 1.0, 5.0)  # 最大5度散布
        else:
            # 重置射击计数
            self.shot_count = 0
        
        # 瞄准时限制最大散布为3度
        if self.is_aiming:
            spread = 0
        
        return spread

    def update(self, dt, game_map, bullets, network_manager=None, all_players=None):
        current_time = time.time()
        
        # 重置复活状态
        if self.is_respawning and current_time - self.last_respawn_check > 1.0:
            self.is_respawning = False
            self.last_door_interaction = 0
        
        # 更新近战武器
        self.melee_weapon.update(dt)
        
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
            
            # 更新瞄准偏移
            self.update_aim_offset((mouse_x, mouse_y), (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
            
            # 键盘控制移动
            keys = pygame.key.get_pressed()
            move_dir = pygame.Vector2(0, 0)
            if keys[K_w]: move_dir.y -= 1
            if keys[K_s]: move_dir.y += 1
            if keys[K_a]: move_dir.x -= 1
            if keys[K_d]: move_dir.x += 1
            
            # 检测静步状态
            self.is_walking = keys[K_LSHIFT] or keys[K_RSHIFT]
            
            # 检测移动声音 - 根据速度调整声音大小
            is_moving = move_dir.length() > 0
            
            # 静步时完全不发出声音
            if self.is_walking:
                self.is_making_sound = False
                self.sound_volume = 0.0
            # 移动时根据速度调整声音大小
            elif is_moving and current_time - self.last_move_sound_time > self.move_sound_interval:
                # 计算速度比例 (0.0-1.0)
                speed_ratio = min(self.velocity.length() / PLAYER_SPEED, 1.0)
                
                # 设置最小速度阈值，低于此速度不发声
                min_speed_threshold = 0.2  # 低于20%速度不发声
                
                if speed_ratio > min_speed_threshold:
                    self.is_making_sound = True
                    # 声音大小随速度线性增加 (0.0-1.0)
                    self.sound_volume = (speed_ratio - min_speed_threshold) / (1.0 - min_speed_threshold)
                    self.last_move_sound_time = current_time
                else:
                    # 速度太低，不发出声音
                    self.is_making_sound = False
                    self.sound_volume = 0.0
            elif not is_moving:
                self.is_making_sound = False
                self.sound_volume = 0.0
            
            if move_dir.length() > 0:
                # 计算移动速度（瞄准时减速）
                current_speed = PLAYER_SPEED
                
                # 检查是否有速度提升效果
                current_time = time.time()
                has_speed_boost = current_time < self.speed_boost_end_time
                
                # 应用各种速度修饰符
                if self.is_aiming:
                    current_speed *= AIMING_SPEED_MULTIPLIER
                if self.is_walking:
                    current_speed *= self.walk_speed_multiplier  # 静步速度
                if has_speed_boost:
                    current_speed *= self.speed_boost_multiplier  # 速度提升效果
                    
                    # 如果速度提升即将结束，发送提示
                    remaining_time = self.speed_boost_end_time - current_time
                    if remaining_time < 1.0 and hasattr(self, 'last_speed_warning_time') and current_time - self.last_speed_warning_time > 1.0:
                        self.last_speed_warning_time = current_time
                        # 尝试发送系统消息
                        network_manager_obj = network_manager
                        if network_manager_obj and hasattr(network_manager_obj, '_send_system_message'):
                            network_manager_obj._send_system_message(f"速度提升效果即将结束: {remaining_time:.1f}秒")
                
                move_dir = move_dir.normalize() * current_speed
                self.velocity += move_dir * dt * 5
            else:
                self.velocity *= 0.9
                
            # 限制最大速度
            max_speed = PLAYER_SPEED
            
            # 检查是否有速度提升效果
            current_time = time.time()
            has_speed_boost = current_time < self.speed_boost_end_time
            
            # 应用各种速度修饰符
            if self.is_aiming:
                max_speed *= AIMING_SPEED_MULTIPLIER
            if self.is_walking:
                max_speed *= self.walk_speed_multiplier  # 静步速度上限
            if has_speed_boost:
                max_speed *= self.speed_boost_multiplier  # 速度提升效果
                
            if self.velocity.length() > max_speed:
                self.velocity = self.velocity.normalize() * max_speed

            # 左键攻击控制（根据武器类型）
            if self.shooting and not self.is_dead:
                if self.weapon_type == "gun":
                    # 枪械射击
                    if not self.is_reloading and self.ammo > 0:
                        if current_time - self.last_shot > BULLET_COOLDOWN:
                            # 计算子弹散布角度
                            spread_angle = self.calculate_bullet_spread()
                            
                            # 应用散布到子弹方向
                            if spread_angle > 0:
                                final_angle = self.angle + random.uniform(-spread_angle, spread_angle)
                            else:
                                final_angle = self.angle
                            bullet_dir = pygame.Vector2(math.cos(math.radians(final_angle)),
                                                      -math.sin(math.radians(final_angle)))
                            bullet_pos = self.pos + bullet_dir * (PLAYER_RADIUS + BULLET_RADIUS)
                            
                            # 请求发射子弹
                            network_manager.request_fire_bullet(
                                [bullet_pos.x, bullet_pos.y],
                                [bullet_dir.x, bullet_dir.y],
                                self.id
                            )
                            
                            self.ammo -= 1
                            self.last_shot = current_time
                            self.last_shot_time = current_time
                            self.shot_count += 1
                            self.is_making_sound = True  # 射击时发出声音
                            self.sound_volume = 1.0  # 射击时声音音量最大
                elif self.weapon_type == "melee":
                    # 近战攻击
                    if self.melee_weapon.can_attack():
                        self.start_melee_attack()
                        self.is_making_sound = True  # 近战攻击时发出声音
                        self.sound_volume = 0.4  # 近战攻击声音音量（略小于射击）
            
            # 近战攻击检测
            if self.melee_weapon.is_attacking:
                # 检查近战攻击是否击中目标
                targets = {}
                if all_players:
                    for pid, player in all_players.items():
                        if pid != self.id and not player.is_dead:
                            targets[pid] = player.pos
                
                # 收集障碍物（墙壁和门）
                obstacles = []
                if game_map:
                    # 添加墙壁作为障碍物
                    for wall in game_map.walls:
                        obstacles.append(wall)
                    # 添加门作为障碍物
                    for door in game_map.doors:
                        if not door.is_open:  # 只有关闭的门才作为障碍物
                            obstacles.append(door.rect)
                
                hit_targets = self.melee_weapon.check_hit(self.pos, targets, obstacles)
                if hit_targets:
                    # 发送近战攻击请求
                    network_manager.request_melee_attack(
                        self.id,
                        self.melee_weapon.attack_direction,
                        hit_targets,
                        is_heavy=self.melee_weapon.is_heavy_attack  # 传递是否为重击
                    )
            
            # 换弹控制
            if (keys[K_r] or self.ammo <= 0) and not self.is_reloading and self.ammo < MAGAZINE_SIZE and self.weapon_type == "gun":
                self.is_reloading = True
                self.reload_start = current_time
                
            if self.is_reloading and (current_time - self.reload_start) >= RELOAD_TIME:
                self.ammo = MAGAZINE_SIZE
                self.is_reloading = False
        
        # 检查是否处于被击中减速状态（所有玩家）
        current_time = time.time()
        is_slowed = current_time < self.hit_slowdown_end_time
        
        # 计算实际速度
        actual_velocity = pygame.Vector2(self.velocity)
        if is_slowed:
            actual_velocity *= HIT_SLOWDOWN_FACTOR
        
        # 更新位置（所有玩家）
        if actual_velocity.length() > 0 and not self.is_respawning and not self.is_dead:
            new_pos = self.pos + actual_velocity * dt
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
            if keys[K_e] and current_time - self.last_door_interaction > 0.5:
                self.last_door_interaction = current_time
                for i, door in enumerate(game_map.doors):
                    if door.try_interact(self.pos):
                        # 发送门状态更新
                        door_state = door.get_state()
                        network_manager.update_door(i, door_state)
                        break

        # 从网络同步生命值和死亡状态（只有本地玩家）
        if is_local_player and self.id in network_manager.players:
            server_data = network_manager.players[self.id]
            
            # 同步生命值
            if self.health != server_data['health']:
                old_health = self.health
                self.health = server_data['health']
                if old_health > self.health:
                    print(f"[同步] 玩家{self.id}生命值从{old_health}同步为{self.health}")
            
            # 同步死亡状态
            if self.is_dead != server_data['is_dead']:
                self.is_dead = server_data['is_dead']
                if self.is_dead:
                    print(f"[同步] 玩家{self.id}死亡状态同步")
                    self.death_time = server_data.get('death_time', current_time)
                    self.respawn_time = server_data.get('respawn_time', current_time + RESPAWN_TIME)

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
                'death_time': self.death_time,
                'respawn_time': self.respawn_time,
                'is_respawning': self.is_respawning,
                'name': self.name,
                'melee_attacking': self.melee_weapon.is_attacking,
                'melee_direction': self.melee_weapon.attack_direction,
                'weapon_type': self.weapon_type,
                'is_aiming': self.is_aiming,
                'is_making_sound': self.is_making_sound,  # 声音状态
                'sound_volume': self.sound_volume  # 新增声音音量
            }
            
            # 更新网络管理器中的玩家数据
            if network_manager.is_server:
                # 服务端：从网络数据同步权威状态
                if self.id in network_manager.players:
                    server_data = network_manager.players[self.id]
                    self.health = server_data.get('health', self.health)
                    self.is_dead = server_data.get('is_dead', self.is_dead)
                    self.death_time = server_data.get('death_time', self.death_time)
                    self.respawn_time = server_data.get('respawn_time', self.respawn_time)
                    
                    # 更新服务端数据（位置等输入数据）
                    network_manager.players[self.id].update(player_data)
                    # 保持权威数据
                    network_manager.players[self.id]['health'] = self.health
                    network_manager.players[self.id]['is_dead'] = self.is_dead
                    network_manager.players[self.id]['death_time'] = self.death_time
                    network_manager.players[self.id]['respawn_time'] = self.respawn_time
                else:
                    network_manager.players[self.id] = player_data
            else:
                # 客户端发送数据
                network_manager.send_data({
                    'type': 'player_update',
                    'data': {str(self.id): player_data}
                })

    def start_melee_attack(self, is_heavy=False):
        """开始近战攻击"""
        if not self.is_dead and not self.is_respawning and self.weapon_type == "melee":
            return self.melee_weapon.start_attack(self.angle, is_heavy)
        return False

    def draw(self, surface, camera_offset, player_pos=None, player_angle=None, walls=None, doors=None, is_local_player=False, is_aiming=False):
        """绘制玩家（考虑视线遮挡）"""
        player_screen_pos = pygame.Vector2(
            self.pos.x - camera_offset.x,
            self.pos.y - camera_offset.y
        )
        
        # 如果不是本地玩家，检查是否可见
        if not is_local_player and player_pos and player_angle and walls and doors:
            # 根据瞄准状态选择视野角度
            current_fov = 30 if is_aiming else 120
            if not is_visible(player_pos, player_angle, self.pos, current_fov, walls, doors):
                return  # 不可见，不绘制
        
        if self.is_dead:
            # 死亡状态绘制灰色圆圈和复活倒计时
            pygame.draw.circle(
                surface, DEAD_COLOR,
                (int(player_screen_pos.x), int(player_screen_pos.y)),
                PLAYER_RADIUS
            )
            
            # 显示复活倒计时
            current_time = time.time()
            remaining_time = max(0, self.respawn_time - current_time)
            if remaining_time > 0:
                respawn_text = f"{remaining_time:.1f}s"
                text_surface = font.render(respawn_text, True, WHITE)
                surface.blit(text_surface, 
                           (int(player_screen_pos.x - text_surface.get_width() // 2),
                            int(player_screen_pos.y - PLAYER_RADIUS - 40)))
            
            return
        
        # 绘制近战攻击效果（仅当使用近战武器时）
        if self.weapon_type == "melee" and self.melee_weapon.is_attacking:
            self.draw_melee_attack(surface, camera_offset)
        
        # 绘制瞄准状态指示
        if is_local_player and self.is_aiming:
            self.draw_aim_indicator(surface, player_screen_pos)
        
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
        
        # 根据武器类型改变颜色
        player_color = self.color
        if self.weapon_type == "melee":
            # 近战武器时显示为偏红色
            player_color = (min(255, self.color[0] + 50), max(0, self.color[1] - 30), max(0, self.color[2] - 30))
        
        pygame.draw.polygon(surface, player_color, screen_points)
        
        # 绘制血条和名字
        health_bar_width = 40
        health_ratio = self.health / self.max_health
        pygame.draw.rect(surface, RED, (screen_points[0][0] - health_bar_width / 2,
                                      screen_points[0][1] - 15,
                                      health_bar_width, 5))
        pygame.draw.rect(surface, GREEN, (screen_points[0][0] - health_bar_width / 2,
                                        screen_points[0][1] - 15,
                                        health_bar_width * health_ratio, 5))
        
        name_surface = small_font.render(self.name, True, WHITE)
        surface.blit(name_surface, (screen_points[0][0] - name_surface.get_width() // 2,
                                   screen_points[0][1] - 35))

    def draw_aim_indicator(self, surface, player_screen_pos):
        """绘制瞄准指示器"""
        # 绘制瞄准圈
        pygame.draw.circle(surface, AIM_COLOR, 
                         (int(player_screen_pos.x), int(player_screen_pos.y)), 
                         PLAYER_RADIUS + 10, 2)
        
        # 绘制准星
        crosshair_size = 15
        pygame.draw.line(surface, AIM_COLOR,
                        (player_screen_pos.x - crosshair_size, player_screen_pos.y),
                        (player_screen_pos.x + crosshair_size, player_screen_pos.y), 2)
        pygame.draw.line(surface, AIM_COLOR,
                        (player_screen_pos.x, player_screen_pos.y - crosshair_size),
                        (player_screen_pos.x, player_screen_pos.y + crosshair_size), 2)

    def draw_melee_attack(self, surface, camera_offset):
        """绘制近战攻击效果"""
        player_screen_pos = pygame.Vector2(
            self.pos.x - camera_offset.x,
            self.pos.y - camera_offset.y
        )
        
        progress = self.melee_weapon.get_attack_progress()
        
        # 绘制攻击弧形
        half_angle = MELEE_ANGLE / 2
        current_angle = MELEE_ANGLE * progress
        
        # 创建攻击弧形的点
        arc_points = [player_screen_pos]
        
        for i in range(int(current_angle) + 1):
            angle = self.melee_weapon.attack_direction - half_angle + i
            angle_rad = math.radians(angle)
            
            end_x = player_screen_pos.x + math.cos(angle_rad) * MELEE_RANGE
            end_y = player_screen_pos.y - math.sin(angle_rad) * MELEE_RANGE
            arc_points.append((end_x, end_y))
        
        # 绘制半透明的攻击扇形
        if len(arc_points) >= 3:
            try:
                attack_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                attack_color = (*MELEE_COLOR, int(150 * (1 - progress)))  # 随着动画进度淡出
                pygame.draw.polygon(attack_surface, attack_color, arc_points)
                surface.blit(attack_surface, (0, 0))
            except:
                # 如果绘制失败，画一个简单的圆弧
                pygame.draw.arc(surface, MELEE_COLOR, 
                               (player_screen_pos.x - MELEE_RANGE, player_screen_pos.y - MELEE_RANGE,
                                MELEE_RANGE * 2, MELEE_RANGE * 2),
                               math.radians(self.melee_weapon.attack_direction - half_angle),
                               math.radians(self.melee_weapon.attack_direction + half_angle),
                               5)

    def sync_from_network(self, network_data):
        """从网络数据同步其他玩家的状态"""
        if 'melee_attacking' in network_data:
            if network_data['melee_attacking'] and not self.melee_weapon.is_attacking:
                # 开始近战攻击动画
                self.melee_weapon.start_attack(network_data.get('melee_direction', 0))
            elif not network_data['melee_attacking']:
                # 停止近战攻击动画
                self.melee_weapon.is_attacking = False
        
        # 同步武器类型
        if 'weapon_type' in network_data:
            self.weapon_type = network_data['weapon_type']
        
        # 同步瞄准状态
        if 'is_aiming' in network_data:
            self.is_aiming = network_data['is_aiming']
            
        # 同步声音状态
        if 'is_making_sound' in network_data:
            self.is_making_sound = network_data['is_making_sound']
            
        # 同步声音音量
        if 'sound_volume' in network_data:
            self.sound_volume = network_data['sound_volume']
    
    def take_damage(self, damage):
        """玩家受到伤害"""
        current_time = time.time()
        self.health -= damage
        
        # 触发被击中减速效果
        self.hit_slowdown_end_time = current_time + HIT_SLOWDOWN_DURATION
        
        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            self.respawn_time = time.time() + RESPAWN_TIME
            return True
        
        return False

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
                door_state = network_manager.doors[i]
                door.set_state(door_state)

class Game:
    def __init__(self):
        self.running = True  
        self.clock = pygame.time.Clock()  
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("多人射击游戏 - 武器切换 + 瞄准系统")
        
        # 游戏状态
        self.state = "MENU"  # MENU, SCANNING, CONNECTING, PLAYING, ERROR
        self.connection_info = None
        self.error_message = ""
        self.connecting_start_time = 0
        
        # 服务器扫描
        self.scanning_servers = False
        self.found_servers = []
        self.scan_thread = None
        
        # 网络管理器
        self.network_manager = None
        
        # 网络同步
        self.last_sync_time = 0
        self.sync_interval = 0.05  # 50ms同步间隔
        
        # 聊天系统
        self.chat_active = False
        self.chat_input = ""
        self.chat_cursor_blink = 0
        self.last_chat_cursor_blink = 0
        
        # 红色滤镜效果
        self.hit_effect_time = 0
        self.hit_effect_duration = 0.3  # 0.3秒的红色滤镜效果
        
        # 视角显示
        self.show_vision = True  # 默认开启视角系统
        
        # 调试模式
        self.debug_mode = True
        
        # 脚步声系统
        self.footstep_detection_range = VISION_RANGE  # 脚步声检测范围，使用视角范围常量
        self.nearby_sound_players = []  # 附近发出声音的玩家
        
        # 游戏规则设置
        self.game_rules = {
            'damage_multiplier': 1.0,  # 伤害倍率，默认为1.0
            'respawn_time': RESPAWN_TIME,      # 复活时间（秒）
            'friendly_fire': True,     # 友军伤害
            'bullet_speed': BULLET_SPEED,      # 子弹速度
            'footstep_range': self.footstep_detection_range    # 脚步声范围
        }
    
    def trigger_hit_effect(self):
        """触发被击中时的红色滤镜效果"""
        print("[受击效果] 触发红色滤镜效果")
        self.hit_effect_time = self.hit_effect_duration
    
    def start_server_scan(self):
        """启动服务器扫描"""
        if not self.scanning_servers:
            self.scanning_servers = True
            self.found_servers = []
            self.scan_thread = threading.Thread(target=self._scan_servers_thread)
            self.scan_thread.daemon = True
            self.scan_thread.start()
    
    def _scan_servers_thread(self):
        """服务器扫描线程"""
        try:
            self.found_servers = scan_for_servers()
        except Exception as e:
            print(f"扫描服务器时出错: {e}")
        finally:
            self.scanning_servers = False
    
    def show_menu(self):
        """显示主菜单"""
        # 菜单状态
        selected_option = 0  # 0=创建服务器, 1=加入游戏, 2=刷新服务器
        name_input_text = "玩家" + str(int(time.time() * 1000) % 10000)
        name_input_active = False
        input_text = ""
        input_active = False
        
        # 自动开始扫描
        if not self.scanning_servers and not self.found_servers:
            self.start_server_scan()
        
        # 按钮定义
        button_width = 200
        button_height = 50
        button_spacing = 20
        start_y = 150
        
        button_create = pygame.Rect(50, start_y, button_width, button_height)
        button_refresh = pygame.Rect(50, start_y + button_height + button_spacing, button_width, button_height)
        name_input_box = pygame.Rect(50, start_y + (button_height + button_spacing) * 2 + 10, button_width, 35)
        input_box = pygame.Rect(50, start_y + (button_height + button_spacing) * 3 + 50, button_width, 35)
        button_connect = pygame.Rect(50, start_y + (button_height + button_spacing) * 3 + 100, button_width, 40)
        
        # 服务器列表区域
        server_list_x = 300
        server_list_y = start_y
        server_list_width = 450
        server_item_height = 60
        
        while self.state == "MENU":
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False
                    return
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        self.running = False
                        return
                    elif event.key == K_UP:
                        selected_option = max(0, selected_option - 1)
                        input_active = False
                        name_input_active = False
                    elif event.key == K_DOWN:
                        selected_option = min(2, selected_option + 1)
                        input_active = False
                        name_input_active = False
                    elif event.key == K_RETURN:
                        if selected_option == 0:
                            # 创建服务器
                            self.connection_info = {'is_server': True}
                            self.state = "CONNECTING"
                            self.connecting_start_time = time.time()
                            return
                        elif selected_option == 1 and input_text.strip():
                            # 手动连接
                            self.connection_info = {
                                'is_server': False,
                                'server_ip': input_text.strip()
                            }
                            # 保存玩家名称到网络管理器
                            if self.network_manager:
                                self.network_manager.player_name = name_input_text
                            else:
                                # 如果网络管理器尚未创建，先保存到游戏实例
                                self.player_name = name_input_text
                            self.state = "CONNECTING"
                            self.connecting_start_time = time.time()
                            return
                        elif selected_option == 2:
                            # 刷新服务器列表
                            self.start_server_scan()
                    elif name_input_active:
                        if event.key == K_BACKSPACE:
                            name_input_text = name_input_text[:-1]
                        else:
                            if len(name_input_text) < 20:
                                name_input_text += event.unicode
                    elif input_active:
                        if event.key == K_BACKSPACE:
                            input_text = input_text[:-1]
                        else:
                            if len(input_text) < 50:
                                input_text += event.unicode
                elif event.type == MOUSEBUTTONDOWN:
                    if button_create.collidepoint(event.pos):
                        selected_option = 0
                        input_active = False
                        # 创建服务器
                        self.connection_info = {'is_server': True}
                        self.state = "CONNECTING"
                        self.connecting_start_time = time.time()
                        return
                    elif button_refresh.collidepoint(event.pos):
                        selected_option = 2
                        input_active = False
                        name_input_active = False
                        # 刷新服务器列表
                        self.start_server_scan()
                    elif name_input_box.collidepoint(event.pos):
                        name_input_active = True
                        input_active = False
                        selected_option = 1
                    elif input_box.collidepoint(event.pos):
                        input_active = True
                        name_input_active = False
                        selected_option = 1
                    elif button_connect.collidepoint(event.pos) and input_text.strip():
                        # 手动连接按钮
                        self.connection_info = {
                            'is_server': False,
                            'server_ip': input_text.strip()
                        }
                        # 保存玩家名称到网络管理器
                        if self.network_manager:
                            self.network_manager.player_name = name_input_text
                        else:
                            # 如果网络管理器尚未创建，先保存到游戏实例
                            self.player_name = name_input_text
                        self.state = "CONNECTING"
                        self.connecting_start_time = time.time()
                        return
                    else:
                        # 检查是否点击了服务器列表项
                        for i, server in enumerate(self.found_servers):
                            server_rect = pygame.Rect(server_list_x, server_list_y + i * (server_item_height + 10), 
                                                    server_list_width, server_item_height)
                            if server_rect.collidepoint(event.pos):
                                # 连接到选中的服务器
                                self.connection_info = {
                                    'is_server': False,
                                    'server_ip': server['ip']
                                }
                                self.state = "CONNECTING"
                                self.connecting_start_time = time.time()
                                return
                        input_active = False
            
            # 绘制菜单
            self.screen.fill(BLACK)
            
            # 标题
            title = title_font.render("多人射击游戏", True, WHITE)
            self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 50))
            
            # 副标题
            subtitle = font.render("武器切换 + 瞄准系统", True, LIGHT_BLUE)
            self.screen.blit(subtitle, (SCREEN_WIDTH//2 - subtitle.get_width()//2, 100))
            
            # 左侧控制面板
            panel_title = large_font.render("游戏控制", True, WHITE)
            self.screen.blit(panel_title, (50, 120))
            
            # 创建服务器按钮
            create_color = GREEN if selected_option == 0 else DARK_BLUE
            pygame.draw.rect(self.screen, create_color, button_create)
            pygame.draw.rect(self.screen, WHITE, button_create, 3)
            create_text = font.render("创建服务器", True, WHITE)
            self.screen.blit(create_text, (button_create.x + (button_create.width - create_text.get_width())//2,
                                         button_create.y + (button_create.height - create_text.get_height())//2))
            
            # 刷新服务器按钮
            refresh_color = GREEN if selected_option == 2 else DARK_BLUE
            pygame.draw.rect(self.screen, refresh_color, button_refresh)
            pygame.draw.rect(self.screen, WHITE, button_refresh, 3)
            refresh_text = font.render("刷新服务器列表", True, WHITE)
            self.screen.blit(refresh_text, (button_refresh.x + (button_refresh.width - refresh_text.get_width())//2,
                                          button_refresh.y + (button_refresh.height - refresh_text.get_height())//2))
            
            # 玩家名称输入框
            name_input_color = YELLOW if name_input_active else WHITE
            pygame.draw.rect(self.screen, BLACK, name_input_box)
            pygame.draw.rect(self.screen, name_input_color, name_input_box, 2)
            
            name_label = font.render("玩家名称:", True, WHITE)
            self.screen.blit(name_label, (name_input_box.x, name_input_box.y - 30))
            
            name_input_surface = font.render(name_input_text, True, WHITE)
            self.screen.blit(name_input_surface, (name_input_box.x + 10, name_input_box.y + 7))
            
            # 玩家名称输入光标
            if name_input_active and pygame.time.get_ticks() % 1000 < 500:
                name_cursor_x = name_input_box.x + 10 + name_input_surface.get_width()
                pygame.draw.line(self.screen, WHITE, 
                               (name_cursor_x, name_input_box.y + 5), 
                               (name_cursor_x, name_input_box.y + name_input_box.height - 5), 2)
            
            # IP输入框
            input_color = YELLOW if input_active else WHITE
            pygame.draw.rect(self.screen, BLACK, input_box)
            pygame.draw.rect(self.screen, input_color, input_box, 2)
            
            ip_label = font.render("手动输入IP:", True, WHITE)
            self.screen.blit(ip_label, (input_box.x, input_box.y - 30))
            
            input_surface = font.render(input_text, True, WHITE)
            self.screen.blit(input_surface, (input_box.x + 10, input_box.y + 7))
            
            # 光标
            if input_active and pygame.time.get_ticks() % 1000 < 500:
                cursor_x = input_box.x + 10 + input_surface.get_width()
                pygame.draw.line(self.screen, WHITE, 
                               (cursor_x, input_box.y + 5), 
                               (cursor_x, input_box.y + input_box.height - 5), 2)
            
            # 手动连接按钮
            connect_enabled = len(input_text.strip()) > 0
            connect_color = GREEN if connect_enabled else GRAY
            pygame.draw.rect(self.screen, connect_color, button_connect)
            pygame.draw.rect(self.screen, WHITE, button_connect, 2)
            connect_text = font.render("手动连接", True, WHITE if connect_enabled else DARK_GRAY)
            self.screen.blit(connect_text, (button_connect.x + (button_connect.width - connect_text.get_width())//2,
                                          button_connect.y + (button_connect.height - connect_text.get_height())//2))
            
            # 右侧服务器列表
            list_title = large_font.render("局域网服务器", True, WHITE)
            self.screen.blit(list_title, (server_list_x, 120))
            
            if self.scanning_servers:
                # 显示扫描状态
                scan_text = font.render("正在扫描局域网服务器...", True, YELLOW)
                self.screen.blit(scan_text, (server_list_x, server_list_y))
                
                # 动画点
                dots = "." * ((pygame.time.get_ticks() // 500) % 4)
                dots_text = font.render(dots, True, YELLOW)
                self.screen.blit(dots_text, (server_list_x + scan_text.get_width() + 10, server_list_y))
                
            elif self.found_servers:
                # 显示找到的服务器
                for i, server in enumerate(self.found_servers[:5]):  # 最多显示5个服务器
                    server_rect = pygame.Rect(server_list_x, server_list_y + i * (server_item_height + 10), 
                                            server_list_width, server_item_height)
                    
                    # 服务器背景
                    pygame.draw.rect(self.screen, DARK_BLUE, server_rect)
                    pygame.draw.rect(self.screen, WHITE, server_rect, 2)
                    
                    # 服务器信息
                    server_name = font.render(server.get('name', '未知服务器'), True, WHITE)
                    server_ip = small_font.render(f"IP: {server['ip']}", True, LIGHT_BLUE)
                    player_info = small_font.render(f"玩家: {server.get('players', 0)}/{server.get('max_players', '?')}", True, GREEN)
                    
                    self.screen.blit(server_name, (server_rect.x + 10, server_rect.y + 5))
                    self.screen.blit(server_ip, (server_rect.x + 10, server_rect.y + 25))
                    self.screen.blit(player_info, (server_rect.x + 10, server_rect.y + 40))
                    
                    # 连接提示
                    connect_hint = small_font.render("点击连接", True, YELLOW)
                    self.screen.blit(connect_hint, (server_rect.x + server_rect.width - connect_hint.get_width() - 10, 
                                                  server_rect.y + server_rect.height//2 - connect_hint.get_height()//2))
            else:
                # 没有找到服务器
                no_server_text = font.render("未找到局域网服务器", True, GRAY)
                self.screen.blit(no_server_text, (server_list_x, server_list_y))
                hint_text = small_font.render("点击\"刷新服务器列表\"重新扫描", True, GRAY)
                self.screen.blit(hint_text, (server_list_x, server_list_y + 30))
            
            # 操作提示
            controls = [
                "方向键/鼠标选择，Enter确认",
                "ESC退出游戏",
                "点击服务器项直接连接"
            ]
            
            for i, control in enumerate(controls):
                control_text = small_font.render(control, True, GRAY)
                self.screen.blit(control_text, (50, SCREEN_HEIGHT - 80 + i * 20))
            
            pygame.display.flip()
            self.clock.tick(FPS)
    
    def show_connecting_screen(self):
        """显示连接中界面"""
        dots = ""
        last_dot_time = 0
        
        while self.state == "CONNECTING":
            current_time = time.time()
            
            # 检查连接超时
            if current_time - self.connecting_start_time > CONNECTION_TIMEOUT:
                self.error_message = "连接超时，请检查网络连接"
                self.state = "ERROR"
                return
            
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False
                    return
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        self.state = "MENU"
                        return
            
            # 尝试初始化游戏
            if self.initialize_game():
                self.state = "PLAYING"
                return
            
            # 检查是否出现错误
            if self.network_manager is not None and self.network_manager.connection_error:
                self.error_message = self.network_manager.connection_error
                self.state = "ERROR"
                return
            
            # 更新动画点
            if current_time - last_dot_time > 0.5:
                dots = dots + "." if len(dots) < 3 else ""
                last_dot_time = current_time
            
            # 绘制连接界面
            self.screen.fill(BLACK)
            
            if self.connection_info['is_server']:
                title = large_font.render("正在启动服务器" + dots, True, WHITE)
                info = font.render("等待其他玩家连接...", True, LIGHT_BLUE)
                local_ip = get_local_ip()
                ip_info = font.render(f"服务器地址: {local_ip}:{SERVER_PORT}", True, GREEN)
                self.screen.blit(ip_info, (SCREEN_WIDTH//2 - ip_info.get_width()//2, SCREEN_HEIGHT//2 + 30))
            else:
                title = large_font.render("正在连接服务器" + dots, True, WHITE)
                info = font.render(f"服务器: {self.connection_info['server_ip']}", True, LIGHT_BLUE)
            
            self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, SCREEN_HEIGHT//2 - 50))
            self.screen.blit(info, (SCREEN_WIDTH//2 - info.get_width()//2, SCREEN_HEIGHT//2))
            
            # 取消提示
            cancel_text = small_font.render("按ESC键取消", True, GRAY)
            self.screen.blit(cancel_text, (SCREEN_WIDTH//2 - cancel_text.get_width()//2, SCREEN_HEIGHT//2 + 70))
            
            pygame.display.flip()
            self.clock.tick(FPS)
    
    def show_error_screen(self):
        """显示错误界面"""
        while self.state == "ERROR":
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False
                    return
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE or event.key == K_RETURN:
                        self.state = "MENU"
                        return
            
            self.screen.fill(BLACK)
            
            # 错误标题
            error_title = large_font.render("连接失败", True, RED)
            self.screen.blit(error_title, (SCREEN_WIDTH//2 - error_title.get_width()//2, SCREEN_HEIGHT//2 - 100))
            
            # 错误信息
            error_lines = self.error_message.split('\n')
            for i, line in enumerate(error_lines):
                error_text = font.render(line, True, WHITE)
                self.screen.blit(error_text, (SCREEN_WIDTH//2 - error_text.get_width()//2, SCREEN_HEIGHT//2 - 50 + i * 30))
            
            # 提示信息
            hint_text = small_font.render("按ESC或Enter键返回主菜单", True, LIGHT_BLUE)
            self.screen.blit(hint_text, (SCREEN_WIDTH//2 - hint_text.get_width()//2, SCREEN_HEIGHT//2 + 100))
            
            pygame.display.flip()
            self.clock.tick(FPS)
    
    def initialize_game(self):
        """初始化游戏组件"""
        try:
            if not self.network_manager:
                # 初始化网络管理器
                if self.connection_info['is_server']:
                    self.network_manager = NetworkManager(is_server=True, game_instance=self)
                else:
                    self.network_manager = NetworkManager(
                        is_server=False,
                        server_address=self.connection_info['server_ip'],
                        game_instance=self
                    )
            
            # 检查连接是否成功
            if not self.network_manager.connected:
                return False
            
            # 等待分配玩家ID（客户端）
            if not self.connection_info['is_server']:
                if self.network_manager.player_id is None:
                    return False
            
            # 随机选择一个房间作为出生点
            spawn_room = random.choice(range(9))
            spawn_row = spawn_room // 3
            spawn_col = spawn_room % 3
            spawn_x = spawn_col * ROOM_SIZE + ROOM_SIZE // 2
            spawn_y = spawn_row * ROOM_SIZE + ROOM_SIZE // 2
            
            # 创建本地玩家
            self.player = Player(self.network_manager.player_id, spawn_x, spawn_y, is_local=True, name=self.network_manager.player_name)
            self.other_players = {}  # 存储其他玩家
            
            # 初始化游戏地图（使用九宫格地图）
            self.game_map = Map()
            self.bullets = []  # 本地子弹对象
            self.camera_offset = pygame.Vector2(0, 0)
            
            print(f"游戏初始化成功，玩家ID: {self.network_manager.player_id}")
            return True
            
        except Exception as e:
            print(f"初始化游戏失败: {e}")
            self.error_message = f"游戏初始化失败: {e}"
            return False
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    if self.chat_active:
                        self.chat_active = False
                        self.chat_input = ""
                    else:
                        self.running = False
                elif event.key == K_y and not self.chat_active:  # 按Y开启聊天
                    self.chat_active = True
                    self.chat_input = ""
                elif event.key == K_3 and not self.chat_active:  # 按3切换武器
                    if self.player and not self.player.is_dead:
                        self.player.switch_weapon()
                elif self.chat_active:
                    # 聊天模式下的按键处理
                    if event.key == K_RETURN:
                        if len(self.chat_input.strip()) > 0:
                            self.network_manager.send_chat_message(self.chat_input.strip())
                        self.chat_active = False
                        self.chat_input = ""
                    elif event.key == K_BACKSPACE:
                        self.chat_input = self.chat_input[:-1]
                    else:
                        if len(self.chat_input) < MAX_CHAT_LENGTH:
                            self.chat_input += event.unicode
                elif not self.chat_active:
                    # 非聊天模式下的按键处理
                    if event.key == K_r and not self.player.is_reloading and not self.player.is_dead and self.player.weapon_type == "gun":
                        self.player.is_reloading = True
                        self.player.reload_start = time.time()
                    elif event.key == K_F3:  # 切换调试模式
                        self.debug_mode = not self.debug_mode
                    elif event.key == K_F4:  # 切换视角显示
                        self.show_vision = not self.show_vision
            elif event.type == MOUSEBUTTONDOWN and not self.chat_active:
                if event.button == 1 and not self.player.is_dead:  # 左键按下且未死亡
                    if self.player.weapon_type == "melee":  # 近战武器时触发轻击
                        self.player.start_melee_attack(is_heavy=False)
                    else:  # 其他武器时射击
                        self.player.shooting = True
                elif event.button == 3 and not self.player.is_dead:  # 右键按下
                    if self.player.weapon_type == "melee":  # 近战武器时触发重击
                        self.player.start_melee_attack(is_heavy=True)
                    else:  # 其他武器时瞄准
                        self.player.is_aiming = True
            elif event.type == MOUSEBUTTONUP and not self.chat_active:
                if event.button == 1:  # 左键释放
                    if self.player.weapon_type != "melee":  # 非近战武器时停止射击
                        self.player.shooting = False
                elif event.button == 3:  # 右键释放
                    if self.player.weapon_type != "melee":  # 非近战武器时停止瞄准
                        self.player.is_aiming = False
    
    def update(self, dt):
        # 检查网络连接状态
        if not self.network_manager.connected:
            if self.network_manager.connection_error:
                self.error_message = self.network_manager.connection_error
            else:
                self.error_message = "网络连接丢失"
            self.state = "ERROR"
            return
        
        current_time = time.time()
        
        # 合并所有玩家（本地+网络）
        all_players = {self.player.id: self.player}
        all_players.update(self.other_players)
        
        # 更新本地玩家
        self.player.update(dt, self.game_map, self.bullets, self.network_manager, all_players)
        
        # 控制网络同步频率
        if current_time - self.last_sync_time > self.sync_interval:
            self.last_sync_time = current_time
            
            # 同步网络玩家数据并清理断线玩家
            with self.network_manager.lock:
                # 获取当前网络中的玩家ID
                network_player_ids = set(self.network_manager.players.keys())
                # 获取当前本地其他玩家ID
                local_other_player_ids = set(self.other_players.keys())
                
                # 移除已断线的玩家
                disconnected_players = local_other_player_ids - network_player_ids
                for pid in disconnected_players:
                    if pid != self.player.id:  # 不要删除本地玩家
                        print(f"[客户端] 移除断线玩家{pid}")
                        del self.other_players[pid]
                
                # 更新或添加在线玩家
                for pid, pdata in self.network_manager.players.items():
                    # 跳过本地玩家
                    if pid == self.player.id:
                        continue
                        
                    # 创建或更新其他玩家
                    if pid not in self.other_players:
                        self.other_players[pid] = Player(pid, pdata['pos'][0], pdata['pos'][1], name=pdata.get('name', f'玩家{pid}'))
                        print(f"[客户端] 添加新玩家{pid}")
                    
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
                    other_player.death_time = pdata.get('death_time', 0)
                    other_player.respawn_time = pdata.get('respawn_time', 0)
                    other_player.is_respawning = pdata.get('is_respawning', False)
                    other_player.name = pdata.get('name', f'玩家{pid}')
                    
                    # 同步状态（包括武器类型和瞄准状态）
                    other_player.sync_from_network(pdata)
            
            # 服务端定期广播
            self.network_manager.update_and_broadcast()
            
            # 同步子弹
            self.sync_bullets()
        
        # 更新子弹
        for bullet in list(self.bullets):
            if bullet.update(dt, self.game_map, all_players, self.network_manager):
                self.bullets.remove(bullet)
                # 通知服务器移除子弹
                if self.network_manager.is_server:
                    self.network_manager.remove_bullet(bullet.id)
        
        # 更新门
        self.game_map.update_doors(dt, self.network_manager)
        
        # 更新相机（考虑瞄准偏移）
        if not self.player.is_dead and not self.player.is_respawning:
            target_offset = pygame.Vector2(
                self.player.pos.x - SCREEN_WIDTH / 2,
                self.player.pos.y - SCREEN_HEIGHT / 2
            )
            
            # 添加瞄准偏移
            target_offset += self.player.aim_offset
            
            self.camera_offset += (target_offset - self.camera_offset) * 0.1
        
        # 检测附近的脚步声
        self.detect_nearby_footsteps()
        
        # 更新聊天光标闪烁
        if self.chat_active:
            current_time = pygame.time.get_ticks()
            if current_time - self.last_chat_cursor_blink > 500:
                self.chat_cursor_blink = not self.chat_cursor_blink
                self.last_chat_cursor_blink = current_time
        
        # 更新红色滤镜效果
        if self.hit_effect_time > 0:
            self.hit_effect_time -= dt
            if self.hit_effect_time < 0:
                self.hit_effect_time = 0

    def sync_bullets(self):
        """同步子弹 - 完全基于服务器数据"""
        network_bullets = self.network_manager.get_bullets()
        
        # 获取当前子弹ID集合
        current_bullet_ids = {b.id for b in self.bullets}
        network_bullet_ids = {b['id'] for b in network_bullets}
        
        # 移除不在网络列表中的子弹
        self.bullets = [b for b in self.bullets if b.id in network_bullet_ids]
        
        # 添加新子弹
        for bullet_data in network_bullets:
            if bullet_data['id'] not in current_bullet_ids:
                # 使用游戏规则中的子弹速度
                bullet_speed = BULLET_SPEED
                if hasattr(self, 'game_rules'):
                    bullet_speed = self.game_rules['bullet_speed']
                
                new_bullet = Bullet(bullet_data, bullet_speed)
                self.bullets.append(new_bullet)
    
    def render(self):
        # 清空屏幕为黑色（默认背景）
        self.screen.fill(BLACK)
        
        # 如果启用视角系统且玩家未死亡，绘制可见的扇形区域
        if self.show_vision and not self.player.is_dead:
            self.render_vision_fan()
        else:
            # 不使用视角系统时，绘制灰色地面
            self.render_full_ground()
        
        # 绘制墙壁和门（始终显示）
        self.render_walls_and_doors()
        
        # 绘制游戏对象
        for bullet in self.bullets:
            if self.show_vision and not self.player.is_dead:
                bullet.draw(self.screen, self.camera_offset, 
                          self.player.pos, self.player.angle, 
                          self.game_map.walls, self.game_map.doors, 
                          self.player.is_aiming)
            else:
                bullet.draw(self.screen, self.camera_offset)

        for player in self.other_players.values():
            if self.show_vision and not self.player.is_dead:
                player.draw(self.screen, self.camera_offset, 
                         self.player.pos, self.player.angle, 
                         self.game_map.walls, self.game_map.doors, 
                         is_local_player=False, is_aiming=self.player.is_aiming)
            else:
                player.draw(self.screen, self.camera_offset, None, None, None, None, is_local_player=False)
        
        # 本地玩家总是绘制
        self.player.draw(self.screen, self.camera_offset, None, None, None, None, is_local_player=True)
        
        # 绘制视角指示（可选）
        if self.show_vision and not self.player.is_dead:
            self.draw_fov_indicator()
        
        # 绘制UI（总是在最上层）
        self.render_ui()
        
        # 小地图
        self.render_minimap()
        
        # 聊天系统
        self.render_chat()
        
        # 绘制脚步声指示器
        self.render_footstep_indicators()
        
        # 绘制红色滤镜效果
        if self.hit_effect_time > 0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            alpha = min(100, int((self.hit_effect_time / self.hit_effect_duration) * 100))
            overlay.fill((255, 0, 0, alpha))
            self.screen.blit(overlay, (0, 0))
        
        pygame.display.flip()
    
    def render_vision_fan(self):
        """绘制视野扇形 - 高效率版本，考虑墙壁和门的遮挡"""
        # 根据瞄准状态选择视野角度
        current_fov = 30 if self.player.is_aiming else 120
        
        # 创建一个透明表面用于绘制视野
        vision_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        
        # 玩家屏幕位置
        player_screen_pos = (
            self.player.pos.x - self.camera_offset.x,
            self.player.pos.y - self.camera_offset.y
        )
        
        # 使用光线投射算法计算可见区域
        half_fov = current_fov / 2
        
        # 优化：根据屏幕分辨率和视野角度动态调整光线数量
        # 瞄准时使用更多光线以获得更精确的边缘
        ray_count = 40 if current_fov > 60 else 20
        angle_step = current_fov / ray_count
        
        # 收集所有可见点，用于构建可见多边形
        visible_points = [player_screen_pos]  # 起始点是玩家位置
        
        # 预先筛选可能与视野相交的墙壁和门，减少循环中的检查次数
        potential_walls = []
        for wall in self.game_map.walls:
            # 简单检查：如果墙壁在玩家视野范围内，则添加到潜在列表
            wall_center_x = wall.x + wall.width / 2
            wall_center_y = wall.y + wall.height / 2
            distance = math.sqrt((self.player.pos.x - wall_center_x)**2 + (self.player.pos.y - wall_center_y)**2)
            if distance <= VISION_RANGE * 1.5:  # 稍微扩大检查范围
                potential_walls.append(wall)
        
        potential_doors = []
        for door in self.game_map.doors:
            if not door.is_open:
                door_center_x = door.rect.x + door.rect.width / 2
                door_center_y = door.rect.y + door.rect.height / 2
                distance = math.sqrt((self.player.pos.x - door_center_x)**2 + (self.player.pos.y - door_center_y)**2)
                if distance <= VISION_RANGE * 1.5:
                    potential_doors.append(door)
        
        # 使用批处理方式处理光线
        batch_size = 5  # 每批处理的光线数量
        for batch_start in range(0, ray_count + 1, batch_size):
            batch_rays = []
            batch_angles = []
            
            # 为这一批次准备光线数据
            for i in range(batch_start, min(batch_start + batch_size, ray_count + 1)):
                angle = self.player.angle - half_fov + (angle_step * i)
                angle_rad = math.radians(angle)
                ray_end_x = self.player.pos.x + math.cos(angle_rad) * VISION_RANGE
                ray_end_y = self.player.pos.y - math.sin(angle_rad) * VISION_RANGE
                ray_end = pygame.Vector2(ray_end_x, ray_end_y)
                batch_rays.append(ray_end)
                batch_angles.append(angle)
            
            # 处理这一批次的所有光线
            for j, ray_end in enumerate(batch_rays):
                closest_hit = None
                closest_distance = float('inf')
                
                # 检查墙壁碰撞
                for wall in potential_walls:
                    intersection = self.get_line_rect_intersection(self.player.pos, ray_end, wall)
                    if intersection:
                        distance = self.player.pos.distance_to(intersection)
                        if distance < closest_distance:
                            closest_distance = distance
                            closest_hit = intersection
                
                # 检查门碰撞
                for door in potential_doors:
                    intersection = self.get_line_rect_intersection(self.player.pos, ray_end, door.rect)
                    if intersection:
                        distance = self.player.pos.distance_to(intersection)
                        if distance < closest_distance:
                            closest_distance = distance
                            closest_hit = intersection
                
                # 确定最终点位置（射线终点或碰撞点）
                if closest_hit:
                    final_point = closest_hit
                else:
                    final_point = ray_end
                
                # 转换为屏幕坐标并添加到可见点列表
                screen_x = final_point.x - self.camera_offset.x
                screen_y = final_point.y - self.camera_offset.y
                visible_points.append((screen_x, screen_y))
        
        # 绘制可见区域多边形
        if len(visible_points) >= 3:
            try:
                # 使用抗锯齿绘制，提高视觉质量
                pygame.draw.polygon(vision_surface, (*VISION_GROUND, 120), visible_points)
                self.screen.blit(vision_surface, (0, 0))
            except Exception as e:
                # 如果绘制失败，降级到简单的圆形
                if 0 <= player_screen_pos[0] <= SCREEN_WIDTH and 0 <= player_screen_pos[1] <= SCREEN_HEIGHT:
                    pygame.draw.circle(self.screen, VISION_GROUND, 
                                     (int(player_screen_pos[0]), int(player_screen_pos[1])), 
                                     min(VISION_RANGE, 200), 0)
    
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
            intersection = self.get_line_line_intersection(start, end, pygame.Vector2(edge[0]), pygame.Vector2(edge[1]))
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
    
    def render_full_ground(self):
        """绘制完整的灰色地面（不使用视角系统时）"""
        # 绘制一个大的灰色矩形作为地面
        ground_rect = pygame.Rect(
            -self.camera_offset.x,
            -self.camera_offset.y,
            ROOM_SIZE * 3,
            ROOM_SIZE * 3
        )
        pygame.draw.rect(self.screen, LIGHT_GRAY, ground_rect)
    
    def render_walls_and_doors(self):
        """绘制所有墙壁和门（始终显示）"""
        # 绘制所有墙壁
        for wall in self.game_map.walls:
            wall_rect = pygame.Rect(
                wall.x - self.camera_offset.x,
                wall.y - self.camera_offset.y,
                wall.width,
                wall.height
            )
            pygame.draw.rect(self.screen, GRAY, wall_rect)
        
        # 绘制所有门
        for door in self.game_map.doors:
            if door.animation_progress < 1.0:  # 只绘制未完全打开的门
                door_rect = pygame.Rect(
                    door.rect.x - self.camera_offset.x,
                    door.rect.y - self.camera_offset.y,
                    door.rect.width,
                    door.rect.height
                )
                pygame.draw.rect(self.screen, door.get_color(False), door_rect)

    def draw_fov_indicator(self):
        """绘制视角指示线"""
        # 移除了视角边缘线和中心线的绘制
    
    def render_ui(self):
        """绘制UI元素"""
        health_text = f"生命: {self.player.health}/{self.player.max_health}"
        weapon_text = f"武器: {'近战' if self.player.weapon_type == 'melee' else '枪械'}"
        self.screen.blit(font.render(health_text, True, WHITE), (20, 20))
        self.screen.blit(font.render(weapon_text, True, YELLOW if self.player.weapon_type == 'melee' else GREEN), (20, 50))
        
        # 根据武器类型显示不同信息
        if self.player.weapon_type == "gun":
            ammo_text = f"弹药: {self.player.ammo}/{MAGAZINE_SIZE}"
            self.screen.blit(font.render(ammo_text, True, WHITE), (20, 80))
            
            if self.player.is_reloading:
                reload_time = max(0, RELOAD_TIME - (time.time() - self.player.reload_start))
                reload_text = f"换弹中: {reload_time:.1f}s"
                self.screen.blit(font.render(reload_text, True, YELLOW), (20, 110))
        else:
            # 近战武器状态
            if self.player.melee_weapon.can_attack():
                melee_text = "近战武器: 就绪"
                melee_color = GREEN
            else:
                remaining_cooldown = MELEE_COOLDOWN - (time.time() - self.player.melee_weapon.last_attack_time)
                melee_text = f"近战武器: {remaining_cooldown:.1f}s"
                melee_color = RED
            
            self.screen.blit(font.render(melee_text, True, melee_color), (20, 80))
        
        # 瞄准状态
        if self.player.is_aiming:
            aim_text = "瞄准中"
            self.screen.blit(font.render(aim_text, True, AIM_COLOR), (20, 110))
        
        if self.player.is_dead:
            # 显示死亡状态
            current_time = time.time()
            remaining_time = max(0, self.player.respawn_time - current_time)
            death_text = f"已死亡 - 复活倒计时: {remaining_time:.1f}s"
            death_surface = font.render(death_text, True, RED)
            self.screen.blit(death_surface, (SCREEN_WIDTH//2 - death_surface.get_width()//2, SCREEN_HEIGHT//2))
        
        player_count = len(self.other_players) + 1
        count_text = f"玩家数: {player_count}"
        self.screen.blit(font.render(count_text, True, WHITE), (SCREEN_WIDTH - 150, 20))
        
        # 显示玩家ID和回收池信息（调试模式）
        if self.debug_mode and self.network_manager.is_server:
            recycled_text = f"回收池: {sorted(self.network_manager.recycled_ids) if self.network_manager.recycled_ids else '空'}"
            self.screen.blit(font.render(recycled_text, True, YELLOW), (SCREEN_WIDTH - 250, 50))
        
        if not self.player.is_dead and not self.player.is_respawning:
            interact_text = "按E键开/关门"
            self.screen.blit(font.render(interact_text, True, WHITE),
                             (SCREEN_WIDTH - 150, SCREEN_HEIGHT - 120))
            
            # 武器控制提示
            if self.player.weapon_type == "gun":
                weapon_text = "左键射击 右键瞄准"
            else:
                weapon_text = "左键近战攻击"
            self.screen.blit(font.render(weapon_text, True, WHITE),
                             (SCREEN_WIDTH - 200, SCREEN_HEIGHT - 90))
            
            # 切换武器提示
            switch_text = "按3切换武器"
            self.screen.blit(font.render(switch_text, True, WHITE),
                             (SCREEN_WIDTH - 150, SCREEN_HEIGHT - 60))
        
        # 聊天提示
        chat_hint = "按Y键聊天"
        self.screen.blit(font.render(chat_hint, True, WHITE),
                         (SCREEN_WIDTH - 150, SCREEN_HEIGHT - 30))
        
        # 显示伤害信息
        damage_text = f"射击伤害: {BULLET_DAMAGE} 近战伤害: {MELEE_DAMAGE}"
        self.screen.blit(font.render(damage_text, True, WHITE), (20, 140))
        
        # 视角相关信息
        current_fov = 30 if self.player.is_aiming else 120
        vision_text = f"视角: {current_fov}° {'(瞄准)' if self.player.is_aiming else '(正常)'})"
        self.screen.blit(font.render(vision_text, True, YELLOW), (20, 170))
        
        # 脚步声提示
        if self.nearby_sound_players:
            footstep_text = f"附近脚步声: {len(self.nearby_sound_players)}个玩家"
            self.screen.blit(font.render(footstep_text, True, RED), (20, 200))
        
        # 调试信息
        if self.debug_mode:
            debug_y = 200
            self.screen.blit(font.render(f"玩家ID: {self.player.id}", True, YELLOW), (20, debug_y))
            debug_y += 25
            self.screen.blit(font.render(f"服务器: {'是' if self.network_manager.is_server else '否'}", True, YELLOW), (20, debug_y))
            debug_y += 25
            self.screen.blit(font.render(f"武器类型: {self.player.weapon_type}", True, YELLOW), (20, debug_y))
            debug_y += 25
            self.screen.blit(font.render(f"瞄准状态: {'是' if self.player.is_aiming else '否'}", True, YELLOW), (20, debug_y))
            debug_y += 25
            self.screen.blit(font.render(f"瞄准偏移: ({self.player.aim_offset.x:.1f}, {self.player.aim_offset.y:.1f})", True, YELLOW), (20, debug_y))
            debug_y += 25
            self.screen.blit(font.render(f"门状态: {len(self.network_manager.doors)}个已同步", True, YELLOW), (20, debug_y))
            debug_y += 25
            self.screen.blit(font.render(f"子弹数: {len(self.bullets)} 网络: {len(self.network_manager.get_bullets())}", True, YELLOW), (20, debug_y))
            debug_y += 25
            self.screen.blit(font.render(f"按F3切换调试模式 F4切换视角显示", True, YELLOW), (20, debug_y))
            debug_y += 25
            self.screen.blit(font.render(f"视角系统: {'开' if self.show_vision else '关'}", True, YELLOW), (20, debug_y))
            debug_y += 25
            self.screen.blit(font.render(f"脚步声: {len(self.nearby_sound_players)}个玩家", True, YELLOW), (20, debug_y))

    def render_chat(self):
        """绘制聊天系统"""
        # 聊天输入框
        if self.chat_active:
            chat_box_height = 35
            chat_box = pygame.Rect(10, SCREEN_HEIGHT - chat_box_height - 10, SCREEN_WIDTH - 20, chat_box_height)
            pygame.draw.rect(self.screen, BLACK, chat_box)
            pygame.draw.rect(self.screen, WHITE, chat_box, 2)
            
            # 聊天提示和输入文字
            chat_prompt = "聊天: "
            prompt_surface = font.render(chat_prompt, True, WHITE)
            self.screen.blit(prompt_surface, (chat_box.x + 5, chat_box.y + 5))
            
            # 输入文字
            input_surface = font.render(self.chat_input, True, WHITE)
            input_x = chat_box.x + 5 + prompt_surface.get_width()
            self.screen.blit(input_surface, (input_x, chat_box.y + 5))
            
            # 光标
            if self.chat_cursor_blink:
                cursor_x = input_x + input_surface.get_width()
                cursor_y = chat_box.y + 5
                pygame.draw.line(self.screen, WHITE, 
                               (cursor_x, cursor_y), 
                               (cursor_x, cursor_y + font.get_height()), 2)
        
        # 聊天消息历史
        recent_messages = self.network_manager.get_recent_chat_messages()
        if recent_messages:
            # 计算聊天框的位置
            chat_y_start = SCREEN_HEIGHT - 60 - (self.chat_active * 45)  # 如果输入框激活，留出更多空间
            
            # 显示最近的消息（从下往上）
            for i, msg in enumerate(reversed(recent_messages[-5:])):  # 最多显示5条消息
                message_y = chat_y_start - i * 25
                if message_y < 250:  # 不要覆盖UI元素
                    break
                
                # 创建消息文本
                message_text = f"{msg.player_name}: {msg.message}"
                message_surface = small_font.render(message_text, True, msg.color)
                
                # 半透明背景
                bg_rect = pygame.Rect(10, message_y - 2, message_surface.get_width() + 10, message_surface.get_height() + 4)
                bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
                bg_surface.fill((0, 0, 0, 128))
                self.screen.blit(bg_surface, bg_rect)
                
                # 消息文本
                self.screen.blit(message_surface, (15, message_y))

    def render_minimap(self):
        """绘制小地图（不显示其他玩家）"""
        minimap_width, minimap_height = 200, 150
        minimap_surface = pygame.Surface((minimap_width, minimap_height))
        minimap_surface.fill(BLACK)
        
        # 设置小地图的缩放比例
        minimap_scale = 0.08
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
                    pygame.draw.rect(minimap_surface, door.get_color(False), (rel_x, rel_y, rel_width, rel_height))
        
        # 绘制本地玩家 - 始终在小地图中心
        player_color = DEAD_COLOR if self.player.is_dead else self.player.color
        if self.player.weapon_type == "melee":
            player_color = MELEE_COLOR
        pygame.draw.circle(minimap_surface, player_color, (int(minimap_center_x), int(minimap_center_y)), 4)

        # 在小地图上显示大概方位（不显示精确位置）
        for sound_info in self.nearby_sound_players:
            direction = sound_info['direction']
            is_shooting = sound_info['is_shooting']
            sound_intensity = sound_info['sound_intensity']
            
            # 根据声音类型选择颜色
            base_color = (255, 50, 50) if is_shooting else (50, 255, 50)  # 红色表示开枪，绿色表示移动
            
            # 根据声音强度调整颜色透明度和指示器大小
            alpha = int(min(255, max(50, 255 * sound_intensity)))  # 最小透明度为50，最大为255
            color = (base_color[0], base_color[1], base_color[2], alpha)
            
            # 计算大概方位（在小地图边缘显示方向指示）
            edge_distance = min(minimap_width, minimap_height) * (0.2 + 0.2 * sound_intensity)  # 距离中心根据声音强度变化
            dir_x = direction.x * edge_distance
            dir_y = direction.y * edge_distance
            
            # 确保指示器在小地图范围内
            indicator_x = int(minimap_center_x + dir_x)
            indicator_y = int(minimap_center_y + dir_y)
            
            # 绘制方向箭头（简化版）
            arrow_size = 3
            pygame.draw.circle(minimap_surface, color, (indicator_x, indicator_y), arrow_size)
            
            # 绘制指向中心的连线表示方向
            pygame.draw.line(minimap_surface, color, 
                           (indicator_x, indicator_y), 
                           (int(minimap_center_x), int(minimap_center_y)), 1)

        # 移除了小地图上的视角方向线绘制

        # 绘制瞄准指示
        if not self.player.is_dead and self.player.is_aiming:
            # 绘制瞄准圈
            pygame.draw.circle(minimap_surface, AIM_COLOR, 
                             (int(minimap_center_x), int(minimap_center_y)), 
                             8, 1)

        # 绘制近战攻击范围指示
        if not self.player.is_dead and self.player.weapon_type == "melee" and self.player.melee_weapon.can_attack():
            # 绘制近战攻击范围
            pygame.draw.circle(minimap_surface, MELEE_COLOR, 
                             (int(minimap_center_x), int(minimap_center_y)), 
                             int(MELEE_RANGE * minimap_scale), 1)

        # 绘制小地图边框
        pygame.draw.rect(minimap_surface, WHITE, (0, 0, minimap_width, minimap_height), 2)
        
        # 将小地图绘制到屏幕上
        self.screen.blit(minimap_surface, (SCREEN_WIDTH - minimap_width - 10, SCREEN_HEIGHT - minimap_height - 10))
    
    def detect_nearby_footsteps(self):
        """检测发出声音的玩家（静步0范围，正常移动根据速度调整范围0-400，开枪600范围）"""
        if self.player.is_dead:
            self.nearby_sound_players = []
            return
            
        nearby_players = []
        
        # 检查所有玩家（包括静步的）
        for player_id, player in self.other_players.items():
            if player.is_dead:
                continue
                
            distance = self.player.pos.distance_to(player.pos)
            
            # 根据玩家状态设置不同检测范围
            if player.shooting:
                detection_range = 600  # 开枪声音范围
            elif player.is_walking:
                detection_range = 0  # 静步时完全无法被探测
            elif player.is_making_sound:
                # 根据声音音量调整检测范围 (0.0-1.0 对应 0-400范围)
                max_range = 400  # 最大检测范围
                detection_range = max_range * player.sound_volume
            else:
                continue  # 没有声音就不检测
                
            if distance <= detection_range:
                # 计算方向向量
                direction = player.pos - self.player.pos
                if direction.length() > 0:
                    direction = direction.normalize()
                
                # 计算声音强度 (距离越近越强)
                sound_intensity = 1.0 - (distance / detection_range) if detection_range > 0 else 0
                # 将声音强度与音量相乘
                if not player.shooting:  # 射击声音不受音量影响
                    sound_intensity *= player.sound_volume
                
                nearby_players.append({
                    'player': player,
                    'distance': distance,
                    'direction': direction,
                    'is_shooting': player.shooting,  # 标记是否为开枪声音
                    'sound_intensity': sound_intensity,  # 声音强度
                    'screen_pos': pygame.Vector2(
                        player.pos.x - self.camera_offset.x,
                        player.pos.y - self.camera_offset.y
                    )
                })
        
        self.nearby_sound_players = nearby_players
    
    def render_footstep_indicators(self):
        """渲染方向指示器（箭头指向声音来源，根据声音强度调整透明度）"""
        if self.player.is_dead or not self.nearby_sound_players:
            return
            
        # 获取屏幕中心位置
        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2
        
        for sound_info in self.nearby_sound_players:
            player = sound_info['player']
            direction = sound_info['direction']
            is_shooting = sound_info['is_shooting']
            sound_intensity = sound_info['sound_intensity']
            
            # 根据声音类型选择颜色
            base_color = (255, 100, 100) if is_shooting else (100, 255, 100)  # 红色表示开枪，绿色表示移动
            
            # 根据声音强度调整颜色透明度
            alpha = int(min(255, max(50, 255 * sound_intensity)))  # 最小透明度为50，最大为255
            color = (base_color[0], base_color[1], base_color[2], alpha)
            
            # 计算箭头位置（屏幕边缘）
            arrow_distance = 80
            arrow_x = center_x + direction.x * arrow_distance
            arrow_y = center_y + direction.y * arrow_distance
            
            # 创建指示器表面
            indicator_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            
            # 根据声音强度调整箭头大小
            arrow_size = 10 + int(5 * sound_intensity)  # 10-15之间变化
            angle = math.atan2(direction.y, direction.x)
            
            # 箭头顶点
            end_x = arrow_x + math.cos(angle) * arrow_size
            end_y = arrow_y + math.sin(angle) * arrow_size
            
            # 箭头两侧
            left_x = arrow_x + math.cos(angle + 2.5) * (arrow_size * 0.7)
            left_y = arrow_y + math.sin(angle + 2.5) * (arrow_size * 0.7)
            right_x = arrow_x + math.cos(angle - 2.5) * (arrow_size * 0.7)
            right_y = arrow_y + math.sin(angle - 2.5) * (arrow_size * 0.7)
            
            # 绘制箭头线条
            pygame.draw.line(indicator_surface, color, 
                           (center_x, center_y), (end_x, end_y), 2 + int(sound_intensity * 2))  # 线宽根据强度变化
            pygame.draw.line(indicator_surface, color, 
                           (end_x, end_y), (left_x, left_y), 2 + int(sound_intensity * 2))
            pygame.draw.line(indicator_surface, color, 
                           (end_x, end_y), (right_x, right_y), 2 + int(sound_intensity * 2))
            
            # 绘制距离圈，大小根据声音强度变化
            circle_radius = int(30 + 20 * sound_intensity)  # 30-50之间变化
            pygame.draw.circle(indicator_surface, color, (center_x, center_y), circle_radius, 1)
            
            # 添加声音类型标签
            label = "开枪" if is_shooting else "移动"
            # 根据声音强度调整标签大小
            label_font = small_font if sound_intensity < 0.7 else font
            label_surface = label_font.render(label, True, color)
            label_x = arrow_x - label_surface.get_width() // 2
            label_y = arrow_y + 20
            
            # 确保标签在屏幕内
            label_x = max(10, min(SCREEN_WIDTH - label_surface.get_width() - 10, label_x))
            label_y = max(10, min(SCREEN_HEIGHT - label_surface.get_height() - 10, label_y))
            
            indicator_surface.blit(label_surface, (label_x, label_y))
            
            self.screen.blit(indicator_surface, (0, 0))
    
    def run(self):
        while self.running:
            if self.state == "MENU":
                self.show_menu()
            elif self.state == "CONNECTING":
                self.show_connecting_screen()
            elif self.state == "ERROR":
                self.show_error_screen()
            elif self.state == "PLAYING":
                dt = self.clock.tick(FPS) / 1000.0
                self.handle_events()
                self.update(dt)
                
                # 检查是否需要切换到错误状态
                if self.state == "ERROR":
                    continue
                    
                self.render()
        
        if self.network_manager:
            self.network_manager.stop()
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()