"""对话摘要工具（base_deps）。

改写自 OpenHands `agenthub/codeact_agent/function_calling.py` 的摘要
相关思路（mid conversation 摘要 + 上下文窗口保护）。本文件提供纯函数
工具：消息 token 估算、滑动窗口截断、中间消息摘要化、摘要文本生成，
供 adaptive_compression（创新点 5）与记忆审计复用。

非原样复制：OpenHands 的摘要面向其自家 prompt 结构，这里实现为
与 Climber ModelAdapter messages 结构无关的通用工具。
"""

from __future__ import annotations

from typing import Any


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """粗估 messages 的 token 总量（中文按 3 字符/token 近似）。"""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += max(1, len(content) // 3)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    total += max(1, len(str(part.get("text", ""))) // 3)
        # 工具调用参数按 JSON 文本估算
        for tc in msg.get("tool_calls", []) or []:
            fn = tc.get("function", {})
            total += max(1, len(str(fn.get("arguments", ""))) // 3)
    return total


def sliding_window(messages: list[dict[str, Any]], keep_ratio: float = 0.5) -> list[dict[str, Any]]:
    """保留最近的 keep_ratio 比例消息（滑动窗口截断）。"""
    if keep_ratio <= 0 or keep_ratio >= 1:
        return messages
    keep = max(2, int(len(messages) * keep_ratio))
    return messages[-keep:]


def summarize_middle(
    messages: list[dict[str, Any]], head: int = 2, tail: int = 4, summary_text: str = ""
) -> list[dict[str, Any]]:
    """保留头部 head 条与尾部 tail 条，中间合并为一条 system 摘要。

    与 adaptive_compression.compress_messages 的无摘要回退路径对齐；
    若消息数不足 head+tail+1，原样返回。
    """
    if len(messages) <= head + tail + 1:
        return messages
    head_msgs = messages[:head]
    tail_msgs = messages[-tail:]
    middle = messages[head:-tail]
    if not middle:
        return messages
    if not summary_text:
        summary_text = _auto_summary(middle)
    summary_msg = {"role": "system", "content": f"[上下文摘要] {summary_text}"}
    return [*head_msgs, summary_msg, *tail_msgs]


def _auto_summary(messages: list[dict[str, Any]], max_chars: int = 800) -> str:
    """无 LLM 时的确定性摘要：按角色压缩中间消息。"""
    parts: list[str] = []
    char_budget = max_chars
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if not isinstance(content, str) or not content.strip():
            continue
        line = f"{role}: {content.strip()[:200]}"
        if char_budget <= 0:
            break
        parts.append(line[:char_budget])
        char_budget -= len(line)
    if not parts:
        return "(无可摘要内容)"
    return "\n".join(parts)
