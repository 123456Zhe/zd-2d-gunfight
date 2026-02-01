"""
游戏配置管理模块

从 settings.json 加载所有游戏配置
"""

import json
import os
from typing import Any, Dict, List


class Settings:
    """配置管理类"""

    _instance = None
    _settings: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_settings()
        return cls._instance

    def _load_settings(self):
        """从 settings.json 加载配置"""
        settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                self._settings = json.load(f)
        except FileNotFoundError:
            print(f"警告: 找不到配置文件 {settings_path}，使用默认配置")
            self._settings = self._get_default_settings()
        except json.JSONDecodeError as e:
            print(f"错误: 配置文件格式错误: {e}，使用默认配置")
            self._settings = self._get_default_settings()

    def _get_default_settings(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "game": {
                "screen_width": 800,
                "screen_height": 600,
                "fps": 60,
                "player_speed": 300,
                "aiming_speed_multiplier": 0.5,
                "bullet_speed": 800,
                "bullet_cooldown": 0.15,
                "reload_time": 2.0,
                "magazine_size": 30,
                "player_radius": 20,
                "bullet_radius": 5,
                "bullet_damage": 20,
                "respawn_time": 3.0,
            },
            "network": {"server_port": 5555, "buffer_size": 4096},
            "ai": {"use_enhanced_ai": True},
            "commands": {"prefix": ".", "enabled": True},
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        支持点号分隔的路径，如 "game.screen_width"
        """
        keys = key.split(".")
        value = self._settings

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        设置配置值

        支持点号分隔的路径，如 "game.screen_width"
        """
        keys = key.split(".")
        target = self._settings

        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]

        target[keys[-1]] = value

    def save(self):
        """保存配置到文件"""
        settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(self._settings, f, indent=4, ensure_ascii=False)

    def reload(self):
        """重新加载配置"""
        self._load_settings()

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._settings.copy()


# 全局配置实例
settings = Settings()


# 便捷函数
def get(key: str, default: Any = None) -> Any:
    """获取配置值"""
    return settings.get(key, default)


def set(key: str, value: Any):
    """设置配置值"""
    settings.set(key, value)


def save():
    """保存配置"""
    settings.save()


def reload():
    """重新加载配置"""
    settings.reload()


# 游戏配置
SCREEN_WIDTH = get("game.screen_width", 800)
SCREEN_HEIGHT = get("game.screen_height", 600)
FPS = get("game.fps", 60)
PLAYER_SPEED = get("game.player_speed", 300)
AIMING_SPEED_MULTIPLIER = get("game.aiming_speed_multiplier", 0.5)
BULLET_SPEED = get("game.bullet_speed", 800)
BULLET_COOLDOWN = get("game.bullet_cooldown", 0.15)
RELOAD_TIME = get("game.reload_time", 2.0)
MAGAZINE_SIZE = get("game.magazine_size", 30)
PLAYER_RADIUS = get("game.player_radius", 20)
BULLET_RADIUS = get("game.bullet_radius", 5)
BULLET_DAMAGE = get("game.bullet_damage", 20)
RESPAWN_TIME = get("game.respawn_time", 3.0)

# 地图配置
ROOM_SIZE = get("map.room_size", 600)
WALL_THICKNESS = get("map.wall_thickness", 20)
DOOR_SIZE = get("map.door_size", 80)
DOOR_ANIMATION_SPEED = get("map.door_animation_speed", 2.0)

# 被击中减速效果
HIT_SLOWDOWN_DURATION = get("hit_effects.slowdown_duration", 0.5)
HIT_SLOWDOWN_FACTOR = get("hit_effects.slowdown_factor", 0.5)

# 近战武器配置
MELEE_DAMAGE = get("melee.damage", 40)
MELEE_RANGE = get("melee.range", 60)
MELEE_COOLDOWN = get("melee.cooldown", 0.8)
MELEE_ANIMATION_TIME = get("melee.animation_time", 0.3)
MELEE_ANGLE = get("melee.angle", 90)
HEAVY_MELEE_DAMAGE = get("melee.heavy_damage", 60)
HEAVY_MELEE_RANGE = get("melee.heavy_range", 45)
HEAVY_MELEE_COOLDOWN = get("melee.heavy_cooldown", 1.2)
HEAVY_MELEE_ANIMATION_TIME = get("melee.heavy_animation_time", 0.45)
HEAVY_MELEE_ANGLE = get("melee.heavy_angle", 60)

# 瞄准配置
AIM_CAMERA_RANGE = get("aiming.camera_range", 400)
AIM_SENSITIVITY = get("aiming.sensitivity", 1)

# 网络配置
SERVER_PORT = get("network.server_port", 5555)
BUFFER_SIZE = get("network.buffer_size", 4096)
HEARTBEAT_INTERVAL = get("network.heartbeat_interval", 1.0)
CLIENT_TIMEOUT = get("network.client_timeout", 5.0)
CONNECTION_TIMEOUT = get("network.connection_timeout", 10.0)
SCAN_TIMEOUT = get("network.scan_timeout", 1.0)

# 视角配置
FIELD_OF_VIEW = get("vision.field_of_view", 120)
VISION_RANGE = get("vision.vision_range", 300)

# 聊天配置
MAX_CHAT_MESSAGES = get("chat.max_messages", 10)
CHAT_DISPLAY_TIME = get("chat.display_time", 10.0)
MAX_CHAT_LENGTH = get("chat.max_length", 50)

# AI配置
USE_ENHANCED_AI = get("ai.use_enhanced_ai", True)
COMMANDS_PREFIX = get("commands.prefix", ".")
COMMANDS_ENABLED = get("commands.enabled", True)


# 颜色定义
def _color(key: str, default: List[int]):
    """获取颜色配置"""
    col = get(f"colors.{key}", default)
    return tuple(col)


WHITE = _color("white", [255, 255, 255])
RED = _color("red", [255, 0, 0])
GREEN = _color("green", [0, 255, 0])
BLUE = _color("blue", [0, 0, 255])
BLACK = _color("black", [0, 0, 0])
GRAY = _color("gray", [100, 100, 100])
DARK_GRAY = _color("dark_gray", [50, 50, 50])
LIGHT_GRAY = _color("light_gray", [140, 140, 140])
VISION_GROUND = _color("vision_ground", [80, 80, 80])
YELLOW = _color("yellow", [255, 255, 0])
DOOR_COLOR = _color("door", [139, 69, 19])
DARK_DOOR_COLOR = _color("dark_door", [69, 34, 9])
DEAD_COLOR = _color("dead", [128, 128, 128])
VISION_COLOR = _color("vision", [255, 255, 0, 30])
FOG_COLOR = _color("fog", [20, 20, 20, 180])
LIGHT_GRAY_TRANSPARENT = _color("light_gray_transparent", [200, 200, 200, 80])
LIGHT_BLUE = _color("light_blue", [173, 216, 230])
DARK_BLUE = _color("dark_blue", [0, 100, 200])
ORANGE = _color("orange", [255, 165, 0])
PURPLE = _color("purple", [128, 0, 128])
MELEE_COLOR = _color("melee", [255, 100, 100])
MELEE_RANGE_COLOR = _color("melee_range", [255, 0, 0, 80])
AIM_COLOR = _color("aim", [0, 255, 255])
