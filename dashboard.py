# dashboard.py
# AI 私人厨师 · 运营数据看板（Streamlit + Altair，深色主题）。
# 运行：streamlit run dashboard.py
#
# 看板回答"产品上线后该看什么"：对话量与活跃趋势、检索命中率、热门菜谱、
# 联网兜底占比、模式偏好——直接支撑产品迭代与商业决策。
# 特性：① 时间范围筛选（近7/14/30天/全部）② KPI 环比上一等长周期 ↑↓。
# 视觉：深色护眼背景 + 卡片化 + 暖橙/健康绿主色 + Altair 美化图表（现代 SaaS 看板风）。
# 所有样式只通过本页注入的 CSS / 自绘 HTML / Altair 生效，不改全局主题，
# 因此不影响同项目的 streamlit_app.py（主聊天应用）。
import sys
from html import escape
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import altair as alt
import streamlit as st
from app import analytics

# ==================== 主题色（深色）====================
ACCENT = "#F97316"      # 暖橙（主色，呼应"美食"）
ACCENT2 = "#34D399"     # 健康绿（健身模式 / DAU）
PAGE_BG = "#0F1117"
CARD_BG = "#181B22"
BORDER = "#262A33"
GRID = "#262A33"
TEXT = "#E6E8EB"
MUTED = "#9AA1AC"

st.set_page_config(page_title="AI 私人厨师 · 运营看板", page_icon="🍳", layout="wide")

# ==================== 全局样式（仅本页注入）====================
st.markdown(
    f"""
    <style>
      #MainMenu, header, footer {{visibility: hidden;}}
      .stApp {{ background: {PAGE_BG}; }}
      .block-container {{ padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1180px; }}

      /* KPI 指标 → 深色卡片 */
      [data-testid="stMetric"] {{
        background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 16px; padding: 16px 18px;
      }}
      [data-testid="stMetricValue"] {{ font-size: 1.7rem; font-weight: 700; color: {TEXT}; }}
      [data-testid="stMetricLabel"] {{ color: {MUTED}; font-weight: 500; }}
      [data-testid="stMetricLabel"] p {{ font-size: .85rem; }}

      /* 带边框容器 → 深色卡片 */
      div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 16px;
      }}
      .card-title {{ font-size: .98rem; font-weight: 700; color: {TEXT}; margin: 2px 0 10px; }}
      [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color: #7E8794 !important; }}

      /* 让时间范围选择框也变深色（关闭态控件）*/
      div[data-baseweb="select"] > div {{ background: {CARD_BG} !important; border-color: {BORDER} !important; }}
      div[data-baseweb="select"] * {{ color: {TEXT} !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ==================== 渐变标题条 ====================
st.markdown(
    """
    <div style="background:linear-gradient(135deg,#F97316 0%,#FB923C 55%,#F59E0B 100%);
                border-radius:18px; padding:22px 26px; margin-bottom:14px;
                color:#fff; box-shadow:0 6px 22px rgba(249,115,22,.30);">
      <div style="font-size:1.55rem; font-weight:800; letter-spacing:.3px;">🍳 AI 私人厨师 · 运营数据看板</div>
      <div style="opacity:.93; margin-top:6px; font-size:.95rem;">
        对话量 · 活跃用户 · 检索命中率 · 热门菜谱 · 联网兜底占比 —— 支撑产品迭代与商业决策
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# 全量先判空
if analytics.summary()["total_turns"] == 0:
    st.warning("还没有数据。先跑 `python seed_demo_data.py` 灌入演示数据，或让应用产生真实对话。")
    st.stop()

# 含模拟数据时诚实标注
if analytics.is_demo_data():
    st.markdown(
        '<div style="background:#2A1E10;border:1px solid #7C5314;color:#FCD9A8;'
        'border-radius:12px;padding:10px 14px;margin-bottom:14px;font-size:.88rem;">'
        '⚠️ 当前含<b>演示/模拟数据</b>（由 <code>seed_demo_data.py</code> 生成，非真实用户）。'
        '删除 <code>resources/analytics.db</code> 后用真实对话产生数据，本提示会自动消失。</div>',
        unsafe_allow_html=True,
    )

# ==================== 时间范围筛选 ====================
WINDOWS = {"近 7 天": 7, "近 14 天": 14, "近 30 天": 30, "全部": None}
min_d, max_d = analytics.date_bounds()

row_l, row_r = st.columns([3, 1])
with row_r:
    sel = st.selectbox("时间范围", list(WINDOWS.keys()), index=1, label_visibility="collapsed")
days = WINDOWS[sel]

# 当前窗口 [start, end]；上一等长窗口 [prev_start, prev_end]，用于环比
start = end = prev_start = prev_end = None
if days and max_d:
    md = date.fromisoformat(max_d)
    start = (md - timedelta(days=days - 1)).isoformat()
    end = max_d
    p_end = date.fromisoformat(start) - timedelta(days=1)
    prev_end = p_end.isoformat()
    prev_start = (p_end - timedelta(days=days - 1)).isoformat()

with row_l:
    rng = f"{start} ~ {end}" if start else f"{min_d} ~ {max_d}（全部）"
    st.markdown(
        f'<div style="color:{MUTED};font-size:.82rem;margin-top:8px;">📅 数据范围：{rng}'
        + (f" · 环比上一个 {days} 天" if prev_start else "")
        + "</div>",
        unsafe_allow_html=True,
    )

# ==================== 指标聚合 ====================
s = analytics.summary(start, end)
prev = analytics.summary(prev_start, prev_end) if prev_start else None
has_prev = bool(prev and prev["total_turns"] > 0)


def d_num(cur, key, ndigits=None):
    """数值型环比增量；无可比周期返回 None。"""
    if not has_prev:
        return None
    d = cur[key] - prev[key]
    return round(d, ndigits) if ndigits is not None else d


def d_pp(cur, key):
    """比率型环比增量，单位百分点(pp)；无可比周期返回 None。"""
    if not has_prev:
        return None
    return f"{(cur[key] - prev[key]) * 100:+.1f}pp"


# ==================== Altair 统一样式（深色、透明背景）====================
def _style(chart):
    return (
        chart.configure_view(stroke=None, fill=None)
        .configure_axis(
            grid=True, gridColor=GRID, gridDash=[3, 3], domain=False,
            tickColor=GRID, labelColor=MUTED, titleColor=MUTED, labelFontSize=12,
        )
        .configure_legend(labelColor=MUTED, titleColor=MUTED)
    )


def card_title(text):
    st.markdown(f'<div class="card-title">{text}</div>', unsafe_allow_html=True)


def _trend(data, color):
    df = pd.DataFrame(data, columns=["date", "n"])
    base = alt.Chart(df).encode(
        x=alt.X("date:T", axis=alt.Axis(title=None, format="%m-%d", labelAngle=0)),
        y=alt.Y("n:Q", axis=alt.Axis(title=None)),
        tooltip=[alt.Tooltip("date:T", title="日期"), alt.Tooltip("n:Q", title="数量")],
    )
    layered = (
        base.mark_area(opacity=0.16, color=color)
        + base.mark_line(color=color, strokeWidth=2.5)
        + base.mark_point(color=color, filled=True, size=42)
    )
    return _style(layered.properties(width="container", height=260, background="transparent"))


# ==================== KPI 概览（含环比）====================
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("💬 累计提问", f"{s['total_turns']:,}", delta=d_num(s, "total_turns"))
c2.metric("👤 活跃用户", f"{s['users']:,}", delta=d_num(s, "users"))
c3.metric("🍽️ 人均提问", s["per_user"], delta=d_num(s, "per_user", 2))
c4.metric("🎯 检索命中率", f"{s['retrieval_hit_rate'] * 100:.1f}%", delta=d_pp(s, "retrieval_hit_rate"))
c5.metric("🌐 联网兜底占比", f"{s['web_fallback_ratio'] * 100:.1f}%",
          delta=d_pp(s, "web_fallback_ratio"), delta_color="inverse")

st.write("")

# ==================== 趋势：每日提问量 + DAU ====================
left, right = st.columns(2)
with left:
    with st.container(border=True):
        card_title("📈 每日提问量趋势")
        st.altair_chart(_trend(analytics.daily_turns(start, end), ACCENT))
with right:
    with st.container(border=True):
        card_title("👥 每日活跃用户 (DAU)")
        st.altair_chart(_trend(analytics.daily_active_users(start, end), ACCENT2))

# ==================== 热门菜谱 + 模式分布 ====================
left2, right2 = st.columns([3, 2])
with left2:
    with st.container(border=True):
        card_title("🔥 热门菜谱 Top10（按检索命中）")
        df = pd.DataFrame(analytics.hot_recipes(10, start, end), columns=["recipe", "n"])
        bar = (
            alt.Chart(df).mark_bar(cornerRadiusEnd=6, color=ACCENT).encode(
                x=alt.X("n:Q", axis=alt.Axis(title=None)),
                y=alt.Y("recipe:N", sort="-x", axis=alt.Axis(title=None)),
                tooltip=[alt.Tooltip("recipe:N", title="菜谱"), alt.Tooltip("n:Q", title="命中次数")],
            ).properties(width="container", height=340, background="transparent")
        )
        st.altair_chart(_style(bar))
with right2:
    with st.container(border=True):
        card_title("🎛️ 模式分布")
        df = pd.DataFrame(analytics.mode_distribution(start, end), columns=["mode", "n"])
        donut = (
            alt.Chart(df).mark_arc(innerRadius=60, cornerRadius=4, stroke=CARD_BG, strokeWidth=2).encode(
                theta=alt.Theta("n:Q", stack=True),
                color=alt.Color(
                    "mode:N",
                    scale=alt.Scale(domain=["gourmet", "fitness", "默认"], range=[ACCENT, ACCENT2, "#6B7280"]),
                    legend=alt.Legend(title=None, orient="bottom"),
                ),
                tooltip=[alt.Tooltip("mode:N", title="模式"), alt.Tooltip("n:Q", title="提问数")],
            ).properties(width="container", height=340, background="transparent")
        )
        st.altair_chart(_style(donut))

# ==================== 最近提问（自绘 HTML 表格，深色可控）====================
with st.container(border=True):
    card_title("🕑 最近提问")
    rows = analytics.recent_queries(20, start, end)
    html = [
        '<table style="width:100%;border-collapse:collapse;font-size:.86rem;">',
        f'<tr style="color:{MUTED};text-align:left;border-bottom:1px solid {BORDER};">'
        '<th style="padding:8px 10px;font-weight:600;">时间</th>'
        '<th style="font-weight:600;">模式</th>'
        '<th style="font-weight:600;">提问</th>'
        '<th style="font-weight:600;text-align:right;padding-right:10px;">检索来源</th></tr>',
    ]
    for ts, mode, q, web in rows:
        src = "🌐 联网" if web else "📚 本地"
        ts_str = str(ts).replace("T", " ")
        html.append(
            f'<tr style="border-bottom:1px solid #20242C;color:#CFD4DB;">'
            f'<td style="padding:7px 10px;white-space:nowrap;color:{MUTED};">{escape(ts_str)}</td>'
            f'<td>{escape(mode or "默认")}</td>'
            f'<td>{escape(q or "")}</td>'
            f'<td style="text-align:right;padding-right:10px;white-space:nowrap;">{src}</td></tr>'
        )
    html.append("</table>")
    st.markdown("".join(html), unsafe_allow_html=True)

st.caption("数据源：resources/analytics.db（埋点事件）。导出 CSV 接 Power BI：`python -c \"from app.analytics import export_csv; print(export_csv())\"`")
