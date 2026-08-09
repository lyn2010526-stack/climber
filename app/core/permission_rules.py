"""权限规则系统 — 三层 allow/ask/deny + glob 模式匹配

参考: Claude Code permissions 系统
文档: docs.claude.com/en/docs/claude-code/permissions

规则按严格顺序评估: deny -> ask -> allow
支持 glob 模式匹配: Bash(npm run *), Read(./.env), Edit(/src/**)
"""

from __future__ import annotations

import fnmatch
import re
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


@dataclass
class PermissionRule:
    """单条权限规则"""
    decision: RuleDecision
    tool: str                    # 工具名或工具类型
    pattern: str | None = None   # glob 模式 (可选)
    description: str = ""

    def matches(self, tool_name: str, arguments: dict[str, Any] | None = None) -> bool:
        """检查规则是否匹配给定的工具调用"""
        # 工具名匹配 — 支持通配符
        if not fnmatch.fnmatch(tool_name.lower(), self.tool.lower()):
            return False

        # 如果有参数模式，检查参数匹配
        if self.pattern and arguments:
            return self._match_pattern(tool_name, arguments)

        return True

    def _match_pattern(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """根据工具类型匹配参数模式"""
        # Bash/Command 工具: pattern 匹配命令字符串
        if tool_name in ("bash", "run_command", "native_run", "command"):
            command = arguments.get("command", "")
            return fnmatch.fnmatch(command, self.pattern) if self.pattern else True

        # 文件操作工具: pattern 匹配文件路径
        if tool_name in ("read_file", "file_read", "write_file", "file_write", "edit"):
            file_path = arguments.get("path", arguments.get("file_path", ""))
            return fnmatch.fnmatch(file_path, self.pattern) if self.pattern else True

        # 网络工具: pattern 匹配 URL
        if tool_name in ("web_search", "http_request", "fetch"):
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

    def evaluate(self, tool_name: str, arguments: dict[str, Any] | None = None) -> RuleDecision:
        """评估工具调用的权限决策"""
        # 模式级别快速判断
        if self.mode == PermissionMode.BYPASS:
            return RuleDecision.ALLOW
        if self.mode == PermissionMode.AUTO:
            # auto 模式下除了高危操作外都允许
            if self._is_high_risk(tool_name, arguments):
                return RuleDecision.ASK
            return RuleDecision.ALLOW
        if self.mode == PermissionMode.ACCEPT_EDITS and tool_name in (
            "read_file", "file_read", "write_file", "file_write", "edit", "list_dir"
        ):
            # 自动接受编辑和读取
            return RuleDecision.ALLOW
        if self.mode == PermissionMode.PLAN:
            # 计划模式只允许读取
            if tool_name in ("read_file", "file_read", "list_dir", "search"):
                return RuleDecision.ALLOW
            return RuleDecision.DENY

        # 检查 Crush 风格的黑名单
        for denied in self.denied_tools:
            if fnmatch.fnmatch(tool_name.lower(), denied.lower()):
                return RuleDecision.DENY

        # 检查 Crush 风格的白名单
        if self.allowed_tools:
            whitelisted = any(
                fnmatch.fnmatch(tool_name.lower(), allowed.lower())
                for allowed in self.allowed_tools
            )
            if not whitelisted:
                return RuleDecision.ASK

        # 按顺序评估规则: deny -> ask -> allow
        matched_rules: list[PermissionRule] = []
        for rule in self.rules:
            if rule.matches(tool_name, arguments):
                matched_rules.append(rule)

        # 按决策优先级排序: deny 优先
        priority = {RuleDecision.DENY: 0, RuleDecision.ASK: 1, RuleDecision.ALLOW: 2}
        matched_rules.sort(key=lambda r: priority.get(r.decision, 1))

        if matched_rules:
            return matched_rules[0].decision

        # 默认行为取决于模式
        if self.mode == PermissionMode.DEFAULT:
            # 默认模式: 读取允许，其他需要确认
            if tool_name in ("read_file", "file_read", "list_dir", "search", "glob"):
                return RuleDecision.ALLOW
            return RuleDecision.ASK

        return RuleDecision.ASK

    def _is_high_risk(self, tool_name: str, arguments: dict[str, Any] | None) -> bool:
        """检查是否为高危操作 — 参考 Claude Code 的分类器"""
        if not arguments:
            return False

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

        if tool_name in ("bash", "run_command", "native_run", "command"):
            command = arguments.get("command", "")
            for pattern in high_risk_patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return True

        # 网络请求
        if tool_name in ("web_search", "http_request", "fetch", "native_web_search"):
            url = arguments.get("url", "")
            if url and not url.startswith(("https://", "http://localhost", "http://127.0.0.1")):
                return True

        return False

    def assess_risk(self, tool_name: str, arguments: dict[str, Any] | None = None) -> str:
        """评估操作风险等级 — 参考 Claude Code Ctrl+E 解释器"""
        if not arguments:
            return "low"

        # 删除操作
        if tool_name in ("file_delete", "delete", "rm"):
            return "high"

        # 命令执行
        if tool_name in ("bash", "run_command", "native_run", "command"):
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
        if tool_name in ("web_search", "http_request", "fetch", "native_web_search"):
            return "medium"

        # 文件读取/写入
        if tool_name in ("read_file", "file_read", "list_dir"):
            return "low"
        if tool_name in ("write_file", "file_write", "edit"):
            return "medium"

        return "low"


def get_default_config() -> PermissionConfig:
    """获取默认权限配置"""
    return PermissionConfig(
        mode=PermissionMode.DEFAULT,
        rules=[
            # 读取操作默认允许
            PermissionRule(RuleDecision.ALLOW, "read_file"),
            PermissionRule(RuleDecision.ALLOW, "file_read"),
            PermissionRule(RuleDecision.ALLOW, "list_dir"),
            PermissionRule(RuleDecision.ALLOW, "search"),
            PermissionRule(RuleDecision.ALLOW, "glob"),
            # 高危命令默认拒绝
            PermissionRule(RuleDecision.DENY, "bash", "rm -rf *"),
            PermissionRule(RuleDecision.DENY, "run_command", "rm -rf *"),
            PermissionRule(RuleDecision.DENY, "bash", "curl *| bash"),
            PermissionRule(RuleDecision.DENY, "bash", "wget *| sh"),
            # 网络访问需要确认
            PermissionRule(RuleDecision.ASK, "web_search"),
            PermissionRule(RuleDecision.ASK, "http_request"),
            PermissionRule(RuleDecision.ASK, "fetch"),
            PermissionRule(RuleDecision.ASK, "native_web_search"),
        ],
    )


def get_plan_mode_config() -> PermissionConfig:
    """计划模式配置 — 只允许读取"""
    return PermissionConfig(
        mode=PermissionMode.PLAN,
        rules=[
            PermissionRule(RuleDecision.ALLOW, "read_file"),
            PermissionRule(RuleDecision.ALLOW, "file_read"),
            PermissionRule(RuleDecision.ALLOW, "list_dir"),
            PermissionRule(RuleDecision.ALLOW, "search"),
            PermissionRule(RuleDecision.ALLOW, "glob"),
            PermissionRule(RuleDecision.ALLOW, "bash", "ls *"),
            PermissionRule(RuleDecision.ALLOW, "bash", "cat *"),
            PermissionRule(RuleDecision.ALLOW, "bash", "find *"),
            PermissionRule(RuleDecision.ALLOW, "bash", "grep *"),
            PermissionRule(RuleDecision.ALLOW, "bash", "git status"),
            PermissionRule(RuleDecision.ALLOW, "bash", "git log *"),
            PermissionRule(RuleDecision.ALLOW, "bash", "git diff *"),
            PermissionRule(RuleDecision.ALLOW, "bash", "git show *"),
            # 其他一律拒绝
            PermissionRule(RuleDecision.DENY, "write_file"),
            PermissionRule(RuleDecision.DENY, "file_write"),
            PermissionRule(RuleDecision.DENY, "edit"),
            PermissionRule(RuleDecision.DENY, "bash", "git push *"),
            PermissionRule(RuleDecision.DENY, "bash", "npm publish *"),
        ],
    )


def get_auto_mode_config() -> PermissionConfig:
    """自动模式配置 — 全自动但有安全检查"""
    return PermissionConfig(
        mode=PermissionMode.AUTO,
        rules=[
            # 只对最高危操作要求确认
            PermissionRule(RuleDecision.ASK, "bash", "rm -rf /*"),
            PermissionRule(RuleDecision.ASK, "bash", "rm -rf /"),
            PermissionRule(RuleDecision.ASK, "bash", "dd if=*"),
            PermissionRule(RuleDecision.ASK, "bash", "mkfs *"),
            PermissionRule(RuleDecision.ASK, "bash", "git push --force *"),
            PermissionRule(RuleDecision.ASK, "bash", "git push -f *"),
            PermissionRule(RuleDecision.ASK, "bash", "npm publish *"),
        ],
    )


# 预定义配置
MODE_CONFIGS = {
    PermissionMode.DEFAULT: get_default_config,
    PermissionMode.PLAN: get_plan_mode_config,
    PermissionMode.AUTO: get_auto_mode_config,
    PermissionMode.ACCEPT_EDITS: lambda: PermissionConfig(
        mode=PermissionMode.ACCEPT_EDITS,
        rules=[
            PermissionRule(RuleDecision.ALLOW, "read_file"),
            PermissionRule(RuleDecision.ALLOW, "file_read"),
            PermissionRule(RuleDecision.ALLOW, "write_file"),
            PermissionRule(RuleDecision.ALLOW, "file_write"),
            PermissionRule(RuleDecision.ALLOW, "edit"),
            PermissionRule(RuleDecision.ALLOW, "list_dir"),
        ],
    ),
    PermissionMode.BYPASS: lambda: PermissionConfig(mode=PermissionMode.BYPASS),
}
