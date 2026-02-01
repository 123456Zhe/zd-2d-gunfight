"""
团队系统模块
管理玩家的团队关系、团队操作和团队状态
"""

import time
import random
from typing import Dict, Set, Optional, List


class Team:
    """团队类"""

    def __init__(self, team_id: int, name: str = None, leader_id: int = None):
        self.team_id = team_id
        self.name = name or f"队伍{team_id}"
        self.members: Set[int] = set()  # 玩家ID集合
        self.leader_id = leader_id  # 队长ID
        self.created_time = time.time()
        self.color = self._generate_team_color(team_id)

    def _generate_team_color(self, team_id: int):
        """生成团队颜色"""
        colors = [
            (255, 100, 100),  # 红色
            (100, 100, 255),  # 蓝色
            (100, 255, 100),  # 绿色
            (255, 255, 100),  # 黄色
            (255, 100, 255),  # 紫色
            (100, 255, 255),  # 青色
        ]
        return colors[team_id % len(colors)]

    def add_member(self, player_id: int):
        """添加成员"""
        self.members.add(player_id)
        if self.leader_id is None:
            self.leader_id = player_id

    def remove_member(self, player_id: int):
        """移除成员"""
        self.members.discard(player_id)
        # 如果移除的是队长，选择新队长
        if self.leader_id == player_id:
            if self.members:
                self.leader_id = min(self.members)
            else:
                self.leader_id = None

    def is_member(self, player_id: int) -> bool:
        """检查是否是成员"""
        return player_id in self.members

    def is_leader(self, player_id: int) -> bool:
        """检查是否是队长"""
        return self.leader_id == player_id

    def get_size(self) -> int:
        """获取团队大小"""
        return len(self.members)

    def is_empty(self) -> bool:
        """检查团队是否为空"""
        return len(self.members) == 0

    def get_members_list(self) -> List[int]:
        """获取成员列表"""
        return list(self.members)


class TeamManager:
    """团队管理器"""

    def __init__(self):
        self.teams: Dict[int, Team] = {}  # team_id -> Team
        self.player_teams: Dict[int, int] = {}  # player_id -> team_id
        self.next_team_id = 1
        self.max_team_size = 5  # 最大团队人数

    def _resolve_team_id_for_player(self, player_id):
        """
        兼容不同类型的玩家ID（int/str），返回其所属team_id；如果未找到返回None
        """
        # 直接命中
        if player_id in self.player_teams:
            return self.player_teams[player_id]

        # 尝试类型转换
        candidates = []
        try:
            candidates.append(int(player_id))
        except Exception:
            pass
        try:
            candidates.append(str(player_id))
        except Exception:
            pass

        for cid in candidates:
            if cid in self.player_teams:
                return self.player_teams[cid]

        return None

    def create_team(self, player_id: int, team_name: str = None) -> Optional[Team]:
        """创建团队"""
        # 检查玩家是否已在团队中
        if player_id in self.player_teams:
            return None

        # 创建新团队
        team_id = self.next_team_id
        self.next_team_id += 1

        team = Team(team_id, team_name, player_id)
        team.add_member(player_id)

        self.teams[team_id] = team
        self.player_teams[player_id] = team_id

        return team

    def join_team(self, player_id: int, team_id: int) -> bool:
        """加入团队"""
        # 检查玩家是否已在团队中
        if player_id in self.player_teams:
            return False

        # 检查团队是否存在
        if team_id not in self.teams:
            return False

        team = self.teams[team_id]

        # 检查团队是否已满
        if team.get_size() >= self.max_team_size:
            return False

        # 添加成员
        team.add_member(player_id)
        self.player_teams[player_id] = team_id

        return True

    def leave_team(self, player_id: int) -> bool:
        """离开团队"""
        if player_id not in self.player_teams:
            return False

        team_id = self.player_teams[player_id]
        team = self.teams[team_id]

        # 移除成员
        team.remove_member(player_id)
        del self.player_teams[player_id]

        # 如果团队为空，删除团队
        if team.is_empty():
            del self.teams[team_id]

        return True

    def delete_team(self, team_id: int, player_id: int = None) -> bool:
        """删除团队（仅队长或管理员可删除）"""
        if team_id not in self.teams:
            return False

        team = self.teams[team_id]

        if player_id is not None and not team.is_leader(player_id):
            return False

        for member_id in list(team.members):
            if member_id in self.player_teams:
                del self.player_teams[member_id]

        del self.teams[team_id]
        return True

    def get_player_team(self, player_id: int) -> Optional[Team]:
        """获取玩家所在的团队"""
        team_id = self._resolve_team_id_for_player(player_id)
        if team_id is None:
            return None
        return self.teams.get(team_id)

    def get_player_team_id(self, player_id: int) -> Optional[int]:
        """获取玩家所在的团队ID"""
        return self._resolve_team_id_for_player(player_id)

    def are_teammates(self, player1_id: int, player2_id: int) -> bool:
        """检查两个玩家是否是队友"""
        team1 = self._resolve_team_id_for_player(player1_id)
        team2 = self._resolve_team_id_for_player(player2_id)
        if team1 is None or team2 is None:
            return False
        return team1 == team2

    def get_teammates(self, player_id: int) -> List[int]:
        """获取玩家的所有队友"""
        team = self.get_player_team(player_id)
        if team is None:
            return []

        # 返回除自己以外的所有队友
        return [pid for pid in team.members if pid != player_id]

    def get_team_members(self, team_id: int) -> List[int]:
        """获取团队的所有成员"""
        if team_id not in self.teams:
            return []

        return self.teams[team_id].get_members_list()

    def remove_player(self, player_id: int):
        """移除玩家（玩家断开连接时调用）"""
        self.leave_team(player_id)

    def get_all_teams(self) -> Dict[int, Team]:
        """获取所有团队"""
        return self.teams.copy()

    def get_team_info(self, team_id: int) -> Optional[dict]:
        """获取团队信息"""
        if team_id not in self.teams:
            return None

        team = self.teams[team_id]
        return {
            "team_id": team.team_id,
            "name": team.name,
            "leader_id": team.leader_id,
            "members": team.get_members_list(),
            "size": team.get_size(),
            "color": team.color,
        }

    def list_teams(self) -> List[dict]:
        """列出所有团队"""
        return [self.get_team_info(team_id) for team_id in self.teams.keys()]

    def invite_to_team(self, inviter_id: int, invitee_id: int) -> tuple:
        """
        邀请玩家加入团队（仅队长可用）

        Args:
            inviter_id: 邀请者ID（必须是队长）
            invitee_id: 被邀请者ID

        Returns:
            (成功标志, 消息)
        """
        # 检查邀请者是否在团队中
        team = self.get_player_team(inviter_id)
        if not team:
            return False, "你不在任何团队中"

        # 检查邀请者是否是队长
        if not team.is_leader(inviter_id):
            return False, "只有队长可以邀请成员"

        # 检查被邀请者是否已经在团队中
        if invitee_id in self.player_teams:
            existing_team = self.get_player_team(invitee_id)
            if existing_team and existing_team.team_id == team.team_id:
                return False, "该玩家已经在你的团队中"
            else:
                return False, "该玩家已经在其他团队中"

        # 检查团队是否已满
        if team.get_size() >= self.max_team_size:
            return False, f"团队已满（最多{self.max_team_size}人）"

        # 邀请成功，直接加入团队
        team.add_member(invitee_id)
        self.player_teams[invitee_id] = team.team_id

        return True, f"已邀请玩家{invitee_id}加入团队"
