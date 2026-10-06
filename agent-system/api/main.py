"""独立 FastAPI 入口：`uvicorn agent_system.api.main:app --port 8010`。

先在 Climber 仓库根目录运行（agent_bootstrap 映射被沙箱拦截的顶层包名）。
"""

from __future__ import annotations

import agent_bootstrap  # noqa: F401  # 顶层包名映射，必须先导入
from agent_system.api.routes import router
from fastapi import FastAPI

app = FastAPI(
    title="Climber agent-system", version="0.1.0", description="TAOR 七阶段智能体引擎 HTTP API"
)
app.include_router(router, prefix="/api/agent", tags=["agent-system"])
