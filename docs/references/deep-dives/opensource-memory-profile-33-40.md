# Open Source Memory & Profile Systems Deep Dive: #33-40

> Scope: items 33-40 from `docs/references/open-source-projects.md`.
> Projects: Letta/MemGPT, Mem0, LlamaIndex, Chroma, Qdrant, LongMem, Recall, AutoMemory.
> Evidence levels: `verified` means direct upstream source inspected; `unavailable` means the indexed URL/source could not be fetched or does not exist; `inferred` means derived from adjacent evidence or code structure rather than a direct line-level statement.

## 33. Letta / MemGPT

### Positioning
Letta is an agent platform built around explicit memory state and memory management tools. Its classic V1 architecture separated in-context core memory from external archival/recall memory; the current Letta Code repository shifted memory into a git-backed memory filesystem.

### Memory / Profile / Temporal Mechanism Essentials

- Core memory is a set of labelled `Block` objects with `label`, `description`, `value`, and `limit`; V1 uses `human`, `persona`, `system` style blocks and renders them into the context window (`letta/schemas/memory.py:68-79`, `letta/orm/block.py:36-50`, `letta/schemas/memory.py:143-173`).
- Archival memory is a separate passage store (`letta/orm/passage.py:77-80`) and is managed by a `PassageManager` that inserts and batches archival passages (`letta/services/passage_manager.py:396-436`, `letta/services/passage_manager.py:543-560`).
- The agent exposes memory editing as model-visible tools: `archival_memory_insert`, `archival_memory_search`, `core_memory_append`, `core_memory_replace`, `memory_rethink`, and `memory_finish_edits` (`letta/functions/function_sets/base.py:164-204`, `letta/functions/function_sets/base.py:246-301`, `letta/functions/function_sets/base.py:490-522`).
- Current Letta Code makes memory a filesystem: `.letta` root, `agents/` and `memory/` directories, git-backed sync, and a `MEMORY.md` root block (`src/agent/memory-filesystem.ts:29-35`, `src/agent/memory-filesystem.ts:92-121`, `src/backend/local/initial-memory.ts:55-56`).
- The temporal dimension is represented by passage/message history and git history, not by a dedicated timestamp graph.

### Climber Mapping

- `app/core/memory/lifecycle.py` is the closest analog: it already implements write/index/retrieve/decay/forget around vector memory.
- `app/core/profile/persistence.py` can carry labelled blocks/traits that Letta labels with `human`/`persona`/`system`.
- `app/core/integration/mem0_memory.py` is the current external memory adapter; adding a Letta-style memory tool layer would fit the existing slash command flow in `app/core/slash/`.

### Landed / Gap / Next Step

- Landed: core memory lifecycle, vector retrieval, and profile persistence exist.
- Gap: no model-visible structured memory block editor or dedicated archival-vs-recall split.
- Next step: add a `memory_block` slash command/tool around `ProfileStore` that exposes `read/write/append/search` operations and keeps a `system/human/persona` label convention.

### Evidence

- Verified: `letta/schemas/memory.py`, `letta/orm/block.py`, `letta/orm/passage.py`, `letta/functions/function_sets/base.py`, `letta/services/passage_manager.py`, `letta-code/src/agent/memory-filesystem.ts`, `letta-code/src/backend/local/initial-memory.ts`.
- Inferred: mapping to Climber's current lifecycle and slash architecture.

## 34. Mem0

### Positioning
Mem0 is a memory layer for LLM apps that extracts, stores, searches, updates, deletes, and links memories per user/agent/run identity. It is the project Climber already has an integration wrapper for.

### Memory / Profile / Temporal Mechanism Essentials

- Identity scope is explicit: `user_id`, `agent_id`, and `run_id` are required or validated on `add`, and all memories are scoped to those entity IDs (`mem0/memory/main.py:330-374`, `mem0/memory/main.py:760-800`).
- Entity extraction and linking are first-class: `_link_entities_for_memory` extracts entities from memory text and upserts them into a separate entity store (`mem0/memory/main.py:707-730`, `mem0/memory/main.py:605-650`).
- Retrieval is hybrid: vector semantic search over-fetches, keyword/BM25 results are normalized, query entities are boosted, and `score_and_rank` combines semantic + BM25 + entity boost (`mem0/utils/scoring.py:60-139`, `mem0/memory/main.py:1642-1708`, `mem0/memory/main.py:1747-1790`).
- BM25 normalization is query-length adaptive (`mem0/utils/scoring.py:16-40`), and semantic score acts as a gate before hybrid combination (`mem0/utils/scoring.py:105-119`).

### Climber Mapping

- `app/core/integration/mem0_memory.py` already wraps Mem0.
- `app/core/vector_memory.py` is the local vector store; Mem0's hybrid scoring can be added as a reranking layer before `VectorMemoryService.search` results are returned.
- `app/core/profile/loop.py` is where Mem0-style identity/entity metadata should be attached to profile events.

### Landed / Gap / Next Step

- Landed: Mem0 external memory adapter and profile event loop.
- Gap: Climber's own retrieval path does not yet expose BM25 + entity boost scoring.
- Next step: add a Mem0-style `score_and_rank` helper in `app/core/vector_memory.py` and call it from `VectorMemoryService.search`; include `user_id`/`agent_id` filters from `app/core/profile/persistence.py`.

### Evidence

- Verified: `mem0/memory/main.py`, `mem0/utils/scoring.py`, `mem0/utils/entity_extraction.py`.
- Inferred: Climber's current search path is semantic-only.

## 35. LlamaIndex

### Positioning
LlamaIndex is a data framework for connecting LLMs to external knowledge. Its relevant abstraction for Climber is the retriever/query-engine contract and query transformation pipeline.

### Memory / Profile / Temporal Mechanism Essentials

- `BaseRetriever.retrieve(query_bundle)` is the central synchronous entry point; it converts a string to `QueryBundle`, calls `_retrieve`, then runs recursive retrieval (`llama-index-core/llama_index/core/base/base_retriever.py:192-226`).
- `RetrieverQueryEngine` retrieves nodes and applies node postprocessors before synthesis (`llama-index-core/llama_index/core/query_engine/retriever_query_engine.py:160-167`, `llama-index-core/llama_index/core/query_engine/retriever_query_engine.py:203-213`).
- Query transforms are prompt-driven (decompose, step-decompose, image output, etc.) and can change the query before retrieval (`llama-index-core/llama_index/core/indices/query/query_transform/prompts.py:1-35`).
- Vector index base classes build on retriever abstractions, so the framework is designed around pluggable retrievers rather than a single monolithic memory store (`llama-index-core/llama_index/core/indices/vector_store/base.py:63-82`).

### Climber Mapping

- `app/core/vector_memory.py` currently acts as a direct Chroma search call.
- `app/core/slash/service.py` is the natural place for a query-transform layer before vector search.
- `DualLoopCoordinator.profile_context` in `app/core/engine/dual_loop.py` can be viewed as the Climber equivalent of a query engine: it should accept a `QueryBundle`-like profile request and return scored memory nodes.

### Landed / Gap / Next Step

- Landed: vector search and profile context injection.
- Gap: no retriever/query-engine contract, no postprocessors, no query transforms.
- Next step: introduce a thin `ProfileRetriever` in `app/core/vector_memory.py` that returns `ProfileNodeWithScore`, then let `app/core/slash/service.py` apply query transforms before retrieval and postprocessors after retrieval.

### Evidence

- Verified: `base_retriever.py`, `retriever_query_engine.py`, `indices/vector_store/base.py`, `query_transform/prompts.py`.
- Inferred: Climber search path is a direct call without these abstractions.

## 36. Chroma

### Positioning
Chroma is the embedded/local vector database used by both Climber and Recall. Its relevance is mostly as infrastructure: collection semantics, metadata filtering, and persistent HNSW behavior.

### Memory / Profile / Temporal Mechanism Essentials

- `Client._query` accepts `where` and `where_document` filters and forwards them to the server (`chromadb/api/client.py:681-703`).
- `SegmentAPI._query` validates filters and routes them through the collection scan (`chromadb/api/segment.py:956-1010`).
- SQLite metadata segment implements metadata and document filtering (`chromadb/segment/impl/metadata/sqlite.py:113-225`, `chromadb/segment/impl/metadata/sqlite.py:524-590`).
- Persistent local HNSW over-queries to account for updated/deleted elements, then merges brute-force and HNSW results to the requested `k` (`chromadb/segment/impl/vector/local_persistent_hnsw.py:428-470`).

### Climber Mapping

- `app/core/vector_memory.py` is the direct Chroma integration point.
- `app/core/memory/lifecycle.py` can use Chroma `where` filters for type/time-based memory scoping instead of post-filtering in Python.

### Landed / Gap / Next Step

- Landed: Chroma persistent collection and vector query in Climber.
- Gap: metadata filters are not fully used for profile/type/time scoping.
- Next step: pass `where={"kind": ..., "created_at": {...}}` through `VectorMemoryService.search` and index Chroma metadata from `app/core/profile/persistence.py`.

### Evidence

- Verified: `chromadb/api/client.py`, `chromadb/api/segment.py`, `chromadb/segment/impl/metadata/sqlite.py`, `chromadb/segment/impl/vector/local_persistent_hnsw.py`.
- Inferred: Climber current usage is mostly unfiltered semantic search.

## 37. Qdrant

### Positioning
Qdrant is a high-performance vector engine with rich payload filters, scroll/pagination, payload selectors, and multi-vector support. It is a useful reference for Climber if Chroma metadata filtering becomes too limited.

### Memory / Profile / Temporal Mechanism Essentials

- `Filter` is a structured boolean tree with `should`, `min_should`, `must`, and `must_not` (`lib/segment/src/types.rs:4480-4520`).
- `FieldCondition` supports match, range, geo, values-count, empty/null checks (`lib/segment/src/types.rs:3639-3660`).
- Scroll and search requests carry `filter`, `limit`, `offset`, `with_payload`, and `with_vector` (`lib/collection/src/operations/types.rs:490-543`, `lib/collection/src/operations/types.rs:676-696`).
- Payload selection supports include/exclude field lists (`lib/segment/src/types.rs:4373-4410`).

### Climber Mapping

- `app/core/vector_memory.py` is the integration point; Qdrant's filter/selector model maps cleanly to profile metadata scoping and projection.
- `app/core/memory/lifecycle.py` can encode decay/forget as metadata-based filters rather than deleting all candidate vectors.

### Landed / Gap / Next Step

- Landed: Chroma-backed vector memory; Qdrant not currently used.
- Gap: no boolean filter tree or payload projection abstraction in Climber.
- Next step: if profile query complexity grows, add an optional Qdrant backend behind `VectorMemoryService` and keep the `Filter`-like request shape in `app/core/vector_memory.py`.

### Evidence

- Verified: `lib/segment/src/types.rs`, `lib/collection/src/operations/types.rs`.
- Inferred: Climber has no Qdrant adapter yet.

## 38. LongMem

### Positioning
LongMem is a research architecture for long-context language modeling using an external memory bank plus a SideNetwork. The original indexed URL `https://github.com/11data/longmem` returns 404; the official paper implementation is `Victorwz/LongMem`, which was used as the verified source.

### Memory / Profile / Temporal Mechanism Essentials

- External memory is optional and configurable: `use_external_memory`, `retrieval_layer_index`, `dstore_size`, `k`, `probe`, `memory_size`, and `long_context_attention` are model args (`fairseq/fairseq/models/transformer_lm_sidenet.py:254-308`).
- At each side-network layer, the external memory is retrieved using the self-attention query projection, and the retrieved key indices are passed into attention (`fairseq/fairseq/modules/sidenet_layer_palm_sidenet_retrieval.py:192-208`).
- Joint multi-head attention consumes the retrieved long-context keys/values (`fairseq/fairseq/modules/joint_multihead_attention_sum.py:132-188`).
- The design is therefore memory-as-retrieval-augmented-attention: dense retrieval over an external key store, then joint attention over local context and retrieved memory.

### Climber Mapping

- `app/core/vector_memory.py` maps to the external key store.
- `app/core/profile/loop.py` can map to the SideNetwork: a small network/model that decides which profile memories to consult before the main loop.
- `DualLoopCoordinator.profile_context` is the joint-attention analog: local conversation context plus retrieved profile context.

### Landed / Gap / Next Step

- Landed: Climber already has profile context injection and vector retrieval.
- Gap: no learned/explicit query-key projection for deciding what to retrieve; retrieval is currently text/vector similarity only.
- Next step: make `ProfileLoopService.calibration` produce a compact profile query embedding that is used as the retrieval key in `VectorMemoryService.search`, matching LongMem's "retrieval key from attention query" idea.

### Evidence

- Verified: `Victorwz/LongMem` `fairseq/fairseq/models/transformer_lm_sidenet.py`, `fairseq/fairseq/modules/sidenet_layer_palm_sidenet_retrieval.py`, `fairseq/fairseq/modules/joint_multihead_attention_sum.py`.
- Unavailable: indexed URL `https://github.com/11data/longmem` (404).

## 39. Recall

### Positioning
Recall is a local MCP/HTTP memory server that stores observations, reasoning, anti-patterns, checkpoints, and reflections in ChromaDB. Its advertised positioning is "graph-structured temporal memory," but the inspected source is a typed Chroma store rather than a graph database.

### Memory / Profile / Temporal Mechanism Essentials

- The store interface is intentionally minimal: count, upsert, query, get, delete, update metadata (`src/recall/store.py:24-31`, `src/recall/store.py:47-48`).
- `ChromaStore` wraps a Chroma collection with cosine HNSW space and pluggable embedder (`src/recall/store.py:60-75`).
- `remember` stores `source`, `indexed_at`, `type: observation`, and optional tags as metadata (`src/recall/tools/remember.py:31-53`).
- `recall` filters by `type` using a `where` clause and returns structured rows with `rank`, `distance`, `type`, `source`, `domain`, `confidence`, `text` (`src/recall/tools/recall.py:26-49`, `src/recall/tools/recall.py:96-105`).
- Durable artifacts are written as typed markdown files by `persist_artifact` (`src/recall/artifacts.py:17-26`).

### Climber Mapping

- `app/core/vector_memory.py` is the Chroma analog.
- `app/core/memory/lifecycle.py` already has decay/forget, which Recall does not.
- The `type` metadata scheme maps directly to Climber's event kinds in `app/core/profile/persistence.py`.

### Landed / Gap / Next Step

- Landed: Chroma vector memory in Climber.
- Gap: no typed `observation/reasoning/anti_pattern/checkpoint/reflection` metadata convention or artifact export.
- Next step: add a `kind` field to vector metadata and expose a `recall` slash command that filters by kind and returns structured scored rows.

### Evidence

- Verified: `src/recall/store.py`, `src/recall/tools/remember.py`, `src/recall/tools/recall.py`, `src/recall/artifacts.py`, `src/recall/snapshot.py`.
- Inferred: the claim of graph/temporal structure is not implemented in the inspected `src/recall` code.

## 40. AutoMemory

### Positioning
AutoMemory is a research scaffold for improving how an LLM uses memory in long-horizon game tasks (Crafter, MiniHack, NetHack). It is a memory-as-filesystem skill, not a general user-profile extraction system.

### Memory / Profile / Temporal Mechanism Essentials

- Memory is a persistent filesystem accessible through file operations: read, search, tail, count, append, write, create (`scaffolds/crafter_v5/agents/memory_agent.py:747-824`).
- The agent runs a two-phase LOG/PLAN loop: LOG records the outcome of the previous step into memory files; PLAN consults memory before choosing an action (`scaffolds/crafter_v5/agents/memory_agent.py:2085-2185`, `loop1_scaffold_evolution/meta_loop.py:217-222`).
- Training data is extracted from real episode traces, selecting LOG turns and the memory-consultation portion of PLAN turns (`loop2_training_engine/data_engine.py:127-146`).
- The trained memory model handles LOG and memory ops while a separate gameplay model commits the final action (`loop2_training_engine/data_engine.py:134-136`).

### Climber Mapping

- `app/core/memory/lifecycle.py` is the write/read lifecycle analog.
- `app/core/profile/loop.py` can map to the LOG phase by persisting profile-relevant observations.
- `DualLoopCoordinator.profile_context` maps to the PLAN phase by consulting profile memory before the main loop.

### Landed / Gap / Next Step

- Landed: Climber has a profile loop and context injection.
- Gap: no explicit LOG/PLAN phase separation and no memory-operation training data pipeline.
- Next step: add a `profile_log_phase` and `profile_plan_phase` pair in `app/core/profile/loop.py`, so profile observations are written before `DualLoopCoordinator.profile_context` reads them.

### Evidence

- Verified: `scaffolds/crafter_v5/agents/memory_agent.py`, `loop2_training_engine/data_engine.py`, `loop1_scaffold_evolution/meta_loop.py`.
- Inferred: applicability to Climber's user-profile context is a research transfer, not a direct product feature.

## Evidence Summary

- Verified: 8 projects have direct upstream source evidence.
- Unavailable: LongMem original indexed URL.
- Inferred: several Climber mappings and project-to-product transfer statements.

## Three Concrete Integration Suggestions

1. Add a Mem0-style hybrid scorer to `app/core/vector_memory.py`: call `score_and_rank(semantic, bm25, entity_boost, threshold, top_k)` in `VectorMemoryService.search`, so profile retrieval uses semantic plus keyword plus entity evidence instead of raw vector similarity alone.

2. Add a typed `kind` metadata convention in `app/core/profile/persistence.py` and pass `where={"kind": ...}` through `VectorMemoryService.search`; expose a Recall-like structured `recall` slash command in `app/core/slash/service.py` returning rank/distance/kind/source/confidence/text.

3. Split the profile loop into explicit LOG and PLAN phases in `app/core/profile/loop.py`: persist profile-relevant observations after each cycle, then let `DualLoopCoordinator.profile_context` consult them before the next cycle, mirroring AutoMemory's LOG/PLAN invariant.
