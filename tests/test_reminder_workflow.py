"""Tests for reminder workflow."""


import pytest

from app.workflows.reminder_workflow import (
    ReminderWorkflowDefinition,
    ReminderWorkflowEngine,
    ReminderWorkflowStep,
)


class TestReminderWorkflowEngine:
    """Tests for workflow engine."""

    def test_create_workflow(self):
        engine = ReminderWorkflowEngine()
        wf = ReminderWorkflowDefinition(name='test')
        wid = engine.create_workflow(wf)
        assert wid == wf.id

    def test_get_workflow(self):
        engine = ReminderWorkflowEngine()
        wf = ReminderWorkflowDefinition(name='test')
        wid = engine.create_workflow(wf)
        result = engine.get_workflow(wid)
        assert result is not None
        assert result.name == 'test'

    def test_list_workflows(self):
        engine = ReminderWorkflowEngine()
        engine.create_workflow(ReminderWorkflowDefinition(name='wf1'))
        engine.create_workflow(ReminderWorkflowDefinition(name='wf2'))
        result = engine.list_workflows()
        assert len(result) == 2

    def test_delete_workflow(self):
        engine = ReminderWorkflowEngine()
        wid = engine.create_workflow(ReminderWorkflowDefinition(name='test'))
        assert engine.delete_workflow(wid)
        assert engine.get_workflow(wid) is None

    def test_register_handler(self):
        engine = ReminderWorkflowEngine()
        engine.register_handler('test_action', lambda p, v: None)
        assert 'test_action' in engine._handlers

    @pytest.mark.asyncio
    async def test_execute_workflow(self):
        engine = ReminderWorkflowEngine()

        async def mock_handler(params, variables):
            variables['result'] = 'done'

        engine.register_handler('mock', mock_handler)
        step = ReminderWorkflowStep(name='step1', action='mock')
        wf = ReminderWorkflowDefinition(name='test', steps=[step])
        wid = engine.create_workflow(wf)

        result = await engine.execute_workflow(wid)
        assert result is not None
        assert result.status == 'completed'

    def test_pause_execution(self):
        engine = ReminderWorkflowEngine()
        execution = ReminderWorkflowExecution(status='running')
        engine._executions[execution.id] = execution
        assert engine.pause_execution(execution.id)
        assert execution.status == 'paused'

    def test_cancel_execution(self):
        engine = ReminderWorkflowEngine()
        execution = ReminderWorkflowExecution(status='running')
        engine._executions[execution.id] = execution
        assert engine.cancel_execution(execution.id)
        assert execution.status == 'cancelled'

    def test_get_stats(self):
        engine = ReminderWorkflowEngine()
        engine.create_workflow(ReminderWorkflowDefinition(name='test'))
        stats = engine.get_stats()
        assert stats['total_workflows'] == 1
