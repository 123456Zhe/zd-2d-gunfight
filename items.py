"""
道具系统模块

提供游戏内道具的定义、效果和拾取机制。
支持多种道具类型：医疗包、弹药箱、护甲、速度提升等。

道具类型:
    - HEALTH_PACK: 恢复生命值
    - AMMO_BOX: 补充弹药
    - ARMOR: 提供护甲值
    - SPEED_BOOST: 临时速度提升
    - DAMAGE_BOOST: 临时伤害提升
    - GRENADE: 手雷（范围伤害）
"""

import pygame
import math
import random
import time
from typing import Dict, List, Optional, Tuple
from enum import Enum, auto
from constants import PLAYER_RADIUS


class ItemType(Enum):
    """道具类型枚举"""
    HEALTH_PACK = auto()
    AMMO_BOX = auto()
    ARMOR = auto()
    SPEED_BOOST = auto()
    DAMAGE_BOOST = auto()
    GRENADE = auto()


class Item:
    """道具基类"""
    
    TYPE = None
    NAME = ""
    DESCRIPTION = ""
    COLOR = (255, 255, 255)
    RADIUS = 15
    DURATION = 0
    RESPAWN_TIME = 30
    
    def __init__(self, item_id: int, x: float, y: float):
        self.id = item_id
        self.pos = pygame.Vector2(x, y)
        self.respawn_time_remaining = 0
        self.is_active = True
        self.last_pickup_time = 0
        self.pickup_cooldown = 1.0
    
    def can_pickup(self, player_id: int) -> bool:
        """检查是否可以拾取"""
        if not self.is_active:
            return False
        current_time = time.time()
        if current_time - self.last_pickup_time < self.pickup_cooldown:
            return False
        return True
    
    def pickup(self, player: 'Player') -> Dict:
        """拾取道具，返回效果数据"""
        self.last_pickup_time = time.time()
        self.is_active = False
        self.respawn_time_remaining = self.RESPAWN_TIME
        effect = self.get_effect(player)
        effect['item_id'] = self.id
        return effect
    
    def get_effect(self, player: 'Player') -> Dict:
        """获取道具效果（子类实现）"""
        return {}
    
    def update(self, dt: float):
        """更新道具状态"""
        if not self.is_active and self.respawn_time_remaining > 0:
            self.respawn_time_remaining -= dt
            if self.respawn_time_remaining <= 0:
                self.respawn_time_remaining = 0
                self.is_active = True
    
    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2,
             player_pos: pygame.Vector2 = None, player_angle: float = None,
             walls: List = None, doors: List = None, is_aiming: bool = False):
        """绘制道具"""
        if not self.is_active:
            return
        
        screen_pos = pygame.Vector2(
            self.pos.x - camera_offset.x,
            self.pos.y - camera_offset.y
        )
        
        if player_pos and player_angle and walls and doors:
            from utils import is_visible
            if not is_visible(player_pos, player_angle, self.pos, 120, walls, doors):
                return
        
        pygame.draw.circle(surface, self.COLOR, (int(screen_pos.x), int(screen_pos.y)), self.RADIUS)
        
        pulse = math.sin(time.time() * 4) * 3
        pygame.draw.circle(surface, self.COLOR, (int(screen_pos.x), int(screen_pos.y)),
                          self.RADIUS + int(pulse), 2)
        
        try:
            import ui
            fonts = ui.get_fonts()
            font = fonts.get("font") or fonts.get("default")
            if font:
                text = font.render(self.NAME[:1], True, (255, 255, 0))
            else:
                text = pygame.font.Font(None, 20).render(self.NAME[:1], True, (255, 255, 0))
        except:
            text = pygame.font.Font(None, 20).render(self.NAME[:1], True, (255, 255, 0))
        
        text_rect = text.get_rect(center=(screen_pos.x, screen_pos.y))
        surface.blit(text, text_rect)
    
    def get_state(self) -> Dict:
        """获取道具状态（网络同步用）"""
        return {
            'id': self.id,
            'type': self.TYPE.name if self.TYPE else None,
            'pos': [self.pos.x, self.pos.y],
            'is_active': self.is_active,
            'respawn_time_remaining': self.respawn_time_remaining
        }
    
    @staticmethod
    def from_state(state: Dict) -> 'Item':
        """从状态创建道具"""
        item_type = state.get('type')
        x, y = state.get('pos', [0, 0])
        item_id = state.get('id', 0)
        
        for item_class in Item.__subclasses__():
            if item_class.TYPE and item_class.TYPE.name == item_type:
                item = item_class(item_id, x, y)
                item.is_active = state.get('is_active', True)
                item.respawn_time_remaining = state.get('respawn_time_remaining', 0)
                return item
        
        return None


class HealthPack(Item):
    """医疗包 - 恢复生命值"""
    
    TYPE = ItemType.HEALTH_PACK
    NAME = "医疗包"
    DESCRIPTION = "恢复50点生命值"
    COLOR = (0, 255, 0)
    RADIUS = 15
    RESPAWN_TIME = 30
    HEAL_AMOUNT = 50
    MAX_HEALTH = 100
    
    def get_effect(self, player: 'Player') -> Dict:
        return {
            'type': 'health',
            'amount': self.HEAL_AMOUNT,
            'message': f"+{self.HEAL_AMOUNT} 生命值"
        }


class AmmoBox(Item):
    """弹药箱 - 补充弹药"""
    
    TYPE = ItemType.AMMO_BOX
    NAME = "弹药箱"
    DESCRIPTION = "补充30发弹药"
    COLOR = (255, 165, 0)
    RADIUS = 15
    RESPAWN_TIME = 25
    AMMO_AMOUNT = 30
    
    def get_effect(self, player: 'Player') -> Dict:
        return {
            'type': 'ammo',
            'amount': self.AMMO_AMOUNT,
            'message': f"+{self.AMMO_AMOUNT} 弹药"
        }


class Armor(Item):
    """护甲 - 提供额外保护"""
    
    TYPE = ItemType.ARMOR
    NAME = "护甲"
    DESCRIPTION = "提供50点护甲，吸收伤害"
    COLOR = (100, 100, 255)
    RADIUS = 15
    RESPAWN_TIME = 35
    ARMOR_AMOUNT = 50
    DAMAGE_REDUCTION = 0.5
    
    def __init__(self, item_id: int, x: float, y: float):
        super().__init__(item_id, x, y)
        self.armor_value = self.ARMOR_AMOUNT
    
    def get_effect(self, player: 'Player') -> Dict:
        return {
            'type': 'armor',
            'amount': self.ARMOR_AMOUNT,
            'message': f"+{self.ARMOR_AMOUNT} 护甲"
        }


class SpeedBoost(Item):
    """速度提升 - 临时增加移动速度"""
    
    TYPE = ItemType.SPEED_BOOST
    NAME = "速度提升"
    DESCRIPTION = "提升移动速度50%，持续10秒"
    COLOR = (255, 255, 0)
    RADIUS = 15
    RESPAWN_TIME = 20
    DURATION = 10.0
    SPEED_MULTIPLIER = 1.5
    
    def get_effect(self, player: 'Player') -> Dict:
        return {
            'type': 'speed_boost',
            'duration': self.DURATION,
            'message': f"速度提升 {self.DURATION}秒"
        }


class DamageBoost(Item):
    """伤害提升 - 临时增加伤害"""
    
    TYPE = ItemType.DAMAGE_BOOST
    NAME = "伤害提升"
    DESCRIPTION = "提升伤害50%，持续15秒"
    COLOR = (255, 0, 0)
    RADIUS = 15
    RESPAWN_TIME = 25
    DURATION = 15.0
    DAMAGE_MULTIPLIER = 1.5
    
    def get_effect(self, player: 'Player') -> Dict:
        return {
            'type': 'damage_boost',
            'duration': self.DURATION,
            'message': f"伤害提升 {self.DURATION}秒"
        }


class Grenade(Item):
    """手雷 - 投掷造成范围伤害"""
    
    TYPE = ItemType.GRENADE
    NAME = "手雷"
    DESCRIPTION = "投掷造成范围伤害"
    COLOR = (128, 128, 128)
    RADIUS = 12
    RESPAWN_TIME = 30
    DAMAGE = 200
    EXPLOSION_RADIUS = 500
    THROW_SPEED = 400
    FUSE_TIME = 3.0
    GRAVITY = 600
    BOUNCE_DAMPING = 0.6
    
    def get_effect(self, player: 'Player') -> Dict:
        return {
            'type': 'grenade',
            'count': 1,
            'message': "获得1颗手雷"
        }


class ThrownGrenade:
    """投掷手雷 - 遵循物理规律"""
    
    GRENADE_ID = 0
    
    def __init__(self, start_pos: pygame.Vector2, direction: pygame.Vector2,
                 throw_speed: float, owner_id: int):
        self.id = ThrownGrenade.GRENADE_ID
        ThrownGrenade.GRENADE_ID += 1
        
        self.pos = pygame.Vector2(start_pos)
        self.velocity = direction.normalize() * throw_speed
        self.owner_id = owner_id
        self.spawn_time = time.time()
        self.exploded = False
        self.explosion_pos = None
        
        self.damage = Grenade.DAMAGE
        self.explosion_radius = Grenade.EXPLOSION_RADIUS
        self.fuse_time = Grenade.FUSE_TIME
        self.gravity = Grenade.GRAVITY
        self.bounce_damping = Grenade.BOUNCE_DAMPING
    
    def update(self, dt: float, walls: List) -> bool:
        """更新手雷位置，返回是否爆炸"""
        if self.exploded:
            return True
        
        new_pos = self.pos + self.velocity * dt
        
        for wall in walls:
            if wall.collidepoint(new_pos.x, new_pos.y):
                wall_center = pygame.Vector2(wall.center)
                dx = abs(new_pos.x - wall_center.x) / (wall.width / 2) if wall.width > 0 else 1
                dy = abs(new_pos.y - wall_center.y) / (wall.height / 2) if wall.height > 0 else 1
                
                if dx > dy:
                    self.velocity.x *= -self.bounce_damping
                else:
                    self.velocity.y *= -self.bounce_damping
                
                self.velocity *= 0.8
                new_pos = self.pos
        
        self.pos = new_pos
        
        if time.time() - self.spawn_time >= self.fuse_time:
            self.explode()
            return True
        
        return False
    
    def explode(self):
        """引爆手雷"""
        self.exploded = True
        self.explosion_pos = pygame.Vector2(self.pos)
    
    def get_targets(self, players: Dict) -> List[Dict]:
        """获取爆炸范围内的目标"""
        if not self.explosion_pos:
            return []
        
        targets = []
        for pid, player in players.items():
            if pid == self.owner_id or player.is_dead:
                continue
            
            distance = self.explosion_pos.distance_to(player.pos)
            if distance <= self.explosion_radius:
                damage_ratio = 1 - (distance / self.explosion_radius)
                damage = int(self.damage * max(0.1, damage_ratio))
                targets.append({
                    'target_id': pid,
                    'damage': damage,
                    'attacker_id': self.owner_id,
                    'type': 'grenade',
                    'explosion_pos': (self.explosion_pos.x, self.explosion_pos.y)
                })
        
        return targets
    
    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2):
        """绘制手雷"""
        screen_pos = (
            self.pos.x - camera_offset.x,
            self.pos.y - camera_offset.y
        )
        
        pygame.draw.circle(surface, (100, 100, 100), (int(screen_pos[0]), int(screen_pos[1])), 8)
        pygame.draw.circle(surface, (50, 50, 50), (int(screen_pos[0]), int(screen_pos[1])), 8, 2)
        
        elapsed = time.time() - self.spawn_time
        pulse = int(50 + 50 * (elapsed % 0.5))
        pygame.draw.circle(surface, (255, pulse, 0), (int(screen_pos[0]), int(screen_pos[1])), 4)
    
    def get_state(self) -> Dict:
        """获取状态用于网络同步"""
        return {
            'id': self.id,
            'pos': [self.pos.x, self.pos.y],
            'velocity': [self.velocity.x, self.velocity.y],
            'owner_id': self.owner_id,
            'spawn_time': self.spawn_time,
            'exploded': self.exploded,
            'explosion_pos': [self.explosion_pos.x, self.explosion_pos.y] if self.explosion_pos else None
        }
    
class ItemManager:
    """道具管理器 - 负责道具的生成、更新和拾取检测"""
    
    def __init__(self):
        self.items: Dict[int, Item] = {}
        self.next_item_id = 1
        self.item_spawn_points: List[Tuple[float, float]] = []
        self.item_weights: Dict[ItemType, float] = {}
        self.respawn_enabled = True
    
    def generate_spawn_points(self, map_rooms: List[pygame.Rect], walls: List[pygame.Rect]):
        """生成道具生成点（避开墙壁和门）"""
        self.item_spawn_points = []
        
        for room in map_rooms:
            points_per_room = 2
            for _ in range(points_per_room):
                for _ in range(10):
                    x = random.randint(room.left + 50, room.right - 50)
                    y = random.randint(room.top + 50, room.bottom - 50)
                    
                    spawn_pos = pygame.Vector2(x, y)
                    
                    can_spawn = True
                    for wall in walls:
                        if wall.collidepoint(x, y):
                            can_spawn = False
                            break
                    
                    if can_spawn:
                        self.item_spawn_points.append((x, y))
                        break
    
    def set_spawn_weights(self, weights: Dict[ItemType, float]):
        """设置道具生成权重"""
        self.item_weights = weights
    
    def spawn_item(self, item_type: ItemType = None, pos: Tuple[float, float] = None) -> Optional[Item]:
        """生成一个道具"""
        if not self.item_spawn_points and not pos:
            return None
        
        if item_type is None:
            if self.item_weights:
                types = list(self.item_weights.keys())
                weights = list(self.item_weights.values())
                item_type = random.choices(types, weights=weights)[0]
            else:
                item_type = random.choice(list(ItemType))
        
        if pos is None:
            pos = random.choice(self.item_spawn_points)
        
        item_class = self.get_item_class(item_type)
        if item_class is None:
            return None
        
        item = item_class(self.next_item_id, pos[0], pos[1])
        self.next_item_id += 1
        self.items[item.id] = item
        return item
    
    def spawn_items(self, count: int = 10):
        """生成多个道具"""
        for _ in range(count):
            self.spawn_item()
    
    def spawn_all_types(self):
        """确保每种道具类型都至少生成一个，每个位置都不同"""
        available_types = list(ItemType)
        used_positions = set()
        
        for item_type in available_types:
            attempts = 0
            while attempts < 50:
                pos = random.choice(self.item_spawn_points)
                pos_key = (int(pos[0] / 50), int(pos[1] / 50))
                
                if pos_key not in used_positions:
                    self.spawn_item(item_type=item_type, pos=pos)
                    used_positions.add(pos_key)
                    break
                attempts += 1
            else:
                pos = random.choice(self.item_spawn_points)
                self.spawn_item(item_type=item_type, pos=pos)
        
        extra_items = 6
        for _ in range(extra_items):
            attempts = 0
            while attempts < 30:
                pos = random.choice(self.item_spawn_points)
                pos_key = (int(pos[0] / 50), int(pos[1] / 50))
                
                if pos_key not in used_positions:
                    self.spawn_item(pos=pos)
                    used_positions.add(pos_key)
                    break
                attempts += 1
            else:
                self.spawn_item()
    
    def get_item_class(self, item_type: ItemType):
        """获取道具类型对应的类"""
        mapping = {
            ItemType.HEALTH_PACK: HealthPack,
            ItemType.AMMO_BOX: AmmoBox,
            ItemType.ARMOR: Armor,
            ItemType.SPEED_BOOST: SpeedBoost,
            ItemType.DAMAGE_BOOST: DamageBoost,
            ItemType.GRENADE: Grenade,
        }
        return mapping.get(item_type)
    
    def check_pickup(self, player: 'Player') -> Optional[Dict]:
        """检查玩家是否拾取道具"""
        pickup_radius = PLAYER_RADIUS + 15
        
        for item in self.items.values():
            if not item.can_pickup(player.id):
                continue
            
            distance = player.pos.distance_to(item.pos)
            if distance <= pickup_radius:
                print(f"[DEBUG] 拾取道具: {item.NAME}, 距离: {distance:.1f}, 半径: {pickup_radius}")
                result = item.pickup(player)
                print(f"[DEBUG] pickup结果: {result}")
                return result
        
        return None
    
    def check_grenade_throw(self, player: 'Player', target_pos: pygame.Vector2,
                           game_map, players: Dict) -> List[Dict]:
        """检查手雷投掷效果 - 带墙壁反弹和视线检测"""
        if getattr(player, 'grenades', 0) <= 0:
            return []
        
        player.grenades -= 1
        
        explosion_radius = Grenade.EXPLOSION_RADIUS
        explosion_damage = Grenade.DAMAGE
        throw_speed = Grenade.THROW_SPEED
        bounce_count = Grenade.BOUNCE_COUNT
        
        final_pos = self._simulate_grenade_path(
            player.pos, target_pos, game_map, throw_speed, bounce_count
        )
        
        targets = []
        for other_id, other_player in players.items():
            if other_id == player.id or other_player.is_dead:
                continue
            
            if not self._has_line_of_sight(final_pos, other_player.pos, game_map):
                continue
            
            distance = final_pos.distance_to(other_player.pos)
            if distance <= explosion_radius:
                damage_ratio = 1 - (distance / explosion_radius)
                damage = int(explosion_damage * max(0.1, damage_ratio))
                targets.append({
                    'target_id': other_id,
                    'damage': damage,
                    'attacker_id': player.id,
                    'type': 'grenade',
                    'explosion_pos': (final_pos.x, final_pos.y)
                })
        
        return targets
    
    def _simulate_grenade_path(self, start_pos: pygame.Vector2, target_pos: pygame.Vector2,
                                 game_map, throw_speed: float, max_bounces: int) -> pygame.Vector2:
        """模拟手雷轨迹，计算反弹后的最终位置"""
        direction = (target_pos - start_pos).normalize()
        current_pos = pygame.Vector2(start_pos)
        velocity = direction * throw_speed
        gravity = 200
        dt = 0.05
        
        walls = getattr(game_map, 'walls', [])
        
        for bounce in range(max_bounces):
            steps = int(3.0 / dt)
            for step in range(steps):
                velocity.y += gravity * dt
                new_pos = current_pos + velocity * dt
                
                for wall in walls:
                    if wall.collidepoint(new_pos.x, new_pos.y):
                        if abs(velocity.x) > abs(velocity.y):
                            velocity.x *= -0.6
                        else:
                            velocity.y *= -0.6
                        new_pos = current_pos
                        break
                
                current_pos = new_pos
            
            if velocity.length() < 50:
                break
        
        return current_pos
    
    def _has_line_of_sight(self, from_pos: pygame.Vector2, to_pos: pygame.Vector2,
                            game_map) -> bool:
        """检查两点之间是否有视线（不穿过墙壁）"""
        walls = getattr(game_map, 'walls', [])
        doors = getattr(game_map, 'doors', [])
        
        obstacles = list(walls) + [d.rect for d in doors]
        
        for obstacle in obstacles:
            if self._line_intersects_rect(from_pos, to_pos, obstacle):
                return False
        
        return True
    
    def _line_intersects_rect(self, p1: pygame.Vector2, p2: pygame.Vector2, rect: pygame.Rect) -> bool:
        """检查线段是否与矩形相交"""
        if rect.left <= p1.x <= rect.right and rect.top <= p1.y <= rect.bottom:
            return True
        if rect.left <= p2.x <= rect.right and rect.top <= p2.y <= rect.bottom:
            return True
        
        left = rect.left
        right = rect.right
        top = rect.top
        bottom = rect.bottom
        
        if self._line_intersects_line(p1, p2, pygame.Vector2(left, top), pygame.Vector2(right, top)):
            return True
        if self._line_intersects_line(p1, p2, pygame.Vector2(right, top), pygame.Vector2(right, bottom)):
            return True
        if self._line_intersects_line(p1, p2, pygame.Vector2(right, bottom), pygame.Vector2(left, bottom)):
            return True
        if self._line_intersects_line(p1, p2, pygame.Vector2(left, bottom), pygame.Vector2(left, top)):
            return True
        
        return False
    
    def _line_intersects_line(self, p1: pygame.Vector2, p2: pygame.Vector2,
                               p3: pygame.Vector2, p4: pygame.Vector2) -> bool:
        """检查两条线段是否相交"""
        def ccw(a, b, c):
            return (c.y - a.y) * (b.x - a.x) > (b.y - a.y) * (c.x - a.x)
        
        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)
    
    def update(self, dt: float):
        """更新所有道具"""
        for item in self.items.values():
            item.update(dt)
    
    def get_active_items(self) -> List[Item]:
        """获取所有活跃道具"""
        return [item for item in self.items.values() if item.is_active]
    
    def get_state(self) -> Dict:
        """获取所有道具状态（网络同步）"""
        return {
            'items': [item.get_state() for item in self.items.values()]
        }
    
    def set_state(self, state: Dict):
        """设置道具状态（网络同步）"""
        items_data = state.get('items', [])
        
        existing_ids = {item.id for item in self.items.values()}
        new_ids = {item['id'] for item in items_data}
        
        for item_data in items_data:
            item_id = item_data['id']
            if item_id in existing_ids:
                item = self.items.get(item_id)
                if item:
                    # 如果本地道具已经不活跃（刚被拾取），不要用旧状态覆盖
                    if not item.is_active and item_data.get('is_active', True):
                        continue
                    item.is_active = item_data.get('is_active', True)
                    item.respawn_time_remaining = item_data.get('respawn_time_remaining', 0)
                    item.pos = pygame.Vector2(item_data.get('pos', [0, 0]))
            else:
                item = Item.from_state(item_data)
                if item:
                    self.items[item.id] = item
        
        for item_id in existing_ids - new_ids:
            if item_id in self.items:
                del self.items[item_id]
    
    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2,
             player_pos: pygame.Vector2 = None, player_angle: float = None,
             walls: List = None, doors: List = None, is_aiming: bool = False):
        """绘制所有活跃道具"""
        for item in self.items.values():
            item.draw(surface, camera_offset, player_pos, player_angle, walls, doors, is_aiming)


def create_default_item_manager() -> ItemManager:
    """创建默认的道具管理器"""
    manager = ItemManager()
    
    weights = {
        ItemType.HEALTH_PACK: 0.35,
        ItemType.AMMO_BOX: 0.25,
        ItemType.ARMOR: 0.15,
        ItemType.SPEED_BOOST: 0.10,
        ItemType.DAMAGE_BOOST: 0.10,
        ItemType.GRENADE: 0.15,
    }
    manager.set_spawn_weights(weights)
    
    return manager
