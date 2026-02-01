"""
游戏内指令系统

提供统一的命令注册、解析和执行功能。
支持本地命令和服务器命令。

命令格式：
    .command [参数1] [参数2] ...

可用命令：
    .help          - 显示帮助
    .kill          - 自杀
    .list          - 列出玩家
    .listai        - 列出AI
    .teamchat/.tc  - 切换团队聊天
    .all           - 切换全局聊天
    .addai         - 添加AI
    .removeai      - 移除AI
    .team add      - 创建团队
    .team delete   - 删除团队
    .team list     - 列出团队
    .team join     - 加入团队
    .team leave    - 离开团队
    .kick          - 踢出玩家（管理员）
    .heal          - 治疗玩家（管理员）
    .broadcast     - 广播消息（管理员）

配置：
    命令前缀可在 settings.json 中通过 commands.prefix 修改（默认为 "."）
    命令系统可在 settings.json 中通过 commands.enabled 禁用
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum, auto

# 导入配置系统
try:
    from config import COMMANDS_PREFIX, COMMANDS_ENABLED
except ImportError:
    COMMANDS_PREFIX = "."
    COMMANDS_ENABLED = True


class CommandCategory(Enum):
    PLAYER = auto()
    CHAT = auto()
    AI = auto()
    TEAM = auto()
    ADMIN = auto()
    INFO = auto()


class CommandPermission(Enum):
    ANY = auto()
    SERVER = auto()
    ADMIN = auto()


@dataclass
class CommandInfo:
    name: str
    description: str
    category: CommandCategory
    permission: CommandPermission
    usage: str
    aliases: List[str]
    handler: Callable


class CommandParser:
    def __init__(self, prefix: str = None):
        self.prefix = prefix if prefix else COMMANDS_PREFIX

    def parse(self, text: str) -> Tuple[str, List[str]]:
        if not text or not text.strip():
            return "", []

        text = text.strip()
        if not text.startswith(self.prefix):
            return "", []

        parts = text[len(self.prefix) :].split()
        cmd = parts[0].lower()
        args = parts[1:]
        return cmd, args


class GameCommandSystem:
    def __init__(self):
        self.commands: Dict[str, CommandInfo] = {}
        self.parser = CommandParser()
        self._register_core_commands()

    def register(
        self,
        name: str,
        handler: Callable,
        description: str,
        category: CommandCategory,
        permission: CommandPermission,
        usage: str,
        aliases: Optional[List[str]] = None,
    ) -> None:
        # 使用配置的前缀更新 usage 说明
        prefix = COMMANDS_PREFIX
        usage = usage.replace(".", prefix, 1) if usage.startswith(".") else usage

        cmd = CommandInfo(
            name, description, category, permission, usage, aliases or [], handler
        )
        self.commands[name] = cmd
        for alias in cmd.aliases:
            if alias not in self.commands:
                self.commands[alias] = cmd

    def get(self, name: str) -> Optional[CommandInfo]:
        return self.commands.get(name.lower())

    def execute(
        self,
        cmd_name: str,
        args: List[str],
        game: Any,
        player_id: int = 0,
        is_server: bool = False,
    ) -> str:
        if not COMMANDS_ENABLED:
            return "命令系统已禁用"

        cmd = self.get(cmd_name)
        if not cmd:
            prefix = COMMANDS_PREFIX
            return f"未知命令: {prefix}{cmd_name}，输入 {prefix}help 查看帮助"

        try:
            result = cmd.handler(args, game, player_id, is_server)
            return result if result else "操作成功"
        except Exception as e:
            return f"命令执行失败: {str(e)}"

    def get_help(self) -> str:
        prefix = COMMANDS_PREFIX
        lines = ["可用命令:"]
        lines.append("=" * 40)

        categories = {
            CommandCategory.PLAYER: "【玩家操作】",
            CommandCategory.CHAT: "【聊天相关】",
            CommandCategory.AI: "【AI管理】",
            CommandCategory.TEAM: "【团队管理】",
            CommandCategory.ADMIN: "【管理员】",
            CommandCategory.INFO: "【信息查询】",
        }

        for cat, name in categories.items():
            cmds = [c for c in self.commands.values() if c.category == cat]
            seen = set()
            unique_cmds = []
            for c in cmds:
                if c.name not in seen:
                    seen.add(c.name)
                    unique_cmds.append(c)
            if unique_cmds:
                lines.append(f"\n{name}")
                for c in unique_cmds:
                    aliases = f" ({', '.join(c.aliases)})" if c.aliases else ""
                    lines.append(f"  {prefix}{c.name:<12} {c.description}{aliases}")

        lines.append("\n" + "=" * 40)
        lines.append(f"提示: 输入 {prefix}<命令> 使用命令")

        return "\n".join(lines)

    def _register_core_commands(self) -> None:
        prefix = COMMANDS_PREFIX

        def help_handler(args, game, player_id, is_server) -> str:
            if args:
                cmd_name = args[0].lstrip(prefix)
                cmd = self.get(cmd_name)
                if cmd:
                    perm_text = {
                        CommandPermission.ADMIN: "管理员",
                        CommandPermission.SERVER: "服务器",
                    }.get(cmd.permission, "所有玩家")
                    usage = (
                        cmd.usage.replace(".", prefix, 1)
                        if cmd.usage.startswith(".")
                        else cmd.usage
                    )
                    return f"{prefix}{cmd.name}\n用法: {usage}\n权限: {perm_text}\n说明: {cmd.description}"
                return f"未找到命令: {prefix}{cmd_name}"
            return self.get_help()

        self.register(
            name="help",
            handler=help_handler,
            description="显示帮助信息",
            category=CommandCategory.INFO,
            permission=CommandPermission.ANY,
            usage=".help [命令名]",
            aliases=["?"],
        )

        def kill_handler(args, game, player_id, is_server) -> str:
            if game.player and not game.player.is_dead:
                game.player.health = 0
                game.player.is_dead = True
                return "你选择了自杀。"
            return "你已死亡，无法自杀"

        self.register(
            name="kill",
            handler=kill_handler,
            description="自杀",
            category=CommandCategory.PLAYER,
            permission=CommandPermission.ANY,
            usage=".kill",
        )

        def list_handler(args, game, player_id, is_server) -> str:
            if not game.network_manager:
                return "当前无网络连接"
            players = game.network_manager.players
            if not players:
                return "当前没有在线玩家"
            lines = ["当前玩家:"]
            for pid, p in players.items():
                name = p.get("name", "未知")
                health = p.get("health", 0)
                dead = p.get("is_dead", False)
                status = "死亡" if dead else f"生命:{health}"
                lines.append(f"  ID:{pid} - {name} ({status})")
            return "\n".join(lines)

        self.register(
            name="list",
            handler=list_handler,
            description="列出在线玩家",
            category=CommandCategory.INFO,
            permission=CommandPermission.ANY,
            usage=".list",
            aliases=["players"],
        )

        def teamchat_handler(args, game, player_id, is_server) -> str:
            game.team_chat_mode = True
            return "已切换到团队聊天模式"

        self.register(
            name="teamchat",
            handler=teamchat_handler,
            description="切换到团队聊天",
            category=CommandCategory.CHAT,
            permission=CommandPermission.ANY,
            usage=".teamchat",
            aliases=["tc"],
        )

        def all_handler(args, game, player_id, is_server) -> str:
            game.team_chat_mode = False
            return "已切换到全局聊天模式"

        self.register(
            name="all",
            handler=all_handler,
            description="切换到全局聊天",
            category=CommandCategory.CHAT,
            permission=CommandPermission.ANY,
            usage=".all",
        )

        def listai_handler(args, game, player_id, is_server) -> str:
            if not is_server:
                return "只有服务器可以查看AI列表"
            if not game.ai_players:
                return "当前没有AI玩家"
            lines = ["AI玩家:"]
            for ai_id in game.ai_players.keys():
                lines.append(f"  AI-{ai_id}")
            return "\n".join(lines)

        self.register(
            name="listai",
            handler=listai_handler,
            description="列出AI玩家",
            category=CommandCategory.INFO,
            permission=CommandPermission.ANY,
            usage=".listai",
        )

        def addai_handler(args, game, player_id, is_server) -> str:
            if not is_server:
                return "只有服务器可以添加AI"
            difficulty = "normal"
            if args:
                difficulty = args[0].lower()
                if difficulty not in ["easy", "normal", "hard"]:
                    return "难度必须是: easy, normal, hard"
            # 性格由系统随机生成，玩家无法选择
            game.add_ai_player(difficulty)
            return f"已添加AI (难度:{difficulty})"

        self.register(
            name="addai",
            handler=addai_handler,
            description="添加AI玩家",
            category=CommandCategory.AI,
            permission=CommandPermission.SERVER,
            usage=".addai [难度]",
            aliases=["spawn"],
        )

        def removeai_handler(args, game, player_id, is_server) -> str:
            if not is_server:
                return "只有服务器可以移除AI"
            if not args:
                return "用法: .removeai <ID|all>"
            target = args[0]
            if target.lower() == "all":
                count = len(game.ai_players)
                for ai_id in list(game.ai_players.keys()):
                    game.remove_ai_player(ai_id)
                return f"已移除所有AI ({count}个)"
            try:
                ai_id = int(target)
                if ai_id in game.ai_players:
                    game.remove_ai_player(ai_id)
                    return f"已移除AI-{ai_id}"
                return f"AI-{ai_id}不存在"
            except ValueError:
                return "无效的AI ID"

        self.register(
            name="removeai",
            handler=removeai_handler,
            description="移除AI玩家",
            category=CommandCategory.AI,
            permission=CommandPermission.SERVER,
            usage=".removeai <ID|all>",
            aliases=["delete"],
        )

        def team_handler(args, game, player_id, is_server) -> str:
            if not args:
                return f"用法: {prefix}team <add|delete|list|join|leave> [参数]"
            subcmd = args[0].lower()
            subargs = args[1:]

            if subcmd == "add":
                name = " ".join(subargs) if subargs else f"团队{player_id}"
                if game.team_system:
                    team_id = game.team_system.create_team(name, player_id)
                    if team_id:
                        return f"已创建团队 '{name}' (ID:{team_id})"
                    return "创建团队失败"
                return "团队系统不可用"

            elif subcmd == "delete":
                if not is_server:
                    return "只有服务器可以删除团队"
                if not subargs:
                    return f"用法: {prefix}team delete <团队ID>"
                try:
                    team_id = int(subargs[0])
                    if game.team_system:
                        if game.team_system.delete_team(team_id, player_id):
                            return f"已删除团队 {team_id}"
                        return "删除失败，可能是团队不存在或你不是队长"
                    return "团队系统不可用"
                except ValueError:
                    return "无效的团队ID"

            elif subcmd == "list":
                if game.team_system:
                    teams = game.team_system.get_all_teams_info()
                    if not teams:
                        return "当前没有团队"
                    lines = ["当前团队:"]
                    for t in teams:
                        lines.append(
                            f"  ID:{t['id']} - {t['name']} ({t['member_count']}人)"
                        )
                    return "\n".join(lines)
                return "团队系统不可用"

            elif subcmd == "join":
                if not subargs:
                    return f"用法: {prefix}team join <团队ID>"
                try:
                    team_id = int(subargs[0])
                    if game.team_system:
                        if game.team_system.join_team(team_id, player_id):
                            return f"已加入团队 {team_id}"
                        return "加入团队失败，可能是团队已满或不存在"
                    return "团队系统不可用"
                except ValueError:
                    return "无效的团队ID"

            elif subcmd == "leave":
                if game.team_system:
                    if game.team_system.leave_team(player_id):
                        return "已离开团队"
                    return "你不在任何团队中"
                return "团队系统不可用"

            return f"未知子命令: {subcmd}"

        self.register(
            name="team",
            handler=team_handler,
            description="团队管理 (add/delete/list/join/leave)",
            category=CommandCategory.TEAM,
            permission=CommandPermission.ANY,
            usage=".team <add|delete|list|join|leave> [参数]",
        )

        def kick_handler(args, game, player_id, is_server) -> str:
            if not is_server:
                return "只有服务器可以踢出玩家"
            if player_id != 1:
                return "只有管理员可以踢出玩家"
            if len(args) < 1:
                return f"用法: {prefix}kick <玩家ID> [原因]"
            try:
                target_id = int(args[0])
                reason = " ".join(args[1:]) if len(args) > 1 else "被管理员踢出"
                if target_id == player_id:
                    return "不能踢出自己"
                if target_id not in game.network_manager.players:
                    return f"玩家{target_id}不存在"

                target_addr = None
                for addr, pid in game.network_manager.clients.items():
                    if pid == target_id:
                        target_addr = addr
                        break

                if target_addr:
                    kick_data = {"type": "kick", "data": {"reason": reason}}
                    game.network_manager.send_to_client(kick_data, target_addr)

                    with game.network_manager.lock:
                        if target_addr in game.network_manager.clients:
                            del game.network_manager.clients[target_addr]
                        if hasattr(game.network_manager, "client_last_seen"):
                            if target_addr in game.network_manager.client_last_seen:
                                del game.network_manager.client_last_seen[target_addr]
                        if target_id in game.network_manager.players:
                            del game.network_manager.players[target_id]

                    game.network_manager.recycle_player_id(target_id)
                    game.network_manager._send_system_message(
                        f"玩家{target_id}已被踢出: {reason}"
                    )
                    return f"已踢出玩家 {target_id}"
                else:
                    return f"无法找到玩家{target_id}的连接"
            except ValueError:
                return "无效的玩家ID"

        self.register(
            name="kick",
            handler=kick_handler,
            description="踢出玩家（管理员）",
            category=CommandCategory.ADMIN,
            permission=CommandPermission.ADMIN,
            usage=".kick <玩家ID> [原因]",
        )

        def heal_handler(args, game, player_id, is_server) -> str:
            if not is_server:
                return "只有服务器可以治疗玩家"
            if len(args) < 1:
                return f"用法: {prefix}heal <玩家ID|all>"
            try:
                target = args[0]
                if target.lower() == "all":
                    for pid in game.network_manager.players:
                        game.network_manager.players[pid]["health"] = 100
                    return "已治愈所有玩家"
                target_id = int(target)
                if target_id in game.network_manager.players:
                    game.network_manager.players[target_id]["health"] = 100
                    return f"已治愈玩家 {target_id}"
                return f"玩家{target_id}不存在"
            except ValueError:
                return "无效的玩家ID"

        self.register(
            name="heal",
            handler=heal_handler,
            description="治疗玩家（管理员）",
            category=CommandCategory.ADMIN,
            permission=CommandPermission.ADMIN,
            usage=".heal <玩家ID|all>",
        )

        def broadcast_handler(args, game, player_id, is_server) -> str:
            if not is_server:
                return "只有服务器可以广播消息"
            if player_id != 1:
                return "只有管理员可以广播消息"
            if not args:
                return f"用法: {prefix}broadcast <消息>"
            message = " ".join(args)
            game.network_manager._send_system_message(f"[公告] {message}")
            return "公告已发送"

        self.register(
            name="broadcast",
            handler=broadcast_handler,
            description="广播系统公告（管理员）",
            category=CommandCategory.ADMIN,
            permission=CommandPermission.ADMIN,
            usage=".broadcast <消息>",
        )


_command_system: Optional[GameCommandSystem] = None


def get_command_system() -> GameCommandSystem:
    global _command_system
    if _command_system is None:
        _command_system = GameCommandSystem()
    return _command_system


def process_command(
    text: str, game: Any, player_id: int = 0, is_server: bool = False
) -> str:
    if not COMMANDS_ENABLED:
        return ""

    cmd_name, args = CommandParser().parse(text)
    if not cmd_name:
        return ""
    return get_command_system().execute(cmd_name, args, game, player_id, is_server)


def show_help(game: Any) -> str:
    return get_command_system().get_help()
