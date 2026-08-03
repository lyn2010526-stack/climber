# Climber 开发指南

> 本文档描述 Climber Agent Engine 的开发环境搭建、代码规范、测试方法和常见任务。

## 环境搭建

### 前置要求

- Python 3.11+
- Node.js 18+
- Git

### 安装步骤

```bash
# 克隆仓库
git clone https://github.com/lyn2010526-stack/climber.git
cd climber/agent-engine

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install pytest pytest-asyncio pytest-cov ruff mypy

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Keys

# 数据库迁移
alembic upgrade head
```

### 启动开发服务器

```bash
# 后端（带热重载）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 前端
cd frontend-react
npm install
npm run dev
```

---

## 项目结构

```
agent-engine/
├── app/
│   ├── api/v1/          # API 路由层
│   │   ├── chat.py      # 聊天端点
│   │   ├── sessions.py  # 会话管理
│   │   ├── agents.py    # Agent 管理
│   │   ├── workflows.py # 工作流
│   │   └── ...          # 其他端点
│   ├── core/            # Agent 引擎核心
│   │   ├── agent_engine.py    # 主引擎
│   │   ├── context_manager.py # 上下文管理
│   │   ├── tool_runtime.py    # 工具运行时
│   │   ├── model_scheduler.py # 模型调度
│   │   ├── permission_controller.py # 权限控制
│   │   └── ...          # 140+ 核心模块
│   ├── middleware/      # 中间件
│   ├── models/          # LLM 适配器
│   ├── storage/         # 数据持久化
│   ├── tools/           # 工具系统
│   ├── workflow/        # 工作流引擎
│   ├── config.py        # 配置
│   └── main.py          # 应用入口
├── tests/               # 测试套件
├── alembic/             # 数据库迁移
├── docs/                # 文档
└── frontend-react/      # 前端
```

---

## 代码规范

### Python 规范

遵循 PEP 8 标准，关键规则：

| 规则 | 说明 |
|------|------|
| 缩进 | 4 空格 |
| 行宽 | 最大 100 字符 |
| 导入 | 分组：标准库 → 第三方 → 本地 |
| 命名 | 函数/变量 `snake_case`，类 `PascalCase` |
| 类型标注 | 所有函数必须有类型标注 |
| 文档字符串 | 公共函数必须有 docstring |

### 代码风格检查

```bash
# 使用 ruff 检查
ruff check app/

# 自动修复
ruff check --fix app/

# 类型检查
mypy app/
```

### 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 文件 | snake_case | `agent_engine.py` |
| 类 | PascalCase | `AgentEngine` |
| 函数 | snake_case | `create_session` |
| 常量 | SCREAMING_SNAKE | `MAX_RETRIES` |
| 私有成员 | 前导下划线 | `_internal_state` |

### 导入顺序

```python
# 1. 标准库
import asyncio
from pathlib import Path

# 2. 第三方
from fastapi import APIRouter
from sqlalchemy import select

# 3. 本地应用
from app.core.agent_engine import AgentEngine
from app.storage.database import Session
```

---

## 测试方法

### 运行测试

```bash
# 运行所有测试
python3 -m pytest tests/ -v

# 运行特定测试文件
python3 -m pytest tests/test_agent_engine.py -v

# 运行特定测试函数
python3 -m pytest tests/test_agent_engine.py::test_function_name -v

# 带覆盖率报告
python3 -m pytest tests/ --cov=app --cov-report=html

# 异步测试
python3 -m pytest tests/ -v --asyncio-mode=auto
```

### 测试框架

- **框架**: pytest
- **异步支持**: pytest-asyncio
- **覆盖率**: pytest-cov
- **Mock**: unittest.mock

### 测试结构

```python
# tests/test_example.py
import pytest
from app.core.agent_engine import AgentEngine

class TestAgentEngine:
    """AgentEngine 测试套件"""

    @pytest.fixture
    def engine(self):
        """创建测试用引擎实例"""
        return AgentEngine(...)

    def test_create_session(self, engine):
        """测试会话创建"""
        session = engine.create_session(...)
        assert session.id is not None

    @pytest.mark.asyncio
    async def test_run(self, engine):
        """测试异步执行"""
        async for event in engine.run(session, "hello"):
            assert event.type is not None
```

### 测试规范

| 规则 | 说明 |
|------|------|
| 文件命名 | `test_*.py` |
| 类命名 | `Test*` |
| 函数命名 | `test_*` |
| 描述 | `"should [预期行为] when [条件]"` |
| 位置 | 与源码同目录或 `tests/` |

---

## 开发工作流

### Git 分支策略

- `main` — 生产就绪代码
- `feature/*` — 新功能开发
- `fix/*` — Bug 修复
- `chore/*` — 维护任务

### 提交规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

类型：
| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档变更 |
| `style` | 代码格式 |
| `refactor` | 重构 |
| `test` | 测试 |
| `chore` | 构建/工具 |

示例：
```
feat(chat): add SSE streaming support for chat endpoint

fix(auth): handle expired tokens gracefully

docs(api): update API endpoint documentation
```

### Pull Request 流程

1. 从 `main` 创建功能分支
2. 实现变更并编写测试
3. 运行 `python3 -m pytest tests/ -v`
4. 运行 `ruff check app/`
5. 更新相关文档
6. 提交 PR 并填写描述
7. 处理审查反馈
8. Squash 合并

---

## 常见任务

### 添加新 API 端点

**需修改的文件**:
1. `app/api/v1/<domain>.py` — 添加路由处理器
2. `app/api/v1/__init__.py` — 注册路由
3. `tests/api/test_<domain>.py` — 添加测试

**步骤**:
1. 在 `app/api/v1/` 创建新路由文件
2. 定义 Pydantic 请求/响应模型
3. 实现路由处理器
4. 在 `__init__.py` 注册路由
5. 编写测试
6. 更新 API 文档

**示例**:
```python
# app/api/v1/example.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class ExampleRequest(BaseModel):
    message: str

@router.post("/example")
async def example_endpoint(request: ExampleRequest):
    return {"result": request.message}
```

### 添加新工具

**需修改的文件**:
1. `app/tools/` — 工具实现
2. `app/tools/__init__.py` — 注册工具
3. `tests/tools/test_*.py` — 测试

**步骤**:
1. 定义工具函数和参数 Schema
2. 使用 `@tool` 装饰器注册
3. 实现工具逻辑
4. 添加测试

### 添加新模型适配器

**需修改的文件**:
1. `app/models/<provider>_adapter.py` — 适配器实现
2. `app/models/registry.py` — 注册模型

**步骤**:
1. 继承 `BaseModelAdapter`
2. 实现 `chat()` 方法
3. 在 Registry 中注册

### 添加数据库迁移

**步骤**:
1. 修改 `app/storage/database.py` 中的模型
2. 生成迁移: `alembic revision --autogenerate -m "描述"`
3. 检查生成的迁移文件
4. 应用迁移: `alembic upgrade head`
5. 测试回滚: `alembic downgrade -1`

### 修复 Bug

**流程**:
1. 编写复现 bug 的失败测试
2. 在代码中定位根因
3. 用最小改动修复
4. 验证测试通过
5. 检查其他地方是否有类似问题

---

## 调试技巧

### 日志

```python
import structlog
logger = structlog.get_logger()

logger.debug("调试信息", key=value)
logger.info("操作记录", user_id=user_id)
logger.warn("可恢复问题", error=str(e))
logger.error("需要关注的故障", exc_info=True)
```

### 健康检查

```bash
# 查看系统健康状态
curl http://localhost:8000/health | jq

# 查看最近日志
curl http://localhost:8000/health/logs?lines=50&errors_only=true | jq

# 查看指标
curl http://localhost:8000/metrics | jq
```

### 诊断端点

```bash
# 系统诊断
curl http://localhost:8000/api/v1/doctor/
```

---

## 性能优化建议

### 数据库

- 使用 PostgreSQL 替代 SQLite 以获得更好的并发性能
- 配置连接池大小
- 为常用查询添加索引
- 使用 WAL 模式（SQLite）

### 缓存

- 启用 Redis 缓存
- 对频繁访问的数据使用内存缓存
- 使用 `@cached` 装饰器

### 异步

- 使用 `async/await` 处理 I/O 密集型操作
- 使用 `asyncio.gather()` 并行执行独立任务
- 避免在异步函数中阻塞

---

## 前端开发

### 技术栈

- React 18+
- TypeScript
- Vite (构建工具)

### 开发命令

```bash
cd frontend-react

# 安装依赖
npm install

# 开发服务器
npm run dev

# 类型检查
npm run typecheck

# 代码检查
npm run lint

# 格式化
npm run format

# 构建
npm run build

# 测试
npm test
```

### 前端结构

```
frontend-react/
├── src/
│   ├── components/     # UI 组件
│   ├── pages/          # 页面
│   ├── hooks/          # 自定义 Hooks
│   ├── services/       # API 服务
│   ├── stores/         # 状态管理
│   └── types/          # TypeScript 类型
├── public/             # 静态资源
└── tests/              # 测试
```
