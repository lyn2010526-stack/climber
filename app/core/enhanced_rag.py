"""Enhanced RAG (Retrieval-Augmented Generation) utilities."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any


def compute_bm25(query: str, documents: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    """Compute BM25 scores for query against documents."""
    query_terms = query.lower().split()
    doc_lengths = [len(doc.lower().split()) for doc in documents]
    avg_dl = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1
    if avg_dl == 0:
        avg_dl = 1
    doc_terms = [Counter(doc.lower().split()) for doc in documents]
    idf = {}
    for term in query_terms:
        df = sum(1 for dt in doc_terms if term in dt)
        idf[term] = math.log((len(documents) - df + 0.5) / (df + 0.5) + 1)

    scores = []
    for i, dt in enumerate(doc_terms):
        score = 0.0
        dl = doc_lengths[i]
        for term in query_terms:
            tf = dt.get(term, 0)
            idf_val = idf.get(term, 0)
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * dl / avg_dl)
            score += idf_val * numerator / denominator
        scores.append(score)
    return scores


def rerank_results(query: str, results: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
    """Rerank search results using BM25."""
    if not results:
        return []
    documents = [r.get("text") or r.get("content", "") for r in results]
    scores = compute_bm25(query, documents)
    scored = [(score, result) for score, result in zip(scores, results, strict=False)]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [result for _, result in scored[:top_k]]


def expand_query(query: str) -> list[str]:
    """Expand query with synonyms and related terms."""
    expansions = {
        "ai": ["artificial intelligence", "machine learning"],
        "ml": ["machine learning", "deep learning"],
        "api": ["interface", "endpoint"],
    }
    expanded = [query]
    query_lower = query.lower()
    for key, synonyms in expansions.items():
        if key in query_lower:
            expanded.extend(synonyms)
    return list(set(expanded))


def compress_context(contexts: list[str], max_total_tokens: int = 2000) -> str:
    """Compress context by extracting key sentences."""
    if isinstance(contexts, str):
        contexts = [contexts]
    full_text = " ".join(contexts)
    if len(full_text) <= max_total_tokens:
        return full_text
    sentences = full_text.split(". ")
    compressed = []
    current_length = 0
    for sentence in sentences:
        if current_length + len(sentence) <= max_total_tokens:
            compressed.append(sentence)
            current_length += len(sentence) + 2
        else:
            break
    result = ". ".join(compressed)
    if len(result) < len(full_text):
        result += "...[TRUNCATED]"
    return result


def reciprocal_rank_fusion(results_list: list[list[dict[str, Any] | tuple[str, float]]], k: int = 60) -> list[tuple[str, float]]:
    """Combine multiple result lists using reciprocal rank fusion."""
    scores: dict[str, float] = {}
    for results in results_list:
        for rank, result in enumerate(results):
            if isinstance(result, tuple):
                doc_id = result[0]
            else:
                doc_id = result.get("id", str(rank))
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)

    scored = list(scores.items())
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:10]
