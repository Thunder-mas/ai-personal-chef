# 单容器部署（Hugging Face Spaces · Docker SDK）：
#   Stage 1 用 Node 构建 React 前端 → 静态产物
#   Stage 2 用 Python 跑 FastAPI，同源伺服 /api/* 与前端静态文件
# 两个 stage 都用 Debian(glibc) 基础镜像，避免 alpine(musl) 下
# rolldown / lightningcss / onnxruntime 等原生二进制找不到的坑。

# ===== Stage 1: 构建 React 前端 =====
FROM node:20-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build          # 产物 → /build/dist

# ===== Stage 2: Python 后端（同源伺服 API + 前端）=====
FROM python:3.11-slim
# HF Spaces 建议以非 root 用户(uid 1000)运行；HOME 需可写（fastembed 模型缓存等）
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1
WORKDIR /home/user/app

# 先装依赖（利用层缓存）
COPY --chown=user requirements-backend.txt ./
RUN pip install --no-cache-dir --user -r requirements-backend.txt

# 再拷贝代码与数据
COPY --chown=user app/ ./app/
COPY --chown=user api/ ./api/
COPY --chown=user data/ ./data/
# 把上一 stage 构建好的前端产物放到 server.py 预期的 frontend/dist
COPY --chown=user --from=frontend /build/dist ./frontend/dist
# 运行时 SQLite（埋点/对话记忆/偏好）写到这里，容器内可写
RUN mkdir -p resources

# HF Spaces Docker 默认端口 7860
EXPOSE 7860
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "7860"]
