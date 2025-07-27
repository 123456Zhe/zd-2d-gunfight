import pygame
import math
import random
import socket
import threading
import json
import time
import subprocess
import ipaddress
from pygame.locals import *
from constants import *

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
        colors = [RED, BLUE, GREEN, YELLOW, ORANGE, PURPLE, (0, 255, 255)]
        return colors[player_id % len(colors)]
    
    def is_expired(self, current_time):
        """检查消息是否过期"""
        return current_time - self.timestamp > CHAT_DISPLAY_TIME