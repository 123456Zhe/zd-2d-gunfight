import socket
import threading
import json
import time
import random
from pygame.locals import *
from constants import (
    SERVER_PORT, BUFFER_SIZE, HEARTBEAT_INTERVAL, CLIENT_TIMEOUT,
    CHAT_DISPLAY_TIME, MAX_CHAT_LENGTH, MAX_CHAT_MESSAGES,
    WHITE, RED, BLUE, GREEN, YELLOW, ORANGE, PURPLE,
    ROOM_SIZE, MAGAZINE_SIZE, CONNECTION_TIMEOUT, RESPAWN_TIME,
    MELEE_DAMAGE, HEAVY_MELEE_DAMAGE, PLAYER_RADIUS
)

# 延迟导入以避免循环依赖
# AIPlayer 会在需要时导入

def generate_default_player_name():
    """生成默认玩家名：玩家+3位随机数字"""
    return f"玩家{random.randint(100, 999)}"

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
        
        # 如果player_id是字符串，使用hash来获取颜色索引
        if isinstance(player_id, str):
            color_index = hash(player_id) % 7
        else:
            color_index = player_id % 7
            
        colors = [RED, BLUE, GREEN, YELLOW, ORANGE, PURPLE, (0, 255, 255)]
        return colors[color_index]
    
    def is_expired(self, current_time):
        """检查消息是否过期"""
        return current_time - self.timestamp > CHAT_DISPLAY_TIME

class NetworkManager:
    def __init__(self, is_server=False, server_address=None, game_instance=None, server_name=None, player_name=None):
        self.is_server = is_server
        self.player_id = None  # 将在连接时分配
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
        self.server_name = server_name or '默认服务器'
        self.player_name = player_name or generate_default_player_name()
        
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
                    'melee_attacking': False,
                    'melee_direction': 0,
                    'weapon_type': 'gun',  # 新增：武器类型
                    'is_aiming': False,  # 新增：瞄准状态
                    'name': self.player_name,  # 修复：使用玩家名称而不是服务器名称
                    'team_id': None  # 新增：团队ID
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
                self.connected = False
                self.connection_error = "无法连接到服务器"
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
        # 使用网络管理器中的服务器名称
        server_name = self.server_name
        print(f"[调试] 获取服务器信息，服务器名称: {server_name}")
        
        return {
            'name': server_name,
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
                'player_name': self.player_name
            }
            self.socket.sendto(json.dumps(connect_msg).encode(), (self.server_address, SERVER_PORT))
            
            # 等待服务器响应
            start_time = time.time()
            while time.time() - start_time < CONNECTION_TIMEOUT:
                try:
                    data, addr = self.socket.recvfrom(BUFFER_SIZE)
                    response = json.loads(data.decode())
                    
                    if response.get('type') == 'connect_response':
                        self.player_id = response.get('client_id', -1)
                        self.server_name = response.get('server_name', '默认服务器')
                        self.connected = True
                        self.last_server_response = time.time()
                        print(f"连接成功！分配到玩家ID: {self.player_id}, 服务器名称: {self.server_name}")
                        
                        # 通知游戏实例服务器名称已更新
                        if self.game_instance:
                            self.game_instance.on_server_name_received(self.server_name)
                        return True
                        
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
                        print(f"[服务端] 玩家{player_id}连接超时，已踢出")
                        
                        # 广播玩家离开消息
                        player_name = self.players.get(player_id, {}).get('name', f'玩家{player_id}')
                        leave_msg = ChatMessage(
                            0, 
                            "[系统]",
                            f"{player_name} 离开了游戏", 
                            time.time()
                        )
                        self.chat_messages.append(leave_msg)
                        self.broadcast_chat_message(leave_msg)
                        
                        # 清理团队信息
                        game_instance = getattr(self, 'game_instance', None)
                        if game_instance and hasattr(game_instance, 'team_manager'):
                            game_instance.team_manager.remove_player(player_id)
                        
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
                        self._handle_connection_request(addr, message)
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
                        # 服务端和客户端都使用_handle_chat_message
                        # 服务端会处理队内聊天并转发，客户端直接接收
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
            
            # 记录客户端
            self.clients[addr] = new_player_id
            self.client_last_seen[addr] = time.time()
            
            # 获取玩家名称
            player_name = generate_default_player_name()
            if data and isinstance(data, dict):
                if 'player_name' in data:
                    player_name = data['player_name']
                elif 'data' in data and isinstance(data['data'], dict) and 'player_name' in data['data']:
                    player_name = data['data']['player_name']
            elif data and isinstance(data, str):
                player_name = data
            
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
                'melee_attacking': False,
                'melee_direction': 0,
                'weapon_type': 'gun',  # 新增：武器类型
                'is_aiming': False,  # 新增：瞄准状态
                'name': player_name,  # 新增：玩家名称
                'team_id': None  # 新增：团队ID
            }
            
            print(f"[服务端] 玩家{new_player_id}已连接，地址：{addr}，玩家名: {player_name}，当前玩家数: {len(self.players)}")
            
            # 发送连接响应（包含服务器名称）
            response = {
                'type': 'connect_response',
                'client_id': new_player_id,
                'server_name': self.server_name,
                'server_time': time.time()
            }
            self.socket.sendto(json.dumps(response).encode(), addr)
            
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
            
            # 广播新玩家加入消息（使用已经获取的玩家名称）
            join_msg = ChatMessage(
                0, 
                "[系统]",
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
                        
                        # 更新客户端发来的数据
                        self.players[pid].update(pdata)
                        
                        # 恢复服务端权威数据（但允许名称更新）
                        self.players[pid]['health'] = current_health
                        self.players[pid]['is_dead'] = current_is_dead
                        self.players[pid]['death_time'] = current_death_time
                        self.players[pid]['respawn_time'] = current_respawn_time
                        self.players[pid]['is_respawning'] = current_is_respawning
                        # 名称允许客户端更新，不恢复旧值
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
                        
                        # 检查是否是队友（团队系统）
                        if game_instance and hasattr(game_instance, 'team_manager'):
                            if game_instance.team_manager.are_teammates(attacker_id, target_id):
                                # 队友不受伤害
                                print(f"[团队] 玩家{attacker_id}尝试攻击队友{target_id}，伤害被阻止")
                                return
                        # 回退：直接比较网络玩家数据的team_id或对象的team_id
                        try:
                            attacker_team_id = self.players.get(attacker_id, {}).get('team_id', None)
                            target_team_id = self.players.get(target_id, {}).get('team_id', None)
                            if attacker_team_id is None or target_team_id is None:
                                # 从游戏实例对象补全
                                if hasattr(game_instance, 'players') and attacker_id in getattr(game_instance, 'players', {}):
                                    attacker_team_id = attacker_team_id or getattr(game_instance.players[attacker_id], 'team_id', None)
                                if hasattr(game_instance, 'ai_players') and attacker_id in getattr(game_instance, 'ai_players', {}):
                                    attacker_team_id = attacker_team_id or getattr(game_instance.ai_players[attacker_id], 'team_id', None)
                                if hasattr(game_instance, 'players') and target_id in getattr(game_instance, 'players', {}):
                                    target_team_id = target_team_id or getattr(game_instance.players[target_id], 'team_id', None)
                                if hasattr(game_instance, 'ai_players') and target_id in getattr(game_instance, 'ai_players', {}):
                                    target_team_id = target_team_id or getattr(game_instance.ai_players[target_id], 'team_id', None)
                            if attacker_team_id is not None and target_team_id is not None and attacker_team_id == target_team_id:
                                print(f"[团队] 玩家{attacker_id}尝试攻击同队目标{target_id}（基于team_id对比），伤害被阻止")
                                return
                        except Exception:
                            pass
                        
                        # 检查是否是AI玩家
                        if game_instance and hasattr(game_instance, 'ai_players') and target_id in game_instance.ai_players:
                            ai_player = game_instance.ai_players[target_id]
                            old_health = ai_player.health
                            is_dead = ai_player.take_damage(damage)
                            
                            # 同步AI玩家状态到网络
                            self.players[target_id]['health'] = ai_player.health
                            self.players[target_id]['is_dead'] = ai_player.is_dead
                            if is_dead:
                                self.players[target_id]['death_time'] = current_time
                                self.players[target_id]['respawn_time'] = ai_player.respawn_time
                            
                            print(f"[{damage_type}伤害] AI玩家{target_id}被玩家{attacker_id}击中，{old_health}->{ai_player.health}")
                            
                            if is_dead:
                                print(f"[死亡] AI玩家{target_id}死亡，将在3秒后复活")
                                
                                # 发送死亡信息到聊天框
                                attacker_name = self.players.get(attacker_id, {}).get('name', f"玩家{attacker_id}")
                                target_name = self.players.get(target_id, {}).get('name', f"AI_{target_id}")
                                death_message = f"{attacker_name} 击杀了 {target_name}！"
                                death_chat = ChatMessage(0, "[系统]", death_message, current_time)
                                self.chat_messages.append(death_chat)
                                if self.is_server:
                                    self.broadcast_chat_message(death_chat)
                        
                        elif game_instance and hasattr(game_instance, 'players') and target_id in game_instance.players:
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
                
                # 如果是本地玩家，还需要更新游戏实例中的玩家对象
                game_instance = getattr(self, 'game_instance', None)
                if (game_instance and hasattr(game_instance, 'player') and 
                    game_instance.player and game_instance.player.id == player_id):
                    
                    # 更新本地玩家对象
                    game_instance.player.pos.x = respawn_data['pos'][0]
                    game_instance.player.pos.y = respawn_data['pos'][1]
                    game_instance.player.health = 100
                    game_instance.player.is_dead = False
                    game_instance.player.is_respawning = False
                    game_instance.player.death_time = 0
                    game_instance.player.respawn_time = 0
                    game_instance.player.ammo = MAGAZINE_SIZE
                    game_instance.player.is_reloading = False
                    
                    print(f"[复活] 本地玩家{player_id}已复活，位置更新为{respawn_data['pos']}")
    
    def _handle_chat_message(self, chat_data):
        """处理聊天消息"""
        if isinstance(chat_data, dict) and all(key in chat_data for key in ['player_id', 'message']):
            message = chat_data['message']
            player_id = chat_data['player_id']
            timestamp = chat_data.get('timestamp', time.time())
            is_team_chat = chat_data.get('is_team_chat', False)  # 是否是队内聊天
            
            # 检查是否是服务端命令
            if self.is_server and message.startswith('.') and player_id != 0:
                # 只有非系统消息的命令才需要处理
                self._handle_server_command(message, player_id)
                return
            
            # 获取玩家名称 - 优先使用消息中包含的名称
            player_name = chat_data.get('player_name', self.players.get(player_id, {}).get('name', f'玩家{player_id}'))
            
            # 处理队内聊天
            if is_team_chat and self.is_server:
                game_instance = getattr(self, 'game_instance', None)
                if game_instance and hasattr(game_instance, 'team_manager'):
                    team = game_instance.team_manager.get_player_team(player_id)
                    if team:
                        # 只发送给队友
                        player_name = f"[团队]{player_name}"
                        msg = ChatMessage(
                            player_id,
                            player_name,
                            message,
                            timestamp
                        )
                        
                        # 添加到聊天历史（只添加到队友的聊天历史）
                        self.chat_messages.append(msg)
                        
                        # 保持聊天历史不超过最大数量
                        if len(self.chat_messages) > MAX_CHAT_MESSAGES * 2:
                            self.chat_messages = self.chat_messages[-MAX_CHAT_MESSAGES:]
                        
                        # 只广播给队友（包括发送者自己，以便在服务端也能看到）
                        for teammate_id in team.members:
                            # 找到队友的地址并发送消息
                            if teammate_id == player_id:
                                # 服务端玩家发送的队内聊天，添加到自己的聊天历史
                                # 消息已经添加到chat_messages中了，这里只需要确保服务端玩家能看到
                                continue
                            else:
                                # 发送给其他队友
                                for addr, pid in self.clients.items():
                                    if pid == teammate_id:
                                        self.send_to_client({
                                            'type': 'chat_message',
                                            'data': {
                                                'player_id': player_id,
                                                'player_name': player_name,
                                                'message': message,
                                                'timestamp': timestamp,
                                                'is_team_chat': True
                                            }
                                        }, addr)
                                        break
                        return
                    else:
                        # 玩家不在团队中，发送系统消息
                        self._send_system_message("你不在任何团队中，无法使用队内聊天")
                        return
            
            # 全局聊天
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
            
            # 如果是服务端且不是系统消息，转发给所有客户端
            if self.is_server and player_id != 0:
                self.broadcast_chat_message(msg)
    
    def _get_safe_spawn_pos_for_ai(self, game_instance, max_attempts=50):
        """为AI玩家获取安全的生成位置（备用方法）"""
        if not game_instance or not hasattr(game_instance, 'game_map'):
            # 如果game_instance或game_map不存在，返回随机位置
            return random.randint(100, ROOM_SIZE * 3 - 100), random.randint(100, ROOM_SIZE * 3 - 100)
        
        game_map = game_instance.game_map
        
        # 尝试使用房间中心位置（更安全）
        for attempt in range(max_attempts):
            room_id = random.randint(0, 8)
            room_row = room_id // 3
            room_col = room_id % 3
            
            # 在房间中心附近随机位置
            spawn_x = room_col * ROOM_SIZE + ROOM_SIZE // 2 + random.randint(-100, 100)
            spawn_y = room_row * ROOM_SIZE + ROOM_SIZE // 2 + random.randint(-100, 100)
            
            # 确保在房间边界内
            spawn_x = max(room_col * ROOM_SIZE + 50, min(spawn_x, (room_col + 1) * ROOM_SIZE - 50))
            spawn_y = max(room_row * ROOM_SIZE + 50, min(spawn_y, (room_row + 1) * ROOM_SIZE - 50))
            
            # 检查位置是否安全
            if self._is_position_safe_for_ai(spawn_x, spawn_y, game_map):
                return spawn_x, spawn_y
        
        # 如果所有尝试都失败，使用更保守的方法：在整个地图范围内随机尝试
        for attempt in range(max_attempts):
            spawn_x = random.randint(100, ROOM_SIZE * 3 - 100)
            spawn_y = random.randint(100, ROOM_SIZE * 3 - 100)
            
            if self._is_position_safe_for_ai(spawn_x, spawn_y, game_map):
                return spawn_x, spawn_y
        
        # 如果还是找不到安全位置，返回地图中心（作为最后的备选）
        return ROOM_SIZE * 1.5, ROOM_SIZE * 1.5
    
    def _is_position_safe_for_ai(self, x, y, game_map):
        """检查位置是否安全（不与墙壁或门碰撞）"""
        try:
            import pygame
            player_rect = pygame.Rect(
                x - PLAYER_RADIUS,
                y - PLAYER_RADIUS,
                PLAYER_RADIUS * 2,
                PLAYER_RADIUS * 2
            )
            
            # 检查墙壁碰撞
            for wall in game_map.walls:
                if player_rect.colliderect(wall):
                    return False
            
            # 检查门碰撞
            for door in game_map.doors:
                if door.check_collision(player_rect):
                    return False
            
            return True
        except Exception:
            # 如果出现任何错误，返回False以触发重试
            return False
                
    def _handle_server_command(self, command, player_id):
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
                health = pdata.get('health', 0)
                is_dead = pdata.get('is_dead', False)
                status = "死亡" if is_dead else f"生命值:{health}"
                player_list.append(f"ID:{pid} - 玩家{pid} ({status})")
                
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
            
        elif cmd == '.addai' and is_admin:
            # 添加AI玩家
            # 支持命令格式: .addai [difficulty] [personality]
            # 例如: .addai normal aggressive
            difficulty = 'normal'
            personality = None
            
            if args:
                # 第一个参数是难度
                if args[0] in ['easy', 'normal', 'hard']:
                    difficulty = args[0]
                    # 第二个参数是性格（如果提供）
                    if len(args) > 1:
                        personality = args[1]
                else:
                    # 如果第一个参数不是难度，可能是性格
                    personality = args[0]
            
            # 生成AI玩家ID
            game_instance = getattr(self, 'game_instance', None)
            if not game_instance:
                self._send_system_message("无法添加AI玩家：游戏实例不存在")
                return
            
            ai_id = game_instance.next_ai_id
            game_instance.next_ai_id += 1
            
            # 使用安全位置生成出生点（避免卡在墙里）
            if hasattr(game_instance, 'get_safe_spawn_pos'):
                spawn_x, spawn_y = game_instance.get_safe_spawn_pos()
            else:
                # 如果没有get_safe_spawn_pos方法，使用带碰撞检测的随机位置
                spawn_x, spawn_y = self._get_safe_spawn_pos_for_ai(game_instance)
            
            # 创建AI玩家（延迟导入以避免循环依赖）
            # 检查是否使用增强版AI
            try:
                # 尝试导入增强版AI
                from ai_player_enhanced import EnhancedAIPlayer
                from ai_personality import AIPersonality, AIPersonalityTraits
                
                # 处理性格参数
                if personality:
                    # 尝试解析性格
                    personality_map = {
                        'aggressive': AIPersonality.AGGRESSIVE,
                        'defensive': AIPersonality.DEFENSIVE,
                        'tactical': AIPersonality.TACTICAL,
                        'stealthy': AIPersonality.STEALTHY,
                        'team': AIPersonality.TEAM_PLAYER,
                        'team_player': AIPersonality.TEAM_PLAYER,
                        'random': AIPersonality.RANDOM
                    }
                    
                    if personality.lower() in personality_map:
                        personality_traits = AIPersonalityTraits(personality_map[personality.lower()])
                    else:
                        # 无效的性格，使用随机
                        personality_traits = AIPersonalityTraits.random_personality()
                else:
                    # 没有指定性格，随机生成
                    personality_traits = AIPersonalityTraits.random_personality()
                
                # 创建增强版AI
                ai_player = EnhancedAIPlayer(ai_id, spawn_x, spawn_y, difficulty, personality_traits)
                ai_player_name = ai_player.name
                use_enhanced_ai = True
                
            except ImportError:
                # 如果增强版AI不可用，使用原版AI
                from ai_player import AIPlayer
                ai_player = AIPlayer(ai_id, spawn_x, spawn_y, difficulty)
                ai_player_name = f'AI_{difficulty}_{ai_id}'
                use_enhanced_ai = False
            
            # 生成巡逻点（如果方法存在）
            if hasattr(ai_player, 'generate_patrol_points'):
                ai_player.generate_patrol_points(game_instance.game_map)
            
            game_instance.ai_players[ai_id] = ai_player
            
            # 添加到玩家列表
            player_data = {
                'pos': [spawn_x, spawn_y],
                'angle': ai_player.angle,
                'health': ai_player.health,
                'ammo': ai_player.ammo,
                'is_reloading': ai_player.is_reloading,
                'shooting': False,
                'is_dead': ai_player.is_dead,
                'death_time': ai_player.death_time,
                'respawn_time': ai_player.respawn_time,
                'is_respawning': False,
                'melee_attacking': False,
                'melee_direction': 0,
                'weapon_type': ai_player.weapon_type,
                'is_aiming': ai_player.is_aiming,
                'name': ai_player_name,
                'team_id': getattr(ai_player, 'team_id', None)  # 添加团队ID
            }
            
            # 添加增强版AI特有的属性
            if use_enhanced_ai:
                player_data['is_walking'] = getattr(ai_player, 'is_walking', False)
                player_data['is_making_sound'] = getattr(ai_player, 'is_making_sound', False)
                player_data['sound_volume'] = getattr(ai_player, 'sound_volume', 0.0)
            
            self.players[ai_id] = player_data
            
            # 生成消息
            if use_enhanced_ai and personality:
                personality_name = personality_traits.personality_type.value
                self._send_system_message(f"已添加AI玩家 (难度: {difficulty}, 性格: {personality_name}, ID: {ai_id})")
            elif use_enhanced_ai:
                personality_name = personality_traits.personality_type.value
                self._send_system_message(f"已添加AI玩家 (难度: {difficulty}, 性格: {personality_name}, ID: {ai_id})")
            else:
                self._send_system_message(f"已添加AI玩家 (难度: {difficulty}, ID: {ai_id})")
        
        elif cmd == '.removeai' and is_admin:
            # 移除AI玩家
            if not args:
                self._send_system_message("用法: .removeai <AI_ID|all>")
                return
            
            game_instance = getattr(self, 'game_instance', None)
            if not game_instance:
                self._send_system_message("无法移除AI玩家：游戏实例不存在")
                return
            
            target = args[0].lower()
            if target == 'all':
                # 移除所有AI
                count = len(game_instance.ai_players)
                for ai_id in list(game_instance.ai_players.keys()):
                    if ai_id in self.players:
                        del self.players[ai_id]
                game_instance.ai_players.clear()
                self._send_system_message(f"已移除所有AI玩家 (共{count}个)")
            else:
                try:
                    ai_id = int(target)
                    if ai_id in game_instance.ai_players:
                        del game_instance.ai_players[ai_id]
                        if ai_id in self.players:
                            del self.players[ai_id]
                        self._send_system_message(f"已移除AI玩家 (ID: {ai_id})")
                    else:
                        self._send_system_message(f"AI玩家不存在 (ID: {ai_id})")
                except ValueError:
                    self._send_system_message(f"无效的AI ID: {target}")
        
        elif cmd == '.listai':
            # 列出所有AI玩家
            game_instance = getattr(self, 'game_instance', None)
            if not game_instance:
                self._send_system_message("无法列出AI玩家：游戏实例不存在")
                return
            
            if not game_instance.ai_players:
                self._send_system_message("当前没有AI玩家")
                return
            
            ai_list = []
            for ai_id, ai_player in game_instance.ai_players.items():
                status = "死亡" if ai_player.is_dead else f"生命值:{ai_player.health}"
                # 检查是否有性格信息（增强版AI）
                if hasattr(ai_player, 'personality_traits'):
                    personality_name = ai_player.personality_traits.personality_type.value
                    ai_list.append(f"ID:{ai_id} - {ai_player.name} (难度:{ai_player.difficulty}, 性格:{personality_name}, {status})")
                else:
                    ai_list.append(f"ID:{ai_id} - {ai_player.name} (难度:{ai_player.difficulty}, {status})")
            
            self._send_system_message(f"AI玩家列表({len(ai_list)}):\n" + "\n".join(ai_list))
        
        elif cmd == '.createteam':
            # 创建团队
            game_instance = getattr(self, 'game_instance', None)
            if not game_instance or not hasattr(game_instance, 'team_manager'):
                self._send_system_message("团队系统未启用")
                return
            
            team_name = " ".join(args) if args else None
            team = game_instance.team_manager.create_team(player_id, team_name)
            
            if team:
                self._send_system_message(f"已创建团队: {team.name} (ID: {team.team_id})")
                # 同步团队信息到网络
                self._sync_team_info(player_id, team.team_id)
            else:
                self._send_system_message("创建团队失败：你已经在团队中")
        
        elif cmd == '.jointeam':
            # 加入团队
            if not args:
                self._send_system_message("用法: .jointeam <团队ID>")
                return
            
            game_instance = getattr(self, 'game_instance', None)
            if not game_instance or not hasattr(game_instance, 'team_manager'):
                self._send_system_message("团队系统未启用")
                return
            
            try:
                team_id = int(args[0])
                if game_instance.team_manager.join_team(player_id, team_id):
                    self._send_system_message(f"已加入团队: {team_id}")
                    # 同步团队信息到网络
                    self._sync_team_info(player_id, team_id)
                else:
                    self._send_system_message("加入团队失败：团队不存在或已满，或你已在团队中")
            except ValueError:
                self._send_system_message(f"无效的团队ID: {args[0]}")
        
        elif cmd == '.leaveteam':
            # 离开团队
            game_instance = getattr(self, 'game_instance', None)
            if not game_instance or not hasattr(game_instance, 'team_manager'):
                self._send_system_message("团队系统未启用")
                return
            
            if game_instance.team_manager.leave_team(player_id):
                self._send_system_message("已离开团队")
                # 同步团队信息到网络
                self._sync_team_info(player_id, None)
            else:
                self._send_system_message("离开团队失败：你不在任何团队中")
        
        elif cmd == '.team' or cmd == '.teaminfo':
            # 显示团队信息
            game_instance = getattr(self, 'game_instance', None)
            if not game_instance or not hasattr(game_instance, 'team_manager'):
                self._send_system_message("团队系统未启用")
                return
            
            team = game_instance.team_manager.get_player_team(player_id)
            if team:
                members_list = ", ".join([f"玩家{pid}" for pid in team.members])
                self._send_system_message(f"团队信息:\n名称: {team.name}\nID: {team.team_id}\n成员: {members_list}\n队长: 玩家{team.leader_id}")
            else:
                self._send_system_message("你不在任何团队中")
        
        elif cmd == '.listteams':
            # 列出所有团队
            game_instance = getattr(self, 'game_instance', None)
            if not game_instance or not hasattr(game_instance, 'team_manager'):
                self._send_system_message("团队系统未启用")
                return
            
            teams = game_instance.team_manager.list_teams()
            if teams:
                team_list = []
                for team_info in teams:
                    members_list = ", ".join([f"玩家{pid}" for pid in team_info['members']])
                    team_list.append(f"团队{team_info['team_id']}: {team_info['name']} (成员: {members_list})")
                self._send_system_message("所有团队:\n" + "\n".join(team_list))
            else:
                self._send_system_message("当前没有团队")
        
        elif cmd == '.invite' or cmd == '.teaminvite':
            # 邀请玩家加入团队（仅队长可用）
            if not args:
                self._send_system_message("用法: .invite <玩家ID>")
                return
            
            game_instance = getattr(self, 'game_instance', None)
            if not game_instance or not hasattr(game_instance, 'team_manager'):
                self._send_system_message("团队系统未启用")
                return
            
            try:
                invitee_id = int(args[0])
                
                # 检查被邀请者是否存在（可以是玩家或AI）
                is_player = invitee_id in self.players
                is_ai = False
                if game_instance and hasattr(game_instance, 'ai_players'):
                    is_ai = invitee_id in game_instance.ai_players
                
                if not is_player and not is_ai:
                    self._send_system_message(f"玩家{invitee_id}不存在")
                    return
                
                # 不能邀请自己
                if invitee_id == player_id:
                    self._send_system_message("不能邀请自己")
                    return
                
                # 获取被邀请者名称
                if is_player:
                    invitee_name = self.players[invitee_id].get('name', f'玩家{invitee_id}')
                else:
                    # AI玩家
                    ai_player = game_instance.ai_players[invitee_id]
                    invitee_name = getattr(ai_player, 'name', f'AI{invitee_id}')
                
                # 使用团队管理器邀请
                success, message = game_instance.team_manager.invite_to_team(player_id, invitee_id)
                
                if success:
                    # 同步团队信息
                    team = game_instance.team_manager.get_player_team(player_id)
                    if team:
                        self._sync_team_info(invitee_id, team.team_id)
                        
                        # 如果被邀请的是AI，更新AI的team_id
                        if is_ai:
                            ai_player = game_instance.ai_players[invitee_id]
                            if hasattr(ai_player, 'team_id'):
                                ai_player.team_id = team.team_id
                                # 如果是增强版AI，重新初始化行为树
                                if hasattr(ai_player, '_initialize_behavior_tree'):
                                    ai_player._initialize_behavior_tree()
                        
                        # 发送成功消息给邀请者
                        inviter_name = self.players.get(player_id, {}).get('name', f'玩家{player_id}')
                        self._send_system_message(f"已邀请 {invitee_name} 加入团队")
                        
                        # 发送系统消息通知被邀请者（通过聊天系统）
                        invite_msg = ChatMessage(
                            0,
                            "[系统]",
                            f"{inviter_name} 邀请你加入了团队 {team.name}",
                            time.time()
                        )
                        self.chat_messages.append(invite_msg)
                        # 如果是玩家，直接发送给该玩家；如果是AI，AI会看到聊天消息
                        if is_player:
                            # 查找被邀请玩家的地址并发送消息
                            for addr, pid in self.clients.items():
                                if pid == invitee_id:
                                    self.send_to_client({
                                        'type': 'chat_message',
                                        'data': {
                                            'player_id': 0,
                                            'player_name': '[系统]',
                                            'message': f"{inviter_name} 邀请你加入了团队 {team.name}",
                                            'timestamp': time.time()
                                        }
                                    }, addr)
                                    break
                        # 也广播给所有玩家（包括AI可以看到）
                        self.broadcast_chat_message(invite_msg)
                    else:
                        self._send_system_message("邀请失败：无法获取团队信息")
                else:
                    self._send_system_message(message)
                    
            except ValueError:
                self._send_system_message(f"无效的玩家ID: {args[0]}")
        
        elif cmd == '.teamchat' or cmd == '.tc':
            # 切换到队内聊天模式
            game_instance = getattr(self, 'game_instance', None)
            if game_instance and hasattr(game_instance, 'team_chat_mode'):
                game_instance.team_chat_mode = True
                self._send_system_message("已切换到队内聊天模式（输入 .all 或 .global 切换回全局聊天）")
            else:
                self._send_system_message("团队聊天功能未启用")
        
        elif cmd == '.all' or cmd == '.global':
            # 切换到全局聊天模式
            game_instance = getattr(self, 'game_instance', None)
            if game_instance and hasattr(game_instance, 'team_chat_mode'):
                game_instance.team_chat_mode = False
                self._send_system_message("已切换到全局聊天模式（输入 .teamchat 或 .tc 切换回队内聊天）")
            else:
                self._send_system_message("团队聊天功能未启用")
        
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
                    ".addai [difficulty] [personality] - 添加AI玩家",
                    "  难度: easy/normal/hard (默认: normal)",
                    "  性格: aggressive/defensive/tactical/stealthy/team/random (默认: random)",
                    "  示例: .addai normal aggressive 或 .addai hard tactical",
                    ".removeai <AI_ID|all> - 移除AI玩家",
                    ".listai - 列出所有AI玩家",
                    ".createteam [名称] - 创建团队",
                    ".jointeam <团队ID> - 加入团队",
                    ".leaveteam - 离开团队",
                    ".team 或 .teaminfo - 显示团队信息",
                    ".listteams - 列出所有团队",
                    ".invite 或 .teaminvite <玩家ID> - 邀请玩家/AI加入团队（仅队长可用）",
                    ".teamchat 或 .tc - 切换到队内聊天",
                    ".all 或 .global - 切换到全局聊天",
                    ".help - 显示此帮助信息"
                ]
                self._send_system_message("可用命令:\n" + "\n".join(commands))
            else:
                commands = [
                    ".list 或 .players - 显示在线玩家列表",
                    ".kill - 自杀",
                    ".listai - 列出所有AI玩家",
                    ".createteam [名称] - 创建团队",
                    ".jointeam <团队ID> - 加入团队",
                    ".leaveteam - 离开团队",
                    ".team 或 .teaminfo - 显示团队信息",
                    ".listteams - 列出所有团队",
                    ".invite 或 .teaminvite <玩家ID> - 邀请玩家/AI加入团队（仅队长可用）",
                    ".teamchat 或 .tc - 切换到队内聊天",
                    ".all 或 .global - 切换到全局聊天",
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
            "[系统]",
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
    
    def _sync_team_info(self, player_id, team_id):
        """同步团队信息到网络"""
        # 更新玩家数据中的团队ID
        if player_id in self.players:
            self.players[player_id]['team_id'] = team_id
        
        # 同步到游戏实例中的玩家对象
        game_instance = getattr(self, 'game_instance', None)
        if game_instance:
            if player_id == self.player_id and hasattr(game_instance, 'player'):
                game_instance.player.team_id = team_id
            elif hasattr(game_instance, 'other_players') and player_id in game_instance.other_players:
                game_instance.other_players[player_id].team_id = team_id
            # 同步到AI玩家
            if hasattr(game_instance, 'ai_players') and player_id in game_instance.ai_players:
                game_instance.ai_players[player_id].team_id = team_id
        
        # 广播团队更新给所有客户端（通过玩家更新消息）
        # 团队信息会随着玩家数据一起同步
    
    def _handle_chat_history(self, history_data):
        """处理聊天历史（客户端接收）"""
        if not self.is_server and isinstance(history_data, dict) and 'messages' in history_data:
            self.chat_messages = []
            for msg_data in history_data['messages']:
                msg = ChatMessage(
                    msg_data['player_id'],
                    msg_data.get('player_name', f'玩家{msg_data["player_id"]}'),
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

    def send_chat_message(self, message, is_team_chat=False):
        """发送聊天消息"""
        if len(message.strip()) == 0:
            return
            
        # 获取玩家名称
        player_name = self.players.get(self.player_id, {}).get('name', f'玩家{self.player_id}')
        chat_data = {
            'type': 'chat_message',
            'data': {
                'player_id': self.player_id,
                'player_name': player_name,
                'message': message[:MAX_CHAT_LENGTH],
                'timestamp': time.time(),
                'is_team_chat': is_team_chat
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
                # 检查玩家复活（服务端统一处理）
                self.check_player_respawns(current_time)
                
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

    def check_player_respawns(self, current_time):
        """检查并处理玩家复活（仅服务端）"""
        if not self.is_server:
            return
            
        with self.lock:
            for player_id, player_data in self.players.items():
                # 检查死亡玩家是否到了复活时间
                if (player_data.get('is_dead', False) and 
                    not player_data.get('is_respawning', False) and
                    player_data.get('respawn_time', 0) > 0 and
                    current_time >= player_data.get('respawn_time', 0)):
                    
                    # 开始复活流程
                    player_data['is_respawning'] = True
                    
                    # 获取随机复活位置
                    spawn_pos = self.get_random_spawn_pos()
                    
                    # 重置玩家状态
                    player_data['pos'] = spawn_pos
                    player_data['health'] = 100
                    player_data['is_dead'] = False
                    player_data['is_respawning'] = False
                    player_data['death_time'] = 0
                    player_data['respawn_time'] = 0
                    
                    # 重置武器状态
                    player_data['ammo'] = MAGAZINE_SIZE
                    player_data['is_reloading'] = False
                    
                    print(f"[服务端] 玩家{player_id}已复活，位置: {spawn_pos}")
                    
                    # 广播复活事件
                    respawn_msg = {
                        'type': 'respawn',
                        'data': {
                            'player_id': player_id,
                            'pos': spawn_pos,
                            'health': 100
                        }
                    }
                    self.send_data(respawn_msg)
                    
                    # 如果是服务端本地玩家，直接处理复活事件
                    if player_id == self.player_id:
                        self._handle_respawn(respawn_msg['data'])

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
        # 返回所有消息，不再检查过期
        return self.chat_messages

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

