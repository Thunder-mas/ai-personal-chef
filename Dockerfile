# 后端镜像：FastAPI + LangGraph Agent。用 uv 按 uv.lock 还原依赖。
FROM python:3.11-slim

# uv：极快的 Python 包管理器（从官方镜像拷二进制）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 先拷依赖清单并安装（这一层可被 Docker 缓存，改代码不必重装依赖）
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# 再拷源码
COPY . .

# 让后续命令直接用虚拟环境里的可执行文件
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
# 注：首次对话会联网下载约 90MB 的 embedding 模型到 resources/（已挂载为卷，只下一次）
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
