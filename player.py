import pygame
import math
import time
import random
from pygame.locals import *
from constants import *
from weapons import MeleeWeapon
import ui

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
        
        # 团队系统
        self.team_id = None  # 所属团队ID
        
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
        
        # 护甲系统
        self.armor = 0  # 护甲值
        self.armor_damage_reduction = 0.5  # 护甲伤害减免比例
        
        # 伤害提升效果
        self.damage_boost_end_time = 0  # 伤害提升结束时间
        self.damage_boost_multiplier = 1.0  # 伤害提升倍率
        
        # 手雷
        self.grenades = 0  # 拥有的手雷数量
        
        # 道具效果提示
        self.effect_message = ""  # 当前显示的效果消息
        self.effect_message_time = 0  # 消息显示结束时间
        
        # 玩家状态（保持向后兼容）
        self.position = self.pos  # 别名，保持兼容性
        self.last_damage_time = 0
        self.damage_cooldown = 0.5  # 伤害冷却时间

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
    
    def can_pickup_item(self):
        """检查是否可以拾取道具"""
        if self.is_dead or self.is_respawning:
            return False
        return True
    
    def apply_item_effect(self, effect: dict):
        """应用道具效果"""
        if not effect:
            return
        
        effect_type = effect.get('type')
        message = effect.get('message', '')
        
        if effect_type == 'health':
            old_health = self.health
            self.health = min(self.health + effect.get('amount', 0), 100)
            healed = self.health - old_health
            self.effect_message = f"+{healed} 生命值"
        elif effect_type == 'ammo':
            old_ammo = self.ammo
            self.ammo = min(self.ammo + effect.get('amount', 0), 999)
            added = self.ammo - old_ammo
            self.effect_message = f"+{added} 弹药"
        elif effect_type == 'armor':
            old_armor = self.armor
            self.armor = min(self.armor + effect.get('amount', 0), 100)
            added = self.armor - old_armor
            self.effect_message = f"+{added} 护甲"
        elif effect_type == 'speed_boost':
            duration = effect.get('duration', 10)
            self.speed_boost_end_time = time.time() + duration
            self.speed_boost_multiplier = 1.5
            self.effect_message = f"速度提升 {duration}秒"
        elif effect_type == 'damage_boost':
            duration = effect.get('duration', 15)
            self.damage_boost_end_time = time.time() + duration
            self.damage_boost_multiplier = 1.5
            self.effect_message = f"伤害提升 {duration}秒"
        elif effect_type == 'grenade':
            count = effect.get('count', 1)
            self.grenades = getattr(self, 'grenades', 0) + count
            self.effect_message = f"获得{count}颗手雷"
        
        if message and not self.effect_message:
            self.effect_message = message
        
        self.effect_message_time = time.time() + 3.0
    
    def update_effects(self, dt: float):
        """更新道具效果状态"""
        current_time = time.time()
        
        if current_time < self.speed_boost_end_time:
            self.speed_boost_multiplier = 1.5
        else:
            self.speed_boost_end_time = 0
            self.speed_boost_multiplier = 1.0
        
        if current_time < self.damage_boost_end_time:
            self.damage_boost_multiplier = 1.5
        else:
            self.damage_boost_end_time = 0
            self.damage_boost_multiplier = 1.0
    
    def get_damage_multiplier(self) -> float:
        """获取伤害倍率"""
        return getattr(self, 'damage_boost_multiplier', 1.0)
    
    def apply_damage(self, damage: int) -> int:
        """应用伤害，返回实际受到的伤害"""
        if self.armor > 0:
            reduction = min(self.armor * self.armor_damage_reduction, damage * 0.7)
            armor_damage = min(self.armor, reduction)
            self.armor = max(0, self.armor - armor_damage)
            actual_damage = max(0, int(damage - reduction))
        else:
            actual_damage = damage
        
        self.health = max(0, self.health - actual_damage)
        return actual_damage
    
    def reset_item_effects(self):
        """重置所有道具效果"""
        self.armor = 0
        self.speed_boost_end_time = 0
        self.speed_boost_multiplier = 1.0
        self.damage_boost_end_time = 0
        self.damage_boost_multiplier = 1.0
        self.grenades = 0
        self.effect_message = ""
        self.effect_message_time = 0

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
        self.position = self.pos  # 保持别名同步
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
        
        # 重置道具效果
        self.reset_item_effects()
        
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
            base_spread = speed_ratio * 20.0  # 基础散布最多20度
            
            # 静步时减少散布
            if self.is_walking:
                spread += base_spread * 0.25  # 静步时散布减至1/4
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

    def update(self, dt, game_map, bullets, network_manager=None, all_players=None, chat_active=False):
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
            # 复活由服务端统一处理，客户端不再自行检查复活时间
            if self.is_dead:
                return
            
            # 只有在非聊天状态下才处理移动和攻击输入
            if not chat_active:
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
                
                # 换弹控制
                if (keys[K_r] or self.ammo <= 0) and not self.is_reloading and self.ammo < MAGAZINE_SIZE and self.weapon_type == "gun":
                    self.is_reloading = True
                    self.reload_start = current_time
                    
                if self.is_reloading and (current_time - self.reload_start) >= RELOAD_TIME:
                    self.ammo = MAGAZINE_SIZE
                    self.is_reloading = False
            else:
                # 聊天状态下，停止移动，但保持摩擦力
                self.velocity *= 0.9
                self.shooting = False
                self.is_making_sound = False
                self.sound_volume = 0.0

            # 即使在聊天时，物理检测（如近战）也允许完成
            if self.melee_weapon.is_attacking:
                # 检查近战攻击是否击中目标
                targets = {}
                if all_players:
                    # 获取团队管理器（如果存在）
                    team_manager = None
                    if network_manager:
                        game_instance = getattr(network_manager, 'game_instance', None)
                        if game_instance and hasattr(game_instance, 'team_manager'):
                            team_manager = game_instance.team_manager
                    
                    for pid, player in all_players.items():
                        if pid != self.id and not player.is_dead:
                            # 检查是否是队友，如果是队友则跳过（队友不受伤害）
                            if team_manager and team_manager.are_teammates(self.id, pid):
                                continue
                            # 回退：比较本地对象上的team_id
                            try:
                                if getattr(self, 'team_id', None) is not None and getattr(player, 'team_id', None) is not None:
                                    if self.team_id == player.team_id:
                                        continue
                            except Exception:
                                pass
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
                self.position = self.pos  # 保持别名同步

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
                    # 复活时间完全依赖服务端，但要确保数据有效
                    server_respawn_time = server_data.get('respawn_time', 0)
                    # 只有当服务端提供了有效的复活时间才使用，否则保持当前值
                    if server_respawn_time > 0:
                        self.respawn_time = server_respawn_time

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

    def take_damage(self, damage, custom_respawn_time=None):
        """玩家受到伤害
        
        Args:
            damage: 伤害值
            custom_respawn_time: 自定义复活时间，如果为None则使用默认值
        """
        current_time = time.time()
        if current_time - self.last_damage_time < self.damage_cooldown:
            return False
            
        self.last_damage_time = current_time
        
        actual_damage = self.apply_damage(damage)
        
        if actual_damage > 0:
            print(f"[护甲系统] 玩家{self.id}受到{actual_damage}伤害，剩余生命{self.health}，护甲{self.armor}")
        
        # 触发被击中减速效果
        self.hit_slowdown_end_time = current_time + HIT_SLOWDOWN_DURATION
        
        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            return True
        
        return False

    def draw(self, surface, camera_offset, player_pos=None, player_angle=None, walls=None, doors=None, is_local_player=False, is_aiming=False, team_manager=None, local_player_id=None):
        """绘制玩家（考虑视线遮挡和团队共享视野）"""
        player_screen_pos = pygame.Vector2(
            self.pos.x - camera_offset.x,
            self.pos.y - camera_offset.y
        )
        
        # 如果不是本地玩家，检查是否可见
        if not is_local_player and player_pos and player_angle and walls and doors:
            # 检查是否是队友（团队共享视野 - 所有队员都能看到其他队员）
            is_teammate = False
            if team_manager and local_player_id is not None:
                is_teammate = team_manager.are_teammates(local_player_id, self.id)
            
            # 如果是队友，始终可见（所有队员共享视野，不只是队长）
            if not is_teammate:
                # 导入工具函数
                from utils import is_visible
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
            # 确保复活时间有效且大于当前时间才显示倒计时
            if self.respawn_time > 0 and self.respawn_time > current_time:
                remaining_time = self.respawn_time - current_time
                # 确保倒计时在合理范围内（0到RESPAWN_TIME秒）
                if 0 < remaining_time <= RESPAWN_TIME:
                    respawn_text = f"{remaining_time:.1f}s"
                    # 使用pygame默认字体
                    font = pygame.font.Font(None, 36)
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
        
        # 使用支持中文的字体
        name_surface = ui.small_font.render(self.name, True, WHITE)
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
            
        # 同步玩家名称
        if 'name' in network_data:
            self.name = network_data['name']
