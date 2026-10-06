"""Document management endpoints."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from pydantic import BaseModel

from app.api.v1.common import current_user_id
from app.core.auth_manager import require_scopes
from app.core.enhanced_rag import (
    compress_context,
    expand_query,
    reciprocal_rank_fusion,
    rerank_results,
)
from app.core.file_index import file_index_service
from app.storage import async_session
from app.storage.database import Document
from app.tools.rag import chunk_text

logger = structlog.get_logger()

router = APIRouter()


class IndexTextResponse(BaseModel):
    id: str
    name: str
    status: str
    chunks: int


class SearchResponse(BaseModel):
    query: str
    results: list[dict[str, Any]]
    n_results: int


_chroma_client = None
_chroma_collection = None


def get_chroma_collection():
    global _chroma_client, _chroma_collection
    if _chroma_collection is None:
        try:
            import chromadb
            _chroma_client = chromadb.PersistentClient(path="./data/chroma")
            _chroma_collection = _chroma_client.get_or_create_collection(
                name="documents",
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:
            logger.warning("documents.get_chroma_collection_failed", error=str(exc))
            return None
    return _chroma_collection


def _delete_chroma_documents(doc_ids: list[str], user_id: str) -> None:
    """Delete vector chunks for document ids, tolerating an unavailable store."""
    if not doc_ids:
        return
    collection = get_chroma_collection()
    if collection is None:
        return
    for doc_id in doc_ids:
        try:
            # ChromaDB rejects multi-key where clauses in delete/query (v1.5+),
            # so combine the conditions with an explicit $and filter.
            collection.delete(
                where={"$and": [{"doc_id": doc_id}, {"user_id": user_id}]}
            )
        except Exception as exc:
            logger.warning("documents.chroma_delete_failed", doc_id=doc_id, error=str(exc))


async def _supersede_documents(user_id: str, filename: str) -> None:
    """Mark existing rows with the same filename as superseded and drop their vectors."""
    from sqlalchemy import select, update

    async with async_session() as session:
        result = await session.execute(
            select(Document.id).where(
                Document.user_id == user_id,
                Document.filename == filename,
                Document.status != "superseded",
            )
        )
        old_ids = [row[0] for row in result.all()]
        if not old_ids:
            return
        await session.execute(
            update(Document).where(Document.id.in_(old_ids)).values(status="superseded")
        )
        await session.commit()
    _delete_chroma_documents(old_ids, user_id)
    file_index_service.remove(filename)


@router.post("/index-text")
async def index_text(
    request: Request,
    text: str = Form(""),
    name: str = Form("untitled"),
    payload: dict | None = None,
    _auth: dict = Depends(require_scopes("write")),
):
    if not text and payload:
        text = payload.get("text", "")
        name = payload.get("name", "untitled")
    if not text:
        return IndexTextResponse(id="", name=name, status="skipped", chunks=0)
    if not file_index_service.needs_indexing(name, text):
        return IndexTextResponse(id="cached", name=name, status="cached", chunks=0)
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    content_hash = file_index_service.compute_hash(text)
    user_id = current_user_id(request)
    await _supersede_documents(user_id, name)
    async with async_session() as session:
        doc = Document(
            user_id=user_id,
            filename=name,
            content=text,
            content_type="text/plain",
            size_bytes=len(text),
            content_hash=content_hash,
            collection="default",
            chunk_count=len(chunks),
            status="ready",
            indexed_at=datetime.now(UTC),
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
    # Index chunks in Chroma for vector search
    indexed = False
    collection = get_chroma_collection()
    if collection is not None and chunks:
        try:
            ids = [f"doc-{doc.id}-{i}" for i in range(len(chunks))]
            metadatas = [
                {"doc_id": doc.id, "filename": name, "chunk_index": i, "user_id": user_id}
                for i in range(len(chunks))
            ]
            collection.add(documents=chunks, ids=ids, metadatas=metadatas)
            indexed = True
        except Exception as e:
            logger.warning("documents.index_text_chroma_add", error=str(e))
    # Only record the index cache when the vector write succeeded, so a failed
    # vector pass does not short-circuit the next upload with the same content.
    if indexed:
        file_index_service.record_index(name, content_hash, len(text), len(chunks))

    return IndexTextResponse(id=doc.id, name=name, status="indexed", chunks=len(chunks))


@router.get("/")
async def list_documents(request: Request):
    user_id = current_user_id(request)
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Document).where(
                Document.user_id == user_id,
                Document.status != "superseded",
            ).order_by(Document.created_at.desc())
        )
        docs = result.scalars().all()
        return [{"id": d.id, "name": d.filename, "status": d.status, "chunks": d.chunk_count, "size": d.size_bytes} for d in docs]


@router.post("/")
async def create_document(
    request: Request,
    payload: dict,
    _auth: dict = Depends(require_scopes("write")),
):
    user_id = current_user_id(request)
    filename = payload.get("filename", "untitled")
    content = payload.get("content") or ""
    if not isinstance(content, str):
        # R13-05: coerce non-string content instead of calling len() on it.
        content = json.dumps(content, ensure_ascii=False)
    content_type = payload.get("content_type", "text/plain")
    collection_name = payload.get("collection", "default")
    content_hash = file_index_service.compute_hash(content)
    chunks = chunk_text(content, chunk_size=500, overlap=50)

    await _supersede_documents(user_id, filename)
    async with async_session() as session:
        doc = Document(
            user_id=user_id,
            filename=filename,
            content=content,
            content_type=content_type,
            size_bytes=len(content),
            content_hash=content_hash,
            collection=collection_name,
            chunk_count=len(chunks),
            status="ready",
            indexed_at=datetime.now(UTC),
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

    # Run the same vector indexing pipeline as /index-text so plain creates
    # produce searchable chunks instead of zero-chunk rows.
    indexed = False
    collection = get_chroma_collection()
    if collection is not None and chunks:
        try:
            ids = [f"doc-{doc.id}-{i}" for i in range(len(chunks))]
            metadatas = [
                {"doc_id": doc.id, "filename": filename, "chunk_index": i, "user_id": user_id}
                for i in range(len(chunks))
            ]
            collection.add(documents=chunks, ids=ids, metadatas=metadatas)
            indexed = True
        except Exception as e:
            logger.warning("documents.create_document_chroma_add", error=str(e))
    if indexed:
        file_index_service.record_index(filename, content_hash, len(content), len(chunks))

    return {"id": doc.id, "name": doc.filename, "status": doc.status, "chunks": doc.chunk_count}


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: Request, query: str, n_results: int = 5):
    user_id = current_user_id(request)
    collection = get_chroma_collection()
    vector_results: list[dict[str, Any]] = []
    like_results: list[dict[str, Any]] = []

    if collection is not None:
        try:
            # R12-H37: expand the query into variants and query each one.
            expanded = expand_query(query)
            per_query: list[list[dict[str, Any]]] = []
            for q in expanded:
                response = collection.query(
                    query_texts=[q],
                    n_results=min(n_results * 2, 10),
                    where={"user_id": user_id},
                )
                q_results: list[dict[str, Any]] = []
                if response and response.get("documents"):
                    for i, doc in enumerate(response["documents"][0]):
                        meta = response["metadatas"][0][i] if response.get("metadatas") else {}
                        distance = response["distances"][0][i] if response.get("distances") else 0
                        q_results.append({
                            "id": str(meta.get("doc_id", "") or f"vec-{i}"),
                            "text": doc,
                            "metadata": meta,
                            "score": 1.0 - distance,
                        })
                per_query.append(q_results)
            # Fuse the per-query lists with reciprocal rank fusion.
            fused = reciprocal_rank_fusion(per_query, k=60)
            fused_ids = {str(doc_id) for doc_id, _ in fused}
            seen: set[str] = set()
            for r in [item for sub in per_query for item in sub]:
                rid = r["id"]
                if rid in seen or rid not in fused_ids:
                    continue
                seen.add(rid)
                vector_results.append(r)
        except Exception as e:
            logger.warning("documents.search_documents_chroma_query", error=str(e))

    # LIKE search always runs so documents without vector entries (e.g. rows
    # created outside the indexing pipeline) remain reachable even when Chroma
    # already returned hits for other documents.
    async with async_session() as session:
        from sqlalchemy import or_, select
        pattern = f"%{query}%"
        result = await session.execute(
            select(Document).where(
                Document.user_id == user_id,
                Document.status != "superseded",
                or_(Document.filename.ilike(pattern), Document.content.ilike(pattern))
            ).limit(n_results * 2)
        )
        like_results.extend({
            "id": d.id,
            "text": d.content or "",
            "metadata": {"filename": d.filename, "doc_id": d.id},
            "score": 0.5,
        } for d in result.scalars().all())

    # Merge vector and LIKE hits, deduplicating by document id.
    merged: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for r in [*vector_results, *like_results]:
        if r["id"] in seen_ids:
            continue
        seen_ids.add(r["id"])
        merged.append(r)
    # R12-H37: cap over-long result text via context compression.
    for r in merged:
        r["text"] = compress_context(r.get("text", ""), max_total_tokens=1500)

    # Rerank with BM25
    reranked = rerank_results(query, merged, top_k=n_results)
    return SearchResponse(query=query, results=reranked, n_results=len(reranked))


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    request: Request,
    _auth: dict = Depends(require_scopes("write")),
):
    user_id = current_user_id(request)
    async with async_session() as session:
        from sqlalchemy import delete, select
        result = await session.execute(
            select(Document).where(Document.id == doc_id, Document.user_id == user_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        await session.execute(delete(Document).where(Document.id == doc_id, Document.user_id == user_id))
        await session.commit()

    # Remove matching chunks from Chroma.
    _delete_chroma_documents([doc_id], user_id)

    # Invalidate the file-index cache so a re-upload of the same name and
    # content is re-indexed instead of being short-circuited as "cached".
    file_index_service.remove(doc.filename)

    return {"id": doc_id, "deleted": True}
