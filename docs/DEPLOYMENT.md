# Climber 部署指南

> 本文档描述 Climber Agent Engine 在各种环境中的部署方式。

## 目录

- [Docker 部署（推荐）](#docker-部署推荐)
- [本地部署](#本地部署)
- [生产环境部署](#生产环境部署)
- [云部署](#云部署)
- [配置参考](#配置参考)
- [故障排除](#故障排除)

---

## Docker 部署（推荐）

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+

### 快速启动

```bash
# 克隆仓库
git clone https://github.com/lyn2010526-stack/climber.git
cd climber/agent-engine

# 启动所有服务
docker-compose up -d
```

### 服务组成

| 服务 | 端口 | 说明 |
|------|------|------|
| api | 8000 | FastAPI 后端 |
| frontend | 5173 | React 前端 |
| postgres | 5432 | PostgreSQL 数据库 |
| redis | 6379 | Redis 缓存 |
| chroma | 8001 | ChromaDB 向量存储 |

### 数据卷

| 卷名 | 说明 |
|------|------|
| postgres_data | PostgreSQL 数据持久化 |
| redis_data | Redis 数据持久化 |
| chroma_data | ChromaDB 向量数据持久化 |

### 常用命令

```bash
# 查看日志
docker-compose logs -f api

# 重启服务
docker-compose restart api

# 停止所有服务
docker-compose down

# 停止并删除数据卷（谨慎操作）
docker-compose down -v

# 重新构建
docker-compose build --no-cache
docker-compose up -d
```

### 健康检查

```bash
# 检查 API 健康状态
curl http://localhost:8000/health

# 检查数据库
docker-compose exec postgres pg_isready -U climber

# 检查 Redis
docker-compose exec redis redis-cli ping
```

---

## 本地部署

### 前置要求

- Python 3.11+
- Node.js 18+
- pip / npm

### 后端部署

```bash
# 克隆仓库
git clone https://github.com/lyn2010526-stack/climber.git
cd climber/agent-engine

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Keys

# 数据库迁移
alembic upgrade head

# 启动服务（开发模式）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 启动服务（生产模式）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 前端部署

```bash
cd frontend-react

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build

# 预览构建结果
npm run preview
```

### 使用 SQLite（默认）

默认配置使用 SQLite，无需额外安装数据库：

```env
DATABASE_URL=sqlite+aiosqlite:///./data/climber.db
```

数据文件存储在 `./data/climber.db`。

### 使用 PostgreSQL

多用户并发场景推荐使用 PostgreSQL：

```bash
# 使用 Docker 启动 PostgreSQL
docker run -d \
  --name climber-postgres \
  -e POSTGRES_USER=climber \
  -e POSTGRES_PASSWORD=climber \
  -e POSTGRES_DB=climber \
  -v postgres_data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:15-alpine
```

```env
DATABASE_URL=postgresql+asyncpg://climber:climber@localhost:5432/climber
```

### 使用 Redis（可选）

Redis 用于缓存和会话存储：

```bash
docker run -d \
  --name climber-redis \
  -v redis_data:/data \
  -p 6379:6379 \
  redis:7-alpine
```

```env
REDIS_URL=redis://localhost:6379/0
```

---

## 生产环境部署

### 安全配置

```env
# 生产环境必须修改
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=<生成强随机密钥>
JWT_SECRET_KEY=<生成强随机密钥>

# 安全加固
SANDBOX_MODE=true
ALLOWED_PATHS=/workspace/projects

# 日志
LOG_LEVEL=WARN
LOG_FORMAT=json
```

### 使用 Nginx 反向代理

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # 前端静态文件
    location / {
        root /var/www/climber/frontend-react/dist;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SSE 流式支持
    location /api/v1/sessions/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    # WebSocket 支持
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
    }
}
```

### 使用 Systemd 管理进程

```ini
# /etc/systemd/system/climber.service
[Unit]
Description=Climber Agent Engine
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=climber
Group=climber
WorkingDirectory=/opt/climber/agent-engine
Environment=PATH=/opt/climber/agent-engine/venv/bin
ExecStart=/opt/climber/agent-engine/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 启用并启动服务
sudo systemctl enable climber
sudo systemctl start climber

# 查看状态
sudo systemctl status climber

# 查看日志
sudo journalctl -u climber -f
```

### 性能调优

```env
# 数据库连接池
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=1800

# SQLite 优化
SQLITE_WAL=true
SQLITE_BUSY_TIMEOUT_MS=5000

# Token 限制
MAX_TOKENS_PER_SESSION=100000
MAX_COST_PER_DAY=50.0

# 内存限制
MEMORY_LIMIT_MB=4096
MEMORY_CHECK_INTERVAL=60
```

### 监控配置

```env
# 结构化 JSON 日志
LOG_FORMAT=json
LOG_LEVEL=WARN

# Prometheus 指标
# 访问 /metrics 端点获取指标
```

推荐监控栈：
- **日志**: ELK Stack 或 Loki + Grafana
- **指标**: Prometheus + Grafana
- **告警**: Alertmanager

---

## 云部署

### 部署到 VPS

```bash
# 1. 登录服务器
ssh user@your-server

# 2. 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 3. 克隆并启动
git clone https://github.com/lyn2010526-stack/climber.git
cd climber/agent-engine
docker-compose up -d
```

### 部署到 Kubernetes

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: climber-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: climber-api
  template:
    metadata:
      labels:
        app: climber-api
    spec:
      containers:
        - name: api
          image: climber/agent-engine:latest
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: climber-secrets
                  key: database-url
            - name: OPENAI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: climber-secrets
                  key: openai-key
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "2Gi"
              cpu: "1000m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: climber-api
spec:
  selector:
    app: climber-api
  ports:
    - port: 80
      targetPort: 8000
  type: ClusterIP
```

### 部署到 Railway / Render

```bash
# Railway
railway init
railway up

# Render (使用 render.yaml)
# 创建 render.yaml 后自动部署
```

---

## 配置参考

### 环境变量完整列表

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `APP_ENV` | 否 | `development` | 运行环境 |
| `APP_DEBUG` | 否 | `true` | 调试模式 |
| `APP_LOG_LEVEL` | 否 | `INFO` | 日志级别 |
| `APP_SECRET_KEY` | 是 | 随机生成 | 应用密钥 |
| `DATABASE_URL`  | 否 | SQLite | 数据库连接 |
| `REDIS_URL` | 否 | 无 | Redis 连接 |
| `VECTOR_STORE_PATH` | 否 | `./data/chroma` | 向量存储路径 |
| `OPENAI_API_KEY` | 否 | 无 | OpenAI API Key |
| `ANTHROPIC_API_KEY` | 否 | 无 | Anthropic API Key |
| `GOOGLE_API_KEY` | 否 | 无 | Google API Key |
| `OLLAMA_BASE_URL` | 否 | `http://localhost:11434` | Ollama 地址 |
| `DEFAULT_MODEL` | 否 | `gpt-4o-mini` | 默认模型 |
| `JWT_SECRET_KEY` | 是 | 随机生成 | JWT 签名密钥 |
| `JWT_EXPIRE_MINUTES` | 否 | `1440` | JWT 过期时间 |
| `CORS_ORIGINS` | 否 | localhost | CORS 允许来源 |
| `HOST` | 否 | `0.0.0.0` | 监听地址 |
| `PORT` | 否 | `8000` | 监听端口 |
| `TELEGRAM_BOT_TOKEN` | 否 | 无 | Telegram Bot Token |
| `SANDBOX_MODE` | 否 | `false` | 沙箱模式 |
| `ALLOWED_PATHS` | 否 | 无 | 允许的文件路径 |
| `MAX_TOKENS_PER_SESSION` | 否 | `100000` | 每会话 Token 限制 |
| `MAX_COST_PER_DAY` | 否 | 无 | 每日费用限制 |
| `MEMORY_LIMIT_MB` | 否 | `2048` | 内存限制 |
| `DB_POOL_SIZE` | 否 | `5` | 数据库连接池大小 |
| `DB_MAX_OVERFLOW` | 否 | `10` | 连接池溢出 |

---

## 故障排除

### 常见问题

**Q: 启动时报错 `Missing required dependency`**
```bash
# 安装缺失依赖
pip install playwright chromadb psutil
```

**Q: 数据库迁移失败**
```bash
# 重置数据库
rm -f data/climber.db
alembic upgrade head
```

**Q: 端口被占用**
```bash
# 查找占用端口的进程
lsof -i :8000
# 或修改 PORT 环境变量
PORT=8001 uvicorn app.main:app
```

**Q: 前端无法连接后端**
```bash
# 检查 CORS 配置
# 确保 .env 中 CORS_ORIGINS 包含前端地址
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

**Q: ChromaDB 连接失败**
```bash
# 检查向量存储目录权限
chmod -R 755 ./data/chroma
```

### 日志位置

- 默认日志目录: `./logs/`
- 可通过 `LOG_DIR` 环境变量修改
- 健康检查日志: `GET /health/logs`

### 获取帮助

```bash
# 诊断信息
curl http://localhost:8000/api/v1/doctor/

# 健康状态
curl http://localhost:8000/health
```
