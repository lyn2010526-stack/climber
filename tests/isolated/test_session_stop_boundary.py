"""Real asyncio stop-boundary tests using the session state machine."""

import asyncio
import gc
import unittest

from app.core import SessionStatus
from app.core.session import AgentSession
from app.core.task_state_machine import TaskState, TaskStateMachine


class SessionStopBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.loop = asyncio.get_running_loop()
        self.errors = []
        self.previous_handler = self.loop.get_exception_handler()
        self.loop.set_exception_handler(lambda loop, context: self.errors.append(context))
        self.session = AgentSession(session_id="stop-boundary")

    async def asyncTearDown(self):
        await self.session._await_pending_tasks()
        gc.collect()
        await asyncio.sleep(0)
        self.loop.set_exception_handler(self.previous_handler)
        self.assertEqual(self.errors, [], self.errors)

    async def test_terminal_stop_is_idempotent(self):
        for state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
            with self.subTest(state=state):
                self.session.state_machine = TaskStateMachine("terminal", initial_state=state)
                before = self.session.state_machine.to_dict()
                self.session.stop()
                self.session.stop()
                await self.session._await_pending_tasks()
                self.assertEqual(self.session.state_machine.to_dict(), before)
                self.assertEqual(self.session._pending_tasks, set())
                self.assertEqual(self.session.state_machine.transition_count, 0)

    async def test_terminal_stop_does_not_leak_unretrieved_exception(self):
        # Regression: a stop racing a normal completion used to fire an
        # untracked CANCELLED transition that raised completed->cancelled
        # InvalidStateTransitionError and was never retrieved.
        for state in (TaskState.COMPLETED, TaskState.FAILED):
            with self.subTest(state=state):
                self.session.state_machine = TaskStateMachine("leak", initial_state=state)
                self.session.stop()
                await self.session._await_pending_tasks()
                gc.collect()
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                self.assertEqual(self.session._pending_tasks, set())
                self.assertEqual(self.session.state_machine.state, state)
                self.assertEqual(self.session.state_machine.transition_count, 0)

    async def test_active_stop_preserves_cancelled_semantics(self):
        for state in (TaskState.PENDING, TaskState.PROCESSING, TaskState.PAUSED):
            with self.subTest(state=state):
                self.session.state_machine = TaskStateMachine("active", initial_state=state)
                self.session.stop()
                self.session.stop()
                self.assertTrue(self.session._stop_requested)
                self.assertTrue(self.session._pending_tasks)
                await self.session._await_pending_tasks()
                self.assertEqual(self.session.status, SessionStatus.STOPPED)
                self.assertEqual(self.session.state_machine.transition_count, 1)
                self.assertEqual(self.session.state_machine.metadata["transition_trigger"], "user_stop")
                self.assertEqual(self.session._pending_tasks, set())

    async def test_completion_before_stop_task_runs_preserves_terminal_state(self):
        for state in (TaskState.COMPLETED, TaskState.FAILED):
            with self.subTest(state=state):
                self.session.state_machine = TaskStateMachine("race", initial_state=TaskState.PROCESSING)
                self.session.stop()
                await self.session.state_machine.transition(state, trigger="execution_finished")
                await self.session._await_pending_tasks()
                self.assertEqual(self.session.state_machine.state, state)
                self.assertEqual(self.session.state_machine.transition_count, 1)

    async def test_cleanup_waits_for_stop_transition_hook(self):
        entered = asyncio.Event()
        release = asyncio.Event()
        finished = asyncio.Event()

        async def hook(machine, old_state, new_state):
            entered.set()
            await release.wait()
            finished.set()

        self.session.state_machine.add_hook(1, hook)
        self.session.stop()
        await asyncio.wait_for(entered.wait(), 1)
        cleanup = asyncio.create_task(self.session.graceful_shutdown())
        try:
            await asyncio.sleep(0)
            self.assertFalse(cleanup.done())
            self.assertFalse(finished.is_set())
        finally:
            release.set()
            await asyncio.wait_for(cleanup, 1)
        self.assertTrue(finished.is_set())
        self.assertEqual(self.session._pending_tasks, set())
        self.assertIsNotNone(self.session.metrics.end_time)

    async def test_context_exit_drains_stop_task(self):
        async with self.session:
            self.session.stop()
            self.assertTrue(self.session._pending_tasks)
        self.assertEqual(self.session.status, SessionStatus.STOPPED)
        self.assertEqual(self.session._pending_tasks, set())

    async def test_finished_background_exception_is_retrieved(self):
        async def fail():
            raise RuntimeError("background cleanup boundary")

        self.session._fire_and_forget(fail())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        self.assertEqual(self.session._pending_tasks, set())

    async def test_cleanup_drains_tasks_added_during_cleanup(self):
        finished = asyncio.Event()

        async def child():
            await asyncio.sleep(0)
            finished.set()

        async def parent():
            self.session._fire_and_forget(child())

        self.session._fire_and_forget(parent())
        await self.session._await_pending_tasks()
        self.assertTrue(finished.is_set())
        self.assertEqual(self.session._pending_tasks, set())

    async def test_cancelled_background_task_is_cleaned_up(self):
        task = self.session._fire_and_forget(asyncio.Event().wait())
        task.cancel()
        await self.session._await_pending_tasks()
        self.assertTrue(task.cancelled())
        self.assertEqual(self.session._pending_tasks, set())


if __name__ == "__main__":
    unittest.main()
