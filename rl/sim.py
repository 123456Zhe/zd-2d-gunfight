"""无头仿真环境。

把游戏的战斗逻辑（地图 / 移动碰撞 / 子弹 / 门 / 行为树 AI）从 main.py 的
Game 类中抽离出来，脱离渲染与网络，可高速步进，供强化学习训练使用。

关键设计：
- 所有战斗单位都复用 EnhancedAIPlayer：物理状态与线上完全一致，且自带你
  "教师 AI"；训练时它的物理状态就是策略载体，直接写入动作即可。
- 用 SimClock 替换 time.time()，使冷却与计时跟随仿真步进而非真实时间。
- 用静态占据网格做射线/LOS，避免每帧大量 pygame clipline 调用。

观测/动作接口见本文件顶部的常量定义。
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # 必须在 import pygame 之前

import math
import random

import numpy as np
import pygame

from constants import (
    ROOM_SIZE,
    PLAYER_SPEED,
    PLAYER_RADIUS,
    BULLET_RADIUS,
    BULLET_SPEED,
    BULLET_DAMAGE,
    BULLET_COOLDOWN,
    MAGAZINE_SIZE,
    RELOAD_TIME,
    RESPAWN_TIME,
)
from map import Map, MAP_TYPES
from utils import normalize_angle
from ai_player_enhanced import EnhancedAIPlayer
from ai_personality import AIPersonality, AIPersonalityTraits

from .clock import SimClock, patched_time

MAP_W = float(ROOM_SIZE * 3)
MAP_H = float(ROOM_SIZE * 3)

N_RAYS = 16
RAY_MAX = 600.0
N_ENEMIES = 3
ENEMY_FEATURES = 8

OBS_DIM = 7 + N_RAYS + N_ENEMIES * ENEMY_FEATURES  # 7 + 16 + 24 = 47
ACTION_DIM = 6  # [move_x, move_y, aim_cos, aim_sin, shoot, reload]

# 训练时让策略能感知的最大移动速度（动作前两位幅度 1.0 对应满速）
MOVE_REF_SPEED = float(PLAYER_SPEED)

# 占据网格分辨率（像素），用于射线与视线检测
GRID_CELL = 20
GRID_W = int(math.ceil(MAP_W / GRID_CELL))
GRID_H = int(math.ceil(MAP_H / GRID_CELL))

# 奖励权重
#
# 目标设计为“在被打死之前打死对手”：击杀 +1、阵亡 -1，配合密集的伤害塑形。
# 两个容易踩的坑：
# 1) 不要给“存活到超时”正奖励，否则策略会学会远远躲着不打；
# 2) 瞄准塑形必须很小，否则“枪口对着敌人绕圈但不开火”会成为更优的局部解。
R_DAMAGE_DEALT = 0.01
R_DAMAGE_TAKEN = 0.01
R_KILL = 1.0
R_WIN = 1.0
R_DEATH = -1.0
R_STEP = -0.0005
R_AIM = 0.0005
# 苟着扣分：长时间不交火（没打出伤害、也没有视线内的敌人）时按步累进扣分。
# 承伤与造成伤害同权重会把策略推向避战，单靠 gamma 修不回来，这里直接给
# "不交战"本身定个价。
R_CAMP = 0.001
R_CAMP_GRACE = 4.0
R_CAMP_MAX_MULT = 3.0
CAMP_SIGHT_RANGE = 600.0

_ZERO = pygame.Vector2(0, 0)


def resolve_map_type(map_type, rng):
    """把 "random" 解析为具体地图类型（每局重新采样）。"""
    if map_type == "random":
        return rng.choice(list(MAP_TYPES))
    return map_type


class Projectile:
    __slots__ = ("owner_id", "pos", "direction", "speed")

    def __init__(self, owner_id, pos, direction, speed):
        self.owner_id = owner_id
        self.pos = pygame.Vector2(pos)
        self.direction = pygame.Vector2(direction)
        self.speed = speed


class HeadlessSim:
    """一局对战的纯逻辑仿真。

    默认 1 个受控单位（learner，槽位 0）对 N 个脚本 AI。
    """

    dt = 1.0 / 60.0

    def __init__(self, n_opponents=1, opponent_difficulty="normal",
                 max_episode_steps=1800, opponent_personalities=None, seed=None,
                 map_type="grid3x3", learner_personality="aggressive",
                 opponent_respawn=False, opponent_hp_fraction=1.0,
                 reward_overrides=None):
        self.n_opponents = int(n_opponents)
        self.opponent_difficulty = opponent_difficulty
        self.max_episode_steps = int(max_episode_steps)
        self.opponent_respawn = bool(opponent_respawn)
        # 课程学习杠杆：把对手血量打折，让学员先学会“赢”，再逐步加回强度。
        # difficulty 本身是生效的（reaction_time 限制开火延迟、accuracy 叠加瞄准
        # 误差），但三档跨度很大：close 出生 40 局实测 easy/normal/hard 的对手
        # 平均开火 0.1/0.5/2.9 次，学员胜率 0.93/0.90/0.38。用血量做课程更平滑。
        self.opponent_hp_fraction = float(opponent_hp_fraction)
        self._opponent_personalities = opponent_personalities
        self.map_type = map_type
        self.current_map_type = None
        try:
            self.learner_personality = AIPersonality(learner_personality)
        except ValueError:
            self.learner_personality = AIPersonality.AGGRESSIVE
        self._rng = random.Random(seed)

        self.learner_id = 0
        self.map = None
        self.agents = {}
        self.projectiles = []
        self.learner = None
        self.opponents = {}
        # 自对弈：给对手挂一个 obs -> action 的策略快照，替代脚本行为树
        self.selfplay_policy = None
        self.clock = SimClock()

        self.steps = 0
        self._done = False
        self._grid = bytearray(GRID_W * GRID_H)
        self._door_sig = None
        self._static_walls = []

        self.episode_damage_dealt = 0.0
        self.episode_damage_taken = 0.0
        self.episode_kills = 0
        self.episode_deaths = 0

        # 单步内的战斗事件计数（用于把伤害/击杀换算成本步奖励）
        self._step_dealt = 0.0
        self._step_taken = 0.0
        self._step_kills = 0
        self.episode_shots = 0
        self._steps_since_engage = 0

        # 奖励权重允许按实例覆盖：评估与 BC 采集沿用模块级默认值，
        # 训练侧可以单独调（gamma 修好后"承伤 -> 避战"仍需降权）。
        self.reward = {
            "win": R_WIN,
            "kill": R_KILL,
            "death": R_DEATH,
            "step": R_STEP,
            "aim": R_AIM,
            "damage_dealt": R_DAMAGE_DEALT,
            "damage_taken": R_DAMAGE_TAKEN,
            "camp_penalty": R_CAMP,
            "camp_grace": R_CAMP_GRACE,
            "camp_max_mult": R_CAMP_MAX_MULT,
        }
        if reward_overrides:
            self.reward.update(
                {k: float(v) for k, v in reward_overrides.items() if v is not None}
            )

    # ------------------------------------------------------------------ 生命周期

    def reset(self, seed=None, n_opponents=None, opponent_difficulty=None,
              spawn_mode="spread", map_type=None, selfplay_policy=None):
        """spawn_mode:
        - "spread": 各自随机房间（贴近真实对局，但交战稀疏）
        - "close":  双方同房出生（交战密集，采样效率高）
        - "mixed":  各半

        map_type: "grid3x3" / "arena" / "random"（每局随机）
        """
        if seed is not None:
            self._rng = random.Random(seed)
            random.seed(seed)
            np.random.seed(seed & 0xFFFFFFFF)
        if n_opponents is not None:
            self.n_opponents = int(n_opponents)
        if opponent_difficulty is not None:
            self.opponent_difficulty = opponent_difficulty

        self.clock = SimClock(1000.0)
        self.current_map_type = resolve_map_type(
            self.map_type if map_type is None else map_type, self._rng
        )
        self.map = Map(self.current_map_type)
        self._static_walls = list(self.map.walls)
        self._build_grid()
        self._door_sig = None
        self.projectiles = []
        self.steps = 0
        self._done = False
        self.episode_damage_dealt = 0.0
        self.episode_damage_taken = 0.0
        self.episode_kills = 0
        self.episode_deaths = 0
        self._step_dealt = 0.0
        self._step_taken = 0.0
        self._step_kills = 0
        self.episode_shots = 0
        self._steps_since_engage = 0

        rooms = list(range(9))
        self._rng.shuffle(rooms)
        learner_room = rooms[0]

        if spawn_mode == "mixed":
            spawn_mode = "close" if self._rng.random() < 0.5 else "spread"

        self.agents = {}
        self.opponents = {}

        placed = []
        lx, ly = self._spawn_pos(learner_room, placed, 0.0)
        placed.append((lx, ly))
        self.learner = self._make_agent(
            self.learner_id, lx, ly, "hard", self.learner_personality
        )
        self.agents[self.learner_id] = self.learner

        personalities = self._opponent_personalities
        for i in range(self.n_opponents):
            aid = 100 + i
            if spawn_mode == "close":
                room = learner_room
            else:
                room = rooms[(i + 1) % len(rooms)]
            x, y = self._spawn_pos(room, placed, 250.0)
            placed.append((x, y))
            if personalities:
                pers = personalities[i % len(personalities)]
            else:
                pers = None
            agent = self._make_agent(aid, x, y, self.opponent_difficulty, pers)
            self.agents[aid] = agent
            self.opponents[aid] = agent

        self.selfplay_policy = selfplay_policy
        self._apply_opponent_hp(full=True)

        return self.obs()

    def set_opponent_hp_fraction(self, fraction):
        """课程学习：运行中动态调整对手血量系数（对已存在的对手立即生效）。"""
        self.opponent_hp_fraction = max(0.05, float(fraction))
        self._apply_opponent_hp(full=False)

    def _apply_opponent_hp(self, full):
        for agent in self.opponents.values():
            agent.max_health = max(1.0, 100.0 * self.opponent_hp_fraction)
            if full:
                agent.health = agent.max_health
            else:
                agent.health = min(agent.health, agent.max_health)

    def _make_agent(self, agent_id, x, y, difficulty, personality):
        if isinstance(personality, str):
            try:
                personality = AIPersonality(personality)
            except ValueError:
                personality = None
        if personality is None:
            traits = AIPersonalityTraits.random_personality()
        elif isinstance(personality, AIPersonalityTraits):
            traits = personality
        else:
            traits = AIPersonalityTraits(personality)
        agent = EnhancedAIPlayer(agent_id, x, y, difficulty, traits)
        agent.generate_patrol_points(self.map)  # 建立导航网格 + door_positions
        # 线上这些字段存在网络数据里，无头仿真直接挂到对象上
        agent.shooting = False
        return agent

    def _spawn_pos(self, room, placed=None, min_dist=0.0):
        row, col = divmod(room, 3)
        cx = col * ROOM_SIZE + ROOM_SIZE // 2
        cy = row * ROOM_SIZE + ROOM_SIZE // 2
        placed = placed or []
        best = None
        best_gap = -1.0
        for _ in range(60):
            x = cx + self._rng.uniform(-ROOM_SIZE * 0.3, ROOM_SIZE * 0.3)
            y = cy + self._rng.uniform(-ROOM_SIZE * 0.3, ROOM_SIZE * 0.3)
            if not self._free(pygame.Vector2(x, y)):
                continue
            if placed:
                gap = min(math.hypot(x - px, y - py) for px, py in placed)
                if gap < min_dist:
                    if gap > best_gap:
                        best, best_gap = (x, y), gap
                    continue
            return x, y
        if best is not None:
            return best
        return float(cx), float(cy)

    # ------------------------------------------------------------------ 占据网格

    def _build_grid(self):
        grid = bytearray(GRID_W * GRID_H)
        for wall in self._static_walls:
            self._stamp_rect(grid, wall)
        for door in self.map.doors:
            if not (door.is_open or door.is_opening):
                self._stamp_rect(grid, door.rect)
        self._grid = grid

    @staticmethod
    def _stamp_rect(grid, rect):
        x0 = max(0, rect.left // GRID_CELL)
        x1 = min(GRID_W - 1, (rect.right - 1) // GRID_CELL)
        y0 = max(0, rect.top // GRID_CELL)
        y1 = min(GRID_H - 1, (rect.bottom - 1) // GRID_CELL)
        for gy in range(y0, y1 + 1):
            base = gy * GRID_W
            for gx in range(x0, x1 + 1):
                grid[base + gx] = 1

    def _refresh_grid_if_needed(self):
        sig = tuple(
            1 if (d.is_open or d.is_opening) else 0 for d in self.map.doors
        )
        if sig != self._door_sig:
            self._door_sig = sig
            self._build_grid()

    def _blocked_xy(self, x, y):
        if x < 0 or y < 0 or x >= MAP_W or y >= MAP_H:
            return True
        gx = int(x / GRID_CELL)
        gy = int(y / GRID_CELL)
        if gx >= GRID_W:
            gx = GRID_W - 1
        if gy >= GRID_H:
            gy = GRID_H - 1
        return self._grid[gy * GRID_W + gx] != 0

    def _ray_dist(self, ox, oy, angle_deg, max_d):
        rad = math.radians(angle_deg)
        dx = math.cos(rad)
        dy = -math.sin(rad)
        dist = 0.0
        while dist < max_d:
            dist += GRID_CELL
            if dist > max_d:
                dist = max_d
            if self._blocked_xy(ox + dx * dist, oy + dy * dist):
                return dist
        return max_d

    def _los_grid(self, ax, ay, bx, by):
        dx = bx - ax
        dy = by - ay
        seg = math.hypot(dx, dy)
        if seg < 1e-6:
            return True
        steps = int(seg / GRID_CELL)
        ux = dx / seg
        uy = dy / seg
        for i in range(1, steps):
            t = i * GRID_CELL
            if self._blocked_xy(ax + ux * t, ay + uy * t):
                return False
        return True

    # ------------------------------------------------------------------ 物理

    def _free(self, pos):
        rect = pygame.Rect(
            pos.x - PLAYER_RADIUS, pos.y - PLAYER_RADIUS,
            PLAYER_RADIUS * 2, PLAYER_RADIUS * 2,
        )
        for wall in self._static_walls:
            if rect.colliderect(wall):
                return False
        for door in self.map.doors:
            if door.check_collision(rect):
                return False
        return True

    def _apply_action(self, agent, action, dt):
        now = self.clock.t

        move_vec = action.get("move", _ZERO)
        if move_vec is None:
            move_vec = _ZERO

        # 移动：X/Y 分离，撞墙时沿墙滑动
        if agent.is_dead:
            move_vec = _ZERO
        else:
            delta_x = move_vec.x * dt
            delta_y = move_vec.y * dt
            if abs(delta_x) > 1e-9:
                test = pygame.Vector2(agent.pos.x + delta_x, agent.pos.y)
                if self._free(test):
                    agent.pos.x = test.x
            if abs(delta_y) > 1e-9:
                test = pygame.Vector2(agent.pos.x, agent.pos.y + delta_y)
                if self._free(test):
                    agent.pos.y = test.y

        agent.angle = float(action.get("angle", agent.angle))

        # 射击（受弹药 / 装填 / 冷却限制）
        fired = False
        want_shoot = bool(action.get("shoot", False))
        if (want_shoot and not agent.is_dead and not agent.is_reloading
                and agent.ammo > 0
                and (now - agent.last_shot_time) >= BULLET_COOLDOWN):
            rad = math.radians(agent.angle)
            direction = pygame.Vector2(math.cos(rad), -math.sin(rad))
            spawn = agent.pos + direction * (PLAYER_RADIUS + BULLET_RADIUS)
            self.projectiles.append(
                Projectile(agent.id, spawn, direction, BULLET_SPEED)
            )
            agent.ammo -= 1
            agent.last_shot_time = now
            fired = True
            if agent.id == self.learner_id:
                self.episode_shots += 1
        agent.shooting = fired

        # 装填
        if (action.get("reload", False) and not agent.is_dead
                and not agent.is_reloading and agent.ammo < MAGAZINE_SIZE):
            agent.is_reloading = True
            agent.reload_start_time = now
        # 打空自动换弹：与内置行为树 AI 一致。否则策略一旦忘记换弹就会彻底哑火，
        # 而“何时主动换弹”仍然留给策略学习（提前换弹能减少火力空窗）。
        if agent.ammo <= 0 and not agent.is_reloading and not agent.is_dead:
            agent.is_reloading = True
            agent.reload_start_time = now
        if agent.is_reloading and (now - agent.reload_start_time) >= RELOAD_TIME:
            agent.ammo = MAGAZINE_SIZE
            agent.is_reloading = False

        # 门交互（行为树 AI 会显式返回要开的门）
        door = action.get("interact_door")
        if door is not None and not door.is_open:
            door.open()

        # 声音状态（供对手听觉感知）
        moving = move_vec.length() > 0.1
        if fired:
            agent.is_making_sound = True
            agent.sound_volume = 1.0
        elif agent.is_reloading:
            agent.is_making_sound = True
            agent.sound_volume = 0.8
        elif moving:
            agent.is_making_sound = True
            agent.sound_volume = 0.3 if getattr(agent, "stealth_mode", False) else 1.0
        else:
            agent.is_making_sound = False
            agent.sound_volume = 0.0

        agent.is_walking = bool(
            action.get("is_walking", getattr(agent, "stealth_mode", False))
        )

    def _auto_open_doors(self):
        """靠近门自动开启，避免 AI 被门卡住（与游戏内自动门设定一致）。"""
        for door in self.map.doors:
            if door.is_open or door.is_opening:
                continue
            center = pygame.Vector2(door.original_rect.center)
            for agent in self.agents.values():
                if agent.is_dead:
                    continue
                if agent.pos.distance_to(center) < 70:
                    door.open()
                    break

    def _players_data(self):
        data = {}
        for aid, agent in self.agents.items():
            data[aid] = {
                "pos": [agent.pos.x, agent.pos.y],
                "angle": agent.angle,
                "health": agent.health,
                "is_dead": agent.is_dead,
                "shooting": agent.shooting,
                "is_reloading": agent.is_reloading,
                "is_walking": agent.is_walking,
                "is_making_sound": agent.is_making_sound,
                "sound_volume": agent.sound_volume,
                "team_id": agent.team_id,
            }
        return data

    # ------------------------------------------------------------------ 子弹与伤害

    def _step_projectiles(self, dt):
        for proj in list(self.projectiles):
            proj.pos.x += proj.direction.x * proj.speed * dt
            proj.pos.y += proj.direction.y * proj.speed * dt
            rect = pygame.Rect(
                proj.pos.x - BULLET_RADIUS, proj.pos.y - BULLET_RADIUS,
                BULLET_RADIUS * 2, BULLET_RADIUS * 2,
            )

            hit_id = None
            for aid, agent in self.agents.items():
                if aid == proj.owner_id or agent.is_dead:
                    continue
                target = pygame.Rect(
                    agent.pos.x - PLAYER_RADIUS, agent.pos.y - PLAYER_RADIUS,
                    PLAYER_RADIUS * 2, PLAYER_RADIUS * 2,
                )
                if rect.colliderect(target):
                    hit_id = aid
                    break

            if hit_id is not None:
                self._apply_damage(hit_id, BULLET_DAMAGE, proj.owner_id)
                self.projectiles.remove(proj)
                continue

            blocked = False
            for wall in self._static_walls:
                if rect.colliderect(wall):
                    blocked = True
                    break
            if not blocked:
                for door in self.map.doors:
                    if door.check_collision(rect):
                        blocked = True
                        break
            if blocked:
                self.projectiles.remove(proj)

    def _apply_damage(self, target_id, damage, attacker_id):
        agent = self.agents[target_id]
        if agent.is_dead:
            return
        agent.health -= damage
        if attacker_id == self.learner_id:
            self.episode_damage_dealt += damage
            self._step_dealt += damage
        if target_id == self.learner_id:
            self.episode_damage_taken += damage
            self._step_taken += damage

        if agent.health <= 0:
            agent.health = 0
            agent.is_dead = True
            agent.death_time = self.clock.t
            agent.respawn_time = self.clock.t + RESPAWN_TIME
            if attacker_id == self.learner_id:
                self.episode_kills += 1
                self._step_kills += 1
            if target_id == self.learner_id:
                self.episode_deaths += 1

    def _respawn_opponents(self):
        if not self.opponent_respawn:
            return
        now = self.clock.t
        for aid, agent in self.opponents.items():
            if agent.is_dead and now >= agent.respawn_time:
                room = self._rng.randrange(9)
                x, y = self._spawn_pos(room)
                agent.respawn(x, y)
                agent.is_reloading = False
                agent.last_shot_time = now

    # ------------------------------------------------------------------ 观测

    def obs(self, agent=None):
        """观测编码：默认给受控单位；自对弈时同一套编码直接给对手用。"""
        if agent is None:
            agent = self.learner
        out = np.zeros(OBS_DIM, dtype=np.float32)

        out[0] = agent.health / 100.0
        out[1] = agent.ammo / float(MAGAZINE_SIZE)
        out[2] = 1.0 if agent.is_reloading else 0.0
        out[3] = math.sin(math.radians(agent.angle))
        out[4] = math.cos(math.radians(agent.angle))
        out[5] = agent.pos.x / MAP_W
        out[6] = agent.pos.y / MAP_H

        ox, oy = agent.pos.x, agent.pos.y
        for i in range(N_RAYS):
            ang = agent.angle + i * (360.0 / N_RAYS)
            out[7 + i] = self._ray_dist(ox, oy, ang, RAY_MAX) / RAY_MAX

        base = 7 + N_RAYS
        enemies = [
            a for aid, a in self.agents.items()
            if aid != agent.id and not a.is_dead
        ]
        enemies.sort(key=lambda a: agent.pos.distance_squared_to(a.pos))

        for k in range(N_ENEMIES):
            off = base + k * ENEMY_FEATURES
            if k >= len(enemies):
                continue
            enemy = enemies[k]
            dx = enemy.pos.x - ox
            dy = enemy.pos.y - oy
            dist = math.hypot(dx, dy)
            bearing = math.degrees(math.atan2(-dy, dx))
            rel = math.radians(normalize_angle(bearing - agent.angle))
            out[off + 0] = dist / MAP_W
            out[off + 1] = math.cos(rel)
            out[off + 2] = math.sin(rel)
            out[off + 3] = enemy.health / 100.0
            out[off + 4] = 1.0
            out[off + 5] = 1.0 if self._los_grid(ox, oy, enemy.pos.x, enemy.pos.y) else 0.0
            out[off + 6] = 1.0 if enemy.shooting else 0.0
            out[off + 7] = 1.0 if enemy.is_reloading else 0.0

        return out

    def _engaged_with_enemy(self, shots_before):
        """本步是否算"在交火"：打出伤害，或看见敌人同时开了枪。

        只看"有视线"不算交火——站着挨打不还击、或一直远远吊着不打，
        正是要罚的苟着行为；而"对着墙开枪"也不算，防止刷判定。
        """
        if self._step_dealt > 0.0:
            return True
        if self.episode_shots <= shots_before:
            return False
        ax, ay = self.learner.pos.x, self.learner.pos.y
        for enemy in self.opponents.values():
            if enemy.is_dead:
                continue
            dx = enemy.pos.x - ax
            dy = enemy.pos.y - ay
            if dx * dx + dy * dy > CAMP_SIGHT_RANGE * CAMP_SIGHT_RANGE:
                continue
            if self._los_grid(ax, ay, enemy.pos.x, enemy.pos.y):
                return True
        return False

    def _camp_penalty(self):
        """苟着扣分：超过 grace 秒没交火后按步累进（有上限）。"""
        base = self.reward["camp_penalty"]
        if base <= 0.0:
            return 0.0
        if not any(not a.is_dead for a in self.opponents.values()):
            return 0.0
        grace_steps = max(1.0, self.reward["camp_grace"] / self.dt)
        over = self._steps_since_engage - grace_steps
        if over <= 0.0:
            return 0.0
        mult = min(1.0 + over / grace_steps, self.reward["camp_max_mult"])
        return base * mult

    def _aim_shaping(self):
        """对准星指向可见敌人的程度给出连续塑形奖励。

        必须连续，不能是"对准才给分"的稀疏奖励：策略靠随机探索几乎不可能
        正好转进一个窄角度区间，平滑梯度才能把"把枪口转向敌人"学出来。
        """
        agent = self.learner
        ox, oy = agent.pos.x, agent.pos.y
        best = 0.0
        for aid, enemy in self.agents.items():
            if aid == self.learner_id or enemy.is_dead:
                continue
            dx = enemy.pos.x - ox
            dy = enemy.pos.y - oy
            bearing = math.degrees(math.atan2(-dy, dx))
            err = abs(normalize_angle(bearing - agent.angle))
            if err >= 90.0:
                continue
            if not self._los_grid(ox, oy, enemy.pos.x, enemy.pos.y):
                continue
            best = max(best, 1.0 - err / 90.0)
        return self.reward["aim"] * best

    # ------------------------------------------------------------------ 动作编解码

    def vec_to_action(self, vec):
        mx = float(vec[0])
        my = float(vec[1])
        mag = math.hypot(mx, my)
        if mag > 1.0:
            mx /= mag
            my /= mag
        move = pygame.Vector2(mx, my) * MOVE_REF_SPEED
        angle = math.degrees(math.atan2(float(vec[3]), float(vec[2])))
        return {
            "move": move,
            "angle": angle,
            "shoot": float(vec[4]) > 0.0,
            "reload": float(vec[5]) > 0.0,
        }

    @staticmethod
    def action_to_vec(action):
        vec = np.zeros(ACTION_DIM, dtype=np.float32)
        move = action.get("move", _ZERO)
        if move is not None and move.length() > 1e-6:
            unit = move.normalize()
            mag = min(move.length() / MOVE_REF_SPEED, 1.0)
            vec[0] = unit.x * mag
            vec[1] = unit.y * mag
        rad = math.radians(float(action.get("angle", 0.0)))
        vec[2] = math.cos(rad)
        vec[3] = math.sin(rad)
        vec[4] = 1.0 if action.get("shoot") else 0.0
        vec[5] = 1.0 if action.get("reload") else 0.0
        return vec

    # ------------------------------------------------------------------ 步进

    def step(self, action_vec):
        """策略控制这一步；返回 (obs, reward, terminated, truncated, info)。"""
        return self._advance(action_vec)

    def teacher_step(self):
        """由行为树教师控制这一步。

        返回 (obs_t, action_t, next_obs, reward, terminated, truncated, info)。
        其中 (obs_t, action_t) 即行为克隆所需的“状态 -> 动作”标签对。
        """
        pre_obs = self.obs()
        act = None

        def _decide():
            nonlocal act
            act = self.learner.update(
                self.dt, self._players_data(), self.map, [], None
            )
            if act is None:
                act = {"move": _ZERO, "angle": self.learner.angle,
                       "shoot": False, "reload": False}
            self._apply_action(self.learner, act, self.dt)

        next_obs, reward, terminated, truncated, info = self._advance(
            None, override_decide=_decide
        )
        label = self.action_to_vec(act)
        return pre_obs, label, next_obs, reward, terminated, truncated, info

    def _advance(self, action_vec, override_decide=None):
        if self._done:
            raise RuntimeError("episode 已结束，请先 reset()")

        self._step_dealt = 0.0
        self._step_taken = 0.0
        self._step_kills = 0
        shots_before = self.episode_shots

        self.clock.advance(self.dt)
        self._refresh_grid_if_needed()
        self._auto_open_doors()

        # 受控单位
        if override_decide is not None:
            override_decide()
        else:
            self._apply_action(self.learner, self.vec_to_action(action_vec), self.dt)

        # 对手 AI：脚本行为树，或自对弈策略快照（两者动作编码完全一致）
        players_data = None
        for aid, agent in self.opponents.items():
            if agent.is_dead:
                continue
            if self.selfplay_policy is not None:
                self._apply_action(
                    agent,
                    self.vec_to_action(self.selfplay_policy(self.obs(agent))),
                    self.dt,
                )
                continue
            if players_data is None:
                players_data = self._players_data()
            act = agent.update(self.dt, players_data, self.map, [], None)
            if act is not None:
                self._apply_action(agent, act, self.dt)

        self._step_projectiles(self.dt)
        self._respawn_opponents()
        self.map.update(self.dt)

        self.steps += 1

        engaged = self._engaged_with_enemy(shots_before)
        if engaged:
            self._steps_since_engage = 0
        else:
            self._steps_since_engage += 1

        reward = (
            self.reward["step"]
            + self._aim_shaping()
            + self.reward["damage_dealt"] * self._step_dealt
            - self.reward["damage_taken"] * self._step_taken
            + self.reward["kill"] * self._step_kills
            - self._camp_penalty()
        )

        terminated = False
        truncated = False
        learner_dead = self.learner.is_dead
        opponents_dead = all(a.is_dead for a in self.opponents.values())
        if learner_dead:
            reward += self.reward["death"]
            terminated = True
        elif opponents_dead:
            # 明确的“赢”：击杀对手后本局结束，给出清晰的学习目标
            reward += self.reward["win"]
            terminated = True
        elif self.steps >= self.max_episode_steps:
            truncated = True

        self._done = terminated or truncated

        info = {
            "damage_dealt": self.episode_damage_dealt,
            "damage_taken": self.episode_damage_taken,
            "kills": self.episode_kills,
            "deaths": self.episode_deaths,
            "learner_dead": learner_dead,
            "win": bool(opponents_dead and not learner_dead),
            "map_type": self.current_map_type,
            "shots": self.episode_shots,
            "engaged": engaged,
            "steps_since_engage": self._steps_since_engage,
        }
        return self.obs(), float(reward), terminated, truncated, info

    def render_rgb(self, scale=0.25):
        """简易可视化（调试用），返回 HxWx3 的 uint8 数组。"""
        w = int(MAP_W * scale)
        h = int(MAP_H * scale)
        surface = pygame.Surface((w, h))
        surface.fill((30, 30, 30))
        for wall in self._static_walls:
            r = pygame.Rect(wall.x * scale, wall.y * scale,
                            max(1, wall.w * scale), max(1, wall.h * scale))
            surface.fill((110, 110, 110), r)
        for door in self.map.doors:
            color = (0, 200, 0) if door.is_open else (139, 69, 19)
            r = pygame.Rect(door.rect.x * scale, door.rect.y * scale,
                            max(1, door.rect.w * scale), max(1, door.rect.h * scale))
            surface.fill(color, r)
        for proj in self.projectiles:
            pygame.draw.circle(
                surface, (255, 255, 0),
                (int(proj.pos.x * scale), int(proj.pos.y * scale)), 2,
            )
        for aid, agent in self.agents.items():
            if agent.is_dead:
                continue
            color = (0, 160, 255) if aid == self.learner_id else (255, 80, 80)
            pygame.draw.circle(
                surface, color,
                (int(agent.pos.x * scale), int(agent.pos.y * scale)), 5,
            )
            rad = math.radians(agent.angle)
            end = (int((agent.pos.x + math.cos(rad) * 60) * scale),
                   int((agent.pos.y - math.sin(rad) * 60) * scale))
            pygame.draw.line(
                surface, color, (int(agent.pos.x * scale), int(agent.pos.y * scale)),
                end, 2,
            )
        return pygame.surfarray.array3d(surface).transpose(1, 0, 2)


if __name__ == "__main__":
    import time as _time

    sim = HeadlessSim(n_opponents=1, max_episode_steps=1800)
    obs = sim.reset(seed=0)
    print("OBS_DIM =", OBS_DIM, "ACTION_DIM =", ACTION_DIM)
    print("obs shape", obs.shape, "dtype", obs.dtype,
          "range", float(obs.min()), float(obs.max()))

    # 教师随机走位，跑 300 步，统计步频
    t0 = _time.time()
    n = 300
    obs2 = obs
    for i in range(n):
        out = sim.teacher_step()
        obs2 = out[0]
        if out[4] or out[5]:
            sim.reset(seed=i + 1)
    dt_real = _time.time() - t0
    print(f"教师模式 {n} 步耗时 {dt_real:.3f}s -> {n / dt_real:.0f} steps/s")
    print("最后 obs 范围", float(obs2.min()), float(obs2.max()))
