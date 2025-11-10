"""
AI行为树系统
使用轻量级行为树框架实现多样化的AI行为
"""

import enum
import random
import math
import time
import pygame
from constants import *


class NodeStatus(enum.Enum):
    """节点状态"""
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"


class BehaviorNode:
    """行为树节点基类"""
    
    def __init__(self, name="Node"):
        self.name = name
        self.status = NodeStatus.FAILURE
        self.parent = None
        self.children = []
    
    def tick(self, ai_player, blackboard):
        """
        执行节点逻辑
        
        Args:
            ai_player: AI玩家对象
            blackboard: 黑板（共享数据）
            
        Returns:
            NodeStatus: 节点执行状态
        """
        raise NotImplementedError("子类必须实现tick方法")
    
    def reset(self):
        """重置节点状态"""
        self.status = NodeStatus.FAILURE
        for child in self.children:
            child.reset()


class CompositeNode(BehaviorNode):
    """组合节点基类"""
    
    def __init__(self, name="Composite", children=None):
        super().__init__(name)
        self.children = children or []


class SelectorNode(CompositeNode):
    """选择节点（或逻辑）：只要有一个子节点成功就返回成功"""
    
    def tick(self, ai_player, blackboard):
        for child in self.children:
            status = child.tick(ai_player, blackboard)
            if status == NodeStatus.SUCCESS:
                self.status = NodeStatus.SUCCESS
                return self.status
            elif status == NodeStatus.RUNNING:
                self.status = NodeStatus.RUNNING
                return self.status
        
        self.status = NodeStatus.FAILURE
        return self.status


class SequenceNode(CompositeNode):
    """序列节点（与逻辑）：所有子节点都成功才返回成功"""
    
    def tick(self, ai_player, blackboard):
        for child in self.children:
            status = child.tick(ai_player, blackboard)
            if status == NodeStatus.FAILURE:
                self.status = NodeStatus.FAILURE
                return self.status
            elif status == NodeStatus.RUNNING:
                self.status = NodeStatus.RUNNING
                return self.status
        
        self.status = NodeStatus.SUCCESS
        return self.status


class ParallelNode(CompositeNode):
    """并行节点：同时执行所有子节点"""
    
    def __init__(self, name="Parallel", children=None, success_count=1):
        super().__init__(name, children)
        self.success_count = success_count  # 需要成功的子节点数量
    
    def tick(self, ai_player, blackboard):
        success_count = 0
        failure_count = 0
        
        for child in self.children:
            status = child.tick(ai_player, blackboard)
            if status == NodeStatus.SUCCESS:
                success_count += 1
            elif status == NodeStatus.FAILURE:
                failure_count += 1
        
        if success_count >= self.success_count:
            self.status = NodeStatus.SUCCESS
        elif failure_count > len(self.children) - self.success_count:
            self.status = NodeStatus.FAILURE
        else:
            self.status = NodeStatus.RUNNING
        
        return self.status


class DecoratorNode(BehaviorNode):
    """装饰节点：修饰子节点的行为"""
    
    def __init__(self, name="Decorator", child=None):
        super().__init__(name)
        self.child = child
        if child:
            child.parent = self
    
    def add_child(self, child):
        """添加子节点"""
        self.child = child
        child.parent = self


class InverterNode(DecoratorNode):
    """反转节点：反转子节点的结果"""
    
    def tick(self, ai_player, blackboard):
        if not self.child:
            return NodeStatus.FAILURE
        
        status = self.child.tick(ai_player, blackboard)
        if status == NodeStatus.SUCCESS:
            return NodeStatus.FAILURE
        elif status == NodeStatus.FAILURE:
            return NodeStatus.SUCCESS
        else:
            return NodeStatus.RUNNING


class RepeatNode(DecoratorNode):
    """重复节点：重复执行子节点指定次数"""
    
    def __init__(self, name="Repeat", child=None, count=-1):
        super().__init__(name, child)
        self.count = count  # -1表示无限重复
        self.current_count = 0
    
    def tick(self, ai_player, blackboard):
        if not self.child:
            return NodeStatus.FAILURE
        
        if self.count > 0 and self.current_count >= self.count:
            self.current_count = 0
            return NodeStatus.SUCCESS
        
        status = self.child.tick(ai_player, blackboard)
        if status == NodeStatus.SUCCESS:
            self.current_count += 1
            if self.count > 0 and self.current_count >= self.count:
                return NodeStatus.SUCCESS
            return NodeStatus.RUNNING
        
        return status
    
    def reset(self):
        super().reset()
        self.current_count = 0


# ==================== 条件节点 ====================

class ConditionNode(BehaviorNode):
    """条件节点基类"""
    pass


class HasEnemyInSight(ConditionNode):
    """检查是否有敌人在视线内"""
    
    def tick(self, ai_player, blackboard):
        enemies = blackboard.get('enemies', [])
        game_map = blackboard.get('game_map')
        team_manager = blackboard.get('team_manager')
        
        # 过滤掉队友（优先使用团队管理器判断，其次使用team_id对比）
        filtered_enemies = []
        for enemy in enemies:
            if enemy.get('is_dead', False):
                continue
            # 检查是否是队友（先用are_teammates，避免ID类型/同步问题）
            if team_manager:
                if team_manager.are_teammates(ai_player.id, enemy.get('id')):
                    continue
                # 补充：如果双方都有team_id字段，也进行一次直接对比（防守）
                if hasattr(ai_player, 'team_id') and ai_player.team_id is not None:
                    enemy_team_id = enemy.get('team_id')
                    if enemy_team_id is not None and enemy_team_id == ai_player.team_id:
                        continue
            filtered_enemies.append(enemy)
        
        # 检查是否有激进型AI特征（扩大检测范围）
        is_aggressive = False
        if hasattr(ai_player, 'personality_traits'):
            is_aggressive = ai_player.personality_traits.personality_type.value == 'aggressive'
        
        # 激进型AI使用更大的检测范围
        sight_range = 400 if is_aggressive else 300
        close_range = 200  # 近距离范围（即使没有视线也尝试攻击）
        
        closest_enemy = None
        closest_distance = float('inf')
        closest_has_los = False
        
        for enemy in filtered_enemies:
            enemy_pos = pygame.Vector2(*enemy['pos'])
            distance = ai_player.pos.distance_to(enemy_pos)
            
            if distance <= sight_range:
                has_los = ai_player.has_line_of_sight(enemy_pos, game_map)
                
                # 优先选择有视线的敌人，如果距离很近也考虑
                if has_los or (distance <= close_range and is_aggressive):
                    if distance < closest_distance or (has_los and not closest_has_los):
                        closest_enemy = enemy
                        closest_distance = distance
                        closest_has_los = has_los
        
        if closest_enemy:
            blackboard['target_enemy'] = closest_enemy
            blackboard['target_pos'] = pygame.Vector2(*closest_enemy['pos'])
            blackboard['has_line_of_sight'] = closest_has_los  # 记录是否有视线
            return NodeStatus.SUCCESS
        
        return NodeStatus.FAILURE


class HasEnemyInSoundRange(ConditionNode):
    """检查是否有敌人在声音范围内"""
    
    def tick(self, ai_player, blackboard):
        enemies = blackboard.get('enemies', [])
        team_manager = blackboard.get('team_manager')
        
        for enemy in enemies:
            if enemy.get('is_dead', False):
                continue
            
            # 检查是否是队友（先用are_teammates，其次team_id）
            if team_manager:
                if team_manager.are_teammates(ai_player.id, enemy.get('id')):
                    continue
                if hasattr(ai_player, 'team_id') and ai_player.team_id is not None:
                    enemy_team_id = enemy.get('team_id')
                    if enemy_team_id is not None and enemy_team_id == ai_player.team_id:
                        continue
            
            enemy_pos = pygame.Vector2(*enemy['pos'])
            distance = ai_player.pos.distance_to(enemy_pos)
            
            # 检查敌人是否发出声音
            if enemy.get('is_making_sound', False) and distance <= ai_player.sound_detection_range:
                blackboard['target_enemy'] = enemy
                blackboard['target_pos'] = enemy_pos
                return NodeStatus.SUCCESS
        
        return NodeStatus.FAILURE


class IsHealthLow(ConditionNode):
    """检查生命值是否低于阈值"""
    
    def __init__(self, name="IsHealthLow", threshold=30):
        super().__init__(name)
        self.threshold = threshold
    
    def tick(self, ai_player, blackboard):
        if ai_player.health <= self.threshold:
            return NodeStatus.SUCCESS
        return NodeStatus.FAILURE


class IsAmmoLow(ConditionNode):
    """检查弹药是否不足"""
    
    def __init__(self, name="IsAmmoLow", threshold=5):
        super().__init__(name)
        self.threshold = threshold
    
    def tick(self, ai_player, blackboard):
        if ai_player.ammo <= self.threshold:
            return NodeStatus.SUCCESS
        return NodeStatus.FAILURE


class IsInDanger(ConditionNode):
    """检查是否处于危险中（多个敌人靠近）"""
    
    def tick(self, ai_player, blackboard):
        enemies = blackboard.get('enemies', [])
        team_manager = blackboard.get('team_manager')
        danger_count = 0
        
        for enemy in enemies:
            if enemy.get('is_dead', False):
                continue
            
            # 检查是否是队友（先用are_teammates，其次team_id）
            if team_manager:
                if team_manager.are_teammates(ai_player.id, enemy.get('id')):
                    continue
                if hasattr(ai_player, 'team_id') and ai_player.team_id is not None:
                    enemy_team_id = enemy.get('team_id')
                    if enemy_team_id is not None and enemy_team_id == ai_player.team_id:
                        continue
            
            enemy_pos = pygame.Vector2(*enemy['pos'])
            distance = ai_player.pos.distance_to(enemy_pos)
            
            if distance < 150:  # 危险距离
                danger_count += 1
        
        if danger_count >= 2:
            return NodeStatus.SUCCESS
        return NodeStatus.FAILURE


class HasGoodCover(ConditionNode):
    """检查当前位置是否有良好的掩体"""
    
    def tick(self, ai_player, blackboard):
        # 这里可以调用代价计算器
        # 简化版本：检查附近是否有墙壁
        return NodeStatus.SUCCESS  # 暂时总是返回成功


class HasTeammateInDanger(ConditionNode):
    """检查是否有队友处于危险中"""
    
    def tick(self, ai_player, blackboard):
        allies = blackboard.get('allies', [])
        enemies = blackboard.get('enemies', [])
        
        if not allies:
            return NodeStatus.FAILURE
        
        for ally in allies:
            if ally.get('is_dead', False):
                continue
            
            ally_pos = pygame.Vector2(*ally['pos'])
            ally_health = ally.get('health', 100)
            
            # 检查队友附近是否有敌人
            nearby_enemies = 0
            closest_enemy_distance = float('inf')
            closest_enemy = None
            
            for enemy in enemies:
                if enemy.get('is_dead', False):
                    continue
                enemy_pos = pygame.Vector2(*enemy['pos'])
                distance = ally_pos.distance_to(enemy_pos)
                
                if distance < 200:  # 危险距离
                    nearby_enemies += 1
                    if distance < closest_enemy_distance:
                        closest_enemy_distance = distance
                        closest_enemy = enemy
            
            # 如果队友生命值低且附近有敌人，或者有多个敌人靠近
            if (ally_health < 50 and nearby_enemies > 0) or nearby_enemies >= 2:
                blackboard['teammate_in_danger'] = ally
                blackboard['teammate_danger_pos'] = ally_pos
                if closest_enemy:
                    blackboard['teammate_threat'] = closest_enemy
                return NodeStatus.SUCCESS
        
        return NodeStatus.FAILURE


class HasTeammateNearby(ConditionNode):
    """检查附近是否有队友"""
    
    def __init__(self, name="HasTeammateNearby", max_distance=300):
        super().__init__(name)
        self.max_distance = max_distance
    
    def tick(self, ai_player, blackboard):
        allies = blackboard.get('allies', [])
        
        if not allies:
            return NodeStatus.FAILURE
        
        for ally in allies:
            if ally.get('is_dead', False):
                continue
            
            ally_pos = pygame.Vector2(*ally['pos'])
            distance = ai_player.pos.distance_to(ally_pos)
            
            if distance <= self.max_distance:
                blackboard['nearby_teammate'] = ally
                return NodeStatus.SUCCESS
        
        return NodeStatus.FAILURE


class HasTeammateEngaging(ConditionNode):
    """检查是否有队友正在与敌人交火"""
    
    def tick(self, ai_player, blackboard):
        allies = blackboard.get('allies', [])
        enemies = blackboard.get('enemies', [])
        
        if not allies:
            return NodeStatus.FAILURE
        
        for ally in allies:
            if ally.get('is_dead', False):
                continue
            
            # 检查队友是否在射击
            if not ally.get('shooting', False):
                continue
            
            ally_pos = pygame.Vector2(*ally['pos'])
            
            # 检查队友附近是否有敌人
            for enemy in enemies:
                if enemy.get('is_dead', False):
                    continue
                enemy_pos = pygame.Vector2(*enemy['pos'])
                distance = ally_pos.distance_to(enemy_pos)
                
                if distance < 300:  # 交火距离
                    blackboard['teammate_engaging'] = ally
                    blackboard['teammate_target'] = enemy
                    return NodeStatus.SUCCESS
        
        return NodeStatus.FAILURE


# ==================== 行为节点 ====================

class ActionNode(BehaviorNode):
    """行为节点基类"""
    pass


class PatrolAction(ActionNode):
    """巡逻行为"""
    
    def __init__(self, name="PatrolAction"):
        super().__init__(name)
        self.stuck_time = 0
        self.last_position = None
        self.last_move_direction = None
        self.stuck_threshold = 0.3  # 进一步降低阈值，更快检测到卡住
        self.last_unstuck_attempt = 0
    
    def tick(self, ai_player, blackboard):
        game_map = blackboard.get('game_map')
        
        # 生成巡逻点（如果还没有）
        if not ai_player.patrol_points:
            ai_player.generate_patrol_points(game_map)
        
        # 检查是否卡住（位置没有变化，但有移动意图）
        current_time = time.time()
        if self.last_position:
            distance_moved = ai_player.pos.distance_to(self.last_position)
            # 如果移动距离小于5像素，判定为卡住
            if distance_moved < 5:
                # 如果上次有移动方向但位置没变化，说明卡住了
                if self.last_move_direction and self.last_move_direction.length() > 0.1:
                    self.stuck_time += 0.016  # 假设每帧16ms
                else:
                    self.stuck_time += 0.016 * 0.5  # 没有移动意图时，卡住时间增长较慢
            else:
                self.stuck_time = 0
        self.last_position = pygame.Vector2(ai_player.pos.x, ai_player.pos.y)
        
        # 执行巡逻逻辑
        target = ai_player.patrol_points[ai_player.current_patrol_index]
        
        # 如果卡住了，尝试恢复
        if self.stuck_time > self.stuck_threshold and current_time - self.last_unstuck_attempt > 0.3:
            self.last_unstuck_attempt = current_time
            # 使用智能脱困机制：找到可以移动的方向
            direction = target - ai_player.pos
            if direction.length() > 0:
                perpendicular = pygame.Vector2(-direction.y, direction.x).normalize()
                preferred_directions = [
                    perpendicular,  # 垂直于目标方向
                    -perpendicular,  # 反方向
                    direction.normalize(),  # 目标方向
                    -direction.normalize(),  # 远离目标方向
                    pygame.Vector2(1, 0),   # 右
                    pygame.Vector2(-1, 0),  # 左
                    pygame.Vector2(0, 1),   # 下
                    pygame.Vector2(0, -1),  # 上
                ]
            else:
                preferred_directions = None
            move_direction = ai_player.find_valid_move_direction(game_map, preferred_directions) * 0.8
            if move_direction.length() > 0:
                self.stuck_time = 0  # 重置卡住时间
                print(f"[AI巡逻] AI{ai_player.id}检测到卡住，找到可移动方向")
            else:
                print(f"[AI巡逻] AI{ai_player.id}检测到卡住，但无法找到可移动方向")
        else:
            ai_player.update_pathfinding(target)
            move_direction = ai_player.get_next_move_direction(game_map)
            
            # 如果路径规划失败，使用直接移动
            if move_direction.length() < 0.1:
                direction = target - ai_player.pos
                if direction.length() > 0:
                    move_direction = direction.normalize()
            
            # 检查移动方向是否会导致碰撞，如果会则立即使用脱困逻辑
            if move_direction.length() > 0.1:
                if not ai_player.can_move_in_direction(move_direction, game_map, distance=30):
                    # 方向会导致碰撞，立即使用脱困逻辑
                    direction = target - ai_player.pos
                    if direction.length() > 0:
                        perpendicular = pygame.Vector2(-direction.y, direction.x).normalize()
                        preferred_directions = [
                            perpendicular,  # 垂直于目标方向
                            -perpendicular,  # 反方向
                            direction.normalize(),  # 目标方向
                            -direction.normalize(),  # 远离目标方向
                            pygame.Vector2(1, 0),   # 右
                            pygame.Vector2(-1, 0),  # 左
                            pygame.Vector2(0, 1),   # 下
                            pygame.Vector2(0, -1),  # 上
                        ]
                    else:
                        preferred_directions = None
                    move_direction = ai_player.find_valid_move_direction(game_map, preferred_directions) * 0.8
        
        if move_direction.length() > 0:
            dx = move_direction.x
            dy = move_direction.y
            ai_player.angle = math.degrees(math.atan2(-dy, dx))
        
        # 记录移动方向，用于下次卡住检测
        self.last_move_direction = move_direction
        
        speed_multiplier = ai_player.get_movement_speed_multiplier()
        blackboard['action'] = {
            'move': move_direction * PLAYER_SPEED * speed_multiplier,
            'angle': ai_player.angle,
            'shoot': False,
            'reload': False
        }
        
        # 检查是否到达巡逻点
        if ai_player.pos.distance_to(target) < 50:
            ai_player.current_patrol_index = (ai_player.current_patrol_index + 1) % len(ai_player.patrol_points)
            ai_player.current_path = []
            ai_player.path_index = 0
        
        return NodeStatus.RUNNING


class ChaseAction(ActionNode):
    """追击行为"""
    
    def __init__(self, name="ChaseAction"):
        super().__init__(name)
        self.stuck_time = 0
        self.last_position = None
        self.last_move_direction = None
        self.stuck_threshold = 0.3  # 进一步降低阈值，更快检测到卡住
        self.last_unstuck_attempt = 0
    
    def tick(self, ai_player, blackboard):
        target_pos = blackboard.get('target_pos')
        if not target_pos:
            return NodeStatus.FAILURE
        
        game_map = blackboard.get('game_map')
        
        # 检查是否卡住（位置没有变化，但有移动意图）
        current_time = time.time()
        if self.last_position:
            distance_moved = ai_player.pos.distance_to(self.last_position)
            # 如果移动距离小于5像素，判定为卡住
            if distance_moved < 5:
                # 如果上次有移动方向但位置没变化，说明卡住了
                if self.last_move_direction and self.last_move_direction.length() > 0.1:
                    self.stuck_time += 0.016  # 假设每帧16ms
                else:
                    self.stuck_time += 0.016 * 0.5  # 没有移动意图时，卡住时间增长较慢
            else:
                self.stuck_time = 0
        self.last_position = pygame.Vector2(ai_player.pos.x, ai_player.pos.y)
        
        # 计算方向
        direction = target_pos - ai_player.pos
        distance = direction.length()
        
        # 如果卡住了，尝试恢复
        if self.stuck_time > self.stuck_threshold and current_time - self.last_unstuck_attempt > 0.3:
            self.last_unstuck_attempt = current_time
            # 使用智能脱困机制：找到可以移动的方向
            if direction.length() > 0:
                perpendicular = pygame.Vector2(-direction.y, direction.x).normalize()
                preferred_directions = [
                    perpendicular,  # 垂直于目标方向
                    -perpendicular,  # 反方向
                    direction.normalize(),  # 目标方向
                    -direction.normalize(),  # 远离目标方向
                    pygame.Vector2(1, 0),   # 右
                    pygame.Vector2(-1, 0),  # 左
                    pygame.Vector2(0, 1),   # 下
                    pygame.Vector2(0, -1),  # 上
                ]
            else:
                preferred_directions = None
            move_direction = ai_player.find_valid_move_direction(game_map, preferred_directions) * 0.8
            if move_direction.length() > 0:
                self.stuck_time = 0  # 重置卡住时间
                print(f"[AI追击] AI{ai_player.id}检测到卡住，找到可移动方向")
            else:
                print(f"[AI追击] AI{ai_player.id}检测到卡住，但无法找到可移动方向")
        else:
            # 尝试路径规划
            ai_player.update_pathfinding(target_pos)
            move_direction = ai_player.get_next_move_direction(game_map)
            
            # 如果路径规划失败，使用直接移动
            if move_direction.length() < 0.1:
                if direction.length() > 0:
                    move_direction = direction.normalize()
                    print(f"[AI追击] AI{ai_player.id}路径规划失败，使用直接移动")
            
            # 检查移动方向是否会导致碰撞，如果会则立即使用脱困逻辑
            if move_direction.length() > 0.1:
                if not ai_player.can_move_in_direction(move_direction, game_map, distance=30):
                    # 方向会导致碰撞，立即使用脱困逻辑
                    if direction.length() > 0:
                        perpendicular = pygame.Vector2(-direction.y, direction.x).normalize()
                        preferred_directions = [
                            perpendicular,  # 垂直于目标方向
                            -perpendicular,  # 反方向
                            direction.normalize(),  # 目标方向
                            -direction.normalize(),  # 远离目标方向
                            pygame.Vector2(1, 0),   # 右
                            pygame.Vector2(-1, 0),  # 左
                            pygame.Vector2(0, 1),   # 下
                            pygame.Vector2(0, -1),  # 上
                        ]
                    else:
                        preferred_directions = None
                    move_direction = ai_player.find_valid_move_direction(game_map, preferred_directions) * 0.8
        
        # 计算角度
        if move_direction.length() > 0:
            dx = move_direction.x
            dy = move_direction.y
            ai_player.angle = math.degrees(math.atan2(-dy, dx))
        elif direction.length() > 0:
            # 即使不能移动，也要面向目标
            dx = direction.x
            dy = direction.y
            ai_player.angle = math.degrees(math.atan2(-dy, dx))
        
        # 记录移动方向，用于下次卡住检测
        self.last_move_direction = move_direction
        
        # 如果距离很近，尝试攻击（激进型AI在追击时也应该攻击）
        can_shoot = False
        if distance < 350:  # 在攻击范围内
            can_shoot = (not ai_player.is_reloading and 
                        ai_player.ammo > 0 and 
                        time.time() - ai_player.last_shot_time >= BULLET_COOLDOWN and
                        ai_player.can_shoot_at_target(target_pos, game_map))
        
        speed_multiplier = ai_player.get_movement_speed_multiplier()
        blackboard['action'] = {
            'move': move_direction * PLAYER_SPEED * speed_multiplier,
            'angle': ai_player.angle,
            'shoot': can_shoot,
            'reload': False
        }
        
        return NodeStatus.RUNNING


class AttackAction(ActionNode):
    """攻击行为"""
    
    def __init__(self, name="AttackAction"):
        super().__init__(name)
        self.stuck_time = 0
        self.last_position = None
        self.last_move_direction = None
        self.stuck_threshold = 0.3  # 进一步降低阈值，更快检测到卡住（0.3秒）
        self.last_unstuck_attempt = 0
    
    def tick(self, ai_player, blackboard):
        target_pos = blackboard.get('target_pos')
        if not target_pos:
            return NodeStatus.FAILURE
        
        game_map = blackboard.get('game_map')
        direction = target_pos - ai_player.pos
        distance = direction.length()
        
        # 检查是否是激进型AI（提前判断，避免重复）
        is_aggressive = hasattr(ai_player, 'personality_traits') and \
                      ai_player.personality_traits.personality_type.value == 'aggressive'
        
        # 计算朝向目标的角度（始终面向目标）
        if distance > 0:
            dx = direction.x
            dy = direction.y
            target_angle = math.degrees(math.atan2(-dy, dx))
            ai_player.angle = target_angle
        
        # 检查是否卡住（位置没有变化，但有移动意图）
        current_time = time.time()
        if self.last_position:
            distance_moved = ai_player.pos.distance_to(self.last_position)
            # 如果移动距离小于5像素，判定为卡住
            if distance_moved < 5:
                # 如果上次有移动方向但位置没变化，说明卡住了
                if self.last_move_direction and self.last_move_direction.length() > 0.1:
                    self.stuck_time += 0.016  # 假设每帧16ms
                else:
                    self.stuck_time += 0.016 * 0.5  # 没有移动意图时，卡住时间增长较慢
            else:
                self.stuck_time = 0
        self.last_position = pygame.Vector2(ai_player.pos.x, ai_player.pos.y)
        
        # 智能定位：保持最佳攻击距离
        move_direction = pygame.Vector2(0, 0)
        
        # 如果卡住了，尝试恢复
        if self.stuck_time > self.stuck_threshold and current_time - self.last_unstuck_attempt > 0.3:
            self.last_unstuck_attempt = current_time
            # 使用智能脱困机制：找到可以移动的方向
            if direction.length() > 0:
                perpendicular = pygame.Vector2(-direction.y, direction.x).normalize()
                preferred_directions = [
                    perpendicular,  # 垂直于目标方向
                    -perpendicular,  # 反方向
                    -direction.normalize(),  # 远离目标方向（优先后退）
                    direction.normalize(),  # 目标方向
                    pygame.Vector2(1, 0),   # 右
                    pygame.Vector2(-1, 0),  # 左
                    pygame.Vector2(0, 1),   # 下
                    pygame.Vector2(0, -1),  # 上
                ]
            else:
                preferred_directions = None
            move_direction = ai_player.find_valid_move_direction(game_map, preferred_directions) * 0.8
            if move_direction.length() > 0:
                self.stuck_time = 0  # 重置卡住时间
                print(f"[AI攻击] AI{ai_player.id}检测到卡住，找到可移动方向")
            else:
                print(f"[AI攻击] AI{ai_player.id}检测到卡住，但无法找到可移动方向")
        elif distance < 80:  # 非常近，直接后退（不使用路径规划）
            # 直接后退，不使用路径规划，避免卡在墙边
            retreat_dir = (ai_player.pos - target_pos)
            if retreat_dir.length() > 0:
                move_direction = retreat_dir.normalize() * 0.8
        elif distance < 120:  # 太近，后退
            retreat_pos = ai_player.pos + (ai_player.pos - target_pos).normalize() * 100
            ai_player.update_pathfinding(retreat_pos)
            move_direction = ai_player.get_next_move_direction(game_map)
            
            # 如果路径规划失败，使用直接后退
            if move_direction.length() < 0.1:
                retreat_dir = (ai_player.pos - target_pos)
                if retreat_dir.length() > 0:
                    move_direction = retreat_dir.normalize() * 0.6
        elif distance > 350:  # 太远，前进（激进型AI应该更积极地接近）
            ai_player.update_pathfinding(target_pos)
            move_direction = ai_player.get_next_move_direction(game_map)
            
            # 如果路径规划失败，使用直接前进
            if move_direction.length() < 0.1:
                if direction.length() > 0:
                    # 激进型AI更积极地接近
                    is_aggressive = hasattr(ai_player, 'personality_traits') and \
                                  ai_player.personality_traits.personality_type.value == 'aggressive'
                    move_speed = 0.9 if is_aggressive else 0.8
                    move_direction = direction.normalize() * move_speed
        elif 120 <= distance <= 350:  # 最佳距离（扩大范围），侧向移动或直接接近
            # 检查是否有视线
            has_los = blackboard.get('has_line_of_sight', ai_player.can_shoot_at_target(target_pos, game_map))
            
            if has_los:
                # 有视线
                if is_aggressive and distance < 250:
                    # 激进型AI在中等距离时可以直接接近，更激进
                    move_direction = direction.normalize() * 0.7
                else:
                    # 侧向移动（非激进型或距离较远）
                    perpendicular = pygame.Vector2(-direction.y, direction.x).normalize()
                    if random.random() > 0.5:
                        perpendicular = -perpendicular
                    move_direction = perpendicular * 0.5
            else:
                # 没有视线，说明直接路径被墙壁阻挡
                # 激进型AI：使用路径规划而不是直接冲向墙壁
                if is_aggressive:
                    # 路径被阻挡，使用路径规划
                    ai_player.update_pathfinding(target_pos)
                    move_direction = ai_player.get_next_move_direction(game_map)
                    
                    # 如果路径规划失败，尝试寻找其他方向
                    if move_direction.length() < 0.1:
                        # 尝试多个角度找到不被阻挡的方向
                        found_direction = False
                        for angle_offset in [-math.pi/4, math.pi/4, -math.pi/2, math.pi/2, math.pi, -math.pi]:
                            cos_a = math.cos(angle_offset)
                            sin_a = math.sin(angle_offset)
                            test_dir = pygame.Vector2(
                                direction.x * cos_a - direction.y * sin_a,
                                direction.x * sin_a + direction.y * cos_a
                            )
                            if test_dir.length() > 0:
                                test_dir = test_dir.normalize()
                                test_pos = ai_player.pos + test_dir * 50
                                if ai_player.has_line_of_sight(test_pos, game_map):
                                    move_direction = test_dir * 0.6
                                    found_direction = True
                                    break
                        
                        # 如果还是没找到，使用路径规划的目标方向
                        if not found_direction:
                            ai_player.update_pathfinding(target_pos)
                            move_direction = ai_player.get_next_move_direction(game_map)
                            if move_direction.length() < 0.1:
                                # 最后备选：侧向移动
                                perpendicular = pygame.Vector2(-direction.y, direction.x).normalize()
                                if random.random() > 0.5:
                                    perpendicular = -perpendicular
                                move_direction = perpendicular * 0.5
                else:
                    # 非激进型AI：尝试多个角度找到有视线的位置
                    found_position = False
                    for angle_offset in [-math.pi/4, math.pi/4, -math.pi/2, math.pi/2, 0]:
                        # 计算旋转后的方向向量
                        cos_a = math.cos(angle_offset)
                        sin_a = math.sin(angle_offset)
                        test_dir = pygame.Vector2(
                            direction.x * cos_a - direction.y * sin_a,
                            direction.x * sin_a + direction.y * cos_a
                        )
                        if test_dir.length() > 0:
                            test_dir = test_dir.normalize()
                            # 检查这个方向是否有更好的视线（简化：直接使用这个方向）
                            move_direction = test_dir * 0.6
                            found_position = True
                            break
                    
                    # 如果还是没找到，使用路径规划
                    if not found_position:
                        ai_player.update_pathfinding(target_pos)
                        move_direction = ai_player.get_next_move_direction(game_map)
                        if move_direction.length() < 0.1:
                            if direction.length() > 0:
                                move_direction = direction.normalize() * 0.5
        
        # 射击判断（激进型AI应该更积极地射击）
        # 重新检查视线（因为位置可能已经改变）
        has_los = ai_player.can_shoot_at_target(target_pos, game_map)
        
        can_shoot = (not ai_player.is_reloading and 
                    ai_player.ammo > 0 and 
                    time.time() - ai_player.last_shot_time >= BULLET_COOLDOWN and
                    has_los)
        
        # 确保激进型AI有移动方向（即使没有视线也要接近）
        # 注意：is_aggressive在上面已经定义过了
        if move_direction.length() < 0.1 and is_aggressive and distance > 0:
            # 如果还没有移动方向，检查是否有视线
            # 如果没有视线，说明路径被阻挡，不应该直接冲向墙壁
            if has_los:
                # 有视线，可以直接接近
                if direction.length() > 0:
                    move_direction = direction.normalize() * 0.6
                    print(f"[AI攻击] AI{ai_player.id}使用直接接近（有视线）")
            else:
                # 没有视线，尝试侧向移动而不是直接冲向墙壁
                if direction.length() > 0:
                    perpendicular = pygame.Vector2(-direction.y, direction.x).normalize()
                    if random.random() > 0.5:
                        perpendicular = -perpendicular
                    move_direction = perpendicular * 0.5
                    print(f"[AI攻击] AI{ai_player.id}使用侧向移动（路径被阻挡）")
        
        # 检查移动方向是否会导致碰撞，如果会则立即使用脱困逻辑
        if move_direction.length() > 0.1:
            if not ai_player.can_move_in_direction(move_direction, game_map, distance=30):
                # 方向会导致碰撞，立即使用脱困逻辑
                if direction.length() > 0:
                    perpendicular = pygame.Vector2(-direction.y, direction.x).normalize()
                    preferred_directions = [
                        perpendicular,  # 垂直于目标方向
                        -perpendicular,  # 反方向
                        -direction.normalize(),  # 远离目标方向（优先后退）
                        direction.normalize(),  # 目标方向
                        pygame.Vector2(1, 0),   # 右
                        pygame.Vector2(-1, 0),  # 左
                        pygame.Vector2(0, 1),   # 下
                        pygame.Vector2(0, -1),  # 上
                    ]
                else:
                    preferred_directions = None
                move_direction = ai_player.find_valid_move_direction(game_map, preferred_directions) * 0.8
        
        # 即使不能射击，也应该保持面向目标
        if not can_shoot and distance > 0:
            # 检查是否需要装填
            if ai_player.ammo == 0 and not ai_player.is_reloading:
                blackboard['action'] = {
                    'move': move_direction * PLAYER_SPEED * 0.5,
                    'angle': ai_player.angle,
                    'shoot': False,
                    'reload': True
                }
                return NodeStatus.RUNNING
        
        # 记录移动方向，用于下次卡住检测
        self.last_move_direction = move_direction
        
        speed_multiplier = ai_player.get_movement_speed_multiplier()
        # 激进型AI移动更快
        move_speed = 1.0 if distance > 200 else 0.8
        if is_aggressive and not has_los:
            move_speed = 1.2  # 没有视线时更积极地移动
        
        blackboard['action'] = {
            'move': move_direction * PLAYER_SPEED * move_speed * speed_multiplier,
            'angle': ai_player.angle,
            'shoot': can_shoot,
            'reload': False
        }
        
        return NodeStatus.RUNNING


class RetreatAction(ActionNode):
    """撤退行为"""
    
    def tick(self, ai_player, blackboard):
        target_pos = blackboard.get('target_pos')
        if not target_pos:
            return NodeStatus.FAILURE
        
        # 计算撤退目标位置
        retreat_direction = (ai_player.pos - target_pos).normalize()
        retreat_distance = 300
        retreat_target = ai_player.pos + retreat_direction * retreat_distance
        
        # 确保在地图范围内
        map_size = ROOM_SIZE * 3
        retreat_target.x = max(50, min(map_size - 50, retreat_target.x))
        retreat_target.y = max(50, min(map_size - 50, retreat_target.y))
        
        game_map = blackboard.get('game_map')
        ai_player.update_pathfinding(retreat_target)
        move_direction = ai_player.get_next_move_direction(game_map)
        
        if move_direction.length() == 0:
            direction = ai_player.pos - target_pos
            if direction.length() > 0:
                move_direction = direction.normalize()
        
        # 保持面向敌人
        to_enemy = target_pos - ai_player.pos
        if to_enemy.length() > 0:
            dx = to_enemy.x
            dy = to_enemy.y
            ai_player.angle = math.degrees(math.atan2(-dy, dx))
        
        can_shoot = (not ai_player.is_reloading and 
                    ai_player.ammo > 0 and 
                    time.time() - ai_player.last_shot_time >= BULLET_COOLDOWN)
        
        speed_multiplier = ai_player.get_movement_speed_multiplier()
        blackboard['action'] = {
            'move': move_direction * PLAYER_SPEED * speed_multiplier,
            'angle': ai_player.angle,
            'shoot': can_shoot,
            'reload': False
        }
        
        return NodeStatus.RUNNING


class FindCoverAction(ActionNode):
    """寻找掩体行为"""
    
    def __init__(self, name="FindCover"):
        super().__init__(name)
        self.cost_calculator = None
    
    def tick(self, ai_player, blackboard):
        # 延迟初始化代价计算器
        if self.cost_calculator is None:
            from ai_cost_calculator import AICostCalculator
            self.cost_calculator = AICostCalculator()
        
        enemies = blackboard.get('enemies', [])
        game_map = blackboard.get('game_map')
        
        # 使用代价计算器寻找最佳掩体位置
        best_pos = self.cost_calculator.find_best_position(
            ai_player.pos, enemies, game_map, max_search_radius=200
        )
        
        if best_pos:
            ai_player.update_pathfinding(best_pos)
            move_direction = ai_player.get_next_move_direction(game_map)
            
            if move_direction.length() > 0:
                dx = move_direction.x
                dy = move_direction.y
                ai_player.angle = math.degrees(math.atan2(-dy, dx))
            
            speed_multiplier = ai_player.get_movement_speed_multiplier()
            blackboard['action'] = {
                'move': move_direction * PLAYER_SPEED * speed_multiplier,
                'angle': ai_player.angle,
                'shoot': False,
                'reload': False
            }
            
            # 检查是否到达掩体位置
            if ai_player.pos.distance_to(best_pos) < 30:
                return NodeStatus.SUCCESS
            
            return NodeStatus.RUNNING
        
        return NodeStatus.FAILURE


class FlankAction(ActionNode):
    """侧翼攻击行为"""
    
    def __init__(self, name="Flank"):
        super().__init__(name)
        self.cost_calculator = None
    
    def tick(self, ai_player, blackboard):
        if self.cost_calculator is None:
            from ai_cost_calculator import AICostCalculator
            self.cost_calculator = AICostCalculator()
        
        target_pos = blackboard.get('target_pos')
        target_enemy = blackboard.get('target_enemy')
        
        if not target_pos or not target_enemy:
            return NodeStatus.FAILURE
        
        enemy_pos = pygame.Vector2(*target_enemy['pos'])
        game_map = blackboard.get('game_map')
        
        # 寻找侧翼位置
        flank_pos = self.cost_calculator.find_flanking_position(
            ai_player.pos, target_pos, enemy_pos, game_map
        )
        
        if flank_pos:
            ai_player.update_pathfinding(flank_pos)
            move_direction = ai_player.get_next_move_direction(game_map)
            
            if move_direction.length() > 0:
                dx = move_direction.x
                dy = move_direction.y
                ai_player.angle = math.degrees(math.atan2(-dy, dx))
            
            speed_multiplier = ai_player.get_movement_speed_multiplier()
            blackboard['action'] = {
                'move': move_direction * PLAYER_SPEED * speed_multiplier,
                'angle': ai_player.angle,
                'shoot': False,
                'reload': False
            }
            
            # 检查是否到达侧翼位置
            if ai_player.pos.distance_to(flank_pos) < 50:
                return NodeStatus.SUCCESS
            
            return NodeStatus.RUNNING
        
        return NodeStatus.FAILURE


class ReloadAction(ActionNode):
    """装填行为"""
    
    def tick(self, ai_player, blackboard):
        if not ai_player.is_reloading:
            ai_player.is_reloading = True
            ai_player.reload_start_time = time.time()
        
        blackboard['action'] = {
            'move': pygame.Vector2(0, 0),
            'angle': ai_player.angle,
            'shoot': False,
            'reload': True
        }
        
        # 检查装填是否完成
        if time.time() - ai_player.reload_start_time >= RELOAD_TIME:
            ai_player.is_reloading = False
            ai_player.ammo = MAGAZINE_SIZE
            return NodeStatus.SUCCESS
        
        return NodeStatus.RUNNING


class AmbushAction(ActionNode):
    """伏击行为"""
    
    def __init__(self, name="Ambush"):
        super().__init__(name)
        self.cost_calculator = None
        self.ambush_position = None
        self.wait_time = 0
    
    def tick(self, ai_player, blackboard):
        if self.cost_calculator is None:
            from ai_cost_calculator import AICostCalculator
            self.cost_calculator = AICostCalculator()
        
        target_enemy = blackboard.get('target_enemy')
        if not target_enemy:
            return NodeStatus.FAILURE
        
        enemy_pos = pygame.Vector2(*target_enemy['pos'])
        game_map = blackboard.get('game_map')
        
        # 如果没有伏击位置，寻找一个
        if self.ambush_position is None:
            # 预测敌人位置（假设敌人会继续移动）
            predicted_pos = enemy_pos  # 简化：使用当前位置
            
            # 寻找最佳伏击位置
            best_ambush_score = -1
            best_pos = None
            
            # 尝试多个角度
            for angle_offset in [0, math.pi/4, math.pi/2, 3*math.pi/4, math.pi, -math.pi/4, -math.pi/2, -3*math.pi/4]:
                distance = 200  # 伏击距离
                ambush_x = enemy_pos.x + math.cos(angle_offset) * distance
                ambush_y = enemy_pos.y - math.sin(angle_offset) * distance
                
                # 确保在地图范围内
                ambush_x = max(50, min(ROOM_SIZE * 3 - 50, ambush_x))
                ambush_y = max(50, min(ROOM_SIZE * 3 - 50, ambush_y))
                
                ambush_pos = pygame.Vector2(ambush_x, ambush_y)
                
                # 检查是否可通行
                if self._is_in_wall(ambush_pos, game_map):
                    continue
                
                # 计算伏击价值
                ambush_value = self.cost_calculator.calculate_ambush_value(
                    ambush_pos, predicted_pos, game_map
                )
                
                if ambush_value > best_ambush_score:
                    best_ambush_score = ambush_value
                    best_pos = ambush_pos
            
            if best_pos:
                self.ambush_position = best_pos
            else:
                return NodeStatus.FAILURE
        
        # 移动到伏击位置
        distance_to_ambush = ai_player.pos.distance_to(self.ambush_position)
        if distance_to_ambush > 30:
            ai_player.update_pathfinding(self.ambush_position)
            move_direction = ai_player.get_next_move_direction(game_map)
            
            if move_direction.length() > 0:
                dx = move_direction.x
                dy = move_direction.y
                ai_player.angle = math.degrees(math.atan2(-dy, dx))
            
            # 使用静步移动到伏击位置
            blackboard['action'] = {
                'move': move_direction * PLAYER_SPEED * 0.4,  # 静步速度
                'angle': ai_player.angle,
                'shoot': False,
                'reload': False,
                'is_walking': True  # 静步
            }
            return NodeStatus.RUNNING
        else:
            # 到达伏击位置，等待敌人
            self.wait_time += 0.016  # 假设每帧16ms
            
            # 面向敌人
            to_enemy = enemy_pos - ai_player.pos
            if to_enemy.length() > 0:
                dx = to_enemy.x
                dy = to_enemy.y
                ai_player.angle = math.degrees(math.atan2(-dy, dx))
            
            # 检查是否可以攻击
            can_shoot = (not ai_player.is_reloading and 
                        ai_player.ammo > 0 and 
                        time.time() - ai_player.last_shot_time >= BULLET_COOLDOWN and
                        ai_player.can_shoot_at_target(enemy_pos, game_map))
            
            # 等待2秒后开始攻击，或者敌人进入范围立即攻击
            if self.wait_time > 2.0 or (can_shoot and ai_player.pos.distance_to(enemy_pos) < 300):
                blackboard['action'] = {
                    'move': pygame.Vector2(0, 0),
                    'angle': ai_player.angle,
                    'shoot': can_shoot,
                    'reload': False,
                    'is_walking': False
                }
                return NodeStatus.RUNNING
            else:
                blackboard['action'] = {
                    'move': pygame.Vector2(0, 0),
                    'angle': ai_player.angle,
                    'shoot': False,
                    'reload': False,
                    'is_walking': True  # 等待时保持静步
                }
                return NodeStatus.RUNNING
    
    def _is_in_wall(self, pos, game_map):
        """检查位置是否在墙壁内"""
        for wall in game_map.walls:
            if wall.collidepoint(pos.x, pos.y):
                return True
        return False
    
    def reset(self):
        super().reset()
        self.ambush_position = None
        self.wait_time = 0


class TeamSupportAction(ActionNode):
    """团队支援行为 - 移动到需要帮助的队友附近"""
    
    def __init__(self, name="TeamSupport"):
        super().__init__(name)
        self.cost_calculator = None
    
    def tick(self, ai_player, blackboard):
        if self.cost_calculator is None:
            try:
                from ai_cost_calculator import AICostCalculator
                self.cost_calculator = AICostCalculator()
            except ImportError:
                self.cost_calculator = None
        
        allies = blackboard.get('allies', [])
        enemies = blackboard.get('enemies', [])
        game_map = blackboard.get('game_map')
        teammate_in_danger = blackboard.get('teammate_in_danger')
        
        if not allies and not teammate_in_danger:
            return NodeStatus.FAILURE
        
        # 优先帮助处于危险中的队友
        target_teammate = teammate_in_danger
        if not target_teammate:
            # 找到需要支援的队友（被敌人攻击的队友）
            min_distance = float('inf')
            for ally in allies:
                if ally.get('is_dead', False):
                    continue
                
                ally_pos = pygame.Vector2(*ally['pos'])
                ally_distance = ai_player.pos.distance_to(ally_pos)
                
                # 检查队友附近是否有敌人
                nearby_enemies = 0
                for enemy in enemies:
                    if enemy.get('is_dead', False):
                        continue
                    enemy_pos = pygame.Vector2(*enemy['pos'])
                    if ally_pos.distance_to(enemy_pos) < 200:
                        nearby_enemies += 1
                
                # 如果队友附近有敌人且距离较近，需要支援
                if nearby_enemies > 0 and ally_distance < min_distance and ally_distance < 400:
                    target_teammate = ally
                    min_distance = ally_distance
        
        if not target_teammate:
            return NodeStatus.FAILURE
        
        # 移动到队友附近的支援位置
        teammate_pos = pygame.Vector2(*target_teammate['pos'])
        teammate_threat = blackboard.get('teammate_threat')
        
        # 计算支援位置（在队友侧翼，可以攻击威胁队友的敌人）
        if teammate_threat:
            threat_pos = pygame.Vector2(*teammate_threat['pos'])
            # 计算侧翼位置（垂直于队友到敌人的方向）
            to_threat = threat_pos - teammate_pos
            if to_threat.length() > 0:
                perpendicular = pygame.Vector2(-to_threat.y, to_threat.x).normalize()
                # 选择离敌人更近的侧翼位置
                support_offset = perpendicular * 100
                support_pos = teammate_pos + support_offset
            else:
                support_pos = teammate_pos + pygame.Vector2(100, 0)
        else:
            # 没有明确威胁，移动到队友附近
            direction_to_teammate = teammate_pos - ai_player.pos
            if direction_to_teammate.length() > 0:
                # 保持一定距离（100-150像素）
                if direction_to_teammate.length() < 100:
                    support_pos = ai_player.pos + direction_to_teammate.normalize() * 120
                elif direction_to_teammate.length() > 200:
                    support_pos = teammate_pos
                else:
                    support_pos = teammate_pos
            else:
                support_pos = teammate_pos + pygame.Vector2(100, 0)
        
        # 确保在地图范围内
        map_size = ROOM_SIZE * 3
        support_pos.x = max(50, min(map_size - 50, support_pos.x))
        support_pos.y = max(50, min(map_size - 50, support_pos.y))
        
        ai_player.update_pathfinding(support_pos)
        move_direction = ai_player.get_next_move_direction(game_map)
        
        # 如果路径规划失败，直接朝队友移动
        if move_direction.length() < 0.1:
            direction_to_support = support_pos - ai_player.pos
            if direction_to_support.length() > 0:
                move_direction = direction_to_support.normalize()
        
        # 面向威胁（如果有）
        if teammate_threat:
            threat_pos = pygame.Vector2(*teammate_threat['pos'])
            direction_to_threat = threat_pos - ai_player.pos
            if direction_to_threat.length() > 0:
                dx = direction_to_threat.x
                dy = direction_to_threat.y
                ai_player.angle = math.degrees(math.atan2(-dy, dx))
        elif move_direction.length() > 0:
            dx = move_direction.x
            dy = move_direction.y
            ai_player.angle = math.degrees(math.atan2(-dy, dx))
        
        # 如果靠近支援位置且能看到威胁，可以射击
        can_shoot = False
        if teammate_threat:
            threat_pos = pygame.Vector2(*teammate_threat['pos'])
            distance_to_threat = ai_player.pos.distance_to(threat_pos)
            if distance_to_threat < 350 and ai_player.can_shoot_at_target(threat_pos, game_map):
                can_shoot = (not ai_player.is_reloading and 
                           ai_player.ammo > 0 and 
                           time.time() - ai_player.last_shot_time >= BULLET_COOLDOWN)
        
        speed_multiplier = ai_player.get_movement_speed_multiplier()
        blackboard['action'] = {
            'move': move_direction * PLAYER_SPEED * speed_multiplier,
            'angle': ai_player.angle,
            'shoot': can_shoot,
            'reload': False
        }
        
        # 检查是否到达支援位置
        if ai_player.pos.distance_to(support_pos) < 50:
            return NodeStatus.SUCCESS
        
        return NodeStatus.RUNNING


class CoordinateAttackAction(ActionNode):
    """协同攻击行为 - 与队友一起攻击同一目标"""
    
    def tick(self, ai_player, blackboard):
        teammate_engaging = blackboard.get('teammate_engaging')
        teammate_target = blackboard.get('teammate_target')
        game_map = blackboard.get('game_map')
        
        if not teammate_engaging or not teammate_target:
            return NodeStatus.FAILURE
        
        target_enemy = teammate_target
        target_pos = pygame.Vector2(*target_enemy['pos'])
        teammate_pos = pygame.Vector2(*teammate_engaging['pos'])
        
        # 计算协同攻击位置（与队友形成交叉火力）
        direction_to_teammate = teammate_pos - target_pos
        if direction_to_teammate.length() > 0:
            # 选择与队友相对的位置
            perpendicular = pygame.Vector2(-direction_to_teammate.y, direction_to_teammate.x).normalize()
            # 随机选择一侧
            side = 1 if random.random() > 0.5 else -1
            attack_offset = perpendicular * (150 * side)
            attack_pos = target_pos + attack_offset
        else:
            attack_pos = target_pos + pygame.Vector2(150, 0)
        
        # 确保在地图范围内
        map_size = ROOM_SIZE * 3
        attack_pos.x = max(50, min(map_size - 50, attack_pos.x))
        attack_pos.y = max(50, min(map_size - 50, attack_pos.y))
        
        # 移动到攻击位置或直接攻击
        distance_to_target = ai_player.pos.distance_to(target_pos)
        distance_to_attack_pos = ai_player.pos.distance_to(attack_pos)
        
        # 如果距离目标较远，移动到攻击位置
        if distance_to_attack_pos > 80:
            ai_player.update_pathfinding(attack_pos)
            move_direction = ai_player.get_next_move_direction(game_map)
            
            if move_direction.length() < 0.1:
                direction_to_attack = attack_pos - ai_player.pos
                if direction_to_attack.length() > 0:
                    move_direction = direction_to_attack.normalize()
        else:
            # 已经在攻击位置，侧向移动保持距离
            direction_to_target = target_pos - ai_player.pos
            if direction_to_target.length() > 0:
                perpendicular = pygame.Vector2(-direction_to_target.y, direction_to_target.x).normalize()
                move_direction = perpendicular * 0.3
            else:
                move_direction = pygame.Vector2(0, 0)
        
        # 面向目标
        direction_to_target = target_pos - ai_player.pos
        if direction_to_target.length() > 0:
            dx = direction_to_target.x
            dy = direction_to_target.y
            ai_player.angle = math.degrees(math.atan2(-dy, dx))
        
        # 如果能看到目标，射击
        can_shoot = False
        if distance_to_target < 350:
            has_los = ai_player.can_shoot_at_target(target_pos, game_map)
            can_shoot = (has_los and 
                        not ai_player.is_reloading and 
                        ai_player.ammo > 0 and 
                        time.time() - ai_player.last_shot_time >= BULLET_COOLDOWN)
        
        speed_multiplier = ai_player.get_movement_speed_multiplier()
        blackboard['action'] = {
            'move': move_direction * PLAYER_SPEED * speed_multiplier,
            'angle': ai_player.angle,
            'shoot': can_shoot,
            'reload': False
        }
        
        return NodeStatus.RUNNING


class CoverTeammateAction(ActionNode):
    """掩护队友行为 - 为队友提供火力掩护"""
    
    def tick(self, ai_player, blackboard):
        allies = blackboard.get('allies', [])
        enemies = blackboard.get('enemies', [])
        game_map = blackboard.get('game_map')
        nearby_teammate = blackboard.get('nearby_teammate')
        
        if not allies and not nearby_teammate:
            return NodeStatus.FAILURE
        
        # 选择最近的队友
        target_teammate = nearby_teammate
        if not target_teammate:
            min_distance = float('inf')
            for ally in allies:
                if ally.get('is_dead', False):
                    continue
                ally_pos = pygame.Vector2(*ally['pos'])
                distance = ai_player.pos.distance_to(ally_pos)
                if distance < min_distance and distance < 300:
                    target_teammate = ally
                    min_distance = distance
        
        if not target_teammate:
            return NodeStatus.FAILURE
        
        teammate_pos = pygame.Vector2(*target_teammate['pos'])
        
        # 寻找威胁队友的敌人
        threat_enemy = None
        min_threat_distance = float('inf')
        
        for enemy in enemies:
            if enemy.get('is_dead', False):
                continue
            enemy_pos = pygame.Vector2(*enemy['pos'])
            distance_to_teammate = teammate_pos.distance_to(enemy_pos)
            
            # 如果敌人靠近队友或在攻击范围内
            if distance_to_teammate < 300:
                if distance_to_teammate < min_threat_distance:
                    threat_enemy = enemy
                    min_threat_distance = distance_to_teammate
        
        # 移动到掩护位置（在队友后方，可以射击威胁）
        if threat_enemy:
            threat_pos = pygame.Vector2(*threat_enemy['pos'])
            # 计算掩护位置（在队友和威胁之间，但偏向队友）
            direction_to_threat = threat_pos - teammate_pos
            if direction_to_threat.length() > 0:
                cover_offset = -direction_to_threat.normalize() * 80  # 在队友后方
                cover_pos = teammate_pos + cover_offset
            else:
                cover_pos = teammate_pos + pygame.Vector2(0, -80)
        else:
            # 没有威胁，保持在队友附近
            direction_to_teammate = teammate_pos - ai_player.pos
            if direction_to_teammate.length() > 150:
                cover_pos = teammate_pos
            else:
                cover_pos = ai_player.pos
        
        # 确保在地图范围内
        map_size = ROOM_SIZE * 3
        cover_pos.x = max(50, min(map_size - 50, cover_pos.x))
        cover_pos.y = max(50, min(map_size - 50, cover_pos.y))
        
        # 移动到掩护位置
        distance_to_cover = ai_player.pos.distance_to(cover_pos)
        if distance_to_cover > 50:
            ai_player.update_pathfinding(cover_pos)
            move_direction = ai_player.get_next_move_direction(game_map)
            
            if move_direction.length() < 0.1:
                direction_to_cover = cover_pos - ai_player.pos
                if direction_to_cover.length() > 0:
                    move_direction = direction_to_cover.normalize()
        else:
            move_direction = pygame.Vector2(0, 0)
        
        # 面向威胁或队友
        if threat_enemy:
            threat_pos = pygame.Vector2(*threat_enemy['pos'])
            direction_to_threat = threat_pos - ai_player.pos
            if direction_to_threat.length() > 0:
                dx = direction_to_threat.x
                dy = direction_to_threat.y
                ai_player.angle = math.degrees(math.atan2(-dy, dx))
        elif direction_to_teammate.length() > 0:
            dx = direction_to_teammate.x
            dy = direction_to_teammate.y
            ai_player.angle = math.degrees(math.atan2(-dy, dx))
        
        # 如果有威胁且能看到，射击
        can_shoot = False
        if threat_enemy:
            threat_pos = pygame.Vector2(*threat_enemy['pos'])
            distance_to_threat = ai_player.pos.distance_to(threat_pos)
            if distance_to_threat < 350:
                has_los = ai_player.can_shoot_at_target(threat_pos, game_map)
                can_shoot = (has_los and 
                           not ai_player.is_reloading and 
                           ai_player.ammo > 0 and 
                           time.time() - ai_player.last_shot_time >= BULLET_COOLDOWN)
        
        speed_multiplier = ai_player.get_movement_speed_multiplier()
        blackboard['action'] = {
            'move': move_direction * PLAYER_SPEED * speed_multiplier,
            'angle': ai_player.angle,
            'shoot': can_shoot,
            'reload': False
        }
        
        return NodeStatus.RUNNING


class BehaviorTree:
    """行为树"""
    
    def __init__(self, root_node):
        self.root = root_node
        self.blackboard = {}  # 黑板（共享数据）
    
    def tick(self, ai_player, enemies, game_map, team_manager=None, allies=None):
        """
        执行行为树
        
        Args:
            ai_player: AI玩家对象
            enemies: 敌人列表
            game_map: 游戏地图对象
            team_manager: 团队管理器（可选）
            allies: 队友列表（可选）
            
        Returns:
            dict: 执行的动作
        """
        # 更新黑板
        self.blackboard['enemies'] = enemies
        self.blackboard['game_map'] = game_map
        self.blackboard['team_manager'] = team_manager
        self.blackboard['allies'] = allies or []
        self.blackboard['action'] = {
            'move': pygame.Vector2(0, 0),
            'angle': ai_player.angle,
            'shoot': False,
            'reload': False
        }
        
        # 执行根节点
        if self.root:
            self.root.tick(ai_player, self.blackboard)
        
        # 返回动作
        return self.blackboard.get('action', {
            'move': pygame.Vector2(0, 0),
            'angle': ai_player.angle,
            'shoot': False,
            'reload': False
        })
    
    def create_aggressive_tree(self):
        """创建激进型行为树 - 支持团队合作"""
        root = SelectorNode("Root")
        
        # 装填（优先处理，但只在弹药用完时）
        reload_sequence = SequenceNode("ReloadSequence")
        reload_sequence.children = [
            IsAmmoLow("IsAmmoLow", threshold=0),  # 只有弹药用完才装填
            ReloadAction("ReloadAction")
        ]
        
        # 团队支援（如果有队友需要帮助）
        support_sequence = SequenceNode("SupportSequence")
        support_sequence.children = [
            HasTeammateInDanger("HasTeammateInDanger"),
            TeamSupportAction("TeamSupportAction")
        ]
        
        # 优先攻击（激进型AI应该优先攻击）
        attack_sequence = SequenceNode("AttackSequence")
        attack_sequence.children = [
            HasEnemyInSight("HasEnemyInSight"),
            AttackAction("AttackAction")
        ]
        
        # 协同攻击（与队友一起攻击）
        coordinate_attack_sequence = SequenceNode("CoordinateAttackSequence")
        coordinate_attack_sequence.children = [
            HasTeammateEngaging("HasTeammateEngaging"),
            CoordinateAttackAction("CoordinateAttackAction")
        ]
        
        # 追击（即使没有视线，也要追击）
        chase_sequence = SequenceNode("ChaseSequence")
        chase_sequence.children = [
            HasEnemyInSoundRange("HasEnemyInSoundRange"),
            ChaseAction("ChaseAction")
        ]
        
        # 巡逻（最后的选择）
        patrol_action = PatrolAction("PatrolAction")
        
        # 激进型AI的优先级：装填 > 支援队友 > 攻击 > 协同攻击 > 追击 > 巡逻
        root.children = [
            reload_sequence, 
            support_sequence, 
            attack_sequence, 
            coordinate_attack_sequence,
            chase_sequence, 
            patrol_action
        ]
        self.root = root
        return root
    
    def create_defensive_tree(self):
        """创建防御型行为树"""
        root = SelectorNode("Root")
        
        # 装填（防御型AI也应该在安全时换弹）
        reload_sequence = SequenceNode("ReloadSequence")
        reload_sequence.children = [
            IsAmmoLow("IsAmmoLow", threshold=5),
            ReloadAction("ReloadAction")
        ]
        
        # 低生命值时撤退
        retreat_sequence = SequenceNode("RetreatSequence")
        retreat_sequence.children = [
            IsHealthLow("IsHealthLow", threshold=30),
            HasEnemyInSight("HasEnemyInSight"),
            RetreatAction("RetreatAction")
        ]
        
        # 寻找掩体
        cover_sequence = SequenceNode("CoverSequence")
        cover_sequence.children = [
            IsInDanger("IsInDanger"),
            FindCoverAction("FindCoverAction")
        ]
        
        # 攻击
        attack_sequence = SequenceNode("AttackSequence")
        attack_sequence.children = [
            HasEnemyInSight("HasEnemyInSight"),
            AttackAction("AttackAction")
        ]
        
        # 巡逻
        patrol_action = PatrolAction("PatrolAction")
        
        root.children = [reload_sequence, retreat_sequence, cover_sequence, attack_sequence, patrol_action]
        self.root = root
        return root
    
    def create_tactical_tree(self):
        """创建战术型行为树 - 支持团队合作和战术配合"""
        root = SelectorNode("Root")
        
        # 装填
        reload_sequence = SequenceNode("ReloadSequence")
        reload_sequence.children = [
            IsAmmoLow("IsAmmoLow", threshold=5),
            ReloadAction("ReloadAction")
        ]
        
        # 团队支援（最高优先级）
        support_sequence = SequenceNode("SupportSequence")
        support_sequence.children = [
            HasTeammateInDanger("HasTeammateInDanger"),
            TeamSupportAction("TeamSupportAction")
        ]
        
        # 协同攻击
        coordinate_attack_sequence = SequenceNode("CoordinateAttackSequence")
        coordinate_attack_sequence.children = [
            HasTeammateEngaging("HasTeammateEngaging"),
            CoordinateAttackAction("CoordinateAttackAction")
        ]
        
        # 侧翼攻击（有队友时更有效）
        flank_sequence = SequenceNode("FlankSequence")
        flank_sequence.children = [
            HasEnemyInSight("HasEnemyInSight"),
            FlankAction("FlankAction"),
            AttackAction("AttackAction")
        ]
        
        # 掩护队友
        cover_teammate_sequence = SequenceNode("CoverTeammateSequence")
        cover_teammate_sequence.children = [
            HasTeammateNearby("HasTeammateNearby", max_distance=300),
            CoverTeammateAction("CoverTeammateAction")
        ]
        
        # 攻击
        attack_sequence = SequenceNode("AttackSequence")
        attack_sequence.children = [
            HasEnemyInSight("HasEnemyInSight"),
            AttackAction("AttackAction")
        ]
        
        # 追击
        chase_sequence = SequenceNode("ChaseSequence")
        chase_sequence.children = [
            HasEnemyInSoundRange("HasEnemyInSoundRange"),
            ChaseAction("ChaseAction")
        ]
        
        # 巡逻
        patrol_action = PatrolAction("PatrolAction")
        
        # 优先级：装填 > 支援 > 协同攻击 > 侧翼 > 掩护 > 攻击 > 追击 > 巡逻
        root.children = [
            reload_sequence, 
            support_sequence, 
            coordinate_attack_sequence,
            flank_sequence, 
            cover_teammate_sequence,
            attack_sequence, 
            chase_sequence, 
            patrol_action
        ]
        self.root = root
        return root
    
    def create_stealthy_tree(self):
        """创建潜行型行为树"""
        root = SelectorNode("Root")
        
        # 装填
        reload_sequence = SequenceNode("ReloadSequence")
        reload_sequence.children = [
            IsAmmoLow("IsAmmoLow", threshold=5),
            ReloadAction("ReloadAction")
        ]
        
        # 伏击
        ambush_sequence = SequenceNode("AmbushSequence")
        ambush_sequence.children = [
            HasEnemyInSoundRange("HasEnemyInSoundRange"),
            AmbushAction("AmbushAction")
        ]
        
        # 攻击（从掩体）
        attack_sequence = SequenceNode("AttackSequence")
        attack_sequence.children = [
            HasEnemyInSight("HasEnemyInSight"),
            AttackAction("AttackAction")
        ]
        
        # 寻找掩体
        cover_sequence = SequenceNode("CoverSequence")
        cover_sequence.children = [
            IsInDanger("IsInDanger"),
            FindCoverAction("FindCoverAction")
        ]
        
        # 巡逻（静步）
        patrol_action = PatrolAction("PatrolAction")
        
        root.children = [reload_sequence, ambush_sequence, cover_sequence, attack_sequence, patrol_action]
        self.root = root
        return root
    
    def create_team_tree(self):
        """创建团队型行为树 - 优先团队合作"""
        root = SelectorNode("Root")
        
        # 装填
        reload_sequence = SequenceNode("ReloadSequence")
        reload_sequence.children = [
            IsAmmoLow("IsAmmoLow", threshold=5),
            ReloadAction("ReloadAction")
        ]
        
        # 团队支援（最高优先级）- 帮助处于危险中的队友
        support_sequence = SequenceNode("SupportSequence")
        support_sequence.children = [
            HasTeammateInDanger("HasTeammateInDanger"),
            TeamSupportAction("TeamSupportAction")
        ]
        
        # 协同攻击 - 与队友一起攻击同一目标
        coordinate_attack_sequence = SequenceNode("CoordinateAttackSequence")
        coordinate_attack_sequence.children = [
            HasTeammateEngaging("HasTeammateEngaging"),
            CoordinateAttackAction("CoordinateAttackAction")
        ]
        
        # 掩护队友 - 为队友提供火力掩护
        cover_teammate_sequence = SequenceNode("CoverTeammateSequence")
        cover_teammate_sequence.children = [
            HasTeammateNearby("HasTeammateNearby", max_distance=300),
            CoverTeammateAction("CoverTeammateAction")
        ]
        
        # 攻击敌人（有视线）
        attack_sequence = SequenceNode("AttackSequence")
        attack_sequence.children = [
            HasEnemyInSight("HasEnemyInSight"),
            AttackAction("AttackAction")
        ]
        
        # 侧翼攻击
        flank_sequence = SequenceNode("FlankSequence")
        flank_sequence.children = [
            HasEnemyInSight("HasEnemyInSight"),
            HasTeammateNearby("HasTeammateNearby", max_distance=400),  # 有队友时才侧翼
            FlankAction("FlankAction"),
            AttackAction("AttackAction")
        ]
        
        # 追击
        chase_sequence = SequenceNode("ChaseSequence")
        chase_sequence.children = [
            HasEnemyInSoundRange("HasEnemyInSoundRange"),
            ChaseAction("ChaseAction")
        ]
        
        # 巡逻
        patrol_action = PatrolAction("PatrolAction")
        
        # 优先级：装填 > 支援队友 > 协同攻击 > 掩护队友 > 攻击 > 侧翼 > 追击 > 巡逻
        root.children = [
            reload_sequence, 
            support_sequence, 
            coordinate_attack_sequence,
            cover_teammate_sequence,
            attack_sequence, 
            flank_sequence, 
            chase_sequence, 
            patrol_action
        ]
        self.root = root
        return root

