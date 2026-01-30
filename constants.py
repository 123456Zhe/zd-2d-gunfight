import pygame

# 从 settings.json 加载所有配置
# 为了保持向后兼容，所有常量从 config.py 导入
try:
    from config import (
        # 游戏配置
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        FPS,
        PLAYER_SPEED,
        AIMING_SPEED_MULTIPLIER,
        BULLET_SPEED,
        BULLET_COOLDOWN,
        RELOAD_TIME,
        MAGAZINE_SIZE,
        PLAYER_RADIUS,
        BULLET_RADIUS,
        BULLET_DAMAGE,
        RESPAWN_TIME,
        # 地图配置
        ROOM_SIZE,
        WALL_THICKNESS,
        DOOR_SIZE,
        DOOR_ANIMATION_SPEED,
        # 效果配置
        HIT_SLOWDOWN_DURATION,
        HIT_SLOWDOWN_FACTOR,
        # 近战配置
        MELEE_DAMAGE,
        MELEE_RANGE,
        MELEE_COOLDOWN,
        MELEE_ANIMATION_TIME,
        MELEE_ANGLE,
        HEAVY_MELEE_DAMAGE,
        HEAVY_MELEE_RANGE,
        HEAVY_MELEE_COOLDOWN,
        HEAVY_MELEE_ANIMATION_TIME,
        HEAVY_MELEE_ANGLE,
        # 瞄准配置
        AIM_CAMERA_RANGE,
        AIM_SENSITIVITY,
        # 网络配置
        SERVER_PORT,
        BUFFER_SIZE,
        HEARTBEAT_INTERVAL,
        CLIENT_TIMEOUT,
        CONNECTION_TIMEOUT,
        SCAN_TIMEOUT,
        # 视角配置
        FIELD_OF_VIEW,
        VISION_RANGE,
        # 聊天配置
        MAX_CHAT_MESSAGES,
        CHAT_DISPLAY_TIME,
        MAX_CHAT_LENGTH,
        # AI配置
        USE_ENHANCED_AI,
        # 颜色
        WHITE,
        RED,
        GREEN,
        BLUE,
        BLACK,
        GRAY,
        DARK_GRAY,
        LIGHT_GRAY,
        VISION_GROUND,
        YELLOW,
        DOOR_COLOR,
        DARK_DOOR_COLOR,
        DEAD_COLOR,
        VISION_COLOR,
        FOG_COLOR,
        LIGHT_GRAY_TRANSPARENT,
        LIGHT_BLUE,
        DARK_BLUE,
        ORANGE,
        PURPLE,
        MELEE_COLOR,
        MELEE_RANGE_COLOR,
        AIM_COLOR,
    )
except ImportError:
    # 如果 config.py 导入失败，使用默认值（用于首次导入）
    # 游戏配置
    SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
    FPS = 60
    PLAYER_SPEED = 300
    AIMING_SPEED_MULTIPLIER = 0.5
    BULLET_SPEED = 800
    BULLET_COOLDOWN = 0.15
    RELOAD_TIME = 2.0
    MAGAZINE_SIZE = 30
    PLAYER_RADIUS = 20
    BULLET_RADIUS = 5
    BULLET_DAMAGE = 20
    RESPAWN_TIME = 3.0

    # 地图配置
    ROOM_SIZE = 600
    WALL_THICKNESS = 20
    DOOR_SIZE = 80
    DOOR_ANIMATION_SPEED = 2.0

    # 效果配置
    HIT_SLOWDOWN_DURATION = 0.5
    HIT_SLOWDOWN_FACTOR = 0.5

    # 近战配置
    MELEE_DAMAGE = 40
    MELEE_RANGE = 60
    MELEE_COOLDOWN = 0.8
    MELEE_ANIMATION_TIME = 0.3
    MELEE_ANGLE = 90
    HEAVY_MELEE_DAMAGE = 60
    HEAVY_MELEE_RANGE = 45
    HEAVY_MELEE_COOLDOWN = 1.2
    HEAVY_MELEE_ANIMATION_TIME = 0.45
    HEAVY_MELEE_ANGLE = 60

    # 瞄准配置
    AIM_CAMERA_RANGE = 400
    AIM_SENSITIVITY = 1

    # 网络配置
    SERVER_PORT = 5555
    BUFFER_SIZE = 4096
    HEARTBEAT_INTERVAL = 1.0
    CLIENT_TIMEOUT = 5.0
    CONNECTION_TIMEOUT = 10.0
    SCAN_TIMEOUT = 1.0

    # 视角配置
    FIELD_OF_VIEW = 120
    VISION_RANGE = 300

    # 聊天配置
    MAX_CHAT_MESSAGES = 10
    CHAT_DISPLAY_TIME = 10.0
    MAX_CHAT_LENGTH = 50

    # AI配置
    USE_ENHANCED_AI = True

    # 颜色
    WHITE = (255, 255, 255)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    BLACK = (0, 0, 0)
    GRAY = (100, 100, 100)
    DARK_GRAY = (50, 50, 50)
    LIGHT_GRAY = (140, 140, 140)
    VISION_GROUND = (80, 80, 80)
    YELLOW = (255, 255, 0)
    DOOR_COLOR = (139, 69, 19)
    DARK_DOOR_COLOR = (69, 34, 9)
    DEAD_COLOR = (128, 128, 128)
    VISION_COLOR = (255, 255, 0, 30)
    FOG_COLOR = (20, 20, 20, 180)
    LIGHT_GRAY_TRANSPARENT = (200, 200, 200, 80)
    LIGHT_BLUE = (173, 216, 230)
    DARK_BLUE = (0, 100, 200)
    ORANGE = (255, 165, 0)
    PURPLE = (128, 0, 128)
    MELEE_COLOR = (255, 100, 100)
    MELEE_RANGE_COLOR = (255, 0, 0, 80)
    AIM_COLOR = (0, 255, 255)
