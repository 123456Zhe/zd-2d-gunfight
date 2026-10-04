import math

import pygame

from constants import SCREEN_HEIGHT, SCREEN_WIDTH


class Camera:
    """世界坐标到屏幕坐标的变换，支持跟随玩家朝向旋转

    屏幕中心对应世界坐标 center，世界相对中心的方向按 angle 旋转，
    使得 angle 为 90 - 玩家朝向时，玩家的正前方始终朝向屏幕上方。
    """

    def __init__(self):
        self.center = pygame.Vector2(0, 0)
        self.angle = 0.0
        self._cos = 1.0
        self._sin = 0.0

    def set_view(self, center, angle=0.0):
        """设置屏幕中心对应的世界坐标与旋转角度"""
        self.center.update(center)
        self.angle = angle
        rad = math.radians(angle)
        self._cos = math.cos(rad)
        self._sin = math.sin(rad)

    def to_screen(self, x, y):
        """世界坐标 -> 屏幕坐标（返回元组，可直接交给 pygame.draw）"""
        dx = x - self.center.x
        dy = y - self.center.y
        return (
            SCREEN_WIDTH / 2.0 + dx * self._cos + dy * self._sin,
            SCREEN_HEIGHT / 2.0 - dx * self._sin + dy * self._cos,
        )

    def to_screen_vec(self, pos):
        """世界坐标 -> 屏幕坐标（返回 Vector2）"""
        sx, sy = self.to_screen(pos.x, pos.y)
        return pygame.Vector2(sx, sy)

    def to_screen_polygon(self, points):
        """世界坐标点列表 -> 屏幕坐标点列表"""
        return [self.to_screen(point[0], point[1]) for point in points]

    def rotate_direction(self, direction):
        """世界方向向量 -> 屏幕方向向量（只旋转，不平移）"""
        return pygame.Vector2(
            direction.x * self._cos + direction.y * self._sin,
            -direction.x * self._sin + direction.y * self._cos,
        )
