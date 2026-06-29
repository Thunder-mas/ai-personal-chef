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
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ==================== 路径与模型 ====================
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_RECIPES_PATH = _PROJECT_ROOT / "data" / "recipes.json"
# AI 现编并通过质量门槛的菜谱回流到这里（运行时数据，gitignore，与人工库分开互不污染）
_GENERATED_PATH = _PROJECT_ROOT / "resources" / "recipes_generated.json"
_VECTOR_CACHE = _PROJECT_ROOT / "resources" / "recipe_vectors.npz"

# 回流入库的写锁（同进程并发写串行化）+ 容量上限（防止无界增长拖慢重建）
_write_lock = threading.Lock()
_MAX_GENERATED = int(os.getenv("RECIPE_WRITEBACK_MAX", "200"))
# embedding 模型缓存到项目内固定目录：首次联网下载，之后直接从磁盘加载（不再联网）
_MODEL_CACHE_DIR = _PROJECT_ROOT / "resources" / "fastembed_cache"
_MODEL_NAME = "BAAI/bge-small-zh-v1.5"  # 中文专用、512 维、体积小

# 懒加载的全局单例（避免每次检索都重新加载模型/向量）
_embedder = None
_recipes: Optional[List[Dict[str, Any]]] = None
_matrix: Optional[np.ndarray] = None  # 形状 (N, dim)，已 L2 归一化
_reranker = None  # BGE-Reranker 单例；None = 未初始化，False = 不可用


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


# ==================== Reranking（精排）====================

def _get_reranker():
    """懒加载 BGE-Reranker：首次调用时才加载，不拖慢应用启动。
    FlagEmbedding 未安装时静默返回 False，search() 自动跳过精排步骤。"""
    global _reranker
    if _reranker is not None:
        return _reranker
    try:
        from FlagEmbedding import FlagReranker
        _reranker = FlagReranker("BAAI/bge-reranker-base", use_fp16=True)
        logger.info("BGE-Reranker 加载成功")
    except Exception as e:
        logger.warning("BGE-Reranker 不可用，跳过精排：%s", e)
        _reranker = False
    return _reranker


def _rerank(query: str, candidates: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    """第二阶段精排：Cross-Encoder 同时看 query + 文档全文，比 Bi-Encoder 更能理解两者交互关系。
    reranker 不可用时退化为截取前 k 条（单阶段检索），保证线上稳定。"""
    reranker = _get_reranker()
    if not reranker:
        return candidates[:k]
    pairs = [[query, _recipe_to_text(r)] for r in candidates]
    scores = reranker.compute_score(pairs, normalize=True)
    reranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
    results = []
    for score, recipe in reranked[:k]:
        r = dict(recipe)
        r["_rerank_score"] = round(float(score), 3)
        results.append(r)
    return results


# ==================== 建库 / 缓存 ====================
def _load_recipes() -> List[Dict[str, Any]]:
    """检索用的全量菜谱 = 人工库(data/recipes.json) + AI 回流库(resources/recipes_generated.json)。
    人工库在前、回流库在后；回流库读取失败时降级为空，绝不影响核心人工库的可用性。
    两个后端(numpy/chroma)、主厨配餐、菜谱卡检索都走这里，回流的菜从此能被检索到。"""
    with open(_RECIPES_PATH, "r", encoding="utf-8") as f:
        recipes = json.load(f)
    return recipes + _load_generated()


def _load_generated() -> List[Dict[str, Any]]:
    """读 AI 回流库；不存在/损坏都返回 []（best-effort，不拖垮 RAG）。"""
    if not _GENERATED_PATH.exists():
        return []
    try:
        with open(_GENERATED_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning("读取 AI 回流菜谱库失败，忽略：%s", e)
        return []


def _save_generated(items: List[Dict[str, Any]]) -> None:
    """原子写：先写临时文件再 os.replace，避免并发/中断把文件写坏。"""
    _GENERATED_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _GENERATED_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _GENERATED_PATH)


def _norm_name(s: str) -> str:
    """菜名归一（去空白 + 小写）用于去重。"""
    return "".join((s or "").split()).lower()


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
    """RAG 检索统一入口（可插拔两阶段，线上默认只走第一阶段）。
    第一阶段（召回）：Bi-Encoder 向量检索 Top-N，快、覆盖广 —— 默认就到这一步。
    第二阶段（精排，可选）：BGE-Reranker Cross-Encoder 重排 → Top-k，理解 query 与文档的交互。
    RAG_BACKEND=chroma 切换向量后端；RAG_RERANK=1 开启精排。

    为何默认单阶段：当前 48 条小库经评测 base Top-3 命中率已 100%（见 eval/report.md），
    精排没有提升空间，还要多背 torch/FlagEmbedding 依赖。精排的价值在召回候选多、
    有难负例的万级以上大库 —— 届时装 FlagEmbedding 并设 RAG_RERANK=1 即开启
    （未装则 _rerank 仍会优雅降级回单阶段，绝不报错）。"""
    recall_k = max(k * 5, 20)  # 多召回，给精排（若开启）足够候选
    backend = os.getenv("RAG_BACKEND", "numpy").lower()
    if backend == "chroma":
        try:
            from app.recipe_rag_chroma import search as _chroma_search
            candidates = _chroma_search(query, recall_k)
        except Exception as e:
            logger.warning("Chroma 后端不可用，回落 numpy：%s", e)
            candidates = _search_numpy(query, recall_k)
    else:
        candidates = _search_numpy(query, recall_k)
    if os.getenv("RAG_RERANK", "0") == "1":   # 默认单阶段；显式开启才走精排
        return _rerank(query, candidates, k)
    return candidates[:k]


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


# ==================== 自进化：AI 菜谱回流入库 ====================
def add_generated_recipe(recipe: Dict[str, Any]) -> bool:
    """把一条 AI 现编的菜谱回流进本地库，使其之后能被 RAG 检索到（数据飞轮 / 自进化知识库）。

    细节都在这里兜住：
      - 去重：与「人工库 + 已回流」任一同名(归一后)即跳过，避免重复入库；
      - 容量上限：超过 _MAX_GENERATED 不再写，防止无界增长拖慢重建；
      - 原子落盘：临时文件 + os.replace；整段加写锁，并发安全；
      - 索引刷新：已加载则增量 append 到内存矩阵并持久化(只 embedding 这一条，省算力)，
        未加载则下次检索按合并后的文件整体重建；
      - 同时失效 Chroma 内存缓存，让 chroma 后端下次检索按指纹变化自动重建。
    返回是否真的写入。质量门槛由调用方(recipe_card)把关。"""
    global _recipes, _matrix
    name = (recipe.get("name") or "").strip()
    if not name:
        return False

    with _write_lock:
        gen = _load_generated()
        if any(_norm_name(r.get("name", "")) == _norm_name(name) for r in _load_recipes()):
            return False  # 人工库或已回流里已有同名
        if len(gen) >= _MAX_GENERATED:
            logger.info("AI 回流菜谱库已达上限 %d，跳过：%s", _MAX_GENERATED, name)
            return False

        gen.append(recipe)
        _save_generated(gen)

        # numpy 内存索引：已加载就增量更新（先赋更长的 _recipes，再赋 _matrix，规避并发读越界）
        if _recipes is not None and _matrix is not None:
            try:
                vec = _embed([_recipe_to_text(recipe)])          # (1, dim)
                _recipes = _recipes + [recipe]
                _matrix = np.vstack([_matrix, vec])
                np.savez(_VECTOR_CACHE, matrix=_matrix,
                         fingerprint=np.array(_fingerprint(_recipes)))
            except Exception as e:
                logger.warning("回流后增量更新向量索引失败，置空待重建：%s", e)
                _recipes, _matrix = None, None

        # Chroma 后端（若曾启用）：失效其内存缓存，下次检索按指纹/条数变化自动重建
        try:
            import sys
            ch = sys.modules.get("app.recipe_rag_chroma")
            if ch is not None:
                ch._recipes_cache = None
                ch._collection = None
        except Exception:
            pass
        return True


def library_counts() -> Dict[str, int]:
    """库存量（人工 / AI 回流 / 合计），用于展示"知识库自动长大了多少"。"""
    with open(_RECIPES_PATH, "r", encoding="utf-8") as f:
        human = len(json.load(f))
    gen = len(_load_generated())
    return {"human": human, "generated": gen, "total": human + gen}


if __name__ == "__main__":
    # python -m app.recipe_rag  → 重建索引并跑一个演示查询
    n = rebuild()
    print(f"已为 {n} 条菜谱建立向量索引 → {_VECTOR_CACHE}")
    for q in ["番茄鸡蛋怎么做", "我想吃辣的下饭菜", "清淡少油的菜"]:
        hits = search(q, k=3)
        print(f"\n🔍 {q}")
        for r in hits:
            print(f"   {r['_score']:.3f}  {r['name']}")
