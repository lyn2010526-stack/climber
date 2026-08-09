# 持续测试守护系统使用指南

## 🎯 目标

建立永不停止的持续测试机制，为任何代码变更提供即时反馈。

---

## 🚀 快速启动

### 方法一：一键启动（推荐）

```bash
chmod +x /workspace/run_continuous_tests.sh
/workspace/run_continuous_tests.sh
```

### 方法二：使用 Python 脚本

```bash
python /workspace/start_guardian.py
```

### 方法三：手动启动（分步骤）

```bash
# 1. 安装依赖
pip install watchdog aiohttp pytest-cov pytest-watch

# 2. 启动 Python 测试监听
pytest tests/ -v --watch --tb=short

# 3. 在新终端启动前端测试监听
cd frontend-react && npm run test:watch

# 4. 启动文件变更检测
python /workspace/watch_tests.py
```

---

## 📁 项目结构

```
/workspace/
├── watch_tests.py          # 主监控脚本
├── start_guardian.py       # 辅助启动脚本
├── run_continuous_tests.sh # 完整启动脚本
├── start_tests.sh          # 快速启动脚本
├── test_dashboard.py       # 可视化仪表盘
├── .coveragerc            # 覆盖率配置
└── coverage_report/       # HTML 覆盖率报告输出目录
    └── index.html         # 实时覆盖率热力图
```

---

## 🔧 核心功能

### 1. 源码变化监听

- **技术**：Watchdog (inotify/fsevents)
- **范围**：`app/`, `tests/`, `skills/`, `agent-engine/`
- **防抖**：1 秒延迟避免重复触发
- **自动触发**：检测到变更 → 5 秒后运行相关测试

### 2. 多框架测试运行

#### Python 测试
```bash
pytest tests/ -v --watch --tb=short
```
- 实时监控 `.py` 文件变更
- 失败时显示详细 traceback
- 自动生成覆盖率报告

#### 前端测试  
```bash
npm run test:watch  # Vitest 监控模式
npx playwright test --ui  # E2E UI 模式
```
- 监听 `.ts`, `.tsx`, `.js`, `.jsx` 文件
- 实时显示测试结果
- 支持调试断点

### 3. 告警通知

支持集成以下渠道（需配置 webhook）：

```python
# watch_tests.py 中修改配置
config.slack_webhook = "https://hooks.slack.com/services/YOUR_WEBHOOK"
# 或
config.discord_webhook = "https://discord.com/api/webhooks/YOUR_WEBHOOK"
```

发送内容：
- ✅ 测试通过通知（绿色）
- ❌ 测试失败告警（红色，含错误摘要）

### 4. 覆盖率热力图

自动生成的 HTML 报告包含：
- 文件级覆盖率
- 函数/行覆盖率饼图
- 趋势分析图表
- 最近失败用例列表

访问位置：`file:///workspace/coverage_report/index.html`

---

## 📊 实时监控

### 查看进程状态

```bash
# 查看所有测试进程
ps aux | grep -E "(pytest|vitest)" | grep -v grep

# 查看日志
tail -f /workspace/logs/frontend_test.log
```

### 仪表板访问

生成并打开可视化仪表板：
```bash
python /workspace/test_dashboard.py
```

在浏览器中打开：
```
file:///workspace/coverage_report/dashboard.html
```

---

## ⚙️ 配置自定义

### 编辑 `watch_tests.py`

```python
@dataclass
class Config:
    # Webhook
    slack_webhook: str = "your-webhook-url"
    
    # 监听目录
    watched_dirs = ["/workspace/app", "/workspace/skills"]
    
    # 忽略模式
    ignore_patterns = ["*.pyc", "__pycache__", ".git"]
    
    # 测试命令
    python_test_cmd = "pytest tests/ -v --cov=. --maxfail=3"
    frontend_test_cmd = "cd frontend-react && npm run test:watch"
    
    # 防抖延迟
    debounce_delay = 1.0  # 秒
```

### systemd 服务部署（可选）

```bash
# 复制服务文件
sudo cp test-guardian.service /etc/systemd/system/

# 启用并启动
sudo systemctl daemon-reload
sudo systemctl enable test-guardian
sudo systemctl start test-guardian

# 查看状态
sudo systemctl status test-guardian
```

---

## 🔍 故障排查

### 问题 1: Watchdog 不触发

**原因**: 某些文件系统不支持 inotify

**解决**: 
```bash
# 检查 inotify 限制
cat /proc/sys/fs/inotify/max_user_watches
# 增加限制
sudo sysctl fs.inotify.max_user_watches=524288
```

### 问题 2: Pytest 测试挂起

**原因**: 异步测试未正确关闭事件循环

**解决**:
```python
# 在 conftest.py 中添加
@pytest.fixture(autouse=True)
def cleanup_event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    yield
    loop.close()
```

### 问题 3: 覆盖率报告空白

**原因**: 源代码路径配置错误

**解决**:
```bash
# 确保覆盖率和测试都在同一工作区
export PYTHONPATH="/workspace:$PYTHONPATH"
```

---

## 🎮 常用操作

### 停止所有服务

```bash
# 方法 1: Ctrl+C (如果前台运行)

# 方法 2: 杀死进程
pkill -f "pytest.*--watch"
pkill -f "vitest"

# 方法 3: 使用 systemd
sudo systemctl stop test-guardian
```

### 查看最新测试结果

```bash
# 运行单次测试
pytest tests/ -v --tb=short

# 查看覆盖率详情
xdg-open /workspace/coverage_report/index.html  # Linux
open /workspace/coverage_report/index.html     # macOS
```

### 添加新测试到监听

编辑 `watch_tests.py`:
```python
watched_dirs = [
    "/workspace/app",
    "/workspace/tests", 
    "/workspace/new_module"  # ← 添加新模块
]
```

---

## 💡 高级技巧

### 智能测试路由

根据文件变更只运行相关测试：

```python
# 在 watch_tests.py 中添加
def get_relevant_tests(file_path):
    if 'auth' in file_path:
        return 'tests/auth/'
    elif 'api' in file_path:
        return 'tests/api/'
    else:
        return 'tests/'
```

### 并行测试执行

```python
# 使用 pytest-xdist
pytest tests/ -n auto --watch
```

安装：
```bash
pip install pytest-xdist
```

### GitHub Actions 集成

`.github/workflows/test.yml`:
```yaml
name: Continuous Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          pytest tests/ --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 📈 性能优化建议

1. **缓存测试环境**: 使用 `pytest-rerunfailures` 减少失败重试时间
2. **增量测试**: 使用 `pytest-testmon` 只运行受影响的测试
3. **分布式测试**: 多台机器并行执行，使用 `pytest-distributed`
4. **跳过慢速测试**: 设置标记 `@pytest.mark.slow` 并在 CI 中跳过

---

## 🎯 成功标准

系统正常运行时应看到：

✅ **Python 测试监听器**: 常驻后台，显示 `Running...`  
✅ **前端测试监听器**: 实时响应 TS/TSX 变更  
✅ **覆盖率报告**: 每次测试后更新  
✅ **通知告警**: 失败时立即推送  
✅ **仪表板**: 实时更新数据  

---

## 🔐 安全提醒

1. **不要泄露 webhook URL**: 这是公开接口
2. **定期清理日志**: `/workspace/logs/` 可能很大
3. **监控资源使用**: 防止测试进程耗尽内存/CPU

---

## 📞 技术支持

遇到问题？检查以下步骤：

1. ✓ Python 版本 >= 3.8
2. ✓ Node.js >= 16.x
3. ✓ 已安装所有依赖 (`requirements.txt`)
4. ✓ 端口未被占用
5. ✓ 权限足够访问 `/workspace`

---

**持续改进**: 这是一个基础框架，可以根据项目需求不断扩展！
