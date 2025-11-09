"""
AI代价计算模块
使用numpy进行批量计算，提高性能
"""

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    # 如果没有numpy，使用math和基础类型作为fallback
    import math
    print("警告: numpy未安装，将使用较慢的fallback实现。建议安装numpy: pip install numpy")

import math
import pygame
from constants import *


class AICostCalculator:
    """AI代价计算器 - 使用numpy进行批量计算"""
    
    def __init__(self, grid_size=50):
        """
        初始化代价计算器
        
        Args:
            grid_size: 代价网格大小（像素）
        """
        self.grid_size = grid_size
        self.map_width = ROOM_SIZE * 3
        self.map_height = ROOM_SIZE * 3
        self.grid_width = int(self.map_width / grid_size)
        self.grid_height = int(self.map_height / grid_size)
        
        # 预计算网格中心点坐标
        if HAS_NUMPY:
            self.grid_centers_x = np.arange(self.grid_width) * grid_size + grid_size / 2
            self.grid_centers_y = np.arange(self.grid_height) * grid_size + grid_size / 2
            self.grid_centers = np.meshgrid(self.grid_centers_x, self.grid_centers_y)
        else:
            # Fallback: 使用列表
            self.grid_centers_x = [i * grid_size + grid_size / 2 for i in range(self.grid_width)]
            self.grid_centers_y = [i * grid_size + grid_size / 2 for i in range(self.grid_height)]
        
    def calculate_threat_cost(self, position, enemies, game_map):
        """
        计算位置受到威胁的代价（越高越危险）
        
        Args:
            position: 目标位置 (x, y)
            enemies: 敌人列表 [{'pos': Vector2, 'angle': float, 'health': int, ...}, ...]
            game_map: 游戏地图对象
            
        Returns:
            float: 威胁代价（0-1之间，1表示极度危险）
        """
        if not enemies:
            return 0.0
        
        if HAS_NUMPY:
            pos = np.array([position.x, position.y])
        else:
            pos = [position.x, position.y]
        
        threat_cost = 0.0
        
        for enemy in enemies:
            if enemy.get('is_dead', False):
                continue
            
            if HAS_NUMPY:
                enemy_pos = np.array(enemy['pos'])
                distance = np.linalg.norm(pos - enemy_pos)
                distance_factor = np.exp(-distance / 200.0)
            else:
                enemy_pos = enemy['pos']
                dx = pos[0] - enemy_pos[0]
                dy = pos[1] - enemy_pos[1]
                distance = math.sqrt(dx*dx + dy*dy)
                distance_factor = math.exp(-distance / 200.0)
            
            # 检查是否有视线（有视线威胁更大）
            has_los = self._has_line_of_sight(position, pygame.Vector2(enemy['pos'][0], enemy['pos'][1]), game_map)
            los_factor = 2.0 if has_los else 0.5
            
            # 敌人健康值影响威胁（健康值越低威胁越小）
            health_factor = enemy.get('health', 100) / 100.0
            
            # 综合威胁
            threat = distance_factor * los_factor * health_factor
            threat_cost += threat
        
        # 归一化到0-1
        return min(1.0, threat_cost / len(enemies)) if enemies else 0.0
    
    def calculate_cover_value(self, position, enemies, game_map):
        """
        计算位置的掩体价值（越高越好）
        
        Args:
            position: 目标位置
            enemies: 敌人列表
            game_map: 游戏地图对象
            
        Returns:
            float: 掩体价值（0-1之间，1表示完美掩体）
        """
        if not enemies:
            return 0.5  # 没有敌人时掩体价值中等
        
        pos = pygame.Vector2(position.x, position.y)
        cover_score = 0.0
        enemy_count = 0
        
        for enemy in enemies:
            if enemy.get('is_dead', False):
                continue
            
            enemy_pos = pygame.Vector2(*enemy['pos'])
            distance = pos.distance_to(enemy_pos)
            
            if distance > 500:  # 太远不考虑
                continue
            
            enemy_count += 1
            
            # 检查是否有直接视线
            has_los = self._has_line_of_sight(pos, enemy_pos, game_map)
            
            if not has_los:
                # 没有视线，掩体价值高
                cover_score += 1.0
            else:
                # 有视线，检查是否有部分遮挡
                # 检查到敌人的路径上是否有墙壁
                walls_between = self._count_walls_between(pos, enemy_pos, game_map)
                if walls_between > 0:
                    cover_score += 0.5
                else:
                    # 没有遮挡，但距离远也有一定价值
                    distance_factor = max(0.1, 1.0 - distance / 500.0)
                    cover_score += distance_factor * 0.3
        
        if enemy_count == 0:
            return 0.5
        
        return min(1.0, cover_score / enemy_count)
    
    def calculate_position_cost_grid(self, ai_pos, enemies, game_map, allies=None):
        """
        批量计算整个地图的代价网格
        
        Args:
            ai_pos: AI当前位置
            enemies: 敌人列表
            game_map: 游戏地图对象
            allies: 友军列表（可选）
            
        Returns:
            numpy.ndarray or list: 代价网格（值越小越好）
        """
        # 初始化代价网格
        if HAS_NUMPY:
            cost_grid = np.zeros((self.grid_height, self.grid_width))
        else:
            cost_grid = [[0.0 for _ in range(self.grid_width)] for _ in range(self.grid_height)]
        
        # 计算每个网格点的代价
        for i in range(self.grid_height):
            for j in range(self.grid_width):
                if HAS_NUMPY:
                    grid_x = self.grid_centers_x[j]
                    grid_y = self.grid_centers_y[i]
                else:
                    grid_x = self.grid_centers_x[j]
                    grid_y = self.grid_centers_y[i]
                
                grid_pos = pygame.Vector2(grid_x, grid_y)
                
                # 检查是否在墙壁内（不可通行）
                if self._is_in_wall(grid_pos, game_map):
                    if HAS_NUMPY:
                        cost_grid[i, j] = 9999.0
                    else:
                        cost_grid[i][j] = 9999.0
                    continue
                
                # 1. 威胁代价（越高越危险，加到总代价中）
                threat_cost = self.calculate_threat_cost(grid_pos, enemies, game_map)
                
                # 2. 掩体价值（越高越好，从总代价中减去）
                cover_value = self.calculate_cover_value(grid_pos, enemies, game_map)
                
                # 3. 距离代价（距离目标越远代价越高）
                # 这里暂时使用到AI当前位置的距离作为参考
                distance_to_ai = math.sqrt((grid_x - ai_pos.x)**2 + (grid_y - ai_pos.y)**2)
                distance_cost = distance_to_ai / 1000.0  # 归一化
                
                # 4. 综合代价（威胁+距离-掩体价值）
                total_cost = threat_cost * 2.0 + distance_cost * 0.5 - cover_value * 1.5
                
                if HAS_NUMPY:
                    cost_grid[i, j] = max(0.0, total_cost)
                else:
                    cost_grid[i][j] = max(0.0, total_cost)
        
        return cost_grid
    
    def find_best_position(self, ai_pos, enemies, game_map, allies=None, 
                          max_search_radius=300):
        """
        找到最佳位置（代价最小）
        
        Args:
            ai_pos: AI当前位置
            enemies: 敌人列表
            game_map: 游戏地图对象
            allies: 友军列表
            max_search_radius: 最大搜索半径
            
        Returns:
            pygame.Vector2: 最佳位置，如果找不到则返回None
        """
        # 计算代价网格
        cost_grid = self.calculate_position_cost_grid(ai_pos, enemies, game_map, allies)
        
        # 只考虑在搜索半径内的位置
        ai_grid_x = int(ai_pos.x / self.grid_size)
        ai_grid_y = int(ai_pos.y / self.grid_size)
        search_radius_grid = int(max_search_radius / self.grid_size)
        
        min_cost = float('inf')
        best_pos = None
        
        # 在搜索半径内寻找代价最小的位置
        for i in range(max(0, ai_grid_y - search_radius_grid), 
                      min(self.grid_height, ai_grid_y + search_radius_grid + 1)):
            for j in range(max(0, ai_grid_x - search_radius_grid), 
                          min(self.grid_width, ai_grid_x + search_radius_grid + 1)):
                
                if HAS_NUMPY:
                    cost = cost_grid[i, j]
                else:
                    cost = cost_grid[i][j]
                
                if cost >= 9999.0:  # 不可通行
                    continue
                
                if cost < min_cost:
                    min_cost = cost
                    if HAS_NUMPY:
                        best_pos = pygame.Vector2(
                            self.grid_centers_x[j],
                            self.grid_centers_y[i]
                        )
                    else:
                        best_pos = pygame.Vector2(
                            self.grid_centers_x[j],
                            self.grid_centers_y[i]
                        )
        
        return best_pos
    
    def calculate_flanking_angle(self, ai_pos, target_pos, enemy_pos):
        """
        计算侧翼攻击角度（值越大表示侧翼效果越好）
        
        Args:
            ai_pos: AI位置
            target_pos: 目标位置
            enemy_pos: 敌人位置
            
        Returns:
            float: 侧翼角度（0-1之间，1表示完美侧翼）
        """
        # 计算敌人到目标的角度
        to_target = target_pos - enemy_pos
        enemy_angle = math.atan2(-to_target.y, to_target.x)
        
        # 计算敌人到AI的角度
        to_ai = ai_pos - enemy_pos
        ai_angle = math.atan2(-to_ai.y, to_ai.x)
        
        # 计算角度差
        angle_diff = abs(ai_angle - enemy_angle)
        if angle_diff > math.pi:
            angle_diff = 2 * math.pi - angle_diff
        
        # 侧翼角度：90度（π/2）为最佳
        optimal_angle = math.pi / 2
        flank_score = 1.0 - abs(angle_diff - optimal_angle) / optimal_angle
        
        return max(0.0, min(1.0, flank_score))
    
    def find_flanking_position(self, ai_pos, target_pos, enemy_pos, game_map, 
                              min_distance=100, max_distance=250):
        """
        寻找侧翼攻击位置
        
        Args:
            ai_pos: AI当前位置
            target_pos: 目标位置
            enemy_pos: 敌人位置
            game_map: 游戏地图对象
            min_distance: 最小距离
            max_distance: 最大距离
            
        Returns:
            pygame.Vector2: 侧翼位置，如果找不到则返回None
        """
        # 计算敌人到目标的方向
        to_target = target_pos - enemy_pos
        target_angle = math.atan2(-to_target.y, to_target.x)
        
        # 尝试多个侧翼角度
        best_pos = None
        best_score = -1.0
        
        for angle_offset in [-math.pi/2, math.pi/2, -math.pi/4, math.pi/4]:
            # 计算侧翼位置
            flank_angle = target_angle + angle_offset
            distance = (min_distance + max_distance) / 2
            
            flank_x = enemy_pos.x + math.cos(flank_angle) * distance
            flank_y = enemy_pos.y - math.sin(flank_angle) * distance
            
            # 确保在地图范围内
            flank_x = max(50, min(self.map_width - 50, flank_x))
            flank_y = max(50, min(self.map_height - 50, flank_y))
            
            flank_pos = pygame.Vector2(flank_x, flank_y)
            
            # 检查是否可通行
            if self._is_in_wall(flank_pos, game_map):
                continue
            
            # 计算侧翼分数
            flank_score = self.calculate_flanking_angle(flank_pos, target_pos, enemy_pos)
            
            # 检查是否有视线到敌人
            has_los = self._has_line_of_sight(flank_pos, enemy_pos, game_map)
            if has_los:
                flank_score *= 1.5  # 有视线时分数更高
            
            if flank_score > best_score:
                best_score = flank_score
                best_pos = flank_pos
        
        return best_pos
    
    def calculate_ambush_value(self, position, predicted_enemy_pos, game_map):
        """
        计算伏击位置的价值
        
        Args:
            position: 伏击位置
            predicted_enemy_pos: 预测的敌人位置
            game_map: 游戏地图对象
            
        Returns:
            float: 伏击价值（0-1之间）
        """
        # 检查是否有良好的掩体
        cover_value = self.calculate_cover_value(position, 
                                                 [{'pos': [predicted_enemy_pos.x, predicted_enemy_pos.y], 
                                                   'is_dead': False}], 
                                                 game_map)
        
        # 检查距离是否合适（不要太近也不要太远）
        distance = position.distance_to(predicted_enemy_pos)
        distance_score = 0.0
        if 150 <= distance <= 300:
            distance_score = 1.0
        elif 100 <= distance < 150 or 300 < distance <= 400:
            distance_score = 0.7
        else:
            distance_score = 0.3
        
        # 检查是否有视线（但不要太明显）
        has_los = self._has_line_of_sight(position, predicted_enemy_pos, game_map)
        los_score = 0.8 if has_los else 0.5  # 有视线但不完全暴露最好
        
        # 综合伏击价值
        ambush_value = (cover_value * 0.4 + distance_score * 0.3 + los_score * 0.3)
        
        return ambush_value
    
    def _has_line_of_sight(self, pos1, pos2, game_map):
        """检查两点之间是否有视线"""
        # 检查墙壁
        for wall in game_map.walls:
            if self._line_intersects_rect(pos1, pos2, wall):
                return False
        
        # 检查关闭的门
        for door in game_map.doors:
            if not door.is_open:
                if self._line_intersects_rect(pos1, pos2, door.rect):
                    return False
        
        return True
    
    def _line_intersects_rect(self, start, end, rect):
        """检查线段是否与矩形相交"""
        # 使用pygame的碰撞检测
        try:
            return rect.clipline((start.x, start.y), (end.x, end.y))
        except:
            # 如果失败，使用简单的边界检查
            min_x = min(start.x, end.x)
            max_x = max(start.x, end.x)
            min_y = min(start.y, end.y)
            max_y = max(start.y, end.y)
            
            return not (rect.right < min_x or rect.left > max_x or 
                       rect.bottom < min_y or rect.top > max_y)
    
    def _count_walls_between(self, pos1, pos2, game_map):
        """计算两点之间的墙壁数量"""
        count = 0
        for wall in game_map.walls:
            if self._line_intersects_rect(pos1, pos2, wall):
                count += 1
        return count
    
    def _is_in_wall(self, pos, game_map):
        """检查位置是否在墙壁内"""
        for wall in game_map.walls:
            if wall.collidepoint(pos.x, pos.y):
                return True
        return False

