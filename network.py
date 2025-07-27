import socket
import threading
import json
import time
import random
from pygame.locals import *
from constants import SERVER_PORT, BUFFER_SIZE, HEARTBEAT_INTERVAL, CLIENT_TIMEOUT

class NetworkManager:
    """网络管理类，处理客户端和服务器的网络通信"""
    def __init__(self, is_server=False, server_name="默认服务器"):
        self.is_server = is_server
        self.server_name = server_name  # 服务器名称
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(0.1)  # 设置超时时间
        
        # 玩家信息
        self.player_id = -1
        self.player_name = "Player" + str(random.randint(100, 999))
        
        # 服务器信息
        self.server_ip = ""
        self.server_port = SERVER_PORT
        
        # 客户端列表（服务器用）
        self.clients = {}  # {client_id: (ip, port, last_heartbeat)}
        self.recycled_ids = set()  # 回收的ID池
        self.next_client_id = 0
        
        # 消息队列
        self.message_queue = []
        self.message_lock = threading.Lock()
        
        # 网络线程
        self.network_thread = None
        self.running = False
        
        # 心跳计时
        self.last_heartbeat_sent = 0
        self.last_heartbeat_received = 0
    
    def start(self, ip="", port=SERVER_PORT):
        """启动网络服务"""
        try:
            self.server_ip = ip
            self.server_port = port
            
            if self.is_server:
                self.socket.bind(("0.0.0.0", port))
                print(f"服务器启动在端口 {port}")
            
            self.running = True
            self.network_thread = threading.Thread(target=self.network_loop)
            self.network_thread.daemon = True
            self.network_thread.start()
            
            return True
        except Exception as e:
            print(f"网络启动失败: {e}")
            return False
    
    def stop(self):
        """停止网络服务"""
        self.running = False
        if self.network_thread:
            self.network_thread.join()
        self.socket.close()
    
    def network_loop(self):
        """网络线程主循环"""
        while self.running:
            try:
                # 接收数据
                data, addr = self.socket.recvfrom(BUFFER_SIZE)
                self.process_message(data, addr)
            except socket.timeout:
                pass
            except Exception as e:
                print(f"网络接收错误: {e}")
            
            # 服务器定期处理
            if self.is_server:
                self.server_update()
            
            # 客户端定期发送心跳
            if not self.is_server and time.time() - self.last_heartbeat_sent > HEARTBEAT_INTERVAL:
                self.send_heartbeat()
    
    def process_message(self, data, addr):
        """处理接收到的网络消息"""
        try:
            message = json.loads(data.decode())
            message_type = message.get("type")
            
            if self.is_server:
                self.process_server_message(message, message_type, addr)
            else:
                self.process_client_message(message, message_type)
        except Exception as e:
            print(f"消息处理错误: {e}")
    
    def process_server_message(self, message, message_type, addr):
        """服务器处理消息"""
        client_id = message.get("client_id", -1)
        
        if message_type == "connect_request":
            self.handle_connect_request(addr, message)
        elif message_type == "heartbeat":
            self.handle_heartbeat(client_id, addr)
        elif message_type == "player_update":
            self.broadcast_message(message, exclude=client_id)
        elif message_type == "bullet_fired":
            self.broadcast_message(message, exclude=client_id)
        elif message_type == "melee_attack":
            self.broadcast_message(message, exclude=client_id)
        elif message_type == "door_interaction":
            self.broadcast_message(message, exclude=client_id)
        elif message_type == "chat_message":
            self.broadcast_message(message)
    
    def process_client_message(self, message, message_type):
        """客户端处理消息"""
        if message_type == "connect_response":
            self.player_id = message.get("client_id", -1)
            self.server_name = message.get("server_name", "默认服务器")
            self.last_heartbeat_received = time.time()
        elif message_type == "heartbeat_response":
            self.last_heartbeat_received = time.time()
        elif message_type in ["player_update", "bullet_fired", "melee_attack", "door_interaction", "chat_message"]:
            with self.message_lock:
                self.message_queue.append(message)
    
    def handle_connect_request(self, addr, message):
        """处理客户端连接请求"""
        client_name = message.get("name", "Player")
        
        # 分配或回收客户端ID
        if self.recycled_ids:
            client_id = self.recycled_ids.pop()
        else:
            client_id = self.next_client_id
            self.next_client_id += 1
        
        # 记录客户端信息
        self.clients[client_id] = (addr[0], addr[1], time.time())
        
        # 发送连接响应
        response = {
            "type": "connect_response",
            "client_id": client_id,
            "server_name": self.server_name,
            "server_time": time.time()
        }
        self.send_message(response, addr)
        
        print(f"新客户端连接: {client_name} (ID: {client_id}) 来自 {addr}")
    
    def handle_heartbeat(self, client_id, addr):
        """处理心跳包"""
        if client_id in self.clients:
            self.clients[client_id] = (addr[0], addr[1], time.time())
            
            # 发送心跳响应
            response = {
                "type": "heartbeat_response",
                "server_time": time.time()
            }
            self.send_message(response, addr)
    
    def server_update(self):
        """服务器定期更新"""
        current_time = time.time()
        
        # 检查超时的客户端
        timed_out_clients = []
        for client_id, (ip, port, last_heartbeat) in self.clients.items():
            if current_time - last_heartbeat > CLIENT_TIMEOUT:
                timed_out_clients.append(client_id)
        
        # 移除超时的客户端
        for client_id in timed_out_clients:
            self.clients.pop(client_id)
            self.recycled_ids.add(client_id)
            print(f"客户端 {client_id} 超时断开")
    
    def send_heartbeat(self):
        """发送心跳包"""
        if self.is_server:
            return
            
        message = {
            "type": "heartbeat",
            "client_id": self.player_id
        }
        self.send_message_to_server(message)
        self.last_heartbeat_sent = time.time()
    
    def send_message(self, message, addr):
        """发送消息到指定地址"""
        try:
            self.socket.sendto(json.dumps(message).encode(), addr)
        except Exception as e:
            print(f"消息发送失败: {e}")
    
    def send_message_to_server(self, message):
        """发送消息到服务器"""
        if not self.server_ip:
            return
            
        message["client_id"] = self.player_id
        self.send_message(message, (self.server_ip, self.server_port))
    
    def broadcast_message(self, message, exclude=None):
        """广播消息给所有客户端"""
        if not self.is_server:
            return
            
        for client_id, (ip, port, _) in self.clients.items():
            if client_id != exclude:
                self.send_message(message, (ip, port))
    
    def get_messages(self):
        """获取接收到的消息"""
        with self.message_lock:
            messages = self.message_queue.copy()
            self.message_queue.clear()
        return messages
    
    def send_player_update(self, position, angle, health, is_dead, is_aiming):
        """发送玩家状态更新"""
        message = {
            "type": "player_update",
            "position": (position.x, position.y),
            "angle": angle,
            "health": health,
            "is_dead": is_dead,
            "is_aiming": is_aiming,
            "timestamp": time.time()
        }
        self.send_message_to_server(message)
    
    def send_bullet_fired(self, position, angle):
        """发送子弹发射消息"""
        message = {
            "type": "bullet_fired",
            "position": (position.x, position.y),
            "angle": angle,
            "timestamp": time.time()
        }
        self.send_message_to_server(message)
    
    def send_melee_attack(self, angle):
        """发送近战攻击消息"""
        message = {
            "type": "melee_attack",
            "angle": angle,
            "timestamp": time.time()
        }
        self.send_message_to_server(message)
    
    def send_door_interaction(self, door_index, door_state_version):
        """发送门交互消息"""
        message = {
            "type": "door_interaction",
            "door_index": door_index,
            "state_version": door_state_version,
            "timestamp": time.time()
        }
        self.send_message_to_server(message)
    
    def send_chat_message(self, text):
        """发送聊天消息"""
        if len(text) > MAX_CHAT_LENGTH:
            text = text[:MAX_CHAT_LENGTH]
            
        message = {
            "type": "chat_message",
            "text": text,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "timestamp": time.time()
        }
        self.send_message_to_server(message)