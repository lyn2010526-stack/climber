"""记忆生命周期层（base_deps）。

改写自 mnemosyne-memory-provider `mnemosyne/memory/sqlite_store.py` 的
设计思路：记忆 TTL 过期清理、记忆权重衰减。非原样复制，实现为原创。

学习要点：
  - TTL：记忆在一定时间内未被访问则过期清理
  - 权重衰减：长期未访问的记忆，权重逐渐降低
  - 合并重复、下调低可信度（配合后台精炼子 Agent 使用）
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent_system.base_deps.fact_extract import FactExtractor
from agent_system.core_models import MemoryAuditEntry, MemoryItem, MemoryKind, now_utc

if TYPE_CHECKING:
    from datetime import datetime

    from agent_system.base_deps.mem_fts5_sqlite import Fts5Store


class MemoryLifecycle:
    """记忆生命周期管理：TTL 清理、权重衰减、合并、审计。

    供后台异步子 Agent 记忆精炼使用（innovation_layer/background_refine.py）。
    """

    def __init__(self, store: Fts5Store, half_life_seconds: float = 7 * 24 * 3600) -> None:
        self.store = store
        self.half_life = half_life_seconds

    def expire_ttl(self) -> list[MemoryAuditEntry]:
        """清理 TTL 过期记忆，输出审计。"""
        expired = self.store.expire_ttl()
        return (
            [MemoryAuditEntry(action="expire", reason=f"TTL 过期清理（共 {expired} 条）")]
            if expired
            else []
        )

    def decay_all(self, now: datetime | None = None) -> list[MemoryAuditEntry]:
        """对所有记忆应用时间衰减（不降 trust，降检索权重 decay）。"""
        now = now or now_utc()
        audits: list[MemoryAuditEntry] = []
        for item in self.store.list_all():
            if item.last_accessed_at is None:
                continue
            age_days = (now - item.last_accessed_at).total_seconds() / 86400
            if age_days >= 14:
                new_decay = 0.5
                audits.append(
                    MemoryAuditEntry(
                        action="downgrade",
                        memory_id=item.id,
                        kind=item.kind,
                        text_preview=item.text[:50],
                        score_before=item.decay,
                        score_after=new_decay,
                        reason=f"14 天未访问，衰减权重 {item.decay}->{new_decay}",
                    )
                )
                self.store.update_trust(item.id, item.trust_score, decay=new_decay)
            elif age_days >= 7:
                new_decay = 0.8
                audits.append(
                    MemoryAuditEntry(
                        action="downgrade",
                        memory_id=item.id,
                        kind=item.kind,
                        text_preview=item.text[:50],
                        score_before=item.decay,
                        score_after=new_decay,
                        reason=f"7 天未访问，衰减权重 {item.decay}->{new_decay}",
                    )
                )
                self.store.update_trust(item.id, item.trust_score, decay=new_decay)
        return audits

    def merge_duplicates(self, similarity_threshold: float = 0.9) -> list[MemoryAuditEntry]:
        """合并重复记忆：相同 predicate+object 或高度相似文本。"""
        audits: list[MemoryAuditEntry] = []
        items = self.store.list_all()
        seen: dict[tuple, list[MemoryItem]] = {}
        for item in items:
            key = (item.kind.value, item.text.strip().lower()[:80])
            seen.setdefault(key, []).append(item)
        for group in seen.values():
            if len(group) < 2:
                continue
            keep = group[0]
            for dup in group[1:]:
                # 更新保留项的可信度（取较高者），删除重复
                if dup.trust_score > keep.trust_score:
                    keep.trust_score = dup.trust_score
                    self.store.update_trust(keep.id, keep.trust_score)
                audits.append(
                    MemoryAuditEntry(
                        action="merge",
                        memory_id=dup.id,
                        kind=dup.kind,
                        text_preview=dup.text[:50],
                        reason=f"与 {keep.id} 重复，合并",
                    )
                )
                self.store.delete(dup.id)
        return audits

    def downgrade_low_trust(self, threshold: float = 0.2) -> list[MemoryAuditEntry]:
        """下调可信度偏低记忆的权重（非删除）。"""
        audits: list[MemoryAuditEntry] = []
        for item in self.store.list_all():
            if item.trust_score < threshold:
                audits.append(
                    MemoryAuditEntry(
                        action="downgrade",
                        memory_id=item.id,
                        kind=item.kind,
                        text_preview=item.text[:50],
                        score_before=item.trust_score,
                        score_after=item.trust_score * 0.5,
                        reason=f"可信度 {item.trust_score:.2f} < {threshold}，下调权重",
                    )
                )
                self.store.update_trust(item.id, item.trust_score * 0.5)
        return audits

    def extract_and_store(
        self, text: str, source_session: str | None = None, context: str = ""
    ) -> list[MemoryAuditEntry]:
        """事实抽取并入库（供精炼子 Agent 使用）。"""
        audits: list[MemoryAuditEntry] = []
        extractor = FactExtractor()
        facts = extractor.extract(text, context)
        for fact in facts:
            item = MemoryItem(
                kind=MemoryKind.FACT,
                text=f"{fact.subject} {fact.predicate} {fact.object}".strip(),
                title=fact.subject,
                doc_type="conversation",
                doc_length=len(fact.object),
                trust_score=fact.confidence,
                source_session=source_session,
                structured={
                    "subject": fact.subject,
                    "predicate": fact.predicate,
                    "object": fact.object,
                    "confidence": fact.confidence,
                },
            )
            existing_id = self.store.upsert(item)
            audits.append(
                MemoryAuditEntry(
                    action="add",
                    memory_id=existing_id,
                    kind=MemoryKind.FACT,
                    text_preview=item.text[:50],
                    score_after=item.trust_score,
                    reason="后台精炼事实抽取入库",
                )
            )
        return audits

    def run_full_refinement(
        self, session_log: str, source_session: str | None = None, context: str = ""
    ) -> list[MemoryAuditEntry]:
        """完整精炼流程：抽取 → 合并 → TTL 清理 → 衰减 → 低可信降权。

        返回记忆审计日志（用户要求：输出记忆审计日志）。
        """
        audits: list[MemoryAuditEntry] = []
        audits.extend(self.extract_and_store(session_log, source_session, context))
        audits.extend(self.merge_duplicates())
        audits.extend(self.expire_ttl())
        audits.extend(self.decay_all())
        audits.extend(self.downgrade_low_trust())
        return audits
