# eval/run_eval.py
# RAG 检索质量评估：用带"标准答案"的测试集，量化本地菜谱知识库的检索效果。
#
# 算的指标（信息检索的通用指标，面试可直接讲）：
#   Hit@k     命中率：top-k 里至少有一条相关菜谱的查询占比（用户体验最直接）
#   Recall@k  召回率：相关菜谱被检回的比例（库里该出的出了多少）
#   Prec@k    精确率：top-k 里有多少是相关的
#   MRR       第一条相关结果排名的倒数均值（越靠前越好，衡量排序质量）
#
# 还可选用 LLM-as-judge：让大模型判断 Top-1 结果是否切合用户提问，得到"相关率"。
#
# 用法：
#   python eval/run_eval.py                 # 只跑检索指标（离线、不花钱）
#   python eval/run_eval.py --ks 1,3,5      # 对比不同 top-k
#   python eval/run_eval.py --judge         # 额外用 LLM 评判 Top-1 相关性（需 MIMO_API_KEY）
import sys
import os
import json
import argparse
from pathlib import Path

# 让 "python eval/run_eval.py" 能 import 到 app.*
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.recipe_rag import search as rag_search

TESTSET_PATH = Path(__file__).resolve().parent / "testset.json"
REPORT_PATH = Path(__file__).resolve().parent / "report.md"


# ==================== 单条查询的指标 ====================
def eval_one(query, relevant, k):
    """对一条查询算 top-k 的命中/召回/精确/RR。"""
    hits = rag_search(query, k=k)
    names = [h["name"] for h in hits]
    scores = [h.get("_score") for h in hits]
    rel = set(relevant)

    matched = [n for n in names if n in rel]
    hit = 1 if matched else 0
    recall = len(set(matched)) / len(rel) if rel else 0.0
    precision = len(matched) / k if k else 0.0

    rr = 0.0
    for rank, n in enumerate(names, start=1):
        if n in rel:
            rr = 1.0 / rank
            break

    return {
        "query": query,
        "relevant": relevant,
        "retrieved": names,
        "scores": scores,
        "hit": hit,
        "recall": round(recall, 3),
        "precision": round(precision, 3),
        "rr": round(rr, 3),
    }


def aggregate(rows):
    """对所有查询求各指标均值。"""
    n = len(rows) or 1
    return {
        "hit": round(sum(r["hit"] for r in rows) / n, 3),
        "recall": round(sum(r["recall"] for r in rows) / n, 3),
        "precision": round(sum(r["precision"] for r in rows) / n, 3),
        "mrr": round(sum(r["rr"] for r in rows) / n, 3),
    }


# ==================== LLM-as-judge（可选）====================
def judge_top1(cases, k=1):
    """用大模型判断每条查询的 Top-1 结果是否切合需求，返回相关率与逐条判定。
    需要 .env 里的 MIMO_API_KEY / MIMO_BASE_URL。"""
    from dotenv import load_dotenv
    load_dotenv()
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("MIMO_API_KEY"), base_url=os.getenv("MIMO_BASE_URL"))
    details, relevant_cnt = [], 0
    for c in cases:
        hits = rag_search(c["query"], k=k)
        if not hits:
            details.append({"query": c["query"], "top1": None, "verdict": "无结果"})
            continue
        top = hits[0]
        prompt = (
            f"用户提问：{c['query']}\n"
            f"系统返回的菜谱：{top['name']}（{top.get('description', '')}）\n"
            "这道菜是否切合用户的需求？只回答两个字：相关 或 不相关。"
        )
        try:
            resp = client.chat.completions.create(
                model="mimo-v2.5",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0,
            )
            verdict = (resp.choices[0].message.content or "").strip()
        except Exception as e:
            verdict = f"评判失败({e})"
        is_rel = verdict.startswith("相关")
        relevant_cnt += 1 if is_rel else 0
        details.append({"query": c["query"], "top1": top["name"], "verdict": verdict})
    rate = round(relevant_cnt / (len(cases) or 1), 3)
    return rate, details


# ==================== 报告 ====================
def md_table(headers, rows):
    line = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = "\n".join("| " + " | ".join(str(c) for c in r) + " |" for r in rows)
    return "\n".join([line, sep, body])


def build_report(ks, agg_by_k, detail_rows, detail_k, judge_rate, judge_details):
    parts = []
    parts.append("# RAG 检索质量评估报告\n")
    parts.append(
        "> 数据集：`eval/testset.json`（带标准答案的查询）。检索器：本地 bge-small-zh-v1.5 "
        "向量化 + numpy 余弦相似度。指标为信息检索通用定义。\n"
    )

    parts.append("## 一、不同 top-k 的整体指标\n")
    agg_rows = [
        [f"k={k}", a["hit"], a["recall"], a["precision"], a["mrr"]]
        for k, a in zip(ks, agg_by_k)
    ]
    parts.append(md_table(["设置", "Hit@k 命中率", "Recall@k 召回率", "Prec@k 精确率", "MRR"], agg_rows))
    parts.append("")

    # 自动给一句调参结论
    best_hit_k = ks[max(range(len(ks)), key=lambda i: agg_by_k[i]["hit"])]
    parts.append(
        f"> **结论**：命中率随 k 增大而上升，k={best_hit_k} 时命中率最高；但 k 越大精确率越低、"
        "且喂给大模型的上下文越长。线上取 **k=3** 是命中率与上下文成本的折中。\n"
    )

    parts.append(f"## 二、逐条明细（k={detail_k}）\n")
    rows = []
    for r in detail_rows:
        rows.append([
            r["query"],
            "、".join(r["relevant"]),
            "、".join(r["retrieved"]),
            "✅" if r["hit"] else "❌",
            r["rr"],
        ])
    parts.append(md_table(["查询", "标准答案(相关)", f"检索Top{detail_k}", "命中", "RR"], rows))
    parts.append("")

    misses = [r for r in detail_rows if not r["hit"]]
    if misses:
        parts.append(f"## 三、未命中分析（{len(misses)} 条）\n")
        for r in misses:
            parts.append(f"- **{r['query']}** → 期望「{'、'.join(r['relevant'])}」，实际检回「{'、'.join(r['retrieved'])}」")
        parts.append("\n> 优化方向：扩充菜谱库、给菜谱补别名/标签、或对语义型 query 加 query 改写。\n")
    else:
        parts.append("## 三、未命中分析\n\n> 本轮全部命中。\n")

    if judge_rate is not None:
        parts.append("## 四、LLM-as-judge（Top-1 相关性）\n")
        parts.append(f"> 由大模型判定每条查询的 Top-1 结果是否切合需求，**相关率 = {judge_rate}**。\n")
        jrows = [[d["query"], d["top1"] or "-", d["verdict"]] for d in judge_details]
        parts.append(md_table(["查询", "Top-1", "评判"], jrows))
        parts.append("")

    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser(description="RAG 检索质量评估")
    ap.add_argument("--ks", default="1,3,5", help="对比的 top-k 列表，逗号分隔")
    ap.add_argument("--detail-k", type=int, default=3, help="逐条明细用哪个 k")
    ap.add_argument("--judge", action="store_true", help="额外用 LLM 评判 Top-1 相关性（需 API key）")
    ap.add_argument("--out", default=str(REPORT_PATH), help="报告输出路径")
    args = ap.parse_args()

    ks = [int(x) for x in args.ks.split(",") if x.strip()]
    cases = json.loads(TESTSET_PATH.read_text(encoding="utf-8"))["cases"]
    print(f"加载测试集 {len(cases)} 条，评估 k={ks} ...\n")

    agg_by_k, detail_rows = [], None
    for k in ks:
        rows = [eval_one(c["query"], c["relevant"], k) for c in cases]
        agg = aggregate(rows)
        agg_by_k.append(agg)
        print(f"k={k}:  命中率 {agg['hit']:.3f}   召回率 {agg['recall']:.3f}   "
              f"精确率 {agg['precision']:.3f}   MRR {agg['mrr']:.3f}")
        if k == args.detail_k:
            detail_rows = rows
    if detail_rows is None:  # detail-k 不在 ks 里时补算一次
        detail_rows = [eval_one(c["query"], c["relevant"], args.detail_k) for c in cases]

    judge_rate, judge_details = None, None
    if args.judge:
        print("\n用 LLM 评判 Top-1 相关性中（会调用 API）...")
        judge_rate, judge_details = judge_top1(cases)
        print(f"LLM 评判 Top-1 相关率：{judge_rate:.3f}")

    report = build_report(ks, agg_by_k, detail_rows, args.detail_k, judge_rate, judge_details)
    Path(args.out).write_text(report, encoding="utf-8")
    print(f"\n报告已写出 → {args.out}")


if __name__ == "__main__":
    # Windows 控制台用 UTF-8 输出中文，避免 GBK 报错
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
