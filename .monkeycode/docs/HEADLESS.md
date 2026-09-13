# Headless 本地运行器

`app/headless/` 提供独立标准库 CLI，支持 Python 3.11+。导入路径独立于 FastAPI、数据库、平台 AgentEngine 和第三方 agent。已有 `pyproject.toml` 的 `climber-headless` 入口指向 `app.headless.cli:main`；源码模式可用 `python3 -m app.headless`。

## 运行

在仓库根目录执行，工作目录预先创建，trace 文件必须是工作目录外的新文件，父目录必须存在：

```bash
mkdir -p /tmp/climber-task
python3 -m app.headless --task examples/headless/task.json --workspace /tmp/climber-task --trace /tmp/climber-fake-trace.jsonl --fake-model examples/headless/fake-model.json
```

此例采用显式 `scripted-fake`，用于验证工具循环和输出协议。预期退出码为 **4**，产物为工作目录内的 `greeting.txt` 和工作目录外的 JSONL trace；stdout 与 trace 的 finish 均包含 `status=4`、`status_name=model_completed_unverified`、`verification=not_run`、`tool_errors=0`。真实模型使用用户自行提供的项目变量：

```bash
export USER_LLM_API_KEY='<your-key>'
export USER_LLM_BASE_URL='https://api.openai.com/v1'
export USER_LLM_MODEL='<your-model>'
python3 -m app.headless --task examples/headless/task.json --workspace /tmp/climber-task --trace /tmp/climber-model-trace.jsonl --max-turns 20 --max-tool-calls 50 --max-tokens 32000 --max-seconds 120
```

请求路径为 BASE_URL 加 `/chat/completions`，使用非流式 function tools、`max_tokens` 和 Bearer 认证。远程端点要求 HTTPS，localhost 支持 HTTP。重定向关闭，HTTP 错误仅返回状态码。模型必须支持该 Chat Completions 子集，并返回整数 `usage.total_tokens`；usage 缺失时停止。没有自动重试。

## 输入输出

- 任务支持 UTF-8 文本或 JSON `{"id":"optional-id","prompt":"required nonempty text"}`，最大 256 KiB，JSON 额外字段拒绝。
- 工具包含 `list_files(path)`、`read_file(path)`、`write_file(path, content)`；路径为相对路径，`.` 表示根目录。文件默认 64 KiB；目录最多 500 项。
- 标准输出为单个 JSON RunResult，含状态、任务 ID、模型类型、轮数、工具数、tokens、最终输出及原因，以及 `verification` 和 `tool_errors`。
- 退出码：**0 保留给将来的独立验收成功**（当前运行器无此返回路径），1 模型/响应错误，2 配置或输入错误，3 预算耗尽，**4 MODEL_COMPLETED_UNVERIFIED，模型完成但尚未独立验收**。纯文本完成、工具调用成功后完成、工具失败后完成均返回 4。
- `verification` 当前固定为 `not_run`。`output` 保留模型原始文本，其中的成功声明仅代表模型自述；自动化调用方应读取结构化状态及 `reason`。
- `tool_errors` 累计工具抛出的受处理异常或返回的 error 结果，仅用于诊断。发生错误时 `reason` 明确报告文件工具被拒绝或失败、累计次数及恢复情况尚未验证；工具错误允许后续纠错，历史计数保留，错误是否已解决需独立验收。预算耗尽或模型错误时也保留该诊断。
- JSONL 顺序记录 start、model_request、model_usage、tool_start、tool_result、finish。每条刷新；trace 路径以独占创建保护已有文件。
- 轨迹记录调用名称/ID与成功状态，省略文件正文和工具参数，最终模型输出仍可能包含任务中的敏感内容，应按敏感产物管理。

## 边界

命令执行始终 fail closed，当前版本没有 OS 沙箱、测试命令执行、网络工具或 ARC-Bench adapter。ARC-Bench 官方契约尚未核实，兼容性待后续确认。

文件使用 `Path.resolve()` containment，拒绝逃逸符号链接和 `.git`、`.env*` 路径，写入拒绝多硬链接文件。请使用专用工作目录，只放允许模型读取或修改的材料；目录中其他文件可能被发送给所配置的模型服务。此检查属于应用级文件边界，并发文件系统变更存在 TOCTOU 风险，读硬链接也需要由工作目录准备者控制。工作目录需由可信进程独占。修改直接写入，失败时保留已完成改动，未实现事务回滚。

token 预算按服务端累计 usage 在响应后核算，单次响应可能越过阈值；下一步工具执行会被阻止。调用前传入剩余预算作为输出上限，该值无法限制输入 token 的计费。时间预算在模型与工具边界检查并传入 HTTP socket timeout，属于协作式截止时间；慢速持续响应和阻塞文件 I/O 的严格墙钟限制需要外部进程监管。没有金额预算、上下文压缩或断点续跑。

## 验证

```bash
python3 -m unittest discover -s tests/headless -p 'test_*.py' -v
ruff check app/headless tests/headless
```

独立 unittest 避开 `tests/conftest.py` 的数据库初始化/清理。测试覆盖 scripted fake CLI 子进程、文件读写、预算、响应校验、HTTP 请求构造及错误处理；真实模型端到端验证需要用户凭据。
