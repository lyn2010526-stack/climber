"""Tests for the user instruction trace archive."""

from __future__ import annotations

import uuid

import pytest

from app.storage.models_instruction_traces import InstructionTrace
from app.storage.repository_instruction_traces import (
    compress_into_summary,
    count_traces,
    create_trace,
    create_traces_bulk,
    estimate_token_count,
    list_by_session,
    list_by_user,
    list_traces,
    list_unarchived,
    mark_archived,
    retrieve_traces,
    update_trace_outcome,
)

UNICODE_SAMPLE = (
    "把这个仓库重构一下\n"
    "第二行：保留 🚀 emoji 和中文标点，。！\n"
    "\t制表符 + 特殊符号 <>&\"'\\/|`~*#$%@^()[]{}"
)


async def _db():
    from app.storage import async_session

    return async_session()


async def test_create_and_read_back_by_session() -> None:
    session_id = str(uuid.uuid4())
    async with await _db() as db:
        trace, deduped = await create_trace(
            db, {"raw_text": "ship the release", "session_id": session_id}
        )
        await db.commit()
        assert deduped is False
        rows = await list_by_session(db, session_id)
        assert [r.id for r in rows] == [trace.id]
        assert rows[0].raw_text == "ship the release"


async def test_raw_text_stored_verbatim() -> None:
    session_id = str(uuid.uuid4())
    async with await _db() as db:
        trace, _ = await create_trace(db, {"raw_text": UNICODE_SAMPLE, "session_id": session_id})
        await db.commit()
        await db.refresh(trace)
        assert trace.raw_text == UNICODE_SAMPLE
        assert "\n" in trace.raw_text
        assert "🚀" in trace.raw_text
        assert trace.raw_text.count("\n") == UNICODE_SAMPLE.count("\n")

        reread = await list_by_session(db, session_id)
        assert reread[0].raw_text == UNICODE_SAMPLE
        assert reread[0].raw_text.startswith("把这个仓库重构一下\n")


async def test_duplicate_write_is_deduplicated() -> None:
    session_id = str(uuid.uuid4())
    payload = {"raw_text": "run the tests twice", "session_id": session_id}
    async with await _db() as db:
        first, dedup_first = await create_trace(db, dict(payload))
        await db.commit()
        second, dedup_second = await create_trace(db, dict(payload))
        await db.commit()

        assert dedup_first is False
        assert dedup_second is True
        assert second.id == first.id
        assert await count_traces(db, session_id=session_id) == 1


async def test_duplicate_across_different_sessions_is_kept() -> None:
    text = "identical sentence, different sessions"
    session_a, session_b = str(uuid.uuid4()), str(uuid.uuid4())
    async with await _db() as db:
        await create_trace(db, {"raw_text": text, "session_id": session_a})
        await create_trace(db, {"raw_text": text, "session_id": session_b})
        await db.commit()
        assert await count_traces(db, session_id=session_a) == 1
        assert await count_traces(db, session_id=session_b) == 1
        assert await count_traces(db) == 2


async def test_dedup_window_zero_disables_suppression() -> None:
    session_id = str(uuid.uuid4())
    payload = {"raw_text": "always archive me", "session_id": session_id}
    async with await _db() as db:
        await create_trace(db, dict(payload), dedup_window_seconds=300)
        await create_trace(db, dict(payload), dedup_window_seconds=0)
        await db.commit()
        assert await count_traces(db, session_id=session_id) == 2


async def test_bulk_write_deduplicates_within_batch() -> None:
    session_id = str(uuid.uuid4())
    payloads = [
        {"raw_text": "step one", "session_id": session_id},
        {"raw_text": "step one", "session_id": session_id},
        {"raw_text": "step two", "session_id": session_id},
    ]
    async with await _db() as db:
        stored, deduped = await create_traces_bulk(db, payloads)
        await db.commit()
        assert len(stored) == 2
        assert deduped == 1
        assert await count_traces(db, session_id=session_id) == 2


async def test_list_by_user_returns_all_sessions() -> None:
    user_id = str(uuid.uuid4())
    async with await _db() as db:
        await create_trace(
            db, {"raw_text": "first", "user_id": user_id, "session_id": str(uuid.uuid4())}
        )
        await create_trace(
            db, {"raw_text": "second", "user_id": user_id, "session_id": str(uuid.uuid4())}
        )
        await create_trace(db, {"raw_text": "other", "user_id": str(uuid.uuid4())})
        await db.commit()

        rows = await list_by_user(db, user_id)
        assert {r.raw_text for r in rows} == {"first", "second"}


async def test_compression_preserves_original_records() -> None:
    session_id = str(uuid.uuid4())
    async with await _db() as db:
        originals = []
        for text in ("alpha instruction", "beta instruction", "gamma instruction"):
            trace, _ = await create_trace(db, {"raw_text": text, "session_id": session_id})
            originals.append(trace)
        await db.commit()
        original_ids = [t.id for t in originals]
        original_raw = [t.raw_text for t in originals]

        summary = await compress_into_summary(
            db,
            original_ids,
            summary="summary of alpha/beta/gamma",
            task_spec={"steps": ["alpha", "beta", "gamma"]},
        )
        await db.commit()

        survivors = await list_traces(db, session_id=session_id, limit=50)
        by_id = {r.id: r for r in survivors}
        for trace_id, raw in zip(original_ids, original_raw, strict=True):
            assert trace_id in by_id, "compression must not delete the original row"
            assert by_id[trace_id].raw_text == raw
            assert by_id[trace_id].is_archived is True
            assert by_id[trace_id].compressed_into_id == summary.id

        assert summary.id in by_id
        assert by_id[summary.id].raw_text == "summary of alpha/beta/gamma"
        assert by_id[summary.id].task_spec == {"steps": ["alpha", "beta", "gamma"]}

        archived = await list_traces(db, session_id=session_id, is_archived=True, limit=50)
        assert {r.id for r in archived} == set(original_ids)
        unarchived = await list_unarchived(db, session_id=session_id)
        assert [r.id for r in unarchived] == [summary.id]


async def test_compression_rejects_empty_selection() -> None:
    async with await _db() as db:
        with pytest.raises(ValueError, match="at least one trace id"):
            await compress_into_summary(db, [], summary="nothing to compress")


async def test_mark_archived_sets_flag_without_delete() -> None:
    session_id = str(uuid.uuid4())
    async with await _db() as db:
        first, _ = await create_trace(db, {"raw_text": "keep me", "session_id": session_id})
        second, _ = await create_trace(db, {"raw_text": "keep me too", "session_id": session_id})
        await db.commit()

        updated = await mark_archived(db, [first.id])
        await db.commit()
        assert updated == 1
        assert (await list_traces(db, session_id=session_id, is_archived=True))[0].id == first.id
        assert (await list_traces(db, session_id=session_id, is_archived=False))[0].id == second.id


async def test_filter_and_pagination() -> None:
    user_id = str(uuid.uuid4())
    other_session = str(uuid.uuid4())
    async with await _db() as db:
        for index in range(5):
            trace, _ = await create_trace(
                db,
                {
                    "raw_text": f"instruction number {index}",
                    "user_id": user_id,
                    "session_id": other_session,
                },
            )
            if index == 0:
                trace.is_archived = True
        await db.commit()

        assert await count_traces(db, user_id=user_id) == 5
        assert await count_traces(db, user_id=user_id, is_archived=True) == 1
        assert await count_traces(db, user_id=user_id, is_archived=False) == 4

        page_one = await list_traces(db, user_id=user_id, limit=2, offset=0)
        page_two = await list_traces(db, user_id=user_id, limit=2, offset=2)
        assert len(page_one) == 2
        assert len(page_two) == 2
        assert not {r.id for r in page_one} & {r.id for r in page_two}

        tail = await list_traces(db, user_id=user_id, limit=2, offset=4)
        assert len(tail) == 1
        assert await list_traces(db, user_id=user_id, limit=10, offset=99) == []


async def test_token_count_is_estimated_when_absent() -> None:
    async with await _db() as db:
        trace, _ = await create_trace(db, {"raw_text": "count my tokens please"})
        await db.commit()
        assert trace.token_count == estimate_token_count("count my tokens please")
        assert trace.token_count > 0


async def test_retrieval_is_user_scoped_and_updates_access_metadata() -> None:
    user_id = str(uuid.uuid4())
    async with await _db() as db:
        own, _ = await create_trace(db, {"raw_text": "private deployment plan", "user_id": user_id})
        await create_trace(
            db, {"raw_text": "private deployment plan", "user_id": str(uuid.uuid4())}
        )
        await db.commit()

        rows = await retrieve_traces(db, user_id=user_id, query="deployment")
        await db.commit()
        assert [row.id for row in rows] == [own.id]
        await db.refresh(own)
        assert own.retrieval_count == 1
        assert own.last_retrieved_at is not None


async def test_outcome_closes_trace_by_turn_without_changing_raw_text() -> None:
    turn_id = str(uuid.uuid4())
    async with await _db() as db:
        trace, _ = await create_trace(
            db,
            {"raw_text": "原样保留\n第二行", "turn_id": turn_id, "status": "running"},
        )
        await db.commit()
        assert (
            await update_trace_outcome(db, turn_id=turn_id, status="completed", outcome="success")
            == 1
        )
        await db.commit()
        await db.refresh(trace)
        assert trace.raw_text == "原样保留\n第二行"
        assert trace.status == "completed"
        assert trace.outcome == "success"
        assert trace.completed_at is not None


async def test_compression_self_reference_is_rejected_by_db() -> None:
    from sqlalchemy.exc import IntegrityError

    async with await _db() as db:
        trace = InstructionTrace(raw_text="guard me", text_hash="deadbeef")
        db.add(trace)
        await db.flush()
        trace.compressed_into_id = trace.id
        with pytest.raises(IntegrityError):
            await db.commit()


# --- HTTP contract ---


async def test_api_write_and_list_roundtrip(client) -> None:
    session_id = str(uuid.uuid4())
    created = await client.post(
        "/api/v1/instruction-traces",
        json={"raw_text": UNICODE_SAMPLE, "session_id": session_id},
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["raw_text"] == UNICODE_SAMPLE
    assert body["session_id"] == session_id
    assert body["source"] == "chat"
    assert body["is_archived"] is False
    assert body["user_id"] == "default-user"

    listed = await client.get("/api/v1/instruction-traces", params={"session_id": session_id})
    assert listed.status_code == 200
    page = listed.json()
    assert page["total"] == 1
    assert page["items"][0]["raw_text"] == UNICODE_SAMPLE


async def test_api_deduplicates_repeated_submission(client) -> None:
    session_id = str(uuid.uuid4())
    payload = {"raw_text": "post this twice", "session_id": session_id}
    first = await client.post("/api/v1/instruction-traces", json=payload)
    second = await client.post("/api/v1/instruction-traces", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    listed = await client.get("/api/v1/instruction-traces", params={"session_id": session_id})
    assert listed.json()["total"] == 1


async def test_api_rejects_empty_raw_text(client) -> None:
    response = await client.post("/api/v1/instruction-traces", json={"raw_text": ""})
    assert response.status_code == 422


async def test_api_rejects_unknown_source(client) -> None:
    response = await client.post(
        "/api/v1/instruction-traces", json={"raw_text": "hi", "source": "telepathy"}
    )
    assert response.status_code == 422


async def test_api_list_filters_and_paginates(client) -> None:
    session_id = str(uuid.uuid4())
    for index in range(3):
        await client.post(
            "/api/v1/instruction-traces",
            json={"raw_text": f"paged instruction {index}", "session_id": session_id},
        )
    page = (
        await client.get(
            "/api/v1/instruction-traces",
            params={"session_id": session_id, "limit": 2, "offset": 0},
        )
    ).json()
    assert page["total"] == 3
    assert len(page["items"]) == 2
    assert page["limit"] == 2
    assert page["offset"] == 0

    tail = (
        await client.get(
            "/api/v1/instruction-traces",
            params={"session_id": session_id, "limit": 2, "offset": 2},
        )
    ).json()
    assert len(tail["items"]) == 1

    archived = (
        await client.get(
            "/api/v1/instruction-traces",
            params={"session_id": session_id, "is_archived": True},
        )
    ).json()
    assert archived["total"] == 0

    by_user = (
        await client.get("/api/v1/instruction-traces", params={"user_id": "default-user"})
    ).json()
    assert by_user["total"] == 3


async def test_api_rejects_out_of_range_page(client) -> None:
    assert (await client.get("/api/v1/instruction-traces", params={"limit": 0})).status_code == 422
    assert (
        await client.get("/api/v1/instruction-traces", params={"offset": -1})
    ).status_code == 422
