# tests/conftest.py
"""共享 fixture：让每个单测都跑在隔离环境里，绝不碰真实库。

设计原则（与 e-commerce 项目一致）：单测必须确定性、零外部依赖——
不连 Redis、不下 embedding 模型、不调 LLM、不写真实 personal_chief.db / recipes_generated.json。
这里把 SQLite 与 AI 回流库重定向到 tmp_path，并清空 RAG 内存全局，跑完即弃。
"""
import sys
from pathlib import Path

import pytest

# 保证 `import app.xxx` 可用（即便未装成包 / pytest pythonpath 没生效）
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """把 fitness / modes 的 SQLite 指向临时文件，绝不写真实 personal_chief.db。"""
    db = tmp_path / "test_chief.db"
    monkeypatch.setattr("app.fitness._DB_PATH", str(db))
    monkeypatch.setattr("app.modes._DB_PATH", str(db))
    return db


@pytest.fixture
def temp_generated(tmp_path, monkeypatch):
    """把 AI 回流库指向临时文件，并清空 RAG 内存索引全局
    （置空可让回流逻辑跳过 embedding 分支，从而不加载向量模型、不写向量缓存）。"""
    import app.recipe_rag as rag
    gen = tmp_path / "recipes_generated.json"
    monkeypatch.setattr(rag, "_GENERATED_PATH", gen)
    monkeypatch.setattr(rag, "_recipes", None)
    monkeypatch.setattr(rag, "_matrix", None)
    return gen
