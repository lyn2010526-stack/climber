"""Document management endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Form, HTTPException, Request
from pydantic import BaseModel

from app.api.v1.common import current_user_id
from app.core.enhanced_rag import rerank_results
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


@router.post("/index-text")
async def index_text(
    request: Request,
    text: str = Form(""),
    name: str = Form("untitled"),
    payload: dict | None = None,
):
    if not text and payload:
        text = payload.get("text", "")
        name = payload.get("name", "untitled")
    if not text:
        return IndexTextResponse(id="", name=name, status="skipped", chunks=0)
    from app.core.file_index import file_index_service
    if not file_index_service.needs_indexing(name, text):
        return IndexTextResponse(id="cached", name=name, status="cached", chunks=0)
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    content_hash = file_index_service.compute_hash(text)
    user_id = current_user_id(request)
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
    file_index_service.record_index(name, content_hash, len(text), len(chunks))
    # Index chunks in Chroma for vector search
    collection = get_chroma_collection()
    if collection is not None and chunks:
        try:
            ids = [f"doc-{doc.id}-{i}" for i in range(len(chunks))]
            metadatas = [
                {"doc_id": doc.id, "filename": name, "chunk_index": i, "user_id": user_id}
                for i in range(len(chunks))
            ]
            collection.add(documents=chunks, ids=ids, metadatas=metadatas)
        except Exception as e:
            logger.warning("documents.index_text_chroma_add", error=str(e))

    return IndexTextResponse(id=doc.id, name=name, status="indexed", chunks=len(chunks))


@router.get("/")
async def list_documents(request: Request):
    user_id = current_user_id(request)
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())
        )
        docs = result.scalars().all()
        return [{"id": d.id, "name": d.filename, "status": d.status, "chunks": d.chunk_count, "size": d.size_bytes} for d in docs]


@router.post("/")
async def create_document(request: Request, payload: dict):
    user_id = current_user_id(request)
    async with async_session() as session:
        doc = Document(
            user_id=user_id,
            filename=payload.get("filename", "untitled"),
            content=payload.get("content", ""),
            content_type=payload.get("content_type", "text/plain"),
            size_bytes=len(payload.get("content", "")),
            collection=payload.get("collection", "default"),
            status="ready",
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        return {"id": doc.id, "name": doc.filename, "status": doc.status, "chunks": doc.chunk_count}


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: Request, query: str, n_results: int = 5):
    user_id = current_user_id(request)
    collection = get_chroma_collection()
    results = []

    if collection is not None:
        try:
            response = collection.query(
                query_texts=[query],
                n_results=min(n_results, 10),
                where={"user_id": user_id},
            )
            if response and response.get("documents"):
                for i, doc in enumerate(response["documents"][0]):
                    meta = response["metadatas"][0][i] if response.get("metadatas") else {}
                    distance = response["distances"][0][i] if response.get("distances") else 0
                    results.append({
                        "text": doc,
                        "metadata": meta,
                        "score": 1.0 - distance,
                    })
        except Exception as e:
            logger.warning("documents.search_documents_chroma_query", error=str(e))

    # Fallback to LIKE if Chroma is empty or unavailable
    if not results:
        async with async_session() as session:
            from sqlalchemy import or_, select
            pattern = f"%{query}%"
            result = await session.execute(
                select(Document).where(
                    Document.user_id == user_id,
                    or_(Document.filename.ilike(pattern), Document.content.ilike(pattern))
                ).limit(n_results)
            )
            docs = result.scalars().all()
            for d in docs:
                results.append({
                    "text": d.content or "",
                    "metadata": {"filename": d.filename, "doc_id": d.id},
                    "score": 0.5,
                })

    # Rerank with BM25
    reranked = rerank_results(query, results, top_k=n_results)
    return SearchResponse(query=query, results=reranked, n_results=len(reranked))


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, request: Request):
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

    # Remove from Chroma
    collection = get_chroma_collection()
    if collection is not None:
        try:
            collection.delete(where={"doc_id": doc_id, "user_id": user_id})
        except Exception as e:
            logger.warning("documents.delete_document_chroma_delete", error=str(e))

    return {"id": doc_id, "deleted": True}
