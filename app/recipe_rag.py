# app/recipe_rag.py
# 菜谱知识库 RAG：本地 embedding + numpy 余弦相似度检索（不依赖任何向量数据库）。
#
# 流程一目了然：
#   建库：每条菜谱 → 拼成文本 → embedding → 归一化 → 存成矩阵（带指纹缓存）
#   检索：用户 query → embedding → 归一化 → 和矩阵做点积(=余弦相似度) → 取 top-k
import os
# 国内 HuggingFace 镜像 SSL 不稳定，且 fastembed 会先探测 HF 再回退。
# 设 OFFLINE 让 HF 调用快速失败 → 直接走 GCS 源/本地已缓存模型，既稳又快。
# （首次下载走 GCS，之后命中本地缓存 resources/fastembed_cache，不再联网。）
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import json
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ==================== 路径与模型 ====================
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_RECIPES_PATH = _PROJECT_ROOT / "data" / "recipes.json"
_VECTOR_CACHE = _PROJECT_ROOT / "resources" / "recipe_vectors.npz"
# embedding 模型缓存到项目内固定目录：首次联网下载，之后直接从磁盘加载（不再联网）
_MODEL_CACHE_DIR = _PROJECT_ROOT / "resources" / "fastembed_cache"
_MODEL_NAME = "BAAI/bge-small-zh-v1.5"  # 中文专用、512 维、体积小

# 懒加载的全局单例（避免每次检索都重新加载模型/向量）
_embedder = None
_recipes: Optional[List[Dict[str, Any]]] = None
_matrix: Optional[np.ndarray] = None  # 形状 (N, dim)，已 L2 归一化


# ==================== embedding ====================
def _get_embedder():
    """懒加载 embedding 模型：首次检索时才加载，不拖慢应用启动。"""
    global _embedder
    if _embedder is None:
        from fastembed import TextEmbedding
        _MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _embedder = TextEmbedding(model_name=_MODEL_NAME, cache_dir=str(_MODEL_CACHE_DIR))
    return _embedder


def _embed(texts: List[str]) -> np.ndarray:
    """文本列表 → L2 归一化的向量矩阵。
    归一化后，两向量的点积就等于余弦相似度，检索时一次矩阵乘法即可。"""
    vecs = np.array(list(_get_embedder().embed(texts)), dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.clip(norms, 1e-8, None)


def embed_query(query: str) -> np.ndarray:
    """单条 query 的归一化向量，带缓存：相同 query 直接命中，省掉一次 embedding 计算与延迟。
    缓存后端为 Redis（配 REDIS_URL 时）或进程内回落，详见 app/cache.py。"""
    from app.cache import get_cache, make_key
    cache = get_cache()
    key = "emb:" + make_key(_MODEL_NAME, query)
    cached = cache.get_bytes(key)
    if cached is not None:
        return np.frombuffer(cached, dtype=np.float32)
    vec = _embed([query])[0]
    cache.set_bytes(key, vec.astype(np.float32).tobytes())
    return vec


def _recipe_to_text(r: Dict[str, Any]) -> str:
    """把一条菜谱拼成用于 embedding 的检索文本。
    菜名 + 标签 + 营养属性 + 描述 + 食材都纳入，能同时命中"菜名""我有什么食材"
    以及"增肌/降火/减脂/三高"这类营养与中医属性的提问。
    （attrs 属性元数据是评测发现"语义盲区"后补的优化：纯向量匹配不到不在文本里的概念，
      把结构化属性写进检索文本即可显著提升这类语义查询的召回。）"""
    parts = [r.get("name", "")]
    if r.get("tags"):
        parts.append("，".join(r["tags"]))
    if r.get("attrs"):
        parts.append("适合：" + "、".join(r["attrs"]))
    if r.get("description"):
        parts.append(r["description"])
    ingredients = r.get("ingredients", [])
    if ingredients:
        parts.append("食材：" + "、".join(i.get("name", "") for i in ingredients))
    return " ".join(p for p in parts if p)


# ==================== 建库 / 缓存 ====================
def _load_recipes() -> List[Dict[str, Any]]:
    with open(_RECIPES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _fingerprint(recipes: List[Dict[str, Any]]) -> str:
    """菜谱内容 + 模型名的指纹。菜谱或模型一变，指纹变，缓存自动失效重算。"""
    raw = _MODEL_NAME + json.dumps(recipes, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _ensure_index(force: bool = False) -> None:
    """确保 recipes 和向量矩阵就绪：优先读缓存，指纹不符或 force 时重新 embedding。"""
    global _recipes, _matrix
    if not force and _recipes is not None and _matrix is not None:
        return

    recipes = _load_recipes()
    fp = _fingerprint(recipes)

    if not force and _VECTOR_CACHE.exists():
        cached = np.load(_VECTOR_CACHE, allow_pickle=False)
        if "fingerprint" in cached and cached["fingerprint"].item() == fp:
            _recipes, _matrix = recipes, cached["matrix"]
            return

    # 缓存缺失/过期 → 重新 embedding 并落盘
    matrix = _embed([_recipe_to_text(r) for r in recipes])
    _VECTOR_CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(_VECTOR_CACHE, matrix=matrix, fingerprint=np.array(fp))
    _recipes, _matrix = recipes, matrix


# ==================== 检索（对外接口）====================
def _search_numpy(query: str, k: int = 3) -> List[Dict[str, Any]]:
    """numpy 后端：query 向量与全量矩阵做一次点积取 top-k。小数据下零依赖、足够快。"""
    _ensure_index()
    q = embed_query(query)             # (dim,)，带缓存
    scores = _matrix @ q               # (N,) 每条菜谱与 query 的余弦相似度
    top_idx = np.argsort(scores)[::-1][:k]
    results = []
    for i in top_idx:
        recipe = dict(_recipes[int(i)])
        recipe["_score"] = round(float(scores[int(i)]), 3)
        results.append(recipe)
    return results


def search(query: str, k: int = 3) -> List[Dict[str, Any]]:
    """RAG 检索统一入口：返回与 query 最相近的 k 条菜谱，每条附 _score 相似度。
    后端由环境变量 RAG_BACKEND 决定：numpy（默认）| chroma。
    chroma 不可用（未安装/出错）时自动回落 numpy，保证线上稳定。"""
    backend = os.getenv("RAG_BACKEND", "numpy").lower()
    if backend == "chroma":
        try:
            from app.recipe_rag_chroma import search as _chroma_search
            return _chroma_search(query, k)
        except Exception as e:
            logger.warning("Chroma 后端不可用，回落 numpy：%s", e)
    return _search_numpy(query, k)


# ---- 评测/对照脚本与 chroma 后端复用的显式入口（保证两版用同一套向量，对比公平）----
search_numpy = _search_numpy
load_recipes = _load_recipes
recipe_to_text = _recipe_to_text
fingerprint = _fingerprint
embed_texts = _embed
get_embedder = _get_embedder


def rebuild() -> int:
    """强制重建向量库（编辑过 data/recipes.json 后可手动调用）。返回菜谱条数。"""
    _ensure_index(force=True)
    return len(_recipes or [])


if __name__ == "__main__":
    # python -m app.recipe_rag  → 重建索引并跑一个演示查询
    n = rebuild()
    print(f"已为 {n} 条菜谱建立向量索引 → {_VECTOR_CACHE}")
    for q in ["番茄鸡蛋怎么做", "我想吃辣的下饭菜", "清淡少油的菜"]:
        hits = search(q, k=3)
        print(f"\n🔍 {q}")
        for r in hits:
            print(f"   {r['_score']:.3f}  {r['name']}")
