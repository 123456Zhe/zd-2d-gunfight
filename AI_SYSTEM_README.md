# AI系统优化说明

## 概述

本次优化为AI玩家系统引入了以下改进：

1. **行为树系统** - 使用行为树框架实现模块化和可扩展的AI决策
2. **代价计算模块** - 使用numpy进行批量计算，提高性能
3. **个性化特征系统** - 不同类型的AI有不同的行为倾向
4. **多样化行为节点** - 包括掩体寻找、伏击、侧翼攻击、团队支援等

## 文件结构

```
ai_cost_calculator.py      # 代价计算模块（使用numpy）
ai_behavior_tree.py        # 行为树系统
ai_personality.py          # 个性化特征系统
ai_player_enhanced.py      # 增强版AI玩家类
```

## 主要特性

### 1. 行为树系统

行为树由以下节点类型组成：

- **组合节点**：
  - `SelectorNode` - 选择节点（或逻辑）
  - `SequenceNode` - 序列节点（与逻辑）
  - `ParallelNode` - 并行节点

- **装饰节点**：
  - `InverterNode` - 反转节点
  - `RepeatNode` - 重复节点

- **条件节点**：
  - `HasEnemyInSight` - 检查是否有敌人在视线内
  - `HasEnemyInSoundRange` - 检查是否有敌人在声音范围内
  - `IsHealthLow` - 检查生命值是否低
  - `IsAmmoLow` - 检查弹药是否不足
  - `IsInDanger` - 检查是否处于危险中

- **行为节点**：
  - `PatrolAction` - 巡逻行为
  - `ChaseAction` - 追击行为
  - `AttackAction` - 攻击行为
  - `RetreatAction` - 撤退行为
  - `FindCoverAction` - 寻找掩体行为
  - `FlankAction` - 侧翼攻击行为
  - `AmbushAction` - 伏击行为
  - `TeamSupportAction` - 团队支援行为
  - `ReloadAction` - 装填行为

### 2. 个性化特征系统

支持以下AI性格类型：

- **AGGRESSIVE** - 激进型：主动攻击，不轻易撤退
- **DEFENSIVE** - 防御型：优先寻找掩体，生命值低时撤退
- **TACTICAL** - 战术型：使用侧翼、伏击等战术
- **STEALTHY** - 潜行型：优先使用静步，寻找伏击机会
- **TEAM_PLAYER** - 团队型：与队友配合，避免误伤
- **RANDOM** - 随机型：行为随机

### 3. 代价计算模块

使用numpy进行批量计算，包括：

- **威胁代价计算** - 评估位置受到威胁的程度
- **掩体价值计算** - 评估位置的掩体价值
- **位置代价网格** - 批量计算整个地图的代价
- **最佳位置寻找** - 基于代价函数找到最佳位置
- **侧翼角度计算** - 计算侧翼攻击的角度
- **伏击价值计算** - 评估伏击位置的价值

## 使用方法

### 1. 安装依赖

```bash
# 安装numpy（可选，但强烈推荐）
pip install numpy

# 如果已安装numpy，系统会自动使用numpy进行优化
# 如果没有numpy，系统会使用fallback实现（较慢）
```

### 2. 在main.py中集成

有两种方式：

#### 方式1：完全替换原有AI系统

```python
# 在main.py中
from ai_player_enhanced import EnhancedAIPlayer

# 创建AI玩家时
ai_player = EnhancedAIPlayer(
    player_id=100,
    x=spawn_x,
    y=spawn_y,
    difficulty='normal',
    personality='aggressive'  # 或者使用AIPersonality枚举
)
```

#### 方式2：逐步迁移（推荐）

保持原有AI系统不变，新AI系统作为可选功能：

```python
# 在main.py中添加选项
USE_ENHANCED_AI = True  # 设置为True使用增强版AI

if USE_ENHANCED_AI:
    from ai_player_enhanced import EnhancedAIPlayer as AIPlayer
else:
    from ai_player import AIPlayer

# 创建AI时
ai_player = AIPlayer(
    player_id=100,
    x=spawn_x,
    y=spawn_y,
    difficulty='normal'
)
```

### 3. 自定义行为树

可以创建自定义行为树：

```python
from ai_behavior_tree import BehaviorTree, SelectorNode, SequenceNode
from ai_behavior_tree import HasEnemyInSight, AttackAction, PatrolAction

# 创建自定义行为树
tree = BehaviorTree(None)
root = SelectorNode("Root")

# 攻击序列
attack_sequence = SequenceNode("AttackSequence")
attack_sequence.children = [
    HasEnemyInSight("HasEnemyInSight"),
    AttackAction("AttackAction")
]

# 巡逻
patrol_action = PatrolAction("PatrolAction")

root.children = [attack_sequence, patrol_action]
tree.root = root

# 使用自定义行为树
ai_player.behavior_tree = tree
```

### 4. 使用个性化特征

```python
from ai_personality import AIPersonality, AIPersonalityTraits

# 创建特定性格的AI
personality = AIPersonalityTraits(AIPersonality.AGGRESSIVE)
ai_player = EnhancedAIPlayer(
    player_id=100,
    x=spawn_x,
    y=spawn_y,
    difficulty='normal',
    personality=personality
)

# 或者随机生成性格
personality = AIPersonalityTraits.random_personality()
ai_player = EnhancedAIPlayer(
    player_id=100,
    x=spawn_x,
    y=spawn_y,
    difficulty='normal',
    personality=personality
)
```

## 性能优化

### 1. Numpy加速

如果安装了numpy，代价计算会显著加速：

```python
# 批量计算代价网格（使用numpy）
cost_grid = calculator.calculate_position_cost_grid(ai_pos, enemies, game_map)

# 如果没有numpy，会使用较慢的fallback实现
```

### 2. 网格大小调整

可以通过调整网格大小来平衡性能和精度：

```python
# 较小的网格 = 更高的精度，但更慢
calculator = AICostCalculator(grid_size=30)

# 较大的网格 = 更快的计算，但精度较低
calculator = AICostCalculator(grid_size=50)
```

## 扩展开发

### 1. 添加新的行为节点

```python
from ai_behavior_tree import ActionNode, NodeStatus

class CustomAction(ActionNode):
    def tick(self, ai_player, blackboard):
        # 实现自定义行为
        blackboard['action'] = {
            'move': pygame.Vector2(0, 0),
            'angle': ai_player.angle,
            'shoot': False,
            'reload': False
        }
        return NodeStatus.SUCCESS
```

### 2. 添加新的条件节点

```python
from ai_behavior_tree import ConditionNode, NodeStatus

class CustomCondition(ConditionNode):
    def tick(self, ai_player, blackboard):
        # 实现自定义条件检查
        if some_condition:
            return NodeStatus.SUCCESS
        return NodeStatus.FAILURE
```

### 3. 添加新的个性化特征

```python
from ai_personality import AIPersonality, AIPersonalityTraits

# 在AIPersonalityTraits._init_traits()中添加新的性格类型
```

## 注意事项

1. **numpy依赖**：虽然系统支持在没有numpy的情况下运行，但强烈建议安装numpy以获得最佳性能。

2. **性能考虑**：代价计算可能会消耗较多CPU资源，建议：
   - 限制同时活跃的AI数量
   - 调整网格大小
   - 减少路径重新计算的频率

3. **兼容性**：增强版AI系统与原有AI系统兼容，可以逐步迁移。

4. **调试**：可以通过查看行为树的执行状态来调试AI行为：
   ```python
   # 在行为树节点中添加日志
   print(f"[AI{ai_player.id}] 执行节点: {node.name}, 状态: {node.status}")
   ```

## 未来改进

1. **机器学习**：可以引入机器学习来优化AI行为
2. **动态行为树**：根据游戏状态动态调整行为树
3. **团队AI**：实现更复杂的团队协作AI
4. **情感系统**：添加情感状态影响AI决策

## 示例代码

完整的使用示例请参考 `ai_player_enhanced.py` 和集成到 `main.py` 的示例代码。

## 问题反馈

如有问题或建议，请提交Issue或Pull Request。

