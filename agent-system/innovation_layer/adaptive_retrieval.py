"""自适应双记忆检索路由（innovation_layer，创新点 1）。

检索策略自动切换：依据文档类型、长度自动切换关键词检索或向量检索，
混合场景做结果融合，适配中文 skill 规则与代码项目混合场景。

创新点（区别于固定单一检索的现有开源 Agent）：
  - 输入：查询文本 + 文档元信息（字符长度、文档类型标记）
  - 短 skill/规则类文档 → FTS5 + 中文加权
  - 长代码、大段自然文本 → 向量检索插件
  - 混合场景 → 两套结果加权融合再排序
  - 输出：召回记忆列表 + 可信度 + 时间衰减权重
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_system.core_models import (
    MemoryKind,
    RetrievedMemory,
)

if TYPE_CHECKING:
    from agent_system.base_deps.chinese_retrieval import ChineseWeightedIndex
    from agent_system.base_deps.mem_fts5_sqlite import Fts5Store

# 检索路由阈值
SHORT_DOC_MAX_LEN = 500          # 短文档：skill/规则
LONG_DOC_MIN_LEN = 2000          # 长文档：代码/长文本
VECTOR_SIM_THRESHOLD = 0.55      # 向量召回的最低相似度


class AdaptiveRetrievalRouter:
    """自适应双记忆检索路由。

    路由决策（R 输入 = 查询 + 文档元信息）：
      route = fts_chinese   if doc_type in {skill, rule} or doc_len <= SHORT_DOC_MAX_LEN
      route = vector        if doc_len >= LONG_DOC_MIN_LEN or doc_type in {code, text}
      route = hybrid        otherwise（混合融合）
    """

    def __init__(
        self,
        fts_store: Fts5Store | None = None,
        chinese_index: ChineseWeightedIndex | None = None,
        vector_store: Any | None = None,   # 可选插件（vector_memory 思路，smart-connections 参考）
        fts_weight: float = 0.6,
        chinese_weight: float = 0.4,
        vector_weight: float = 0.5,
    ) -> None:
        self.fts_store = fts_store
        self.chinese_index = chinese_index
        self.vector_store = vector_store
        self.fts_weight = fts_weight
        self.chinese_weight = chinese_weight
        self.vector_weight = vector_weight

    # ---- 路由决策 ----

    def decide_route(self, query: str, doc_type: str | None = None,
                     doc_length: int = 0, force: str | None = None) -> str:
        """决定走哪条检索路径。"""
        if force:
            return force
        if doc_type in {"skill", "rule"} or (0 < doc_length <= SHORT_DOC_MAX_LEN):
            return "fts_chinese"
        if doc_type in {"code", "text"} or doc_length >= LONG_DOC_MIN_LEN:
            return "vector" if self.vector_store is not None else "fts_chinese"
        return "hybrid"

    # ---- 检索 ----

    async def retrieve(self, query: str, top_k: int = 10,
                       doc_type: str | None = None, doc_length: int = 0,
                       force_route: str | None = None,
                       kinds: list[str] | None = None,
                       profile_context: dict[str, Any] | None = None) -> list[RetrievedMemory]:
        """自适应检索入口。

        Args:
            query: 查询文本
            doc_type: 文档类型标记（skill|rule|code|text|conversation|None）
            doc_length: 文档字符长度
            force_route: 强制路由（fts_chinese|vector|hybrid）
            kinds: 限定记忆种类
            profile_context: 画像偏好上下文（Climber 现有 rank_with_profile 对接）
        """
        route = self.decide_route(query, doc_type, doc_length, force_route)
        results: list[RetrievedMemory] = []

        if route in ("fts_chinese", "hybrid"):
            if self.fts_store is not None:
                results.extend(self.fts_store.search(query, top_k=top_k, kinds=kinds))
            if self.chinese_index is not None:
                results.extend(self.chinese_index.search(query, top_k=top_k, kinds=kinds))

        if route in ("vector", "hybrid") and self.vector_store is not None:
            try:
                vector_results = await self._vector_search(query, top_k, kinds, profile_context)
                results.extend(vector_results)
            except Exception:  # noqa: S110 - 向量插件不可用时回退关键词结果
                pass

        return self._fuse(query, results, route, top_k)

    async def _vector_search(self, query: str, top_k: int, kinds: list[str] | None,
                             profile_context: dict[str, Any] | None) -> list[RetrievedMemory]:
        """调用向量检索插件（Chroma vector_memory 或 smart-connections 思路插件）。"""
        collection = "archival"  # 长文档/代码默认集合
        raw = await self.vector_store.search(
            collection, query, top_k=top_k,
            profile_context=profile_context,
        )
        results: list[RetrievedMemory] = []
        for doc in raw:
            item = _dict_to_memory_item(doc)
            if kinds and item.kind.value not in kinds:
                continue
            vector_score = float(doc.get("score", 0.0))
            if vector_score < VECTOR_SIM_THRESHOLD:
                continue
            results.append(RetrievedMemory(
                item=item, route="vector", score=round(vector_score, 4),
                vector_score=round(vector_score, 4),
                reason=f"vector={vector_score:.2f}",
            ))
        return results

    # ---- 融合排序 ----

    def _fuse(self, query: str, results: list[RetrievedMemory],
              route: str, top_k: int) -> list[RetrievedMemory]:
        """加权融合：同一条记忆多路由得分合并，去重排序。"""
        by_id: dict[str, RetrievedMemory] = {}
        for r in results:
            mem_id = r.item.id
            if mem_id in by_id:
                existing = by_id[mem_id]
                existing.vector_score = max(existing.vector_score, r.vector_score)
                existing.keyword_score = max(existing.keyword_score, r.keyword_score)
                existing.route = "hybrid" if existing.route != "hybrid" else existing.route
                continue
            by_id[mem_id] = r
        # 单路由/多路由统一按融合权重算分
        keyword_weights = {
            "fts": self.fts_weight,
            "chinese": self.chinese_weight,
        }
        for r in by_id.values():
            keyword = r.keyword_score * keyword_weights.get(r.route, 0.0)
            if r.route == "hybrid":
                keyword = r.keyword_score * max(self.fts_weight, self.chinese_weight)
            fused = keyword + r.vector_score * self.vector_weight
            r.score = round(fused, 4)
        fused = list(by_id.values())
        fused.sort(key=lambda r: r.score, reverse=True)
        return fused[:top_k]

    def _rerank_with_profile(self, results: list[RetrievedMemory],
                             profile_context: dict[str, Any] | None) -> list[RetrievedMemory]:
        """画像偏好微调排序（对接 Climber rank_with_profile 思路）。"""
        if not profile_context or not profile_context.get("enabled"):
            return results
        confidence = float(profile_context.get("confidence", 0.0) or 0.0)
        if confidence <= 0:
            return results
        for r in results:
            prefs = profile_context.get("task_preferences", {}) or {}
            task_type = (r.item.metadata or {}).get("task_type")
            if task_type and isinstance(prefs, dict):
                boost = float(prefs.get(task_type, 0.0) or 0.0)
                r.profile_boost = round(boost * confidence, 4)
                r.score = round(r.score + 0.2 * r.profile_boost, 4)
        results.sort(key=lambda r: r.score, reverse=True)
        return results


def _dict_to_memory_item(doc: dict[str, Any]):
    """把向量存储返回的 dict 转成 MemoryItem。"""
    from agent_system.core_models import MemoryItem, now_utc
    metadata = doc.get("metadata") or {}
    kind_str = metadata.get("kind", "text")
    try:
        kind = MemoryKind(kind_str)
    except ValueError:
        kind = MemoryKind.TEXT
    text = doc.get("text", "")
    return MemoryItem(
        id=doc.get("id", ""),
        kind=kind,
        text=text,
        title=metadata.get("title", ""),
        doc_type=metadata.get("doc_type", "text"),
        doc_length=len(text),
        metadata=metadata,
        trust_score=float(metadata.get("trust_score", 0.5)),
        created_at=now_utc(),
    )
