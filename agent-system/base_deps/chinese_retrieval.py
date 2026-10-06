"""中文加权关键词检索层（base_deps）。

改写自 zeyi `zeyi/memory/chinese_retrieval.py` 的设计思路：
中文分词、停用词过滤、标题加权打分。不复制源码，仅实现其
面向中文检索的关键要素：

  - 中文分词（2-gram + 3-gram，含英文词边界）
  - 停用词过滤（中英常用）
  - 标题加权（标题命中权重高于正文）
  - 返回关键词命中得分

学习重点（见 zeyi chinese_retrieval.py）：
  - 中文没有空格分词，需要 n-gram 或分词器
  - 标题通常比正文更相关，应加权
  - 停用词影响召回质量
"""

from __future__ import annotations

import re
import sqlite3
from collections import Counter

from agent_system.core_models import MemoryItem, RetrievedMemory

_CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
_LATIN_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]*")

# 中英停用词表（zeyi 思路：过滤高频无意义词）
STOPWORDS = {
    # 中文
    "的",
    "了",
    "是",
    "在",
    "和",
    "与",
    "或",
    "也",
    "都",
    "就",
    "而",
    "及",
    "我",
    "你",
    "他",
    "她",
    "它",
    "我们",
    "你们",
    "他们",
    "这个",
    "那个",
    "一个",
    "之",
    "于",
    "为",
    "以",
    "对",
    "从",
    "到",
    "把",
    "被",
    "让",
    "给",
    "使",
    "这",
    "那",
    "些",
    "很",
    "更",
    "最",
    "只",
    "但",
    "如果",
    "因为",
    "所以",
    "然后",
    "接着",
    "并且",
    "以及",
    "或者",
    "可以",
    "需要",
    "应该",
    "将",
    "会",
    # 英文
    "the",
    "a",
    "an",
    "of",
    "to",
    "in",
    "and",
    "or",
    "for",
    "on",
    "with",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "that",
    "this",
    "it",
    "as",
    "at",
    "by",
    "from",
    "not",
    "we",
    "you",
    "they",
    "he",
    "she",
    "i",
}


def tokenize_chinese(text: str) -> list[str]:
    """中文分词：2-gram 字符对 + 3-gram + 拉丁词，过滤停用词。

    - 中文连续片段走 n-gram（zeyi 中文分词的轻量实现）
    - 英文/数字按词切分
    - 停用词过滤
    """
    tokens: list[str] = []
    # 拉丁词
    for w in _LATIN_WORD_RE.findall(text):
        wl = w.lower()
        if wl not in STOPWORDS and len(wl) > 1:
            tokens.append(wl)
    # 中文 n-gram
    for ch_seq in re.findall(r"[\u4e00-\u9fff]+", text):
        seq = ch_seq
        for i in range(len(seq) - 1):
            bigram = seq[i : i + 2]
            if bigram not in STOPWORDS:
                tokens.append(bigram)
        for i in range(len(seq) - 2):
            trigram = seq[i : i + 3]
            if trigram not in STOPWORDS:
                tokens.append(trigram)
    # 去重保持顺序
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def tokenize_query(text: str) -> list[str]:
    """查询分词，同样过滤停用词。"""
    return tokenize_chinese(text)


class ChineseWeightedIndex:
    """中文加权检索索引（内存 + SQLite 可持久化）。

    设计：
      - 标题词表 weighted 高于正文
      - 命中即按词频率 + 位置权重打分
      - 支持与 FTS5 结果融合
    """

    TITLE_WEIGHT = 2.0
    BODY_WEIGHT = 1.0

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._token_rows: dict[str, list[tuple[str, float]]] = {}  # token -> [(mem_id, weight)]
        self._titles: dict[str, str] = {}
        self._docs: dict[str, MemoryItem] = {}
        if db_path:
            self._connect()

    def _connect(self) -> None:
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cn_index (
                token TEXT NOT NULL,
                memory_id TEXT NOT NULL,
                weight REAL NOT NULL,
                PRIMARY KEY (token, memory_id)
            );
            CREATE TABLE IF NOT EXISTS cn_docs (
                memory_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                kind TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def add(self, item: MemoryItem) -> None:
        """索引一条记忆：标题加权 2.0，正文 1.0。"""
        self._docs[item.id] = item
        self._titles[item.id] = item.title
        tokens = tokenize_chinese(f"{item.title}\n{item.text}")
        for token in tokens:
            weight = (
                self.TITLE_WEIGHT if token in tokenize_chinese(item.title) else self.BODY_WEIGHT
            )
            self._token_rows.setdefault(token, []).append((item.id, weight))
        if self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO cn_docs(memory_id, title, text, kind) VALUES (?,?,?,?)",
                (item.id, item.title, item.text, item.kind.value),
            )
            self._conn.execute("DELETE FROM cn_index WHERE memory_id=?", (item.id,))
            for t in set(tokens):
                w = self.TITLE_WEIGHT if t in tokenize_chinese(item.title) else self.BODY_WEIGHT
                self._conn.execute(
                    "INSERT OR REPLACE INTO cn_index(token, memory_id, weight) VALUES (?,?,?)",
                    (t, item.id, w),
                )
            self._conn.commit()

    def delete(self, memory_id: str) -> None:
        self._docs.pop(memory_id, None)
        self._titles.pop(memory_id, None)
        for token in list(self._token_rows):
            self._token_rows[token] = [
                (mid, w) for mid, w in self._token_rows[token] if mid != memory_id
            ]
        if self._conn:
            self._conn.execute("DELETE FROM cn_docs WHERE memory_id=?", (memory_id,))
            self._conn.execute("DELETE FROM cn_index WHERE memory_id=?", (memory_id,))
            self._conn.commit()

    def search(
        self, query: str, top_k: int = 10, kinds: list[str] | None = None
    ) -> list[RetrievedMemory]:
        """中文加权检索。

        打分 = 命中 token 权重和 / 查询 token 数，标题命中额外加权。
        """
        query_tokens = tokenize_query(query)
        if not query_tokens:
            return []
        scores: Counter[str] = Counter()  # mem_id -> raw score
        for token in query_tokens:
            for mem_id, weight in self._token_rows.get(token, []):
                scores[mem_id] += weight

        results: list[RetrievedMemory] = []
        for mem_id, raw in scores.most_common(top_k * 3):
            item = self._docs.get(mem_id)
            if item is None:
                continue
            if kinds and item.kind.value not in kinds:
                continue
            # 归一化：raw 除以查询 token 数，越高的 token 越相关
            normalized = min(1.0, raw / max(len(query_tokens), 1))
            title_hit = any(t in tokenize_chinese(item.title) for t in query_tokens)
            if title_hit:
                normalized = min(1.0, normalized * 1.3)  # 标题加权
            results.append(
                RetrievedMemory(
                    item=item,
                    route="chinese",
                    score=round(normalized, 4),
                    keyword_score=round(normalized, 4),
                    reason=f"cn_tokens={raw:.0f}/{len(query_tokens)} title_hit={title_hit}",
                )
            )
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
