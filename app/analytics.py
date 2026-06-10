# app/analytics.py
# 运营埋点与指标：把每次对话/检索记成事件，支撑运营数据看板。
#
# 设计要点：
#   1) 埋点绝不能影响主流程——所有写入都包在 try/except 里，失败就静默跳过。
#   2) 一张 events 表用 kind 区分两类事件：
#        kind='turn'      —— 一轮用户提问（模式、是否带图、走了本地检索还是联网兜底）
#        kind='retrieval' —— 一次本地知识库检索（命中的 Top-1 菜谱与相似度）
#   3) 指标聚合用纯 SQL，既练 SQL 又能直接导出给 Power BI。
import sqlite3
import csv
from pathlib import Path
from datetime import datetime

_DB = Path(__file__).resolve().parents[1] / "resources" / "analytics.db"
# 检索"命中"阈值：Top-1 相似度 >= 该值，认为检索到了足够相关的结果
_HIT_SCORE = 0.5


def _conn():
    _DB.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(_DB), check_same_thread=False)


def init_analytics_db():
    """建表（幂等）。"""
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts         TEXT,
                date       TEXT,
                thread_id  TEXT,
                kind       TEXT,
                mode       TEXT,
                query      TEXT,
                has_image  INTEGER DEFAULT 0,
                used_local INTEGER DEFAULT 0,
                used_web   INTEGER DEFAULT 0,
                top_recipe TEXT,
                top_score  REAL
            )"""
        )


def _insert(**kw):
    cols = ",".join(kw.keys())
    ph = ",".join("?" for _ in kw)
    with _conn() as c:
        c.execute(f"INSERT INTO events ({cols}) VALUES ({ph})", tuple(kw.values()))


# ==================== 埋点（写入）====================
def log_turn(thread_id, mode, query, has_image=False, used_local=False, used_web=False, ts=None):
    """记一轮用户提问。埋点失败不影响对话。"""
    try:
        ts = ts or datetime.now()
        _insert(
            ts=ts.isoformat(timespec="seconds"),
            date=ts.strftime("%Y-%m-%d"),
            thread_id=thread_id or "",
            kind="turn",
            mode=mode or "",
            query=(query or "")[:200],
            has_image=int(bool(has_image)),
            used_local=int(bool(used_local)),
            used_web=int(bool(used_web)),
        )
    except Exception:
        pass


def log_retrieval(query, top_recipe, top_score, ts=None):
    """记一次本地知识库检索的 Top-1 结果。"""
    try:
        ts = ts or datetime.now()
        _insert(
            ts=ts.isoformat(timespec="seconds"),
            date=ts.strftime("%Y-%m-%d"),
            kind="retrieval",
            query=(query or "")[:200],
            top_recipe=top_recipe or "",
            top_score=float(top_score or 0),
        )
    except Exception:
        pass


# ==================== 指标聚合（读取）====================
def _rows(sql, args=()):
    with _conn() as c:
        return c.execute(sql, args).fetchall()


def _where(base_conds, start, end):
    """拼 WHERE 子句：基础条件 + 可选日期范围（含端点）。返回 (子句str, 参数list)。"""
    conds = list(base_conds)
    args = []
    if start:
        conds.append("date >= ?"); args.append(start)
    if end:
        conds.append("date <= ?"); args.append(end)
    clause = (" WHERE " + " AND ".join(conds)) if conds else ""
    return clause, args


def date_bounds():
    """数据中最早/最晚的日期（按 turn 事件）。无数据返回 (None, None)。"""
    row = _rows("SELECT MIN(date), MAX(date) FROM events WHERE kind='turn'")[0]
    return row[0], row[1]


def summary(start=None, end=None):
    """概览 KPI（可选日期范围 start/end，'YYYY-MM-DD'，含端点）。"""
    cl, a = _where(["kind='turn'"], start, end)
    turns = _rows(f"SELECT COUNT(*) FROM events{cl}", a)[0][0] or 0
    cl, a = _where(["kind='turn'", "thread_id<>''"], start, end)
    users = _rows(f"SELECT COUNT(DISTINCT thread_id) FROM events{cl}", a)[0][0] or 0
    cl, a = _where(["kind='turn'", "used_web=1"], start, end)
    web = _rows(f"SELECT COUNT(*) FROM events{cl}", a)[0][0] or 0
    cl, a = _where(["kind='turn'", "has_image=1"], start, end)
    img = _rows(f"SELECT COUNT(*) FROM events{cl}", a)[0][0] or 0
    cl, a = _where(["kind='retrieval'"], start, end)
    retr = _rows(
        f"SELECT COUNT(*), SUM(CASE WHEN top_score>=? THEN 1 ELSE 0 END) FROM events{cl}",
        [_HIT_SCORE] + a,
    )[0]
    retr_total, retr_hit = (retr[0] or 0), (retr[1] or 0)
    return {
        "total_turns": turns,
        "users": users,
        "per_user": round(turns / users, 2) if users else 0,
        "web_fallback_ratio": round(web / turns, 3) if turns else 0,
        "image_ratio": round(img / turns, 3) if turns else 0,
        "retrieval_hit_rate": round(retr_hit / retr_total, 3) if retr_total else 0,
    }


def daily_turns(start=None, end=None):
    """每日提问量 [(date, n)]。"""
    cl, a = _where(["kind='turn'"], start, end)
    return _rows(f"SELECT date, COUNT(*) FROM events{cl} GROUP BY date ORDER BY date", a)


def daily_active_users(start=None, end=None):
    """每日活跃用户 DAU [(date, n)]。"""
    cl, a = _where(["kind='turn'", "thread_id<>''"], start, end)
    return _rows(f"SELECT date, COUNT(DISTINCT thread_id) FROM events{cl} GROUP BY date ORDER BY date", a)


def hot_recipes(limit=10, start=None, end=None):
    """热门菜谱 Top-N（按被检索命中次数）[(recipe, n)]。"""
    cl, a = _where(["kind='retrieval'", "top_recipe<>''"], start, end)
    return _rows(
        f"SELECT top_recipe, COUNT(*) FROM events{cl} GROUP BY top_recipe ORDER BY COUNT(*) DESC LIMIT ?",
        a + [limit],
    )


def mode_distribution(start=None, end=None):
    """模式分布 [(mode, n)]。"""
    cl, a = _where(["kind='turn'"], start, end)
    return [(m or "默认", n) for m, n in _rows(
        f"SELECT mode, COUNT(*) FROM events{cl} GROUP BY mode ORDER BY COUNT(*) DESC", a
    )]


def recent_queries(limit=20, start=None, end=None):
    """最近提问 [(ts, mode, query, used_web)]。"""
    cl, a = _where(["kind='turn'"], start, end)
    return _rows(
        f"SELECT ts, mode, query, used_web FROM events{cl} ORDER BY id DESC LIMIT ?",
        a + [limit],
    )


def is_demo_data():
    """看板里是否含演示/模拟数据（seed_demo_data.py 生成的 demo-user-* 线程）。
    用于在看板上诚实标注，避免把模拟流量误当成真实用户。"""
    n = _rows("SELECT COUNT(*) FROM events WHERE thread_id LIKE 'demo-user-%'")[0][0] or 0
    return n > 0


# ==================== 导出（给 Power BI / Excel）====================
def export_csv(path=None):
    """把全部事件导出成 CSV（utf-8-sig，Excel/Power BI 直接打开不乱码）。"""
    path = Path(path) if path else (_DB.parent / "analytics_export.csv")
    cols = ["id", "ts", "date", "thread_id", "kind", "mode", "query",
            "has_image", "used_local", "used_web", "top_recipe", "top_score"]
    rows = _rows(f"SELECT {','.join(cols)} FROM events ORDER BY id")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    return str(path), len(rows)


# 模块导入即确保表存在（幂等、便宜）
init_analytics_db()


if __name__ == "__main__":
    print("概览:", summary())
    print("每日提问:", daily_turns())
    print("热门菜谱:", hot_recipes())
