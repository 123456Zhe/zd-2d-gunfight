"""神经网络 AI（纯 numpy 推理）。

把 RL 训练用的 47 维观测和 6 维动作原样搬到游戏里：
- 观测：自身状态 + 16 条射线 + 最近 3 个敌人的 8 维特征
- 动作：[move_x, move_y, aim_cos, aim_sin, shoot, reload]
权重来自 PPO 导出的 npz，运行时不依赖 torch / stable-baselines3。
"""

import math
import time
from pathlib import Path

import numpy as np
import pygame

from constants import (
    BULLET_COOLDOWN,
    MAGAZINE_SIZE,
    PLAYER_RADIUS,
    PLAYER_SPEED,
    RELOAD_TIME,
    RL_POLICY_PATH,
    ROOM_SIZE,
)
from utils import normalize_angle
from ai_player_enhanced import EnhancedAIPlayer

MAP_W = float(ROOM_SIZE * 3)
MAP_H = float(ROOM_SIZE * 3)
GRID_CELL = 20
GRID_W = int(math.ceil(MAP_W / GRID_CELL))
GRID_H = int(math.ceil(MAP_H / GRID_CELL))

N_RAYS = 16
RAY_MAX = 600.0
N_ENEMIES = 3
ENEMY_FEATURES = 8
OBS_DIM = 7 + N_RAYS + N_ENEMIES * ENEMY_FEATURES

_W0 = "mlp_extractor.policy_net.0.weight"
_B0 = "mlp_extractor.policy_net.0.bias"
_W2 = "mlp_extractor.policy_net.2.weight"
_B2 = "mlp_extractor.policy_net.2.bias"
_AW = "action_net.weight"
_AB = "action_net.bias"
SYNC_KEYS = (_W0, _B0, _W2, _B2, _AW, _AB)


def resolve_policy_path(path=None):
    raw = Path(path or RL_POLICY_PATH)
    if raw.is_absolute():
        return raw
    here = Path(__file__).resolve().parent
    for base in (here, Path.cwd()):
        candidate = base / raw
        if candidate.exists():
            return candidate
    return here / raw


class NumpyPolicy:
    """与 SB3 MlpPolicy 对齐的确定性前向（取动作均值）。"""

    def __init__(self, path):
        path = resolve_policy_path(path)
        if not path.exists():
            raise FileNotFoundError(f"找不到神经网络权重: {path}")
        with np.load(path) as z:
            missing = [key for key in SYNC_KEYS if key not in z]
            if missing:
                raise KeyError(f"策略权重缺少字段: {missing}")
            self._w = {key: z[key].astype(np.float32) for key in SYNC_KEYS}

    def act(self, obs):
        w = self._w
        x = np.asarray(obs, dtype=np.float32)
        h = np.tanh(x @ w[_W0].T + w[_B0])
        h = np.tanh(h @ w[_W2].T + w[_B2])
        out = h @ w[_AW].T + w[_AB]
        out = np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)
        # SB3 的 predict() 会把动作裁剪到动作空间边界，推理必须保持一致
        return np.clip(out, -1.0, 1.0)


class ObservationEncoder:
    """复刻 rl/sim.py 的观测编码；网格按地图缓存，门状态变化时重建。"""

    def __init__(self, game_map):
        self.map = game_map
        self._static_walls = list(game_map.walls)
        self._door_sig = None
        self._grid = bytearray(GRID_W * GRID_H)
        self._build_grid()

    @classmethod
    def for_map(cls, game_map):
        encoder = getattr(game_map, "_rl_obs_encoder", None)
        if encoder is None or encoder.map is not game_map:
            encoder = cls(game_map)
            game_map._rl_obs_encoder = encoder
        encoder.refresh()
        return encoder

    def refresh(self):
        sig = tuple(
            1 if (door.is_open or door.is_opening) else 0
            for door in self.map.doors
        )
        if sig != self._door_sig:
            self._door_sig = sig
            self._build_grid()

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

    def _blocked_xy(self, x, y):
        if x < 0 or y < 0 or x >= MAP_W or y >= MAP_H:
            return True
        gx = min(GRID_W - 1, int(x / GRID_CELL))
        gy = min(GRID_H - 1, int(y / GRID_CELL))
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

    def _los(self, ax, ay, bx, by):
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

    @staticmethod
    def _field(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    def obs(self, agent, players):
        out = np.zeros(OBS_DIM, dtype=np.float32)
        out[0] = float(agent.health) / 100.0
        out[1] = float(agent.ammo) / float(MAGAZINE_SIZE)
        out[2] = 1.0 if agent.is_reloading else 0.0
        out[3] = math.sin(math.radians(agent.angle))
        out[4] = math.cos(math.radians(agent.angle))
        out[5] = agent.pos.x / MAP_W
        out[6] = agent.pos.y / MAP_H

        ox, oy = agent.pos.x, agent.pos.y
        for i in range(N_RAYS):
            ang = agent.angle + i * (360.0 / N_RAYS)
            out[7 + i] = self._ray_dist(ox, oy, ang, RAY_MAX) / RAY_MAX

        enemies = []
        for pid, data in players.items():
            if pid == agent.id or self._field(data, "is_dead", False):
                continue
            pos = self._field(data, "pos")
            if not pos or len(pos) != 2:
                continue
            team_id = self._field(data, "team_id")
            if agent.team_id is not None and team_id == agent.team_id:
                continue
            enemies.append((float(pos[0]), float(pos[1]), data))

        enemies.sort(
            key=lambda item: (item[0] - ox) ** 2 + (item[1] - oy) ** 2
        )

        base = 7 + N_RAYS
        for k, (ex, ey, data) in enumerate(enemies[:N_ENEMIES]):
            off = base + k * ENEMY_FEATURES
            dx = ex - ox
            dy = ey - oy
            dist = math.hypot(dx, dy)
            bearing = math.degrees(math.atan2(-dy, dx))
            rel = math.radians(normalize_angle(bearing - agent.angle))
            out[off + 0] = dist / MAP_W
            out[off + 1] = math.cos(rel)
            out[off + 2] = math.sin(rel)
            out[off + 3] = float(self._field(data, "health", 100)) / 100.0
            out[off + 4] = 1.0
            out[off + 5] = 1.0 if self._los(ox, oy, ex, ey) else 0.0
            out[off + 6] = 1.0 if self._field(data, "shooting", False) else 0.0
            out[off + 7] = 1.0 if self._field(data, "is_reloading", False) else 0.0

        return out


class RLAIPlayer(EnhancedAIPlayer):
    """用导出的 PPO 策略驱动一个 AI；接口与 EnhancedAIPlayer 对齐。"""

    def __init__(self, player_id, x, y, difficulty="normal", personality=None,
                 policy_path=None):
        super().__init__(player_id, x, y, "hard", personality)
        self.name = f"AI_RL_{player_id}"
        self.difficulty = "rl"
        self.policy = NumpyPolicy(policy_path)
        self.obs_encoder = None
        self.shooting = False

    def generate_patrol_points(self, game_map):
        self.obs_encoder = ObservationEncoder.for_map(game_map)

    def _initialize_behavior_tree(self):
        return None

    def _ensure_encoder(self, game_map):
        if self.obs_encoder is None or self.obs_encoder.map is not game_map:
            self.obs_encoder = ObservationEncoder.for_map(game_map)

    def _nearest_closed_door(self, game_map):
        best = None
        best_dist = 70.0
        for door in game_map.doors:
            if door.is_open or door.is_opening:
                continue
            center = pygame.Vector2(
                getattr(door, "original_rect", door.rect).center
            )
            dist = self.pos.distance_to(center)
            if dist < best_dist:
                best = door
                best_dist = dist
        return best

    def update(self, dt, players, game_map, bullets, team_manager=None):
        if self.is_dead:
            return None

        now = time.time()
        if self.is_reloading and now - self.reload_start_time >= RELOAD_TIME:
            self.ammo = MAGAZINE_SIZE
            self.is_reloading = False

        self._ensure_encoder(game_map)
        obs = self.obs_encoder.obs(self, players)
        vec = self.policy.act(obs)

        mx, my = float(vec[0]), float(vec[1])
        mag = math.hypot(mx, my)
        if mag > 1.0:
            mx /= mag
            my /= mag
        move = pygame.Vector2(mx, my) * PLAYER_SPEED
        angle = math.degrees(math.atan2(float(vec[3]), float(vec[2])))

        want_shoot = bool(vec[4] > 0.0)
        want_reload = bool(vec[5] > 0.0)
        can_shoot = (
            not self.is_reloading
            and self.ammo > 0
            and now - self.last_shot_time >= BULLET_COOLDOWN
        )
        shoot = want_shoot and can_shoot
        if self.ammo <= 0 and not self.is_reloading:
            want_reload = True

        if shoot and team_manager is not None:
            allies = []
            for pid, data in players.items():
                if pid == self.id:
                    continue
                try:
                    if team_manager.are_teammates(self.id, pid):
                        allies.append(data)
                except Exception:
                    pass
            if not self.is_line_clear_of_allies(allies, angle):
                shoot = False

        action = {
            "move": move,
            "angle": angle,
            "shoot": shoot,
            "reload": want_reload,
            "is_walking": False,
            "is_making_sound": False,
            "sound_volume": 0.0,
        }

        door = self._nearest_closed_door(game_map)
        if door is not None:
            action["interact_door"] = door

        moving = move.length() > 0.1
        sound = 0.0
        if shoot:
            sound = 1.0
        elif want_reload:
            sound = 0.8
        elif moving:
            sound = 1.0
        self.shooting = shoot
        self.is_making_sound = sound > 0.0
        self.sound_volume = sound
        action["is_making_sound"] = self.is_making_sound
        action["sound_volume"] = sound
        return action
