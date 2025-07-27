import pygame

# 游戏配置
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
FPS = 60
PLAYER_SPEED = 200
AIMING_SPEED_MULTIPLIER = 0.5  # 瞄准时速度倍率
BULLET_SPEED = 500
BULLET_COOLDOWN = 0.15  # 连发间隔
RELOAD_TIME = 2.0
MAGAZINE_SIZE = 30
PLAYER_RADIUS = 20
BULLET_RADIUS = 5
ROOM_SIZE = 600
WALL_THICKNESS = 20
DOOR_SIZE = 80
DOOR_ANIMATION_SPEED = 2.0  # 门动画速度
BULLET_DAMAGE = 20  # 子弹伤害
RESPAWN_TIME = 3.0  # 复活时间（秒）

# 被击中减速效果
HIT_SLOWDOWN_DURATION = 0.5  # 减速持续时间（秒）
HIT_SLOWDOWN_FACTOR = 0.5  # 减速倍率（0.5表示减速到原来的一半）
SERVER_PORT = 5555
BUFFER_SIZE = 4096

# 近战武器配置
MELEE_DAMAGE = 40  # 近战伤害
MELEE_RANGE = 60  # 近战攻击范围
MELEE_COOLDOWN = 0.8  # 近战攻击冷却时间
MELEE_ANIMATION_TIME = 0.3  # 近战攻击动画时间
MELEE_ANGLE = 90  # 近战攻击角度范围（度）

# 重击配置
HEAVY_MELEE_DAMAGE = 60  # 重击伤害 (1.5倍)
HEAVY_MELEE_RANGE = 45  # 重击攻击范围 (0.75倍)
HEAVY_MELEE_COOLDOWN = 1.2  # 重击攻击冷却时间 (1.5倍)
HEAVY_MELEE_ANIMATION_TIME = 0.45  # 重击攻击动画时间 (1.5倍)
HEAVY_MELEE_ANGLE = 60  # 重击攻击角度范围 (0.67倍)

# 瞄准配置
AIM_CAMERA_RANGE = 150  # 瞄准时相机可以偏移的最大距离
AIM_SENSITIVITY = 0.3  # 瞄准时鼠标灵敏度

# 网络配置
HEARTBEAT_INTERVAL = 1.0  # 心跳间隔（秒）
CLIENT_TIMEOUT = 5.0  # 客户端超时时间（秒）
CONNECTION_TIMEOUT = 10.0  # 连接超时时间（秒）
SCAN_TIMEOUT = 1.0  # 扫描单个IP的超时时间 - 增加到1秒

# 视角配置
FIELD_OF_VIEW = 120  # 视角角度（度）
VISION_RANGE = 300   # 视角范围（像素）- 优化：减少视角范围

# 聊天配置
MAX_CHAT_MESSAGES = 10  # 最大显示聊天消息数
CHAT_DISPLAY_TIME = 10.0  # 聊天消息显示时间（秒）
MAX_CHAT_LENGTH = 50  # 最大聊天消息长度

# 颜色定义
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
DARK_GRAY = (50, 50, 50)  # 迷雾中的墙壁颜色
LIGHT_GRAY = (140, 140, 140)  # 可见地面颜色
VISION_GROUND = (80, 80, 80)  # 视野内地面颜色（优化：使用更暗的颜色）
YELLOW = (255, 255, 0)
DOOR_COLOR = (139, 69, 19)
DARK_DOOR_COLOR = (69, 34, 9)  # 迷雾中的门颜色
DEAD_COLOR = (128, 128, 128)  # 死亡状态颜色
VISION_COLOR = (255, 255, 0, 30)  # 视角范围颜色（半透明黄色）
FOG_COLOR = (20, 20, 20, 180)  # 战争迷雾颜色（深灰色，半透明）
LIGHT_GRAY_TRANSPARENT = (200, 200, 200, 80)  # 半透明浅灰色
LIGHT_BLUE = (173, 216, 230)  # 浅蓝色
DARK_BLUE = (0, 100, 200)  # 深蓝色
ORANGE = (255, 165, 0)  # 橙色
PURPLE = (128, 0, 128)  # 紫色
MELEE_COLOR = (255, 100, 100)  # 近战攻击颜色
MELEE_RANGE_COLOR = (255, 0, 0, 80)  # 近战范围指示颜色
AIM_COLOR = (0, 255, 255)  # 瞄准指示颜色