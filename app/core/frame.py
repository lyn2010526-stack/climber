"""Frame Protocol - 强类型事件协议

参考: MonkeyCode desktop/src/driver/frame.rs
将所有引擎事件统一为强类型 Frame，支持流式折叠和状态机归约。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal
from uuid import uuid4


class FrameType(str, Enum):
    """Frame 类型枚举 — 单一词汇表，不允许随意扩展"""
    # 会话生命周期
    SESSION_START = "session-start"
    SESSION_END = "session-end"

    # 消息流
    MESSAGE_START = "message-start"
    MESSAGE_TOKEN = "message-token"
    MESSAGE_END = "message-end"

    # 工具调用
    TOOL_CALL = "tool-call"
    TOOL_RESULT = "tool-result"

    # 权限
    PERMISSION_REQ = "permission-req"
    PERMISSION_RESOLVED = "permission-resolved"

    # 思考/推理
    THINKING_START = "thinking-start"
    THINKING_TOKEN = "thinking-token"
    THINKING_END = "thinking-end"

    # 计划
    PLAN_UPDATE = "plan-update"

    # 状态
    STATUS = "status"
    ERROR = "error"


class FrameKind(str, Enum):
    """Frame 子类型"""
    INFO = "info"
    WARN = "warn"
    SUCCESS = "success"
    ERROR = "error"


PermissionAction = Literal[
    "file_read", "file_write", "file_delete",
    "command", "network", "mcp_tool",
]

PermissionDecision = Literal[
    "allow", "allow_session", "allow_always", "deny",
]


@dataclass(slots=True)
class Frame:
    """强类型事件帧 — 所有引擎输出的统一格式

    结构参考 MonkeyCode: {type, kind?, data?, timestamp(ms), seq}
    """
    type: FrameType
    kind: FrameKind | None = None
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    seq: int = 0
    id: str = field(default_factory=lambda: str(uuid4())[:8])

    def to_dict(self) -> dict[str, Any]:
        """序列化为 JSON-compatible dict"""
        result: dict[str, Any] = {
            "id": self.id,
            "type": self.type.value,
            "ts": self.timestamp,
            "seq": self.seq,
            "data": self.data,
        }
        if self.kind:
            result["kind"] = self.kind.value
        return result

    @classmethod
    def permission_req(
        cls,
        tool_call_id: str,
        action: PermissionAction,
        description: str,
        details: str | None = None,
        severity: str = "medium",
        seq: int = 0,
    ) -> Frame:
        """创建权限请求帧"""
        return cls(
            type=FrameType.PERMISSION_REQ,
            kind=FrameKind.WARN,
            data={
                "toolCallId": tool_call_id,
                "action": action,
                "description": description,
                "details": details,
                "severity": severity,
            },
            seq=seq,
        )

    @classmethod
    def permission_resolved(
        cls,
        tool_call_id: str,
        decision: PermissionDecision,
        seq: int = 0,
    ) -> Frame:
        """创建权限决策帧"""
        return cls(
            type=FrameType.PERMISSION_RESOLVED,
            kind=FrameKind.SUCCESS,
            data={
                "toolCallId": tool_call_id,
                "decision": decision,
            },
            seq=seq,
        )

    @classmethod
    def tool_call(
        cls,
        name: str,
        arguments: dict[str, Any],
        display_name: str | None = None,
        tool_type: str = "builtin",
        seq: int = 0,
    ) -> Frame:
        """创建工具调用帧"""
        return cls(
            type=FrameType.TOOL_CALL,
            kind=FrameKind.INFO,
            data={
                "name": name,
                "displayName": display_name or name,
                "arguments": arguments,
                "toolType": tool_type,
                "status": "running",
            },
            seq=seq,
        )

    @classmethod
    def tool_result(
        cls,
        name: str,
        result: str | None = None,
        error: str | None = None,
        duration_ms: int | None = None,
        seq: int = 0,
    ) -> Frame:
        """创建工具结果帧"""
        status = "error" if error else "success"
        return cls(
            type=FrameType.TOOL_RESULT,
            kind=FrameKind.ERROR if error else FrameKind.SUCCESS,
            data={
                "name": name,
                "result": result,
                "error": error,
                "duration": duration_ms,
                "status": status,
            },
            seq=seq,
        )

    @classmethod
    def message_token(cls, content: str, seq: int = 0) -> Frame:
        """创建消息 token 帧"""
        return cls(
            type=FrameType.MESSAGE_TOKEN,
            data={"content": content},
            seq=seq,
        )

    @classmethod
    def thinking_token(cls, content: str, seq: int = 0) -> Frame:
        """创建思考 token 帧"""
        return cls(
            type=FrameType.THINKING_TOKEN,
            data={"content": content},
            seq=seq,
        )


class FrameFolder:
    """流式帧折叠器 — 将相邻同类型帧折叠为单帧

    参考 MonkeyCode desktop/src/driver/fold.rs
    折叠是等价变换：reduceBatch(raw) ≡ reduceBatch(folded)
    """

    _FOLDABLE = {
        FrameType.MESSAGE_TOKEN,
        FrameType.THINKING_TOKEN,
    }

    def __init__(self):
        self._buffer: list[Frame] = []

    def add(self, frame: Frame) -> Frame | None:
        """添加帧，如果可折叠则累积，否则返回前一个累积帧"""
        if frame.type in self._FOLDABLE:
            if self._buffer and self._buffer[-1].type == frame.type:
                # 折叠：累积内容
                prev = self._buffer[-1]
                prev.data["content"] = prev.data.get("content", "") + frame.data.get("content", "")
                prev.timestamp = frame.timestamp  # 更新时间戳
                return None
            else:
                self._buffer.append(frame)
                return None
        else:
            # 不可折叠帧：先刷新缓冲
            flushed = self._flush()
            return flushed

    def _flush(self) -> Frame | None:
        """刷新缓冲区，返回第一个累积帧"""
        if not self._buffer:
            return None
        result = self._buffer[0]
        # 如果有多个累积帧，合并内容
        if len(self._buffer) > 1:
            contents = [f.data.get("content", "") for f in self._buffer]
            result.data["content"] = "".join(contents)
        self._buffer = [result]  # 保留合并后的帧
        return self._buffer.pop()

    def finalize(self) -> Frame | None:
        """结束折叠，返回剩余帧"""
        return self._flush()


class FrameReducer:
    """帧归约器 — 将帧序列归约为 UI 状态

    参考 MonkeyCode desktop/ui/src/reduce.ts
    """

    def __init__(self):
        self.messages: list[dict[str, Any]] = []
        self.tool_calls: list[dict[str, Any]] = []
        self.permission_requests: dict[str, dict[str, Any]] = {}
        self.thinking: str = ""
        self.status: str = "idle"
        self._current_message: dict[str, Any] | None = None

    def reduce(self, frame: Frame) -> dict[str, Any]:
        """处理单帧，返回当前状态快照"""
        ft = frame.type

        if ft == FrameType.MESSAGE_START:
            self._current_message = {"content": "", "role": "assistant"}
        elif ft == FrameType.MESSAGE_TOKEN:
            if self._current_message is not None:
                self._current_message["content"] += frame.data.get("content", "")
        elif ft == FrameType.MESSAGE_END:
            if self._current_message is not None:
                self.messages.append(self._current_message)
                self._current_message = None
        elif ft == FrameType.THINKING_TOKEN:
            self.thinking += frame.data.get("content", "")
        elif ft == FrameType.THINKING_END:
            pass  # thinking 已累积完成
        elif ft == FrameType.TOOL_CALL:
            self.tool_calls.append(frame.data)
        elif ft == FrameType.TOOL_RESULT:
            # 更新对应工具调用的结果
            name = frame.data.get("name", "")
            for tc in self.tool_calls:
                if tc.get("name") == name and tc.get("status") == "running":
                    tc.update(frame.data)
                    break
        elif ft == FrameType.PERMISSION_REQ:
            tool_call_id = frame.data.get("toolCallId", "")
            self.permission_requests[tool_call_id] = frame.data
        elif ft == FrameType.PERMISSION_RESOLVED:
            tool_call_id = frame.data.get("toolCallId", "")
            if tool_call_id in self.permission_requests:
                self.permission_requests[tool_call_id]["decision"] = frame.data.get("decision")
        elif ft == FrameType.STATUS:
            self.status = frame.data.get("status", self.status)
        elif ft == FrameType.ERROR:
            self.status = "error"

        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        """获取当前状态快照"""
        return {
            "messages": list(self.messages),
            "toolCalls": list(self.tool_calls),
            "permissionRequests": dict(self.permission_requests),
            "thinking": self.thinking,
            "status": self.status,
        }
