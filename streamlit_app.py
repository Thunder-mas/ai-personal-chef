# app.py - Streamlit 界面（美化版）
import streamlit as st
from app.agents.ai_chef import chat_stream
import base64
import re
import sqlite3

# ==================== 自定义 CSS 样式 ====================
st.markdown("""
<style>
    /* 全局背景 — 暖砂色 + 颗粒纹理 */
    .stApp {
        background-color: #E8DCC7;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
    }

    /* 主标题样式 — Organic: warm serif feel, terracotta accent */
    .main-title {
        font-family: Georgia, "Times New Roman", serif;
        font-size: 2.4rem;
        font-weight: 700;
        color: #3D2B1F;
        text-align: center;
        padding: 1.2rem 0 0.5rem;
        margin-bottom: 0.25rem;
        letter-spacing: -0.01em;
    }
    .main-title-accent {
        color: #C66B3D;
    }

    /* 副标题 */
    .subtitle {
        font-family: Georgia, "Times New Roman", serif;
        font-size: 1.05rem;
        color: #6B5B4E;
        text-align: center;
        margin-bottom: 1.5rem;
        font-weight: 400;
        font-style: italic;
    }

    /* 分隔线 */
    .organic-rule {
        border: none;
        border-top: 2px solid #C66B3D;
        width: 60px;
        margin: 1.5rem auto;
    }

    /* 功能卡片 — 圆角 + 陶土色左边框 + 淡暖底 */
    .feature-card {
        background: #F5EDE3;
        color: #3D2B1F;
        padding: 1.5rem 1.2rem;
        border-radius: 16px;
        border: none;
        border-left: 4px solid #C66B3D;
        margin: 0.5rem 0;
        transition: transform 0.3s ease;
    }
    .feature-card:hover {
        transform: translateY(-2px);
    }
    .feature-emoji {
        font-size: 1.8rem;
        margin-bottom: 0.6rem;
        display: block;
    }
    .feature-title {
        font-family: Georgia, "Times New Roman", serif;
        font-size: 1rem;
        font-weight: 700;
        color: #3D2B1F;
        margin-bottom: 0.3rem;
    }
    .feature-desc {
        font-family: Georgia, "Times New Roman", serif;
        font-size: 0.85rem;
        color: #6B5B4E;
        line-height: 1.5;
    }

    /* 按钮 — 赤陶色圆角 */
    .stButton > button {
        background: #C66B3D;
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.5rem 1.5rem;
        font-family: Georgia, "Times New Roman", serif;
        font-weight: 600;
        font-size: 0.9rem;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: #A85530;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(198, 107, 61, 0.3);
    }

    /* 收藏列表 */
    .favorite-item {
        background: #F5EDE3;
        color: #3D2B1F;
        padding: 0.6rem 0.9rem;
        border-radius: 12px;
        margin: 0.3rem 0;
        border-left: 3px solid #C66B3D;
        font-family: Georgia, "Times New Roman", serif;
        font-size: 0.9rem;
    }

    /* 偏好标签 */
    .preference-tag {
        display: inline-block;
        background: #D4C5B0;
        color: #3D2B1F;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        margin: 0.25rem;
        font-family: Georgia, "Times New Roman", serif;
        font-size: 0.85rem;
    }

    /* 隐藏默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 主内容区底部留空间给固定输入框 */
    .block-container {
        padding-bottom: 5rem !important;
    }

    /* 聊天气泡微调 */
    .stChatMessage {
        border-radius: 16px;
    }

    /* 上传框：只留按钮，去掉所有边框背景 */
    [data-testid="stFileUploader"] section {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        min-height: 0 !important;
    }
    [data-testid="stFileUploader"] section > div > div > small,
    [data-testid="stFileUploader"] section > div > div > span {
        display: none !important;
    }
    /* 上传按钮做成小图标样式 */
    [data-testid="stFileUploader"] button {
        background: transparent !important;
        color: #8B7D6B !important;
        border: none !important;
        font-size: 1.1rem !important;
        padding: 0.3rem !important;
        min-width: auto !important;
        width: auto !important;
        box-shadow: none !important;
    }
    [data-testid="stFileUploader"] button:hover {
        color: #C66B3D !important;
        background: transparent !important;
    }

    /* 输入框通用样式 — 逐层覆盖 Streamlit 深色容器 */
    [data-testid="stChatInput"],
    [data-testid="stChatInput"] *,
    [data-testid="stChatInput"] *::before,
    [data-testid="stChatInput"] *::after {
        background-color: transparent !important;
        border-color: transparent !important;
    }
    [data-testid="stChatInput"],
    [data-testid="stChatInput"] > div,
    [data-testid="stChatInput"] > div > div {
        border-radius: 24px !important;
    }
    [data-testid="stChatInput"] textarea {
        background: #F5EDE3 !important;
        color: #3D2B1F !important;
        border-radius: 24px !important;
        border: 1px solid #D4C5B0 !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1) !important;
        padding: 1rem 3rem 1rem 1.2rem !important;
        min-height: 3.5rem !important;
        font-family: Georgia, "Times New Roman", serif !important;
        font-size: 1rem !important;
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: #A0937E !important;
    }
    [data-testid="stChatInput"] textarea:focus {
        box-shadow: 0 4px 24px rgba(198, 107, 61, 0.15) !important;
        border-color: #C66B3D !important;
        outline: none !important;
    }
    /* 发送按钮 */
    [data-testid="stChatInput"] button {
        background: #C66B3D !important;
        color: white !important;
        border-radius: 50% !important;
        border: none !important;
        width: 2.2rem !important;
        height: 2.2rem !important;
        min-width: 2.2rem !important;
        box-shadow: none !important;
    }
    [data-testid="stChatInput"] button:hover {
        background: #A85530 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 初始化数据库 ====================
def init_db():
    with sqlite3.connect('resources/personal_chief.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_name TEXT,
            recipe_content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preference TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

def save_favorite(recipe_name, recipe_content):
    with sqlite3.connect('resources/personal_chief.db') as conn:
        c = conn.cursor()
        c.execute("INSERT INTO favorites (recipe_name, recipe_content) VALUES (?, ?)",
                  (recipe_name, recipe_content))

def save_preference(preference):
    with sqlite3.connect('resources/personal_chief.db') as conn:
        c = conn.cursor()
        c.execute("INSERT INTO preferences (preference) VALUES (?)", (preference,))

def get_favorites():
    with sqlite3.connect('resources/personal_chief.db') as conn:
        c = conn.cursor()
        c.execute("SELECT recipe_name, created_at FROM favorites ORDER BY created_at DESC")
        return c.fetchall()

def get_preferences():
    with sqlite3.connect('resources/personal_chief.db') as conn:
        c = conn.cursor()
        c.execute("SELECT preference FROM preferences ORDER BY created_at DESC")
        return [p[0] for p in c.fetchall()]

init_db()

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="AI 私人厨师",
    page_icon="👨‍🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 主页面 ====================
# 标题
st.markdown('<div class="main-title">AI <span class="main-title-accent">私人厨师</span></div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">告诉我你有什么食材，我来帮你想想做什么好吃的</div>', unsafe_allow_html=True)

# 分隔线
st.markdown('<hr class="organic-rule">', unsafe_allow_html=True)

# 功能介绍卡片
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('''<div class="feature-card">
        <span class="feature-emoji">🔍</span>
        <div class="feature-title">智能搜索</div>
        <div class="feature-desc">帮你从海量菜谱中找到最合适的</div>
    </div>''', unsafe_allow_html=True)
with col2:
    st.markdown('''<div class="feature-card">
        <span class="feature-emoji">💬</span>
        <div class="feature-title">多轮对话</div>
        <div class="feature-desc">记住你的口味和喜好</div>
    </div>''', unsafe_allow_html=True)
with col3:
    st.markdown('''<div class="feature-card">
        <span class="feature-emoji">⭐</span>
        <div class="feature-title">收藏功能</div>
        <div class="feature-desc">把喜欢的菜谱存起来，随时查看</div>
    </div>''', unsafe_allow_html=True)

st.markdown('<hr class="organic-rule">', unsafe_allow_html=True)

# ==================== 对话区域 ====================
# 初始化 session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None

# 根据是否有消息，动态调整输入框和上传按钮位置
has_messages = len(st.session_state.messages) > 0
if not has_messages:
    st.markdown("""
    <style>
    [data-testid="stChatInput"] {
        position: fixed !important;
        bottom: 18vh !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: min(700px, calc(100% - 4rem)) !important;
        z-index: 100 !important;
    }
    [data-testid="stFileUploader"] {
        position: fixed !important;
        bottom: calc(18vh + 0.5rem) !important;
        left: calc(50% - 350px + 1rem) !important;
        z-index: 101 !important;
    }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
    [data-testid="stChatInput"] {
        position: fixed !important;
        bottom: 1rem !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: min(700px, calc(100% - 4rem)) !important;
        z-index: 100 !important;
    }
    [data-testid="stFileUploader"] {
        position: fixed !important;
        bottom: calc(1rem + 0.4rem) !important;
        left: calc(50% - 350px + 1rem) !important;
        z-index: 101 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 显示对话历史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 图片上传（紧凑样式，紧贴输入框上方）
uploaded_file = st.file_uploader(
    "上传食材照片（可选）",
    type=["jpg", "jpeg", "png"],
    label_visibility="collapsed"
)
if uploaded_file:
    st.session_state.uploaded_image = uploaded_file

# 用户输入
user_input = st.chat_input("请输入你的食材或需求")

# 处理用户输入
if user_input:
    # 构建消息
    if st.session_state.uploaded_image:
        st.image(st.session_state.uploaded_image, caption="上传的食材照片", width=300)

        image_bytes = st.session_state.uploaded_image.getvalue()
        image_base64 = base64.b64encode(image_bytes).decode()

        user_message = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"请识别这张图片中的食材，并推荐菜谱。用户描述：{user_input}"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                }
            ]
        }
    else:
        user_message = {"role": "user", "content": user_input}

    st.session_state.messages.append(user_message)

    with st.chat_message("user"):
        st.markdown(user_input if isinstance(user_input, str) else "上传了图片")

    # 调用 AI 代理
    try:
        all_messages = st.session_state.messages.copy()

        with st.chat_message("assistant"):
            ai_response = st.write_stream(chat_stream(all_messages))

        if ai_response:
            st.session_state.messages.append({
                "role": "assistant",
                "content": ai_response
            })

        if re.search(r'(帮我)?收藏(这个|一下|菜谱|这道)', user_input) and ai_response:
            recipe_name = "菜谱"
            titles = re.findall(r'\*\*(.*?)\*\*', ai_response)
            if titles:
                recipe_name = titles[0]

            save_favorite(recipe_name, ai_response)
            st.success(f"已收藏：{recipe_name}")

        if re.search(r'(我(的)?偏好|我忌口|我不吃|过敏)', user_input):
            save_preference(user_input)
            st.success("已记住你的偏好")

    except Exception as e:
        st.error(f"出错了：{e}")
        st.write("请检查网络连接和API配置")

    # 清除已使用的图片，避免下次对话重复发送
    st.session_state.uploaded_image = None

# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown("### 使用说明")

    st.write("""
    1. 上传食材照片（可选）
    2. 在文本框中输入你的食材
    3. AI 会为你推荐合适的菜谱
    4. 说"收藏这个"可以保存菜谱
    5. 说"我忌口..."可以记住偏好
    """)

    st.markdown('<hr class="organic-rule" style="width:100%; margin: 1rem 0;">', unsafe_allow_html=True)

    # 收藏列表
    favorites = get_favorites()
    if favorites:
        st.markdown("### 我的收藏")
        for name, date in favorites:
            st.markdown(f'<div class="favorite-item">{name}</div>', unsafe_allow_html=True)

    # 偏好列表
    preferences = get_preferences()
    if preferences:
        st.markdown("### 我的偏好")
        for pref in preferences[:5]:
            st.markdown(f'<span class="preference-tag">{pref}</span>', unsafe_allow_html=True)

    st.markdown('<hr class="organic-rule" style="width:100%; margin: 1rem 0;">', unsafe_allow_html=True)

    if st.button("清除对话历史", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown(
        '<div style="text-align: center; color: #8B7D6B; font-size: 0.8rem; font-style: italic; margin-top: 1rem;">'
        'AI Private Chef'
        '</div>',
        unsafe_allow_html=True
    )
