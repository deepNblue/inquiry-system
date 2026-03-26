# 部署指南

## 环境要求

- Python 3.10+
- Docker (可选)
- PostgreSQL (可选)
- Redis (可选)

## 本地部署

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml
```

### 3. 运行

```bash
# CLI 模式
python main.py -i products.csv -m web history

# API 服务
python api.py

# Web 界面
python ui.py
```

## Docker 部署

### 快速部署

```bash
./start.sh docker
```

### 手动部署

```bash
# 构建镜像
docker build -t inquiry-system .

# 运行
docker run -p 8000:8000 -p 7860:7860 \
  -v $(pwd)/data:/app/data \
  -e DB_TYPE=postgres \
  inquiry-system
```

## 生产环境部署

### 1. 准备服务器

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 安装 Docker Compose
apt install docker-compose
```

### 2. 配置环境变量

```bash
cp .env.production .env
# 编辑 .env 填入密码和密钥
```

### 3. 启动服务

```bash
docker-compose -f docker-compose.prod.yaml up -d
```

### 4. 检查状态

```bash
docker-compose ps
docker-compose logs -f api
```

## Nginx 反向代理

```nginx
server {
    listen 80;
    server_name inquiry.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 监控

### 健康检查

```bash
curl http://localhost:8000/health
```

### 日志

```bash
# API 日志
docker-compose logs api

# 监控日志
docker-compose logs -f monitor
```

## 备份

### 数据库备份

```bash
# SQLite
cp data/history.db data/backup/history_$(date +%Y%m%d).db

# PostgreSQL
pg_dump -U inquiry inquiry > backup_$(date +%Y%m%d).sql
```

### 自动备份 (cron)

```bash
# 每天凌晨3点备份
0 3 * * * cp /opt/inquiry-system/data/history.db /opt/inquiry-system/backups/
```

## 故障排除

### 服务启动失败

```bash
# 检查日志
docker-compose logs api

# 检查端口占用
netstat -tlnp | grep 8000
```

### 数据库连接失败

```bash
# 检查 PostgreSQL
docker-compose logs postgres

# 检查 Redis
docker-compose logs redis
```
