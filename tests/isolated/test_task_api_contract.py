"""Focused API contract checks for task submission and subtask endpoints."""

import pytest
from pydantic import ValidationError

from app.api.v1.routes.tasks import router
from app.schemas.api_v1.tasks import (
    ClaimSubtasksRequest,
    CompleteSubtaskRequest,
    SubtaskResponse,
    SubmitTaskRequest,
)


def test_factory_run_requires_objective() -> None:
    with pytest.raises(ValidationError, match="non-empty objective"):
        SubmitTaskRequest(task_type="factory_run", payload={})

    request = SubmitTaskRequest(
        task_type="factory_run", payload={"objective": "build the feature"}
    )
    assert request.task_type == "factory_run"


def test_submit_task_rejects_unknown_task_type_and_fields() -> None:
    with pytest.raises(ValidationError):
        SubmitTaskRequest(task_type="unknown", payload={})
    with pytest.raises(ValidationError):
        ClaimSubtasksRequest(agent_id="agent", unexpected=True)
    with pytest.raises(ValidationError):
        CompleteSubtaskRequest(agent_id="agent", unexpected=True)


def test_subtask_response_exposes_worker_id_as_subtask_id() -> None:
    response = SubtaskResponse.model_validate(
        {
            "id": "st-1",
            "description": "Work",
            "status": "claimed",
            "dependencies": [],
            "claimed_by": "agent-1",
        }
    )

    assert response.subtask_id == "st-1"
    assert response.model_dump(by_alias=True)["subtask_id"] == "st-1"
    assert response.status == "claimed"


def test_subtask_routes_declare_response_models() -> None:
    prefix = router.prefix
    routes = {route.path.removeprefix(prefix): route for route in router.routes}

    assert routes["/{task_id}/subtasks"].response_model.__name__ == "SubtaskListResponse"
    assert routes["/{task_id}/subtasks/claim"].response_model.__name__ == "SubtaskListResponse"
    assert (
        routes["/{task_id}/subtasks/{subtask_id}/complete"].response_model.__name__
        == "SubtaskResponse"
    )
