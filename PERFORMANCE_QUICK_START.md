# Agent Engine - 性能优化实施指南

快速开始：按照以下步骤实施所有性能优化措施。

---

## 🚀 一键启动优化

### Step 1: 检查当前状态

```bash
# 查看 CPU 核心数
nproc --all

# 查看当前 Gunicorn 配置
grep "^workers" gunicorn.conf.py

# 查看数据库索引数量
sqlite3 data/climber.db "SELECT COUNT(*) FROM sqlite_master WHERE type='index';"
```

### Step 2: 应用优化配置

```bash
# 设置优化环境变量
export GUNICORN_WORKERS=$(( $(nproc --all) * 2 + 1 ))
export GUNICORN_WORKER_CONNECTIONS=2000
export GUNICORN_TIMEOUT=180
export GUNICORN_MAX_REQUESTS=5000
export GUNICORN_PRELOAD=true

echo "✓ Worker 数量：$GUNICORN_WORKERS"
```

### Step 3: 重启服务

```bash
# 停止旧进程
pkill -f "gunicorn.*agent-engine"
sleep 2

# 启动新配置
cd /workspace/agent-engine
nohup gunicorn app.main:app --config gunicorn.conf.py > logs/gunicorn.log 2>&1 &

# 验证
curl http://localhost:8000/health
ps aux | grep gunicorn
```

### Step 4: 前端构建优化

```bash
cd frontend-react
npm install --save-dev vite-plugin-gzip rollup-plugin-visualizer vite-plugin-image-optimizer
npm run build

# 查看构建结果
ls -lh dist/assets/
cat dist/assets/*.html | grep -i "vendor"
```

### Step 5: Redis 缓存预热 (可选，需要先安装 Redis)

```bash
pip install redis
python redis_cache_warming.py
```

---

## 📊 预期性能提升

| 指标 | 优化前 | 优化后 (预计) |
|------|--------|-------------|
| 单请求延迟 | 8.48ms | 4-6ms |
| 100 并发 P99 | 1277ms | 150-200ms |
| 500 并发 P99 | 8468ms | 400-500ms |
| 1000 并发 P99 | 13514ms | 800-1000ms |
| 内存峰值 | 27MB | 12-15MB |

---

## 🔍 重新测试验证

使用现有测试脚本重新运行性能测试:

```bash
cd /workspace/agent-engine
python3 comprehensive_performance_test.py
```

---

## 📝 完整文档参考

详细报告文件位置:
- `OPTIMIZATION_REPORT.md` - 完整中文优化报告 (含所有测试结果)
- `PERFORMANCE_TESTING_SUMMARY.md` - 执行摘要
- `performance_test_results.json` - JSON 格式原始数据
- `comprehensive_performance_report.json` - 综合分析报告

优化脚本位置:
- `optimize_database.py` - 数据库索引优化工具
- `redis_cache_warming.py` - Redis 缓存预热工具
- `comprehensive_performance_test.py` - 完整测试框架

配置文件位置:
- `gunicorn.conf.py` - Gunicorn 服务器配置
- `frontend-react/vite.config.optimized.ts` - 前端构建优化
- `caddyfile_config` - Web server 反向代理配置

---

**需要帮助？**  
详细实施步骤和理论说明请参考 OPTIMIZATION_REPORT.md
