"""
工具函数模块
包含游戏中使用的通用工具函数，如角度计算、视野检测、碰撞检测等
"""

import pygame
import math
from constants import *


# ============================================================================
# 角度计算函数
# ============================================================================

def normalize_angle(angle):
    """将角度标准化到-180到180度范围"""
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return angle


def angle_difference(angle1, angle2):
    """计算两个角度之间的最小差值"""
    diff = abs(normalize_angle(angle1) - normalize_angle(angle2))
    return min(diff, 360 - diff)


# ============================================================================
# 视野检测函数
# ============================================================================

def is_in_field_of_view(player_pos, player_angle, target_pos, fov_degrees):
    """检查目标位置是否在玩家的视野范围内"""
    if player_pos == target_pos:
        return True
    
    # 计算从玩家到目标的角度
    dx = target_pos.x - player_pos.x
    dy = target_pos.y - player_pos.y
    target_angle = math.degrees(math.atan2(-dy, dx))  # 注意Y轴方向
    
    # 计算角度差
    angle_diff = angle_difference(player_angle, target_angle)
    
    # 检查是否在视野范围内
    return angle_diff <= fov_degrees / 2


def has_line_of_sight(start_pos, end_pos, walls, doors):
    """检查两点之间是否有视线（不被墙壁或关闭的门阻挡）"""
    # 检查与墙壁的碰撞
    for wall in walls:
        if line_intersects_rect(start_pos, end_pos, wall):
            return False
    
    # 检查与关闭的门的碰撞
    for door in doors:
        if not door.is_open and line_intersects_rect(start_pos, end_pos, door.rect):
            return False
    
    return True


def is_visible(player_pos, player_angle, target_pos, fov_degrees, walls, doors):
    """检查目标是否可见（在视野内且有视线）"""
    # 首先检查是否在视野角度内
    if not is_in_field_of_view(player_pos, player_angle, target_pos, fov_degrees):
        return False
    
    # 然后检查是否有视线
    return has_line_of_sight(player_pos, target_pos, walls, doors)


def create_vision_fan_points(player_pos, player_angle, fov_degrees, vision_range, num_points=30):
    """创建视角扇形的点集合 - 优化版本"""
    points = [player_pos]  # 扇形的中心点
    
    half_fov = fov_degrees / 2
    angle_step = fov_degrees / num_points
    
    # 生成扇形边界上的点
    for i in range(num_points + 1):
        angle = player_angle - half_fov + (angle_step * i)
        angle_rad = math.radians(angle)
        end_x = player_pos[0] + math.cos(angle_rad) * vision_range
        end_y = player_pos[1] - math.sin(angle_rad) * vision_range
        points.append((end_x, end_y))
    
    return points


# ============================================================================
# 碰撞检测函数
# ============================================================================

def line_intersects_rect(start, end, rect):
    """检查线段是否与矩形相交"""
    # 获取矩形的四条边
    left = rect.left
    right = rect.right
    top = rect.top
    bottom = rect.bottom
    
    # 检查线段是否与矩形的四条边相交
    # 左边
    if line_intersects_line(start, end, (left, top), (left, bottom)):
        return True
    # 右边
    if line_intersects_line(start, end, (right, top), (right, bottom)):
        return True
    # 上边
    if line_intersects_line(start, end, (left, top), (right, top)):
        return True
    # 下边
    if line_intersects_line(start, end, (left, bottom), (right, bottom)):
        return True
    
    return False


def line_intersects_line(p1, p2, p3, p4):
    """检查两条线段是否相交"""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 0.0001:
        return False
    
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
    
    return 0 <= t <= 1 and 0 <= u <= 1


def is_in_melee_range(attacker_pos, attacker_angle, target_pos, melee_range, melee_angle):
    """检查目标是否在近战攻击范围内"""
    # 计算距离
    distance = (target_pos - attacker_pos).length()
    if distance > melee_range:
        return False
    
    # 计算角度
    dx = target_pos.x - attacker_pos.x
    dy = target_pos.y - attacker_pos.y
    target_angle = math.degrees(math.atan2(-dy, dx))
    
    # 检查是否在攻击角度范围内
    angle_diff = angle_difference(attacker_angle, target_angle)
    return angle_diff <= melee_angle / 2
