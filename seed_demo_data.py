# seed_demo_data.py
# 给运营看板灌"演示数据"：在没有真实线上流量时，也能展示/截图看板。
# 数据是模拟的，但检索命中的菜谱与相似度来自真实的 RAG 检索（rag_search），
# 所以"热门菜谱""命中率"等指标是真实可信的形状。
#
# 用法：
#   python seed_demo_data.py            # 灌最近 14 天的数据（先清空旧的演示数据）
#   python seed_demo_data.py --days 30  # 灌 30 天
#   python seed_demo_data.py --keep     # 不清空，追加
import sys
import json
import random
import argparse
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.analytics import log_turn, log_retrieval, summary, export_csv, _conn
from app.recipe_rag import search as rag_search

random.seed(42)  # 可复现

USERS = [f"demo-user-{i:02d}" for i in range(1, 13)]
TESTSET = ROOT / "eval" / "testset.json"


def precompute_retrieval(cases):
    """对每个不同的 query 预先跑一次真实检索，缓存 Top-1（菜名+相似度）。"""
    cache = {}
    for c in cases:
        q = c["query"]
        if q in cache:
            continue
        hits = rag_search(q, k=1)
        cache[q] = (hits[0]["name"], hits[0]["_score"]) if hits else (None, 0.0)
    return cache


def clear():
    with _conn() as c:
        c.execute("DELETE FROM events")
    print("已清空旧事件。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--keep", action="store_true", help="不清空，追加")
    args = ap.parse_args()

    cases = json.loads(TESTSET.read_text(encoding="utf-8"))["cases"]
    print(f"预计算 {len(cases)} 条查询的真实检索结果...")
    retr = precompute_retrieval(cases)

    if not args.keep:
        clear()

    today = datetime.now().date()
    total = 0
    for d in range(args.days - 1, -1, -1):
        day = today - timedelta(days=d)
        # 越近的日期流量越高（模拟产品增长），加点随机波动
        base = 6 + int((args.days - d) * 0.9)
        n_turns = max(3, base + random.randint(-3, 5))
        for _ in range(n_turns):
            case = random.choice(cases)
            query = case["query"]
            user = random.choice(USERS)
            mode = "fitness" if random.random() < 0.3 else "gourmet"
            has_image = random.random() < 0.18
            # 难类查询更可能触发联网兜底；其余小概率兜底
            hard = str(case.get("type", "")).startswith("难")
            used_web = random.random() < (0.45 if hard else 0.1)
            ts = datetime(day.year, day.month, day.day,
                          random.randint(7, 22), random.randint(0, 59), random.randint(0, 59))

            log_turn(user, mode, query, has_image=has_image, used_local=True, used_web=used_web, ts=ts)
            top_name, top_score = retr[query]
            if top_name:
                log_retrieval(query, top_name, top_score, ts=ts)
            total += 1

    print(f"已灌入 {total} 轮提问（约 {args.days} 天）。")
    print("概览:", summary())
    path, n = export_csv()
    print(f"已导出 CSV（可接 Power BI）→ {path}（{n} 行）")


if __name__ == "__main__":
    main()
