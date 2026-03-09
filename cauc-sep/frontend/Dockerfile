# ============================================================================
# CAUC-SEP Frontend Dockerfile
# 多阶段构建 - Vue3 + Vite + Nginx
# ============================================================================

# ==================== 构建阶段 ====================
FROM node:20-alpine AS builder

LABEL maintainer="CAUC-SEP Team"
LABEL description="CAUC-SEP Frontend - Vue3 Application"

# 设置环境变量
ENV NODE_ENV=production \
    VITE_API_BASE_URL=/api \
    VITE_WS_BASE_URL=/ws

# 设置工作目录
WORKDIR /app

# 复制package文件
COPY package*.json ./

# Install dependencies (use npm ci for reliable CI builds)
RUN npm ci --prefer-offline --no-audit && \
    npm cache clean --force

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# ==================== 运行阶段 ====================
FROM nginx:alpine AS runtime

LABEL maintainer="CAUC-SEP Team"

# 安装curl用于健康检查
RUN apk add --no-cache curl

# 创建必要的目录
RUN mkdir -p /var/cache/nginx /var/log/nginx /var/run && \
    chown -R nginx:nginx /var/cache/nginx /var/log/nginx /var/run

# 从构建阶段复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制Nginx配置
COPY nginx.conf /etc/nginx/nginx.conf

# 创建非root用户运行配置
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /etc/nginx

# 切换到非root用户
USER nginx

# 暴露端口
EXPOSE 8080

# 健康检查配置
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 启动Nginx
CMD ["nginx", "-g", "daemon off;"]
