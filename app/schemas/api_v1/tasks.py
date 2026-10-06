"""Task API schemas — mirroring the actual /tasks endpoints.

The task worker is invoked through ``task_manager.submit(task_type, payload)``,
so the submit request carries the handler type plus an opaque payload. Keeping
this schema in sync with ``app.api/v1/routes/tasks.py`` avoids drift between
the documented contract and the endpoint body.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.schemas.api_v1.base import StrictRequest


class SubmitTaskRequest(StrictRequest):
    task_type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)