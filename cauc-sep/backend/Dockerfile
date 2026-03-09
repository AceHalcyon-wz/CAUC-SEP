# ============================================================================
# CAUC-SEP Backend Dockerfile
# 多阶段构建 - 生产环境优化
# ============================================================================

# ==================== 构建阶段 ====================
FROM python:3.11-slim AS builder

LABEL maintainer="CAUC-SEP Team"
LABEL description="CAUC-SEP Backend - FastAPI Application"

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ==================== 运行阶段 ====================
FROM python:3.11-slim AS runtime

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    # 应用配置
    APP_ENV=production \
    LOG_LEVEL=INFO \
    # 安全配置
    CORS_ORIGINS="" \
    # 数据库配置
    DATABASE_URL="" \
    # Redis配置
    REDIS_URL=""

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libhdf5-serial-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 创建非root用户
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 创建应用目录
WORKDIR /app

# 创建必要的目录并设置权限
RUN mkdir -p /app/logs /app/exports /app/data && \
    chown -R appuser:appgroup /app

# 复制应用代码
COPY --chown=appuser:appgroup . .

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查配置
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
