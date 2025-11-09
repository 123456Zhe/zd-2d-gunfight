"""
AI个性化特征系统
定义不同类型的AI性格和行为倾向
"""

import random
import enum


class AIPersonality(enum.Enum):
    """AI性格类型"""
    AGGRESSIVE = "aggressive"      # 激进型：主动攻击，不轻易撤退
    DEFENSIVE = "defensive"        # 防御型：优先寻找掩体，生命值低时撤退
    TACTICAL = "tactical"          # 战术型：使用侧翼、伏击等战术
    STEALTHY = "stealthy"          # 潜行型：优先使用静步，寻找伏击机会
    TEAM_PLAYER = "team_player"    # 团队型：与队友配合，避免误伤
    RANDOM = "random"              # 随机型：行为随机


class AIPersonalityTraits:
    """AI个性特征"""
    
    def __init__(self, personality_type):
        self.personality_type = personality_type
        self._init_traits()
    
    def _init_traits(self):
        """根据性格类型初始化特征"""
        if self.personality_type == AIPersonality.AGGRESSIVE:
            self.aggression = 0.9          # 攻击性：90%
            self.defensiveness = 0.2       # 防御性：20%
            self.stealth_preference = 0.1  # 潜行偏好：10%
            self.team_cooperation = 0.3    # 团队合作：30%
            self.risk_tolerance = 0.8      # 风险承受度：80%
            self.retreat_threshold = 0.1   # 撤退阈值：10%生命值
            
        elif self.personality_type == AIPersonality.DEFENSIVE:
            self.aggression = 0.3
            self.defensiveness = 0.9
            self.stealth_preference = 0.5
            self.team_cooperation = 0.4
            self.risk_tolerance = 0.3
            self.retreat_threshold = 0.4   # 40%生命值就撤退
            
        elif self.personality_type == AIPersonality.TACTICAL:
            self.aggression = 0.6
            self.defensiveness = 0.5
            self.stealth_preference = 0.4
            self.team_cooperation = 0.6
            self.risk_tolerance = 0.5
            self.retreat_threshold = 0.25
            
        elif self.personality_type == AIPersonality.STEALTHY:
            self.aggression = 0.4
            self.defensiveness = 0.6
            self.stealth_preference = 0.9
            self.team_cooperation = 0.3
            self.risk_tolerance = 0.4
            self.retreat_threshold = 0.3
            
        elif self.personality_type == AIPersonality.TEAM_PLAYER:
            self.aggression = 0.5
            self.defensiveness = 0.5
            self.stealth_preference = 0.3
            self.team_cooperation = 0.9
            self.risk_tolerance = 0.6
            self.retreat_threshold = 0.25
            
        elif self.personality_type == AIPersonality.RANDOM:
            # 随机特征
            self.aggression = random.uniform(0.2, 0.9)
            self.defensiveness = random.uniform(0.2, 0.9)
            self.stealth_preference = random.uniform(0.1, 0.9)
            self.team_cooperation = random.uniform(0.2, 0.9)
            self.risk_tolerance = random.uniform(0.2, 0.8)
            self.retreat_threshold = random.uniform(0.1, 0.4)
        
        # 共同特征
        self.patrol_preference = 1.0 - self.aggression  # 攻击性越低，越喜欢巡逻
        self.cover_priority = self.defensiveness        # 防御性越高，越优先寻找掩体
        self.flank_preference = self.team_cooperation * 0.7  # 团队合作高的更容易侧翼
    
    @classmethod
    def random_personality(cls):
        """随机生成一个性格"""
        personality = random.choice(list(AIPersonality))
        if personality == AIPersonality.RANDOM:
            # 如果随机到RANDOM，再随机一次选择具体性格
            personality = random.choice([
                AIPersonality.AGGRESSIVE,
                AIPersonality.DEFENSIVE,
                AIPersonality.TACTICAL,
                AIPersonality.STEALTHY,
                AIPersonality.TEAM_PLAYER
            ])
        return cls(personality)
    
    def get_behavior_tree_type(self):
        """根据性格返回行为树类型"""
        if self.personality_type == AIPersonality.AGGRESSIVE:
            return "aggressive"
        elif self.personality_type == AIPersonality.DEFENSIVE:
            return "defensive"
        elif self.personality_type == AIPersonality.TACTICAL:
            return "tactical"
        elif self.personality_type == AIPersonality.STEALTHY:
            return "stealthy"
        elif self.personality_type == AIPersonality.TEAM_PLAYER:
            return "team"  # 团队型使用专门的团队树
        else:
            return "tactical"  # 默认使用战术树
    
    def should_retreat(self, health_percent, enemy_count, enemy_distance):
        """判断是否应该撤退"""
        # 基础撤退条件
        if health_percent <= self.retreat_threshold:
            return True
        
        # 多个敌人靠近
        if enemy_count >= 2 and enemy_distance < 150:
            return True
        
        # 低风险承受度且生命值较低
        if health_percent < 0.5 and self.risk_tolerance < 0.5:
            return True
        
        return False
    
    def should_use_stealth(self, enemy_distance, enemy_count):
        """判断是否应该使用静步"""
        # 高潜行偏好
        if self.stealth_preference > 0.7:
            return True
        
        # 敌人较近但未发现
        if 80 < enemy_distance < 200 and enemy_count == 1:
            return True
        
        return False
    
    def should_flank(self, enemy_count, teammate_count):
        """判断是否应该侧翼攻击"""
        # 高团队合作且有队友
        if self.flank_preference > 0.6 and teammate_count > 0:
            return True
        
        # 战术型性格
        if self.personality_type == AIPersonality.TACTICAL:
            return True
        
        return False

