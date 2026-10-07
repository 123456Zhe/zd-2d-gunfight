import math
import pygame
import random
from pygame.locals import *
from constants import *
from audio import audio

# 门开度小于这个值时自动回位到关闭（由角度换算成开度比例）
DOOR_SELF_CLOSE_PROGRESS = DOOR_SELF_CLOSE_ANGLE / DOOR_OPEN_ANGLE if DOOR_OPEN_ANGLE else 0.0


def rotate_vector(vec, degrees):
    """按角度（角度制，屏幕坐标系）旋转二维向量"""
    rad = math.radians(degrees)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    return pygame.Vector2(vec.x * cos_a - vec.y * sin_a, vec.x * sin_a + vec.y * cos_a)


def segment_intersection(p1, p2, p3, p4):
    """两条线段的交点，不相交返回 None"""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-9:
        return None
    
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
    
    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        return pygame.Vector2(x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    return None




DOOR_SOUND_LISTENER = None  # 本地玩家世界坐标（Game 每帧设置），用于门音效距离衰减


def _play_door_sound(name, pos):
    """播放门音效：按门与本地玩家的距离衰减，听不到远处的门"""
    listener = None
    if DOOR_SOUND_LISTENER is not None:
        listener = (DOOR_SOUND_LISTENER.x, DOOR_SOUND_LISTENER.y)
    audio.play(name, pos=(pos.x, pos.y), listener_pos=listener, max_dist=700.0)


class Door:
    """门类，管理门的状态、动画和交互

    门板绕墙体厚度中线上的铰链旋转，因此可以向墙体两侧任意推开（双向门）。
    animation_progress 取值 -1.0 ~ 1.0：0 为关闭，+1/-1 分别为两个方向完全打开。
    手动推门带加速度与阻尼，松开后靠惯性继续摆动。
    """
    def __init__(self, x, y, width, height, is_vertical=False, swing=1):
        self.original_rect = pygame.Rect(x, y, width, height)
        self.rect = pygame.Rect(x, y, width, height)
        self.is_vertical = is_vertical  # True 时门板沿 X 轴横跨门洞（位于水平墙上）
        self.swing = 1 if swing >= 0 else -1  # 铰链在门洞的哪一端
        self.is_open = False  # 门是否完全打开
        self.is_opening = False  # 门是否正在自动打开
        self.is_closing = False  # 门是否正在自动关闭
        self.animation_progress = 0.0  # 开门程度 (-1.0 - 1.0)
        self.swing_velocity = 0.0  # 手动推门时的角速度（进度/秒）
        self.is_being_pushed = False  # 本帧是否有人正在推（用于自动回位判定）
        self.interaction_cooldown = 0.5  # 交互冷却时间(秒)
        self.last_interaction_time = -999.0  # 上次交互时间（初始允许立即交互）
        self.state_version = 0  # 门状态版本号，用于同步
        self.angle = 0.0  # 门板当前旋转角度
        self._init_hinge()
        self.update_rect()
    
    def _init_hinge(self):
        """计算铰链位置与门板的局部坐标轴

        铰链位于门洞一端的墙体厚度中线上，门板厚度以铰链线为中心各占一半，
        这样朝两侧旋转都不会穿进墙体。base_dir 沿门板长度方向，
        base_normal 沿厚度方向。
        """
        rect = self.original_rect
        
        if self.is_vertical:
            # 门板沿 X 轴横跨门洞，墙体厚度在 Y 轴
            self.panel_length = float(rect.width)
            self.panel_thickness = float(rect.height)
            hinge_x = rect.x if self.swing > 0 else rect.right
            hinge_y = rect.centery
            direction = 1.0 if self.swing > 0 else -1.0
            self.base_dir = pygame.Vector2(direction, 0)
            self.base_normal = pygame.Vector2(0, 1)
        else:
            # 门板沿 Y 轴横跨门洞，墙体厚度在 X 轴
            self.panel_length = float(rect.height)
            self.panel_thickness = float(rect.width)
            hinge_x = rect.centerx
            hinge_y = rect.y if self.swing > 0 else rect.bottom
            direction = 1.0 if self.swing > 0 else -1.0
            self.base_dir = pygame.Vector2(0, direction)
            self.base_normal = pygame.Vector2(1, 0)
        
        self.hinge = pygame.Vector2(hinge_x, hinge_y)
        self.angle = 0.0
    
    def get_corners(self):
        """返回门板四个角的世界坐标（随动画旋转）"""
        direction = rotate_vector(self.base_dir, self.angle)
        normal = rotate_vector(self.base_normal, self.angle)
        half_thickness = normal * (self.panel_thickness / 2)
        near_a = self.hinge - half_thickness
        near_b = self.hinge + half_thickness
        span = direction * self.panel_length
        return [near_a, near_a + span, near_b + span, near_b]
    
    def update(self, dt):
        """更新门的状态和动画"""
        if self.is_opening:
            target = 1.0 if self.animation_progress >= 0 else -1.0
            step = dt * DOOR_ANIMATION_SPEED
            if target > 0:
                self.animation_progress = min(target, self.animation_progress + step)
            else:
                self.animation_progress = max(target, self.animation_progress - step)
            if abs(self.animation_progress) >= 1.0:
                self.animation_progress = target
                self.is_opening = False
                self.is_open = True
        elif self.is_closing:
            step = dt * DOOR_ANIMATION_SPEED
            if self.animation_progress > 0:
                self.animation_progress = max(0.0, self.animation_progress - step)
            else:
                self.animation_progress = min(0.0, self.animation_progress + step)
            if abs(self.animation_progress) < 1e-9:
                self.animation_progress = 0.0
                self.is_closing = False
                self.is_open = False
        else:
            self._update_swing(dt)
        
        self.is_being_pushed = False
        
        # 更新门板的旋转角度与包围盒
        self.update_rect()
    
    def _update_swing(self, dt):
        """按惯性推进门板，速度按指数衰减"""
        # 只在门几乎停下且开度很小时自动回位到关闭。
        # 必须带速度门槛，否则刚被推开的门会在小角度区被直接刹停，失去惯性。
        if (not self.is_being_pushed
                and abs(self.animation_progress) < DOOR_SELF_CLOSE_PROGRESS
                and abs(self.swing_velocity) < DOOR_SELF_CLOSE_VELOCITY):
            self.swing_velocity = 0.0
            self.animation_progress *= math.exp(-DOOR_SELF_CLOSE_SPEED * dt)
            if abs(self.animation_progress) < 1e-3:
                self.animation_progress = 0.0
            self.is_open = False
            return
        
        if self.swing_velocity == 0.0:
            return
        
        self.animation_progress += self.swing_velocity * dt
        
        if self.animation_progress >= 1.0:
            if abs(self.swing_velocity) > DOOR_SLAM_VELOCITY:
                _play_door_sound('door_slam', self.hinge)
            self.animation_progress = 1.0
            self.swing_velocity = 0.0
        elif self.animation_progress <= -1.0:
            if abs(self.swing_velocity) > DOOR_SLAM_VELOCITY:
                _play_door_sound('door_slam', self.hinge)
            self.animation_progress = -1.0
            self.swing_velocity = 0.0
        else:
            self.swing_velocity *= math.exp(-DOOR_DAMPING * dt)
            if abs(self.swing_velocity) < 1e-4:
                self.swing_velocity = 0.0
            
            # 快到位又几乎停下时吸附到全开，避免停在 149 度这种尴尬位置
            if (not self.is_being_pushed
                    and abs(self.swing_velocity) < DOOR_SELF_CLOSE_VELOCITY
                    and abs(self.animation_progress) > 1.0 - DOOR_SELF_CLOSE_PROGRESS):
                self.animation_progress = math.copysign(1.0, self.animation_progress)
                self.swing_velocity = 0.0
        
        self.is_open = abs(self.animation_progress) >= 1.0
    
    def update_rect(self):
        """根据动画进度更新门板旋转角度与包围盒"""
        self.angle = self.animation_progress * DOOR_OPEN_ANGLE
        
        corners = self.get_corners()
        left = int(math.floor(min(point.x for point in corners)))
        top = int(math.floor(min(point.y for point in corners)))
        right = int(math.ceil(max(point.x for point in corners)))
        bottom = int(math.ceil(max(point.y for point in corners)))
        
        # 原地修改，保持外部持有的 rect 引用有效
        self.rect.x = left
        self.rect.y = top
        self.rect.width = max(1, right - left)
        self.rect.height = max(1, bottom - top)
    
    def get_obb(self):
        """返回门板的定向包围盒：(中心, 长度轴, 厚度轴, 半长, 半厚)"""
        direction = rotate_vector(self.base_dir, self.angle)
        normal = rotate_vector(self.base_normal, self.angle)
        center = self.hinge + direction * (self.panel_length / 2)
        return center, direction, normal, self.panel_length / 2, self.panel_thickness / 2
    
    def in_interaction_range(self, player_pos):
        """玩家是否处于可以操作这扇门的范围内"""
        interaction_range = PLAYER_RADIUS * 3  # 交互范围
        door_center = pygame.Vector2(self.original_rect.centerx, self.original_rect.centery)
        distance = (door_center - player_pos).length()
        return distance <= interaction_range + max(self.original_rect.width, self.original_rect.height) / 2
    
    def try_interact(self, player_pos):
        """切换门状态（自动播放动画），返回是否成功交互"""
        current_time = pygame.time.get_ticks() / 1000
        
        # 检查是否在冷却时间内
        if current_time - self.last_interaction_time < self.interaction_cooldown:
            return False
        
        if not self.in_interaction_range(player_pos):
            return False
        
        self.last_interaction_time = current_time
        
        # 切换门的状态
        if self.is_open or self.is_opening:
            return self.close()
        return self.open()
    
    def open(self):
        """开始自动播放开门动画"""
        if abs(self.animation_progress) >= 1.0:
            return False
        self.is_opening = True
        self.is_closing = False
        self.swing_velocity = 0.0
        self.state_version += 1
        _play_door_sound('door_open', self.hinge)
        return True
    
    def close(self):
        """开始自动播放关门动画"""
        if abs(self.animation_progress) <= 0.0:
            return False
        self.is_closing = True
        self.is_opening = False
        self.swing_velocity = 0.0
        self.state_version += 1
        _play_door_sound('door_close', self.hinge)
        return True
    
    def apply_push(self, direction, dt):
        """手动推门：direction > 0 推向一侧，< 0 推向另一侧

        不断累加速度而不是直接设置位置，因此松手后门会靠惯性继续摆动。
        """
        if direction == 0:
            return
        
        self.is_opening = False
        self.is_closing = False
        self.is_being_pushed = True
        
        self.swing_velocity += direction * DOOR_PUSH_ACCEL * dt
        self.swing_velocity = max(-DOOR_MAX_SPEED, min(DOOR_MAX_SPEED, self.swing_velocity))
        self.state_version += 1
    
    def push_sign_for_player(self, player_angle):
        """玩家按“左”推门时应传给 apply_push 的 direction 符号（+1/-1）

        计算门板自由端在 direction=+1 时的运动方向：若朝向玩家左侧则返回 +1，
        这样无论站在门的哪一侧，“按左”都让门板往自己的左侧摆，直觉一致。
        """
        tangent = (rotate_vector(self.base_dir, self.angle + 2.0)
                   - rotate_vector(self.base_dir, self.angle))
        rad = math.radians(player_angle + 90.0)
        left = pygame.Vector2(math.cos(rad), -math.sin(rad))
        return 1 if tangent.dot(left) >= 0 else -1

    def nearest_corner_distance(self, pos):
        """位置到门板四个端点的最近距离"""
        return min(pos.distance_to(corner) for corner in self.get_corners())
    
    def check_collision(self, rect):
        """门板与矩形是否重叠：始终按当前旋转后的门板形状判定"""
        center, axis_u, axis_v, half_u, half_v = self.get_obb()
        rect_center = pygame.Vector2(rect.centerx, rect.centery)
        half_w = rect.width / 2
        half_h = rect.height / 2
        
        for axis in ((1.0, 0.0), (0.0, 1.0), (axis_u.x, axis_u.y), (axis_v.x, axis_v.y)):
            ax, ay = axis
            rect_radius = half_w * abs(ax) + half_h * abs(ay)
            door_radius = (
                half_u * abs(axis_u.x * ax + axis_u.y * ay)
                + half_v * abs(axis_v.x * ax + axis_v.y * ay)
            )
            distance = abs(
                (rect_center.x - center.x) * ax + (rect_center.y - center.y) * ay
            )
            if distance > rect_radius + door_radius:
                return False
        return True
    
    def resolve_circle(self, center, radius):
        """圆形实体与门板重叠时返回推开后的圆心，否则返回 None"""
        obb_center, axis_u, axis_v, half_u, half_v = self.get_obb()
        delta = center - obb_center
        local_u = delta.dot(axis_u)
        local_v = delta.dot(axis_v)
        
        clamped_u = max(-half_u, min(half_u, local_u))
        clamped_v = max(-half_v, min(half_v, local_v))
        offset_u = local_u - clamped_u
        offset_v = local_v - clamped_v
        distance = math.hypot(offset_u, offset_v)
        
        # 相切（距离恰好等于半径）不算重叠，避免推出后反复微调
        if distance >= radius - 1e-6:
            return None
        
        if distance > 1e-6:
            push_local = pygame.Vector2(offset_u / distance, offset_v / distance)
            penetration = radius - distance
        else:
            # 圆心落在门板内部：沿穿透最浅的轴推出
            pen_u = half_u - abs(local_u)
            pen_v = half_v - abs(local_v)
            if pen_u <= pen_v:
                push_local = pygame.Vector2(1.0 if local_u >= 0 else -1.0, 0.0)
                penetration = pen_u + radius
            else:
                push_local = pygame.Vector2(0.0, 1.0 if local_v >= 0 else -1.0)
                penetration = pen_v + radius
        
        direction = axis_u * push_local.x + axis_v * push_local.y
        return center + direction * penetration
    
    def line_intersection(self, start, end):
        """线段与门板的最近交点，没有交点返回 None"""
        # 先用包围盒快速排除（Rect.clipline 是 C 实现）
        if not self.rect.clipline((start[0], start[1]), (end[0], end[1])):
            return None
        
        corners = self.get_corners()
        closest = None
        min_distance = float("inf")
        start_vec = pygame.Vector2(start)
        
        for index in range(4):
            point = segment_intersection(
                start, end, corners[index], corners[(index + 1) % 4]
            )
            if point is not None:
                distance = start_vec.distance_to(point)
                if distance < min_distance:
                    min_distance = distance
                    closest = point
        return closest
    
    def line_intersects(self, start, end):
        """线段是否与门板相交"""
        return self.line_intersection(start, end) is not None
    
    def get_state(self):
        """获取当前门状态"""
        return {
            'is_open': self.is_open,
            'is_opening': self.is_opening,
            'is_closing': self.is_closing,
            'animation_progress': self.animation_progress,
            'swing_velocity': self.swing_velocity,
            'version': self.state_version
        }
    
    def set_state(self, state):
        """设置门状态"""
        # 只有版本号更高的状态才会被应用
        if 'version' in state and state['version'] > self.state_version:
            self.is_open = state.get('is_open', False)
            self.is_opening = state.get('is_opening', False)
            self.is_closing = state.get('is_closing', False)
            self.animation_progress = max(
                -1.0, min(1.0, state.get('animation_progress', 0.0))
            )
            # 同步角速度，让远端也按同样的惯性继续摆动；钳制防恶意超速
            self.swing_velocity = max(
                -DOOR_MAX_SPEED,
                min(DOOR_MAX_SPEED, state.get('swing_velocity', 0.0)),
            )
            self.state_version = state['version']
            self.update_rect()
            return True
        return False
    
    def get_color(self, in_fog=False):
        """门始终使用木色，开到位也不变色"""
        if in_fog:
            return DARK_DOOR_COLOR
        return DOOR_COLOR

MAP_TYPES = ("grid3x3", "arena")


class Map:
    """游戏地图类。

    map_type:
    - "grid3x3": 3x3 九宫格房间 + 门（原有地图，默认，保持向后兼容）
    - "arena":   同尺寸开放式竞技场，只有外墙与散布掩体，没有房间分隔
    """
    def __init__(self, map_type="grid3x3"):
        if map_type not in MAP_TYPES:
            raise ValueError(f"未知地图类型: {map_type}，可选 {MAP_TYPES}")
        self.map_type = map_type
        self.rooms = []
        self.doors = []
        self.walls = []
        self.door_positions = []
        self.generate_map()

    def generate_map(self):
        """生成地图。所有类型都保留 3x3 分区单元（供出生点与道具分布使用）"""
        # 创建3x3房间网格单元
        for row in range(3):
            for col in range(3):
                x = col * ROOM_SIZE
                y = row * ROOM_SIZE
                self.rooms.append(pygame.Rect(x, y, ROOM_SIZE, ROOM_SIZE))

        if self.map_type == "arena":
            self.generate_arena()
        else:
            self.generate_doors()
            self.generate_walls()

    def generate_arena(self):
        """开放式竞技场：外墙 + 中央十字 + 四角/四边掩体，各区域彼此连通。

        相比九宫格没有分隔墙与门，交战密度高得多，适合训练对战 AI。
        """
        size = ROOM_SIZE * 3
        t = WALL_THICKNESS
        cx = cy = size // 2

        # 外墙
        self.walls.append(pygame.Rect(0, 0, size, t))
        self.walls.append(pygame.Rect(0, size - t, size, t))
        self.walls.append(pygame.Rect(0, 0, t, size))
        self.walls.append(pygame.Rect(size - t, 0, t, size))

        # 中央十字掩体
        arm, thick = 300, 70
        self.walls.append(pygame.Rect(cx - arm, cy - thick // 2, arm * 2, thick))
        self.walls.append(pygame.Rect(cx - thick // 2, cy - arm, thick, arm * 2))

        # 四角方形掩体
        block, inset = 150, 300
        for ox in (inset, size - inset - block):
            for oy in (inset, size - inset - block):
                self.walls.append(pygame.Rect(ox, oy, block, block))

        # 四边中部掩体
        edge_len, edge_thick, edge_margin = 280, 80, 150
        self.walls.append(
            pygame.Rect(cx - edge_thick // 2, edge_margin, edge_thick, edge_len))
        self.walls.append(
            pygame.Rect(cx - edge_thick // 2, size - edge_margin - edge_len,
                        edge_thick, edge_len))
        self.walls.append(
            pygame.Rect(edge_margin, cy - edge_thick // 2, edge_len, edge_thick))
        self.walls.append(
            pygame.Rect(size - edge_margin - edge_len, cy - edge_thick // 2,
                        edge_len, edge_thick))

        self.doors = []
        self.door_positions = []
    
    def generate_doors(self):
        """生成门并记录位置"""
        # 水平方向的门（左右连接房间）
        for row in range(3):
            for col in range(2):
                door_x = (col + 1) * ROOM_SIZE - WALL_THICKNESS
                door_y = row * ROOM_SIZE + (ROOM_SIZE - DOOR_SIZE) // 2
                swing = 1 if (row + col) % 2 == 0 else -1
                
                door = Door(door_x, door_y, WALL_THICKNESS, DOOR_SIZE, is_vertical=False, swing=swing)
                self.doors.append(door)
                self.door_positions.append(door.original_rect)
        
        # 垂直方向的门（上下连接房间）
        for row in range(2):
            for col in range(3):
                door_x = col * ROOM_SIZE + (ROOM_SIZE - DOOR_SIZE) // 2
                door_y = (row + 1) * ROOM_SIZE - WALL_THICKNESS
                swing = 1 if (row + col) % 2 == 0 else -1
                
                door = Door(door_x, door_y, DOOR_SIZE, WALL_THICKNESS, is_vertical=True, swing=swing)
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
    
    def draw(self, screen, camera, in_fog=False):
        """绘制地图"""
        # 绘制墙壁（随相机旋转，按多边形绘制）
        for wall in self.walls:
            corners = (
                (wall.left, wall.top),
                (wall.right, wall.top),
                (wall.right, wall.bottom),
                (wall.left, wall.bottom),
            )
            pygame.draw.polygon(
                screen, DARK_GRAY if in_fog else GRAY, camera.to_screen_polygon(corners)
            )
        
        # 绘制门
        for door in self.doors:
            points = camera.to_screen_polygon(door.get_corners())
            pygame.draw.polygon(screen, door.get_color(in_fog), points)
            pygame.draw.polygon(screen, DARK_DOOR_COLOR, points, 1)