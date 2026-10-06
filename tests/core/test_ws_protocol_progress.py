"""Tests for the unified WS event protocol, progress tracking and task tree.

Covers:
- six-type canonical event protocol with payload type labels, legacy event
  names still broadcast (compat), identity events never duplicated;
- ProgressTracker token/tool/activity counters, ring buffer and stall
  detection with one-shot alarm;
- sub-agent task tree events (tree_node_added / tree_node_updated) with
  task name, status and elapsed time, plus snapshot queries for
  reconnection sync;
- agent_runner canonical event mirroring when a group_id is provided.

Run with pytest. No live LLM, no real WebSocket transport.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.core import AgentEvent, AgentEventType
from app.core.collaboration import agent_runner
from app.core.collaboration import progress as progress_module
from app.core.collaboration.progress import (
    RECENT_ACTIVITY_LIMIT,
    ProgressTracker,
    TaskTree,
    broadcast_stall_warnings,
    drop_progress_tracker,
    drop_task_tree,
    get_progress_snapshots,
    get_progress_tracker,
    get_task_tree,
    get_task_tree_snapshot,
)
from app.core.group_ws_hub import (
    CANONICAL_EVENT_TYPES,
    EVENT_PROTOCOL_VERSION,
    LEGACY_EVENT_MAP,
    SUPPORTED_EVENT_TYPES,
    get_group_event_log,
    get_group_state_snapshot,
)
import app.core.group_ws_hub as hub_module
from app.core.group_ws_hub import group_ws_hub
from app.core.principal import Principal


class FakeWebSocket:
    def __init__(self):
        self.sent = []
        self.fail = False

    async def send_json(self, message):
        if self.fail:
            raise RuntimeError("connection closed")
        self.sent.append(message)


class WsEventProtocolTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.group_id = f"group-{id(self)}"

    def tearDown(self):
        hub_module._group_event_log.pop(self.group_id, None)
        conns = hub_module._group_connections.pop(self.group_id, None)
        if conns:
            conns.clear()

    async def connect(self, count=1):
        sockets = []
        for _ in range(count):
            ws = FakeWebSocket()
            sockets.append(ws)
            await group_ws_hub.connect(self.group_id, ws)
        return sockets

    def legacy_frames(self, ws, event_type):
        return [m for m in ws.sent if m.get("type") == event_type]

    async def test_supported_types_include_canonical_six(self):
        self.assertTrue(CANONICAL_EVENT_TYPES.issubset(SUPPORTED_EVENT_TYPES))
        self.assertEqual(CANONICAL_EVENT_TYPES, {
            "status", "content_delta", "tool_result",
            "task_update", "message_complete", "error",
        })

    async def test_every_supported_legacy_event_maps_to_canonical(self):
        extras = {"tree_node_added", "tree_node_updated", "progress_warning", "progress_snapshot"}
        legacy_names = SUPPORTED_EVENT_TYPES - CANONICAL_EVENT_TYPES - extras
        self.assertTrue(legacy_names)
        for name in legacy_names:
            self.assertIn(name, LEGACY_EVENT_MAP, name)
        for canonical in LEGACY_EVENT_MAP.values():
            self.assertIn(canonical, CANONICAL_EVENT_TYPES)

    async def test_broadcast_legacy_frame_stays_unchanged_and_mirrors_canonically(self):
        ws = (await self.connect())[0]
        message = {"type": "worker_done", "data": {"content": "done", "tokens_used": 5}}

        await group_ws_hub.broadcast(self.group_id, message)

        legacy = self.legacy_frames(ws, "worker_done")
        self.assertEqual(len(legacy), 1)
        self.assertEqual(legacy[0]["data"], {"content": "done", "tokens_used": 5})
        mirrors = self.legacy_frames(ws, "message_complete")
        self.assertEqual(len(mirrors), 1)
        mirror_data = mirrors[0]["data"]
        self.assertEqual(mirror_data["event"], "worker_done")
        self.assertEqual(mirror_data["protocol_version"], EVENT_PROTOCOL_VERSION)
        self.assertEqual(mirror_data["content"], "done")
        self.assertEqual(mirror_data["tokens_used"], 5)

    async def test_identity_canonical_event_broadcasts_once(self):
        ws = (await self.connect())[0]

        await group_ws_hub.broadcast(
            self.group_id, {"type": "task_update", "data": {"id": "t1", "status": "running"}}
        )

        self.assertEqual(len(ws.sent), 1)
        self.assertEqual(ws.sent[0]["type"], "task_update")
        self.assertEqual(ws.sent[0]["data"], {"id": "t1", "status": "running"})

    async def test_broadcast_canonical_injects_event_label(self):
        ws = (await self.connect())[0]

        sent = await group_ws_hub.broadcast_canonical(
            self.group_id, "content_delta", {"content": "hi"}, kind="text"
        )

        self.assertTrue(sent)
        self.assertEqual(len(ws.sent), 1)
        frame = ws.sent[0]
        self.assertEqual(frame["type"], "content_delta")
        self.assertEqual(frame["data"]["event"], "text")
        self.assertEqual(frame["data"]["content"], "hi")
        self.assertEqual(frame["data"]["protocol_version"], EVENT_PROTOCOL_VERSION)

    async def test_broadcast_canonical_rejects_unknown_type(self):
        await self.connect()
        with patch.object(hub_module, "logger") as mock_logger:
            sent = await group_ws_hub.broadcast_canonical(self.group_id, "not_a_type", {})
        self.assertFalse(sent)
        mock_logger.warning.assert_called_once()
        self.assertEqual(get_group_event_log(self.group_id), [])

    async def test_unknown_legacy_type_is_sent_without_mirror(self):
        ws = (await self.connect())[0]
        with patch.object(hub_module, "logger") as mock_logger:
            await group_ws_hub.broadcast(self.group_id, {"type": "mystery", "data": {}})
        mock_logger.warning.assert_called_once()
        self.assertEqual(len(ws.sent), 1)

    async def test_disconnect_prunes_only_dead_socket_and_keeps_task_recording(self):
        live, dead = await self.connect(2)
        dead.fail = True

        await group_ws_hub.broadcast(self.group_id, {"type": "worker_start", "data": {"member_id": "m"}})

        self.assertIn(live, hub_module._group_connections[self.group_id])
        self.assertNotIn(dead, hub_module._group_connections[self.group_id])
        self.assertEqual(len(live.sent), 2)

    async def test_broadcast_without_clients_still_records_snapshot_log(self):
        # Client disconnected: the task keeps running and events keep
        # accumulating for the reconnecting snapshot pull.
        await group_ws_hub.broadcast(self.group_id, {"type": "worker_start", "data": {"member_id": "m"}})

        snapshot = get_group_state_snapshot(self.group_id)
        self.assertEqual(snapshot["connected_clients"], 0)
        self.assertEqual(snapshot["protocol_version"], EVENT_PROTOCOL_VERSION)
        self.assertEqual(snapshot["task_tree"], {
            "group_id": self.group_id, "task_id": "", "nodes": [],
        })
        frames = [entry["message"] for entry in snapshot["recent_events"]]
        self.assertEqual([f["type"] for f in frames], ["worker_start", "status"])
        self.assertEqual(frames[1]["data"]["event"], "worker_start")

    async def test_get_group_event_log_returns_recent_frames(self):
        await self.connect()
        for i in range(3):
            await group_ws_hub.broadcast(
                self.group_id, {"type": "typing", "data": {"seq": i}}
            )
        log = get_group_event_log(self.group_id, limit=2)
        self.assertEqual(len(log), 2)
        self.assertTrue(all("at" in entry for entry in log))
        self.assertEqual(log[-1]["message"]["data"], {"event": "typing", "seq": 2, "protocol_version": 1})

    async def test_tree_node_events_mirror_into_canonical_task_update(self):
        # The real hub mirrors tree events into the canonical protocol so
        # six-type consumers observe the sub-agent task tree too.
        tree = TaskTree(self.group_id, task_id="task-2")
        self.addCleanup(drop_task_tree, self.group_id)
        ws = FakeWebSocket()
        await group_ws_hub.connect(self.group_id, ws)
        self.addAsyncCleanup(group_ws_hub.disconnect, self.group_id, ws)

        root = await tree.add_root("real hub task")
        await tree.update_status(root.node_id, "completed")

        types = [m["type"] for m in ws.sent]
        self.assertEqual(types, [
            "tree_node_added", "task_update", "tree_node_updated", "task_update",
        ])
        mirrors = [m["data"] for m in ws.sent if m["type"] == "task_update"]
        self.assertEqual(mirrors[0]["event"], "tree_node_added")
        self.assertEqual(mirrors[0]["task_name"], "real hub task")
        self.assertEqual(mirrors[1]["event"], "tree_node_updated")
        self.assertEqual(mirrors[1]["status"], "completed")


class ProgressTrackerTests(unittest.IsolatedAsyncioTestCase):
    def test_records_tokens_and_tool_calls(self):
        tracker = ProgressTracker(tracker_id="t", group_id="g", agent_id="a", role="worker")
        tracker.record_input_tokens(10)
        tracker.record_input_tokens(4)
        tracker.record_output_tokens(3)
        tracker.record_output_tokens(5)
        tracker.record_tool_call("search")
        tracker.record_tool_call("read_file")
        tracker.record_tool_call()

        self.assertEqual(tracker.latest_input_tokens, 4)
        self.assertEqual(tracker.cumulative_output_tokens, 8)
        self.assertEqual(tracker.tool_use_count, 3)
        snapshot = tracker.snapshot()
        self.assertEqual(snapshot["total_tokens"], 12)
        self.assertEqual(len(snapshot["recent_activities"]), 3)

    async def test_recent_activities_is_a_five_slot_ring_buffer(self):
        tracker = ProgressTracker(tracker_id="t")
        for i in range(7):
            tracker.record_activity(f"step-{i}")

        self.assertEqual(len(tracker.recent_activities), RECENT_ACTIVITY_LIMIT)
        labels = [a["label"] for a in tracker.recent_activities]
        self.assertEqual(labels, ["step-2", "step-3", "step-4", "step-5", "step-6"])

    def test_stall_detection_and_one_shot_warning(self):
        tracker = ProgressTracker(tracker_id="t", stall_threshold_seconds=10.0)
        tracker.record_activity("start", now=100.0)

        self.assertFalse(tracker.is_stalled(now=109.0))
        self.assertTrue(tracker.is_stalled(now=110.5))
        warning = tracker.stall_warning(now=110.5)
        self.assertIsNotNone(warning)
        self.assertEqual(warning["tracker_id"], "t")
        self.assertEqual(warning["idle_seconds"], 10.5)
        self.assertEqual(warning["threshold_seconds"], 10.0)
        self.assertIsNone(tracker.stall_warning(now=115.0))

        tracker.record_activity("resumed", now=116.0)
        self.assertFalse(tracker.is_stalled(now=116.0))
        self.assertIsNone(tracker.stall_warning(now=116.0))
        self.assertTrue(tracker.is_stalled(threshold_seconds=5.0, now=122.0))

    async def test_tracker_registry_and_group_snapshot(self):
        tracker = get_progress_tracker("g1:a1", group_id="g1", agent_id="a1", role="worker")
        get_progress_tracker("g2:a2", group_id="g2", agent_id="a2", role="reviewer")
        self.addCleanup(drop_progress_tracker, "g1:a1")
        self.addCleanup(drop_progress_tracker, "g2:a2")

        self.assertIs(get_progress_tracker("g1:a1"), tracker)
        self.assertIn("g1:a1", get_progress_snapshots("g1"))
        self.assertNotIn("g2:a2", get_progress_snapshots("g1"))
        self.assertIn("g2:a2", get_progress_snapshots())

    async def test_broadcast_stall_warnings_only_for_stalled_trackers(self):
        stalled = get_progress_tracker("g1:stalled", group_id="g1", agent_id="s", stall_threshold_seconds=5.0)
        healthy = get_progress_tracker("g1:healthy", group_id="g1", agent_id="h", stall_threshold_seconds=5.0)
        self.addCleanup(drop_progress_tracker, "g1:stalled")
        self.addCleanup(drop_progress_tracker, "g1:healthy")
        stalled.record_activity("start", now=1000.0)
        healthy.record_activity("start", now=1009.0)

        with patch.object(progress_module.group_ws_hub, "broadcast_canonical", new_callable=AsyncMock) as bc:
            with patch.object(progress_module.time, "monotonic", return_value=1010.0):
                warnings = await broadcast_stall_warnings("g1")

        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["agent_id"], "s")
        self.assertEqual(warnings[0]["idle_seconds"], 10.0)
        self.assertEqual(bc.await_count, 1)
        args = bc.await_args.args
        self.assertEqual(args[1], "status")
        self.assertEqual(args[2]["warning"], "stalled")
        self.assertEqual(bc.await_args.kwargs.get("kind"), "progress_warning")
        # A second scan emits nothing: the alarm is one-shot per stall period.
        with patch.object(progress_module.time, "monotonic", return_value=1010.0):
            self.assertEqual(await broadcast_stall_warnings("g1"), [])


class TaskTreeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.group_id = f"tree-group-{id(self)}"
        self.broadcast = AsyncMock()
        patcher = patch.object(progress_module.group_ws_hub, "broadcast", self.broadcast)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        drop_task_tree(self.group_id)

    def events(self, kind):
        return [call.args[1]["data"] for call in self.broadcast.await_args_list
                if call.args[1]["type"] == kind]

    async def test_task_start_and_subtask_nodes_broadcast_structured_events(self):
        tree = get_task_tree(self.group_id, task_id="task-1", create=True)
        root = await tree.add_root("Build the feature")
        child = await tree.add_node(root.node_id, "worker:agent-a", metadata={"role": "worker"})

        added = self.events("tree_node_added")
        self.assertEqual(len(added), 2)
        self.assertEqual(added[0]["event"], "tree_node_added")
        self.assertEqual(added[0]["task_name"], "Build the feature")
        self.assertIsNone(added[0]["parent_id"])
        self.assertEqual(added[0]["task_id"], "task-1")
        self.assertEqual(added[0]["status"], "running")
        self.assertEqual(added[1]["parent_id"], root.node_id)
        self.assertEqual(added[1]["task_name"], "worker:agent-a")
        self.assertEqual(child.parent_id, root.node_id)

    async def test_node_status_change_broadcasts_update_with_elapsed(self):
        tree = get_task_tree(self.group_id, create=True)
        root = await tree.ensure_root("task name")

        node = await tree.update_status(root.node_id, "completed")

        updates = self.events("tree_node_updated")
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["event"], "tree_node_updated")
        self.assertEqual(updates[0]["task_name"], "task name")
        self.assertEqual(updates[0]["status"], "completed")
        self.assertIn("elapsed_ms", updates[0])
        self.assertGreaterEqual(updates[0]["elapsed_ms"], 0)
        self.assertIsNotNone(node.ended_at)
        # Terminal status freezes elapsed time.
        frozen = node.elapsed_ms()
        later = node.elapsed_ms(now=node.ended_at + 10)
        self.assertEqual(frozen, later)

    async def test_ensure_root_is_idempotent(self):
        tree = get_task_tree(self.group_id, create=True)
        first = await tree.ensure_root("same task")
        second = await tree.ensure_root("other name")

        self.assertIs(first, second)
        self.assertEqual(len(self.events("tree_node_added")), 1)

    async def test_unknown_parent_node_rejected(self):
        tree = get_task_tree(self.group_id, create=True)
        with self.assertRaises(KeyError):
            await tree.add_node("no-such-node", "orphan")

    async def test_tree_snapshot_for_reconnection(self):
        tree = get_task_tree(self.group_id, task_id="task-9", create=True)
        root = await tree.add_root("parent task")
        child = await tree.add_node(root.node_id, "reviewer:agent-b")
        await tree.update_status(child.node_id, "failed")

        snapshot = get_task_tree_snapshot(self.group_id)
        self.assertEqual(snapshot["group_id"], self.group_id)
        self.assertEqual(snapshot["task_id"], "task-9")
        statuses = {n["task_name"]: n["status"] for n in snapshot["nodes"]}
        self.assertEqual(statuses, {"parent task": "running", "reviewer:agent-b": "failed"})
        self.assertEqual(get_task_tree_snapshot("unknown-group")["nodes"], [])


class AgentRunnerBroadcastTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.broadcast_canonical = AsyncMock()
        self.broadcast = AsyncMock()
        self.patches = [
            patch.object(agent_runner.group_ws_hub, "broadcast_canonical", self.broadcast_canonical),
            patch.object(agent_runner.group_ws_hub, "broadcast", self.broadcast),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(progress_module._progress_trackers.clear)
        self.addCleanup(progress_module._task_trees.clear)
        self.principal = Principal(subject_id="owner-1")

    def canonical_types(self):
        return [call.args[1] for call in self.broadcast_canonical.await_args_list]

    def canonical_payload(self, index):
        return self.broadcast_canonical.await_args_list[index].args[2]

    async def run_simple(self, group_id, events):
        async def fake_run_agent(*args, **kwargs):
            for event in events:
                yield event

        with patch.object(agent_runner, "run_agent", fake_run_agent):
            return await agent_runner.run_agent_simple(
                agent_id="agent-a", provider="openai", model_id="gpt-4o",
                api_key="test-only", system_prompt="s", user_message="u",
                tools=[], group_id=group_id, role="worker", principal=self.principal,
            )

    async def test_run_agent_simple_mirrors_events_as_canonical_frames(self):
        events = [
            AgentEvent(AgentEventType.TEXT, {"content": "hello "}),
            AgentEvent(AgentEventType.TOOL_CALL, {"name": "search"}),
            AgentEvent(AgentEventType.TOOL_RESULT, {"result": "found it"}),
            AgentEvent(AgentEventType.DONE, {"status": "completed", "tokens_used": 7}),
        ]

        result = await self.run_simple("group-x", events)

        self.assertEqual(result, ("hello ", 7))
        self.assertEqual(self.canonical_types(), [
            "content_delta", "tool_result", "tool_result", "message_complete",
        ])
        self.assertEqual(self.canonical_payload(0), {
            "event": "text", "role": "worker", "agent_id": "agent-a", "content": "hello ",
        })
        self.assertEqual(self.canonical_payload(1)["event"], "tool_call")
        self.assertEqual(self.canonical_payload(1)["tool_name"], "search")
        self.assertEqual(self.canonical_payload(2)["event"], "tool_result")
        self.assertEqual(self.canonical_payload(3), {
            "event": "message_complete", "role": "worker", "agent_id": "agent-a", "tokens_used": 7,
        })
        tracker = get_progress_tracker("group-x:agent-a")
        self.assertEqual(tracker.tool_use_count, 1)
        self.assertEqual(tracker.cumulative_output_tokens, 7)
        self.assertEqual(tracker.role, "worker")

    async def test_run_agent_simple_without_group_id_stays_silent(self):
        events = [
            AgentEvent(AgentEventType.TEXT, {"content": "hello"}),
            AgentEvent(AgentEventType.DONE, {"tokens_used": 3}),
        ]

        result = await self.run_simple(None, events)

        self.assertEqual(result, ("hello", 3))
        self.broadcast_canonical.assert_not_awaited()
        self.assertEqual(progress_module._progress_trackers, {})

    async def test_run_agent_simple_error_event_is_mirrored(self):
        async def fake_run_agent(*args, **kwargs):
            yield AgentEvent(AgentEventType.ERROR, {"error": "boom"})

        with patch.object(agent_runner, "run_agent", fake_run_agent):
            with self.assertRaisesRegex(Exception, "boom"):
                await agent_runner.run_agent_simple(
                    agent_id="agent-a", provider="openai", model_id="m", api_key="k",
                    system_prompt="s", user_message="u", tools=[],
                    group_id="group-err", role="worker", principal=self.principal,
                )

        self.assertEqual(self.canonical_types(), ["error"])
        self.assertEqual(self.canonical_payload(0)["event"], "agent_error")

    async def retry_success_events(self):
        async def fake_run_agent(*args, **kwargs):
            yield AgentEvent(AgentEventType.TEXT, {"content": "ok"})
            yield AgentEvent(AgentEventType.DONE, {"status": "completed", "tokens_used": 4})

        return fake_run_agent

    async def test_retry_runner_records_task_tree_lifecycle(self):
        async def fake_run_agent(*args, **kwargs):
            yield AgentEvent(AgentEventType.DONE, {"status": "completed", "tokens_used": 4})

        with patch.object(agent_runner, "run_agent", fake_run_agent):
            result = await agent_runner.run_agent_with_retry(
                agent_id="agent-a", provider="openai", model_id="gpt-4o",
                api_key="k", system_prompt="s", user_message="u", tools=[],
                group_id="group-tree", role="worker", principal=self.principal,
                task_name="Implement feature",
            )

        self.assertEqual(result, ("", 4))
        snapshot = get_task_tree_snapshot("group-tree")
        self.assertEqual(len(snapshot["nodes"]), 2)
        root, node = snapshot["nodes"]
        self.assertIsNone(root["parent_id"])
        self.assertEqual(root["task_name"], "Implement feature")
        self.assertEqual(node["parent_id"], root["node_id"])
        self.assertEqual(node["task_name"], "worker:agent-a")
        self.assertEqual(node["status"], "completed")
        added = [c.args[1] for c in self.broadcast.await_args_list if c.args[1]["type"] == "tree_node_added"]
        updated = [c.args[1] for c in self.broadcast.await_args_list if c.args[1]["type"] == "tree_node_updated"]
        self.assertEqual(len(added), 2)
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]["data"]["status"], "completed")
        self.assertEqual(updated[0]["data"]["task_name"], "worker:agent-a")
        self.assertIn("elapsed_ms", updated[0]["data"])

    async def test_retry_runner_marks_node_failed_without_breaking_error(self):
        async def fake_run_agent(*args, **kwargs):
            raise RuntimeError("primary failed")
            yield  # pragma: no cover

        with patch.object(agent_runner, "run_agent", fake_run_agent), patch.object(
            agent_runner, "MAX_RETRIES", 0
        ), patch.object(agent_runner, "_get_fallback_model", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "worker failed after retry"):
                await agent_runner.run_agent_with_retry(
                    agent_id="agent-a", provider="openai", model_id="gpt-4o",
                    api_key="k", system_prompt="s", user_message="u", tools=[],
                    group_id="group-fail", role="worker", principal=self.principal,
                )

        snapshot = get_task_tree_snapshot("group-fail")
        node = snapshot["nodes"][-1]
        self.assertEqual(node["status"], "failed")
        self.assertEqual(self.canonical_types(), [])

    async def test_retry_runner_cancellation_marks_node_stopped(self):
        async def fake_run_agent(*args, **kwargs):
            raise asyncio.CancelledError()
            yield  # pragma: no cover

        with patch.object(agent_runner, "run_agent", fake_run_agent):
            with self.assertRaises(asyncio.CancelledError):
                await agent_runner.run_agent_with_retry(
                    agent_id="agent-a", provider="openai", model_id="gpt-4o",
                    api_key="k", system_prompt="s", user_message="u", tools=[],
                    group_id="group-cancel", role="worker", principal=self.principal,
                )

        snapshot = get_task_tree_snapshot("group-cancel")
        self.assertEqual(snapshot["nodes"][-1]["status"], "stopped")

    async def test_retry_runner_without_group_id_skips_tree(self):
        async def fake_run_agent(*args, **kwargs):
            yield AgentEvent(AgentEventType.DONE, {"status": "completed", "tokens_used": 1})

        progress_module._task_trees.clear()
        with patch.object(agent_runner, "run_agent", fake_run_agent):
            await agent_runner.run_agent_with_retry(
                agent_id="agent-a", provider="openai", model_id="gpt-4o",
                api_key="k", system_prompt="s", user_message="u", tools=[],
                group_id="", role="worker", principal=self.principal,
            )

        self.assertEqual(progress_module._task_trees, {})

    async def test_run_agent_simple_registers_task_tree_node(self):
        events = [
            AgentEvent(AgentEventType.TEXT, {"content": "done"}),
            AgentEvent(AgentEventType.DONE, {"status": "completed", "tokens_used": 2}),
        ]

        result = await self.run_simple("group-node", events)

        self.assertEqual(result, ("done", 2))
        snapshot = get_task_tree_snapshot("group-node")
        self.assertEqual(len(snapshot["nodes"]), 2)
        root, node = snapshot["nodes"]
        self.assertIsNone(root["parent_id"])
        self.assertEqual(root["task_name"], "task:group-node")
        self.assertEqual(node["parent_id"], root["node_id"])
        self.assertEqual(node["task_name"], "worker:agent-a")
        self.assertEqual(node["status"], "completed")

    async def test_run_agent_simple_marks_node_failed_on_error_event(self):
        events = [AgentEvent(AgentEventType.ERROR, {"error": "boom"})]

        with self.assertRaisesRegex(Exception, "boom"):
            await self.run_simple("group-node-fail", events)

        snapshot = get_task_tree_snapshot("group-node-fail")
        self.assertEqual(snapshot["nodes"][-1]["status"], "failed")

    async def test_retry_runner_broadcasts_live_progress_per_attempt(self):
        attempts = {"count": 0}

        async def flaky_run_agent(*args, **kwargs):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RuntimeError("transient")
            yield AgentEvent(AgentEventType.TEXT, {"content": "recovered"})
            yield AgentEvent(AgentEventType.DONE, {"status": "completed", "tokens_used": 5})

        with patch.object(agent_runner, "run_agent", flaky_run_agent), patch.object(
            agent_runner, "MAX_RETRIES", 1
        ):
            result = await agent_runner.run_agent_with_retry(
                agent_id="agent-a", provider="openai", model_id="gpt-4o",
                api_key="k", system_prompt="s", user_message="u", tools=[],
                group_id="group-live", role="worker", principal=self.principal,
            )

        self.assertEqual(result, ("recovered", 5))
        # The worker retry path now mirrors live progress for the successful attempt.
        self.assertEqual(self.canonical_types(), ["content_delta", "message_complete"])
        # One tree node per attempt: the failed try then the recovered one.
        snapshot = get_task_tree_snapshot("group-live")
        self.assertEqual([n["status"] for n in snapshot["nodes"]], ["running", "failed", "completed"])
        self.assertEqual(snapshot["nodes"][1]["task_name"], "worker:agent-a")
        self.assertEqual(snapshot["nodes"][2]["task_name"], "worker:agent-a")


if __name__ == "__main__":
    unittest.main()
