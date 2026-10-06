"""权限规则系统 — 三层 allow/ask/deny + glob 模式匹配

参考: Claude Code permissions 系统
文档: docs.claude.com/en/docs/claude-code/permissions

规则按严格顺序评估: deny -> ask -> allow
支持 glob 模式匹配: Bash(npm run *), Read(./.env), Edit(/src/**)

工具名在匹配前统一规范化为规范名 (normalize_tool_name)，因此 edit / edit_file、
list_dir / list_directory 等跨命名空间的别名指向同一能力，规则与调用点共用
同一份映射。
"""

from __future__ import annotations

import fnmatch
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RuleDecision(StrEnum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


class PermissionMode(StrEnum):
    """权限模式 — 参考 Claude Code 的 mode 系统"""
    DEFAULT = "default"          # 手动模式：只自动允许读取
    ACCEPT_EDITS = "acceptEdits"  # 自动接受编辑
    PLAN = "plan"                # 计划模式：只读预览
    AUTO = "auto"                # 全自动（有分类器安全检查）
    BYPASS = "bypass"            # 跳过所有权限检查
    STRICT = "strict"            # 严格模式：未显式允许即拒绝


class PermissionTier(StrEnum):
    """User-facing capability ceiling for the three security levels."""

    READ_ONLY = "read_only"
    PARTIAL_WRITE = "partial_write"
    FULL_WRITE = "full_write"


# ---------------------------------------------------------------------------
# 工具名规范化
# ---------------------------------------------------------------------------
# 同一能力在不同代码路径下有不同名字：permission_rules 历史上用 edit/list_dir，
# engine/validation.py 用 edit_file/list_directory，headless/skills 用 list_files，
# native 工具带 native_ 前缀。全部映射到规范名，规则匹配与调用点共用这一份定义。
TOOL_NAME_ALIASES: dict[str, str] = {
    # 文件读取
    "read": "read_file",
    "file_read": "read_file",
    "native_read_file": "read_file",
    # 文件写入
    "write": "write_file",
    "file_write": "write_file",
    "native_write_file": "write_file",
    "edit": "edit_file",
    # 目录列举
    "ls": "list_directory",
    "list_dir": "list_directory",
    "list_files": "list_directory",
    "native_list_dir": "list_directory",
    # 命令执行
    "bash": "run_command",
    "command": "run_command",
    "shell": "run_command",
    "execute_command": "run_command",
    "stream_command": "run_command",
    "container_exec": "run_command",
    "native_run": "run_command",
    # 删除
    "rm": "file_delete",
    "delete": "file_delete",
    # 网络
    "native_web_search": "web_search",
}

# 能力分组 — 只收录规范名，别名由 normalize_tool_name 归一后再比较
_COMMAND_TOOLS: frozenset[str] = frozenset({"run_command"})
_NETWORK_TOOLS: frozenset[str] = frozenset({"web_search", "http_request", "fetch"})
_FILE_READ_TOOLS: frozenset[str] = frozenset(
    {"read_file", "list_directory", "search", "glob", "file_exists", "file_info", "file_diff"}
)
_FILE_WRITE_TOOLS: frozenset[str] = frozenset(
    {"write_file", "edit_file", "append_file", "apply_patch"}
)
_FILE_TOOLS: frozenset[str] = _FILE_READ_TOOLS | _FILE_WRITE_TOOLS
# 参数模式匹配用：删除操作同样作用于文件路径，但不属于 acceptEdits 自动放行范围
_FILE_PATH_TOOLS: frozenset[str] = _FILE_TOOLS | {"file_delete"}

# acceptEdits 模式自动放行的工具（沿用历史范围，别名已归一）
_EDIT_MODE_TOOLS: frozenset[str] = frozenset(
    {"read_file", "list_directory", "write_file", "edit_file", "append_file"}
)
# 计划模式自动放行的只读工具
_PLAN_READ_TOOLS: frozenset[str] = frozenset({"read_file", "list_directory", "search"})
# 默认模式自动放行的只读工具
_DEFAULT_READ_TOOLS: frozenset[str] = _FILE_READ_TOOLS

_GLOB_CHARS: frozenset[str] = frozenset("*?[")


def normalize_tool_name(tool_name: str) -> str:
    """把工具名规范化成规范名

    - 统一去空白与小写
    - 已知别名映射到规范名 (edit -> edit_file, list_dir -> list_directory)
    - 含 glob 通配符的名称原样保留，交由 fnmatch 处理

    Args:
        tool_name: 规则或调用方给出的原始工具名。

    Returns:
        规范工具名。
    """
    if not tool_name:
        return ""
    name = tool_name.strip().lower()
    if _GLOB_CHARS & set(name):
        return name
    return TOOL_NAME_ALIASES.get(name, name)


@dataclass
class PermissionRule:
    """单条权限规则"""
    decision: RuleDecision
    tool: str                    # 工具名或工具类型
    pattern: str | None = None   # glob 模式 (可选)
    description: str = ""

    def matches(self, tool_name: str, arguments: dict[str, Any] | None = None) -> bool:
        """检查规则是否匹配给定的工具调用"""
        target = normalize_tool_name(tool_name)

        # 工具名匹配 — 规则侧与调用侧都规范化，支持别名与通配符
        if not fnmatch.fnmatch(target, normalize_tool_name(self.tool)):
            return False

        # 如果有参数模式，检查参数匹配
        if self.pattern:
            return self._match_pattern(target, arguments or {})

        return True

    def _match_pattern(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """根据工具能力匹配参数模式 — tool_name 已是规范名"""
        # 命令执行工具: pattern 匹配命令字符串
        if tool_name in _COMMAND_TOOLS:
            command = arguments.get("command", "")
            return fnmatch.fnmatch(command, self.pattern) if self.pattern else True

        # 文件操作工具: pattern 匹配文件路径
        if tool_name in _FILE_PATH_TOOLS:
            file_path = arguments.get(
                "path", arguments.get("file_path", arguments.get("dir", ""))
            )
            return fnmatch.fnmatch(file_path, self.pattern) if self.pattern else True

        # 网络工具: pattern 匹配 URL
        if tool_name in _NETWORK_TOOLS:
            url = arguments.get("url", "")
            return fnmatch.fnmatch(url, self.pattern) if self.pattern else True

        return True


@dataclass
class PermissionConfig:
    """权限配置 — 完整规则集"""
    mode: PermissionMode = PermissionMode.DEFAULT
    rules: list[PermissionRule] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)  # Crush 风格的工具白名单
    denied_tools: list[str] = field(default_factory=list)   # Crush 风格的工具黑名单
    tier: PermissionTier = PermissionTier.FULL_WRITE

    def evaluate(self, tool_name: str, arguments: dict[str, Any] | None = None) -> RuleDecision:
        """评估工具调用的权限决策

        评估顺序: tier 上限 -> denied_tools 黑名单 -> deny 规则 -> ask 规则
        -> 模式快捷判断 -> allowed_tools 白名单 -> allow 规则 -> 模式兜底。
        DENY 优先于白名单，STRICT 模式下未显式允许即拒绝。
        """
        tool = normalize_tool_name(tool_name)

        # The tier is a ceiling. Existing deny/ask rules remain authoritative,
        # while the default read-only tier cannot silently gain write access.
        tier_decision = self._tier_decision(tool, arguments)
        if tier_decision == RuleDecision.DENY:
            return RuleDecision.DENY
        if self.mode == PermissionMode.PLAN and tool not in _FILE_READ_TOOLS:
            return RuleDecision.DENY

        if self._matches_tool_list(self.denied_tools, tool):
            return RuleDecision.DENY

        priority = {RuleDecision.DENY: 0, RuleDecision.ASK: 1, RuleDecision.ALLOW: 2}
        matched_rules = [rule for rule in self.rules if rule.matches(tool, arguments)]
        matched_rules.sort(key=lambda r: priority.get(r.decision, 1))
        top_decision = matched_rules[0].decision if matched_rules else None
        if top_decision in (RuleDecision.DENY, RuleDecision.ASK):
            return top_decision
        if tier_decision == RuleDecision.ASK:
            return RuleDecision.ASK

        # 模式级别快速判断
        if self.mode == PermissionMode.BYPASS:
            return tier_decision or RuleDecision.ALLOW
        if self.mode == PermissionMode.AUTO:
            # auto 模式下除了高危操作外都允许
            if self._is_high_risk(tool, arguments):
                return RuleDecision.ASK
            return tier_decision or RuleDecision.ALLOW
        if self.mode == PermissionMode.ACCEPT_EDITS and tool in _EDIT_MODE_TOOLS:
            return tier_decision or RuleDecision.ALLOW
        if self.mode == PermissionMode.PLAN:
            # 计划模式只允许读取
            if tool in _FILE_READ_TOOLS:
                return RuleDecision.ALLOW
            return RuleDecision.DENY

        whitelisted = self._matches_tool_list(self.allowed_tools, tool)
        allow_matched = top_decision == RuleDecision.ALLOW

        # 检查 Crush 风格的白名单：未列名工具需确认，STRICT 模式下直接拒绝
        if self.allowed_tools and not (whitelisted or allow_matched):
            if self.mode == PermissionMode.STRICT:
                return RuleDecision.DENY
            return RuleDecision.ASK

        if allow_matched:
            return RuleDecision.ALLOW

        # 默认行为取决于模式
        if self.mode == PermissionMode.STRICT:
            # 严格模式：白名单/allow 规则之外一律拒绝
            return RuleDecision.ALLOW if whitelisted else RuleDecision.DENY

        if self.mode == PermissionMode.DEFAULT and tool in _DEFAULT_READ_TOOLS:
            # 默认模式: 读取允许，其他需要确认
            return RuleDecision.ALLOW

        return tier_decision or RuleDecision.ASK

    def _tier_decision(
        self, tool_name: str, arguments: dict[str, Any] | None,
    ) -> RuleDecision | None:
        """Return the tier ceiling without overriding explicit deny rules."""
        tool = normalize_tool_name(tool_name)
        if tool in _FILE_READ_TOOLS:
            return None
        if self.tier == PermissionTier.READ_ONLY:
            return RuleDecision.DENY
        if self.tier == PermissionTier.PARTIAL_WRITE:
            if tool not in _FILE_WRITE_TOOLS:
                return RuleDecision.DENY
            if tool in _FILE_WRITE_TOOLS:
                path = (arguments or {}).get("path", (arguments or {}).get("file_path", ""))
                if not isinstance(path, str) or not path:
                    return RuleDecision.ASK
                path = os.path.abspath(path)
                if any(path == root or path.startswith(root + "/")
                       for root in ("/etc", "/root", "/proc", "/sys", "/dev")):
                    return RuleDecision.DENY
                return None
        return None

    def _matches_tool_list(self, names: list[str], tool: str) -> bool:
        """工具名是否命中给定名单 — 名单项与工具名都规范化，支持 glob"""
        return any(fnmatch.fnmatch(tool, normalize_tool_name(name)) for name in names)

    def _is_high_risk(self, tool_name: str, arguments: dict[str, Any] | None) -> bool:
        """检查是否为高危操作 — 参考 Claude Code 的分类器"""
        if not arguments:
            return False

        tool = normalize_tool_name(tool_name)

        # 高危命令模式
        high_risk_patterns = [
            r'rm\s+-rf',
            r'curl.*\|.*bash',
            r'curl.*\|.*sh',
            r'wget.*\|.*sh',
            r'git\s+push\s+--force',
            r'git\s+push\s+-f',
            r'docker\s+rm',
            r'docker\s+system\s+prune',
            r'npm\s+publish',
            r'drop\s+table',
            r'drop\s+database',
            r'truncate\s+table',
        ]

        if tool in _COMMAND_TOOLS:
            command = arguments.get("command", "")
            for pattern in high_risk_patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return True

        # 网络请求
        if tool in _NETWORK_TOOLS:
            url = arguments.get("url", "")
            if url and not url.startswith(("https://", "http://localhost", "http://127.0.0.1")):
                return True

        return False

    def assess_risk(self, tool_name: str, arguments: dict[str, Any] | None = None) -> str:
        """评估操作风险等级 — 参考 Claude Code Ctrl+E 解释器"""
        if not arguments:
            return "low"

        tool = normalize_tool_name(tool_name)

        # 删除操作
        if tool == "file_delete":
            return "high"

        # 命令执行
        if tool in _COMMAND_TOOLS:
            command = arguments.get("command", "")
            high_risk = ['rm', 'mv', 'dd', 'mkfs', 'format', 'fdisk', 'shutdown', 'reboot']
            medium_risk = ['git push', 'npm publish', 'pip install', 'docker', 'kubectl']

            for pattern in high_risk:
                if command.startswith(pattern) or f' {pattern}' in command:
                    return "high"
            for pattern in medium_risk:
                if pattern in command:
                    return "medium"
            return "low"

        # 网络访问
        if tool in _NETWORK_TOOLS:
            return "medium"

        # 文件读取/写入
        if tool in _FILE_READ_TOOLS:
            return "low"
        if tool in _FILE_WRITE_TOOLS:
            return "medium"

        return "low"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the permission config for persistence across restarts."""
        return {
            "mode": self.mode.value,
            "rules": [
                {
                    "decision": r.decision.value,
                    "tool": r.tool,
                    "pattern": r.pattern,
                    "description": r.description,
                }
                for r in self.rules
            ],
            "allowed_tools": list(self.allowed_tools),
            "denied_tools": list(self.denied_tools),
            "tier": self.tier.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PermissionConfig:
        """Reconstruct a PermissionConfig from a persisted dict."""
        try:
            mode = PermissionMode(data.get("mode", PermissionMode.DEFAULT.value))
        except ValueError:
            mode = PermissionMode.DEFAULT
        try:
            tier = PermissionTier(data.get("tier", PermissionTier.FULL_WRITE.value))
        except ValueError:
            tier = PermissionTier.READ_ONLY
        rules: list[PermissionRule] = []
        for r in data.get("rules") or []:
            try:
                decision = RuleDecision(r.get("decision", RuleDecision.ASK.value))
            except ValueError:
                decision = RuleDecision.ASK
            rules.append(
                PermissionRule(
                    decision=decision,
                    tool=str(r.get("tool", "")),
                    pattern=r.get("pattern"),
                    description=str(r.get("description", "")),
                )
            )
        return cls(
            mode=mode,
            rules=rules,
            allowed_tools=list(data.get("allowed_tools") or []),
            denied_tools=list(data.get("denied_tools") or []),
            tier=tier,
        )


def get_default_config() -> PermissionConfig:
    """获取默认权限配置"""
    return PermissionConfig(
        mode=PermissionMode.DEFAULT,
        tier=PermissionTier.FULL_WRITE,
        rules=[
            # 读取操作默认允许
            PermissionRule(RuleDecision.ALLOW, "read_file"),
            PermissionRule(RuleDecision.ALLOW, "list_directory"),
            PermissionRule(RuleDecision.ALLOW, "search"),
            PermissionRule(RuleDecision.ALLOW, "glob"),
            # 高危命令默认拒绝
            PermissionRule(RuleDecision.DENY, "run_command", "rm -rf *"),
            PermissionRule(RuleDecision.DENY, "run_command", "curl *| bash"),
            PermissionRule(RuleDecision.DENY, "run_command", "wget *| sh"),
            # 网络访问需要确认
            PermissionRule(RuleDecision.ASK, "web_search"),
            PermissionRule(RuleDecision.ASK, "http_request"),
            PermissionRule(RuleDecision.ASK, "fetch"),
        ],
    )


def get_plan_mode_config() -> PermissionConfig:
    """计划模式配置 — 只允许读取"""
    return PermissionConfig(
        mode=PermissionMode.PLAN,
        rules=[
            PermissionRule(RuleDecision.ALLOW, "read_file"),
            PermissionRule(RuleDecision.ALLOW, "list_directory"),
            PermissionRule(RuleDecision.ALLOW, "search"),
            PermissionRule(RuleDecision.ALLOW, "glob"),
            PermissionRule(RuleDecision.ALLOW, "run_command", "ls *"),
            PermissionRule(RuleDecision.ALLOW, "run_command", "cat *"),
            PermissionRule(RuleDecision.ALLOW, "run_command", "find *"),
            PermissionRule(RuleDecision.ALLOW, "run_command", "grep *"),
            PermissionRule(RuleDecision.ALLOW, "run_command", "git status"),
            PermissionRule(RuleDecision.ALLOW, "run_command", "git log *"),
            PermissionRule(RuleDecision.ALLOW, "run_command", "git diff *"),
            PermissionRule(RuleDecision.ALLOW, "run_command", "git show *"),
            # 其他一律拒绝
            PermissionRule(RuleDecision.DENY, "write_file"),
            PermissionRule(RuleDecision.DENY, "edit_file"),
            PermissionRule(RuleDecision.DENY, "append_file"),
            PermissionRule(RuleDecision.DENY, "file_delete"),
            PermissionRule(RuleDecision.DENY, "run_command", "git push *"),
            PermissionRule(RuleDecision.DENY, "run_command", "npm publish *"),
        ],
    )


def get_auto_mode_config() -> PermissionConfig:
    """自动模式配置 — 全自动但有安全检查"""
    return PermissionConfig(
        mode=PermissionMode.AUTO,
        rules=[
            # 只对最高危操作要求确认
            PermissionRule(RuleDecision.ASK, "run_command", "rm -rf /*"),
            PermissionRule(RuleDecision.ASK, "run_command", "rm -rf /"),
            PermissionRule(RuleDecision.ASK, "run_command", "dd if=*"),
            PermissionRule(RuleDecision.ASK, "run_command", "mkfs *"),
            PermissionRule(RuleDecision.ASK, "run_command", "git push --force *"),
            PermissionRule(RuleDecision.ASK, "run_command", "git push -f *"),
            PermissionRule(RuleDecision.ASK, "run_command", "npm publish *"),
        ],
    )


def get_strict_mode_config() -> PermissionConfig:
    """严格模式配置 — 只读工具放行，其余未显式允许即拒绝"""
    return PermissionConfig(
        mode=PermissionMode.STRICT,
        rules=[
            # 只读工具显式放行
            PermissionRule(RuleDecision.ALLOW, "read_file"),
            PermissionRule(RuleDecision.ALLOW, "list_directory"),
            PermissionRule(RuleDecision.ALLOW, "search"),
            PermissionRule(RuleDecision.ALLOW, "glob"),
            # 破坏性操作直接拒绝
            PermissionRule(RuleDecision.DENY, "file_delete"),
            PermissionRule(RuleDecision.DENY, "run_command", "rm -rf *"),
            PermissionRule(RuleDecision.DENY, "run_command", "curl *| bash"),
            PermissionRule(RuleDecision.DENY, "run_command", "wget *| sh"),
            PermissionRule(RuleDecision.DENY, "run_command", "git push *"),
            PermissionRule(RuleDecision.DENY, "run_command", "npm publish *"),
        ],
    )


# 预定义配置
MODE_CONFIGS: dict[PermissionMode, Callable[[], PermissionConfig]] = {
    PermissionMode.DEFAULT: get_default_config,
    PermissionMode.PLAN: get_plan_mode_config,
    PermissionMode.AUTO: get_auto_mode_config,
    PermissionMode.STRICT: get_strict_mode_config,
    PermissionMode.ACCEPT_EDITS: lambda: PermissionConfig(
        mode=PermissionMode.ACCEPT_EDITS,
        rules=[
            PermissionRule(RuleDecision.ALLOW, "read_file"),
            PermissionRule(RuleDecision.ALLOW, "list_directory"),
            PermissionRule(RuleDecision.ALLOW, "write_file"),
            PermissionRule(RuleDecision.ALLOW, "edit_file"),
            PermissionRule(RuleDecision.ALLOW, "append_file"),
        ],
    ),
    PermissionMode.BYPASS: lambda: PermissionConfig(mode=PermissionMode.BYPASS),
}
