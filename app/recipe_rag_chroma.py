# app/recipe_rag_chroma.py
"""菜谱 RAG —— Chroma 向量库后端（与 recipe_rag.py 的 numpy 版做对照）。

关键设计：复用 recipe_rag 里同一套 fastembed 向量（bge-small-zh-v1.5）灌进 Chroma，
所以两个后端的差异只在「索引 / 检索方式」，不在 embedding 模型 —— 对比才公平。

为什么要有这版（面试可讲）：
  - numpy 版：把全量向量读进内存，每次检索做一次「query 向量 × 全矩阵」点积，O(N·dim)。
    小数据（这里 48 条）零依赖、零部署成本、足够快，是当前线上的选择。
  - Chroma 版：HNSW 近似最近邻（亚线性检索）、磁盘持久化、可增量写入、可加元数据过滤。
    当菜谱量级到几万/几十万、需要在线增删与过滤时，才值得引入这套向量库。
"""
import os
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")  # 关掉 Chroma 匿名遥测

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.recipe_rag import (
    load_recipes,
    recipe_to_text,
    fingerprint,
    embed_texts,
    embed_query,
)

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_CHROMA_DIR = _PROJECT_ROOT / "resources" / "chroma_db"
_COLLECTION = "recipes"

_client = None
_collection = None
_recipes_cache: Optional[List[Dict[str, Any]]] = None  # 菜谱缓存：避免每次检索重读 recipes.json


def _get_recipes() -> List[Dict[str, Any]]:
    """菜谱列表（懒加载 + 缓存），与 numpy 后端一致，避免每次查询重读文件。"""
    global _recipes_cache
    if _recipes_cache is None:
        _recipes_cache = load_recipes()
    return _recipes_cache


def _metadata(fp: str) -> dict:
    # hnsw:space=cosine → 距离为余弦距离（1 - 余弦相似度），便于换算回相似度对齐 numpy 版
    return {"hnsw:space": "cosine", "fp": fp}


def _build(col, recipes) -> None:
    """把菜谱的（复用 numpy 版的）归一化向量批量写入 collection。"""
    texts = [recipe_to_text(r) for r in recipes]
    vecs = embed_texts(texts)  # (N, dim)，与 numpy 版完全相同的向量
    col.add(
        ids=[str(i) for i in range(len(recipes))],
        embeddings=[v.tolist() for v in vecs],
        documents=texts,
        metadatas=[{"idx": i, "name": recipes[i].get("name", "")} for i in range(len(recipes))],
    )


def _get_collection():
    """懒加载 Chroma collection：指纹（菜谱+模型）变或条数对不上就重建。"""
    global _client, _collection
    if _collection is not None:
        return _collection

    import chromadb

    _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    _client = chromadb.PersistentClient(path=str(_CHROMA_DIR))

    recipes = _get_recipes()
    fp = fingerprint(recipes)
    col = _client.get_or_create_collection(name=_COLLECTION, metadata=_metadata(fp))

    stored_fp = (col.metadata or {}).get("fp")
    if col.count() == 0:
        _build(col, recipes)
    elif stored_fp != fp or col.count() != len(recipes):
        logger.info("Chroma 指纹/条数变化，重建索引")
        _client.delete_collection(_COLLECTION)
        col = _client.create_collection(name=_COLLECTION, metadata=_metadata(fp))
        _build(col, recipes)

    _collection = col
    return col


def search(query: str, k: int = 3) -> List[Dict[str, Any]]:
    """Chroma 检索：返回与 query 最相近的 k 条菜谱，结构与 numpy 版一致（含 _score）。"""
    col = _get_collection()
    recipes = _get_recipes()
    q = embed_query(query)  # 复用带缓存的 query 向量
    res = col.query(query_embeddings=[q.tolist()], n_results=k)
    ids = res["ids"][0]
    dists = res["distances"][0]
    out: List[Dict[str, Any]] = []
    for id_, dist in zip(ids, dists):
        recipe = dict(recipes[int(id_)])
        recipe["_score"] = round(1.0 - float(dist), 3)  # 余弦距离 → 余弦相似度
        out.append(recipe)
    return out


def rebuild() -> int:
    """强制重建 Chroma 索引（编辑过 data/recipes.json 后可调用）。返回条数。"""
    global _client, _collection, _recipes_cache
    _recipes_cache = None  # 让菜谱缓存随重建刷新，picks up data/recipes.json 的改动
    import chromadb

    _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
    try:
        client.delete_collection(_COLLECTION)
    except Exception:
        pass
    _collection = None
    col = _get_collection()
    return col.count()


if __name__ == "__main__":
    # python -m app.recipe_rag_chroma → 重建 Chroma 索引并跑演示查询
    n = rebuild()
    print(f"已为 {n} 条菜谱建立 Chroma 索引 → {_CHROMA_DIR}")
    for q in ["番茄鸡蛋怎么做", "我想吃辣的下饭菜", "清淡少油的菜"]:
        hits = search(q, k=3)
        print(f"\n🔍 {q}")
        for r in hits:
            print(f"   {r['_score']:.3f}  {r['name']}")
