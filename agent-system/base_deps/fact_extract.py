"""结构化事实抽取层（base_deps）。

改写自 hindsight `hindsight/memory/fact_extract.py` 的设计思路：
从对话与工具返回文本中抽取结构化事实（三元组：主语-谓词-宾语）。

不复制源码。实现原创：
  - 规则 + 轻量启发式抽取（无 LLM 依赖，确定性可评测）
  - 支持 LLM 后端可选增强（用户项目可注入）
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_VERB_PATTERNS = [
    r"(?:我们|我|项目|系统|服务|模块|函数|类|接口|配置|代码|脚本)?"
    r"(?:把|将)?\s*([\u4e00-\u9fffA-Za-z_][\u4e00-\u9fffA-Za-z0-9_.\-]{1,40})"
    r"\s*(?:被|已|用于|用来|改为|改成|设为|设置|实现了|实现|完成|修复|添加|增加|删除|更新|引入|调用|返回|抛出|定义为|建立|创建|部署|运行|启动|停止|替换|迁移)\s*"
    r"([\u4e00-\u9fffA-Za-z0-9_./\- :，。]{1,60})",
]

_KEYWORD_RULES = [
    # 错误修复类
    (r"(?:修复|解决|fix)[了：:]?\s*([\u4e00-\u9fffA-Za-z0-9_.\-/ ]+)", "修复"),
    (r"(?:bug|缺陷|问题)\s*[：:]\s*([\u4e00-\u9fffA-Za-z0-9_.\-/ ]+)", "缺陷"),
    # 依赖/版本类
    (r"(?:依赖|库|package|包)\s*[：:]\s*([\u4e00-\u9fffA-Za-z0-9_.\- ]+)", "依赖"),
    # 性能类
    (r"(?:性能|耗时|延迟)\s*[：:]\s*([\u4e00-\u9fffA-Za-z0-9%.ms秒 ]+)", "性能"),
    # 结果类
    (r"(?:结果|output|返回|结论)\s*[：:]\s*(.{1,80})", "结果"),
]

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{4}/\d{2}/\d{2}")


@dataclass
class Fact:
    subject: str
    predicate: str
    object: str
    confidence: float = 0.5
    source: str = "heuristic"
    context: str = ""


class FactExtractor:
    """从对话/工具返回文本中抽取结构化事实。

    确定性启发式优先（可评测），可注入 LLM 后端增强。
    """

    def __init__(self, llm_extractor: Any | None = None) -> None:
        self._llm = llm_extractor

    def extract(self, text: str, context: str = "") -> list[Fact]:
        """抽取结构化事实列表。"""
        facts: list[Fact] = []
        if not text:
            return facts

        # 1) 三元组规则
        for match in re.finditer(r"([\u4e00-\u9fffA-Za-z_][\u4e00-\u9fffA-Za-z0-9_.\-]{0,40})"
                                 r"\s*(?:被|已|用于|用来|实现|完成|修复|设置|定义为)\s*"
                                 r"([\u4e00-\u9fffA-Za-z0-9_./\- :]{1,50})",
                                 text):
            subject, obj = match.group(1), match.group(2)
            if subject and obj and len(subject) > 1 and len(obj) > 1:
                facts.append(Fact(subject=subject, predicate="关联/设置", object=obj,
                                  confidence=0.55, context=context[:120]))

        # 2) 关键词规则
        for pattern, predicate in _KEYWORD_RULES:
            for match in re.finditer(pattern, text):
                value = match.group(1).strip()
                if value and 2 <= len(value) <= 100:
                    facts.append(Fact(subject="", predicate=predicate, object=value,
                                      confidence=0.6, context=context[:120]))

        # 3) 版本/时间事实
        facts.extend(
            Fact(subject="版本", predicate="版本号", object=match.group(1),
                 confidence=0.5, context=context[:120])
            for match in re.finditer(r"v?(\d+\.\d+(?:\.\d+)?)", text)
        )

        # 4) 去重（同 predicate+object）
        seen: set[tuple[str, str]] = set()
        deduped: list[Fact] = []
        for fact in facts:
            key = (fact.predicate, fact.object)
            if key not in seen:
                seen.add(key)
                deduped.append(fact)
        facts = deduped

        # 5) LLM 增强（可选）
        if self._llm is not None and facts:
            try:
                enhanced = self._llm(text, facts)
                if enhanced:
                    facts = enhanced
            except Exception:  # noqa: S110 - LLM 失败保持启发式结果
                pass
        return facts


def extract_facts(text: str, context: str = "") -> list[dict[str, Any]]:
    """便捷入口，返回 dict 列表（供记忆精炼后台子 Agent 调用）。"""
    extractor = FactExtractor()
    return [{
        "subject": f.subject,
        "predicate": f.predicate,
        "object": f.object,
        "confidence": f.confidence,
        "context": f.context,
    } for f in extractor.extract(text, context)]
