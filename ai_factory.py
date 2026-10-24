"""AI 创建工厂：优先神经网络，失败时按配置回退行为树。"""

from constants import RL_POLICY_FALLBACK, USE_ENHANCED_AI, USE_RL_AI


def make_ai_player(ai_id, x, y, difficulty="normal", personality_traits=None):
    """返回 (ai_player, backend)，backend 为 "rl" / "enhanced" / "basic"。"""
    if USE_RL_AI:
        try:
            from rl_ai import RLAIPlayer

            player = RLAIPlayer(ai_id, x, y, difficulty, personality_traits)
            print(f"[AI] 使用神经网络策略 (ID={ai_id})")
            return player, "rl"
        except Exception as exc:
            if not RL_POLICY_FALLBACK:
                raise
            print(f"[AI] 神经网络加载失败: {exc}，回退行为树 AI")

    if USE_ENHANCED_AI:
        try:
            from ai_personality import AIPersonalityTraits
            from ai_player_enhanced import EnhancedAIPlayer

            traits = personality_traits or AIPersonalityTraits.random_personality()
            return EnhancedAIPlayer(ai_id, x, y, difficulty, traits), "enhanced"
        except ImportError as exc:
            print(f"[AI] 增强版 AI 不可用: {exc}，回退基础 AI")

    from ai_player import AIPlayer

    return AIPlayer(ai_id, x, y, difficulty), "basic"
