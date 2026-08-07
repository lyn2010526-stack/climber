"""Tests for deployment workflow."""


import pytest

from app.workflows.deployment_workflow import (
    DeploymentWorkflowDefinition,
    DeploymentWorkflowEngine,
    DeploymentWorkflowExecution,
    DeploymentWorkflowStep,
)


class TestDeploymentWorkflowEngine:
    """Tests for workflow engine."""

    def test_create_workflow(self):
        engine = DeploymentWorkflowEngine()
        wf = DeploymentWorkflowDefinition(name='test')
        wid = engine.create_workflow(wf)
        assert wid == wf.id

    def test_get_workflow(self):
        engine = DeploymentWorkflowEngine()
        wf = DeploymentWorkflowDefinition(name='test')
        wid = engine.create_workflow(wf)
        result = engine.get_workflow(wid)
        assert result is not None
        assert result.name == 'test'

    def test_list_workflows(self):
        engine = DeploymentWorkflowEngine()
        engine.create_workflow(DeploymentWorkflowDefinition(name='wf1'))
        engine.create_workflow(DeploymentWorkflowDefinition(name='wf2'))
        result = engine.list_workflows()
        assert len(result) == 2

    def test_delete_workflow(self):
        engine = DeploymentWorkflowEngine()
        wid = engine.create_workflow(DeploymentWorkflowDefinition(name='test'))
        assert engine.delete_workflow(wid)
        assert engine.get_workflow(wid) is None

    def test_register_handler(self):
        engine = DeploymentWorkflowEngine()
        engine.register_handler('test_action', lambda p, v: None)
        assert 'test_action' in engine._handlers

    @pytest.mark.asyncio
    async def test_execute_workflow(self):
        engine = DeploymentWorkflowEngine()

        async def mock_handler(params, variables):
            variables['result'] = 'done'

        engine.register_handler('mock', mock_handler)
        step = DeploymentWorkflowStep(name='step1', action='mock')
        wf = DeploymentWorkflowDefinition(name='test', steps=[step])
        wid = engine.create_workflow(wf)

        result = await engine.execute_workflow(wid)
        assert result is not None
        assert result.status == 'completed'

    def test_pause_execution(self):
        engine = DeploymentWorkflowEngine()
        execution = DeploymentWorkflowExecution(status='running')
        engine._executions[execution.id] = execution
        assert engine.pause_execution(execution.id)
        assert execution.status == 'paused'

    def test_cancel_execution(self):
        engine = DeploymentWorkflowEngine()
        execution = DeploymentWorkflowExecution(status='running')
        engine._executions[execution.id] = execution
        assert engine.cancel_execution(execution.id)
        assert execution.status == 'cancelled'

    def test_get_stats(self):
        engine = DeploymentWorkflowEngine()
        engine.create_workflow(DeploymentWorkflowDefinition(name='test'))
        stats = engine.get_stats()
        assert stats['total_workflows'] == 1
