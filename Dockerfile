# 自动询价系统 - Dockerfile
# 多阶段构建优化

# 阶段1：构建
FROM python:3.12-slim AS builder

WORKDIR /build

# 安装编译依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --user

# 阶段2：运行
FROM python:3.12-slim

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 appuser

# 从构建阶段复制依赖
COPY --from=builder /root/.local /home/appuser/.local

# 复制应用代码
COPY --chown=appuser:appuser . .

# 创建目录
RUN mkdir -p /app/data /app/output /app/logs && \
    chown -R appuser:appuser /app

# 切换用户
USER appuser

# 设置环境变量
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai

# 暴露端口
EXPOSE 8000 7860

# 默认命令
CMD ["python3", "api.py"]
