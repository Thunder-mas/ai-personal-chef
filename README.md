# 🍳 AI 私人厨师 · AI Personal Chef

> 一个**可迁移到任意垂直领域的大模型应用框架**——以"私人厨师"为载体，完整实现了
> **Agent 工具编排、RAG 检索、多模态识别、长期对话记忆、可扩展模式系统**。
> 把通用大模型「落地」成一个有记忆、有人设、能动手的产品，而非简单套壳调 API。

聊天问菜谱只是表层；底层是一套**行业大模型落地的标准范式**（RAG + Agent + 记忆 + 多模态 + 垂直化），
可平移到金融问答、政务知识库、企业 Copilot 等任意场景。

---

## ✨ 核心亮点

| 能力 | 实现 |
|---|---|
| 🧠 **Agent + 工具编排** | 基于 **LangGraph** 的 `agent ⇄ tools` 循环，模型自主决定何时检索/记忆 |
| 📚 **从零实现 RAG** | 本地 `bge-small-zh` 向量化 + **numpy 余弦相似度**检索本地菜谱库（不依赖向量数据库黑箱） |
| 👁️ **多模态识别** | 拍冰箱照片 → `mimo-v2-omni` 识别食材 → 自动推荐（感知与推理解耦） |
| 💾 **长期对话记忆** | LangGraph **SqliteSaver checkpointer**，按会话线程持久化，前端只发增量 |
| 🎭 **可扩展模式系统** | 美食 / 健身模式（注册表/策略模式），切换即换人设，且**按对话隔离**互不串味 |
| 🏋️ **循证业务计算** | 健身宏量用 Mifflin-St Jeor + 能量平衡推算，**有依据非拍脑袋** |
| ⚡ **真·Token 级流式** | FastAPI **SSE** + LangGraph `messages` 流，逐字输出 |
| 🧩 **结构化卡片渲染** | 大模型输出结构化 JSON → 前端渲染成菜谱卡 / 周计划课表（含流式占位与容错解析） |

---

## 🏗️ 系统架构

```mermaid
flowchart TB
    subgraph ENTRY["三个入口 · 共享同一 Agent"]
        CLI["CLI · main.py"]
        ST["Streamlit · streamlit_app.py"]
        WEB["Web 前端 · React + Vite"]
    end

    API["FastAPI · api/server.py"]

    subgraph CORE["LangGraph Agent · ai_chef.py"]
        GRAPH["agent 节点 ⇄ tools 节点"]
    end

    subgraph TOOLS["工具层"]
        RAG["本地菜谱检索 · RAG"]
        SEARCH["联网搜索 · Tavily"]
        PREF["偏好记忆"]
    end

    EMB["fastembed bge-zh + numpy 余弦"]
    KB[("data/recipes.json")]
    CK[("SqliteSaver · 对话记忆")]
    MODE["模式系统 · 美食/健身"]
    VISION["多模态识别 · mimo-v2-omni"]
    LLM["MIMO mimo-v2.5 · OpenAI 兼容"]

    WEB -->|"SSE 流式"| API
    CLI --> GRAPH
    ST --> GRAPH
    API --> GRAPH
    GRAPH -->|"按 thread 持久化"| CK
    GRAPH -->|"动态系统提示"| MODE
    GRAPH --> TOOLS
    RAG --> EMB
    EMB --> KB
    WEB -. 拍照 .-> VISION
    VISION --> GRAPH
    GRAPH -->|"生成"| LLM
```

---

## 🧩 功能一览

- 💬 **流式对话推荐**：根据食材/需求推荐菜谱，逐字流式输出
- 📷 **拍照识别食材**：上传冰箱照片，自动识别食材并推荐
- 📚 **本地菜谱知识库**：语义检索（"番茄鸡蛋"也能召回"西红柿炒蛋"）
- 🛒 **购物清单**：从收藏/周计划一键聚合食材
- 📅 **一周食谱**：早 / 午 / 晚三餐课表式周计划
- 🎭 **模式切换**：美食模式（讲风味）/ 健身模式（按营养目标）
- 🏋️ **健身档案 + 每日目标**：身高体重目标 → 算出每日热量/蛋白/碳水/脂肪
- 📊 **今日饮食记录**：记录摄入，进度条对比每日目标
- ❤️ **偏好记忆**：说一次"不吃香菜""对花生过敏"，之后推荐自动避开

---

## 📸 界面预览

| 主界面 | 菜品卡片 | 一周食谱 |
|---|---|---|
| ![主界面](docs/screenshots/界面展示.png) | ![菜品卡片](docs/screenshots/菜品卡片.png) | ![一周食谱](docs/screenshots/周计划.png) |

| 拍照识别食材 | 健身档案 | 每日营养目标 |
|---|---|---|
| ![拍照识别食材](docs/screenshots/图片识别.png) | ![健身档案](docs/screenshots/健身档案.png) | ![每日营养目标](docs/screenshots/每日热量.png) |

| 运营数据看板 | 口味偏好 | 购物清单 |
|---|---|---|
| ![运营数据看板](docs/screenshots/数据看板.png) | ![口味偏好](docs/screenshots/口味偏好.png) | ![购物清单](docs/screenshots/购物清单.png) |

---

## 🛠️ 技术栈

**后端 / AI**
- Python 3.11、**FastAPI**（SSE 流式）
- **LangGraph**（Agent 编排 + checkpointer 记忆）、LangChain
- **MIMO**（小米）大模型：`mimo-v2.5`（对话）/ `mimo-v2-omni`（多模态），OpenAI 兼容
- **fastembed** + `BAAI/bge-small-zh-v1.5` 向量化、**numpy** 余弦检索
- **SQLite**（偏好 / 健身档案 / 模式 / 饮食记录 / 对话记忆）
- Tavily（联网搜索）

**前端**
- **React 19 + TypeScript + Vite**
- **Zustand**（状态 + 持久化）、**Tailwind CSS v4**
- react-markdown、lucide-react

---

## 🚀 快速开始

### 1. 后端

```bash
# 安装依赖（使用 uv）
uv sync

# 配置环境变量：项目根目录新建 .env
#   MIMO_API_KEY=你的密钥
#   MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
#   TAVILY_API_KEY=你的密钥   # 联网搜索可选

# 启动 API（供前端调用）
uvicorn api.server:app --reload --port 8000
```

也可单独体验另外两个入口：

```bash
python main.py                 # 命令行版
streamlit run streamlit_app.py # Streamlit 版
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev        # 打开 http://localhost:5173
```

> 前端通过 Vite 代理把 `/api` 转发到后端 `:8000`，本地直接联调。

### 3. 一键 Docker 部署（上线推荐）

```bash
cp .env.example .env      # 填入密钥
docker compose up -d --build
# 浏览器打开 http://服务器IP —— 前端 nginx 已同源反代 /api 到后端
```

完整服务器部署步骤见 **[DEPLOY.md](DEPLOY.md)**。

### 4. 评估与运营看板

```bash
python eval/run_eval.py            # RAG 检索评估 → eval/report.md
python seed_demo_data.py           # 给看板灌演示数据
streamlit run dashboard.py         # 运营数据看板
```

---

## 📂 项目结构

```
app/
├── agents/ai_chef.py   # LangGraph Agent：图定义 / 工具 / 流式 / 系统提示
├── recipe_rag.py       # RAG：embedding + numpy 余弦检索 + 向量缓存
├── vision.py           # 多模态：照片 → 食材识别
├── modes.py            # 模式注册表（美食/健身）
├── fitness.py          # 健身档案 + 每日宏量目标（循证计算）
├── food_log.py         # 今日饮食记录 + 进度
├── preferences.py      # 偏好记忆
├── analytics.py        # 运营埋点 + 指标聚合 + Power BI 导出
└── recipe_text.py      # 菜谱 JSON → 可读文本（CLI/Streamlit 用）
api/server.py           # FastAPI：/api/chat(SSE) 及各业务接口
data/recipes.json       # 本地菜谱知识库
eval/                   # RAG 检索评估：测试集 + 脚本 + 报告
frontend/               # React + TS 前端
dashboard.py            # 运营数据看板（Streamlit）
seed_demo_data.py       # 给看板灌演示数据
main.py                 # CLI 入口
streamlit_app.py        # Streamlit 入口
Dockerfile / docker-compose.yml  # 一键容器化部署（详见 DEPLOY.md）
```

---

## 💡 技术亮点（面试可深入）

- **从零实现 RAG**：归一化向量后用一次矩阵乘法做余弦相似度取 top-k，看得见检索的全部数学；针对国内网络做了模型离线缓存加固，并在检索失败时优雅回退联网搜索。
- **LangGraph 对话记忆**：用 `add_messages` reducer + SqliteSaver checkpointer，按 `thread_id` 持久化整段对话，前端每轮只发增量、历史由后端恢复。
- **模式按对话隔离**：定位并修复了"切换模式后行为串味"的问题——根因是**对话历史压过系统提示**，方案是模式随请求注入 + 每对话独立线程。
- **多模态"感知前置"**：把图像识别拆成独立步骤（omni 模型识别食材 → 转文本 → 主 Agent 推理），让感知与推理解耦、互不影响。
- **解析健壮性**：花括号匹配 + 按形状分派 + JSON 容错修复 + 流式未完成占位，保证大模型的结构化输出稳定渲染成卡片。

---

## 📈 工程化 & 产品化（不止于 Demo）

把"能跑的 Demo"做成"能上线、能持续优化、能讲清怎么赚钱"的产品——这是生产级 AI 应用与玩具的分水岭。

### ✅ 可量化的 RAG 评估闭环 · [`eval/`](eval/)
- 44 条带标准答案的测试集，计算 **命中率 / 召回率 / 精确率 / MRR**，多 top-k 对比，并支持 **LLM-as-judge** 给结果打分。
- **完整闭环：评估 → 优化 → 复测**。评测发现纯向量检索对"降火""适合孩子"这类不在文本里的营养/属性概念有盲区 → 给菜谱补结构化 `attrs` 元数据并纳入检索文本 → 同一评测集上 **Top-3 命中率从 95.5% 提升到 100%、MRR 0.92→0.95**，盲区查询全部修复（对照 `eval/report_before.md` 与 `eval/report.md`）。
- 跑：`python eval/run_eval.py`（离线、约 10 秒，自动生成报告）。

### 📊 运营可观测看板 · [`dashboard.py`](dashboard.py)
- 全链路**埋点**（提问量、活跃用户 DAU、检索命中率、热门菜谱、联网兜底占比、模式偏好），写入独立事件库，且**全程 try 兜底、绝不影响主对话**。
- **Streamlit 看板**实时呈现运营指标；事件可一键**导出 CSV 接入 Power BI**。
- 跑：`python seed_demo_data.py` 灌演示数据 → `streamlit run dashboard.py`。

### 🐳 一键容器化部署 · `Dockerfile` / `docker-compose.yml`
- 前端 nginx 托管静态资源并**同源反代 `/api`**（免跨域），且为 **SSE 流式关闭代理缓冲**（否则逐字流会被缓冲成整段）；后端只在内网可见。
- 一条命令上线：`docker compose up -d --build`。完整步骤见 **[DEPLOY.md](DEPLOY.md)**。

### 💰 商业化设想（产品 / 市场视角）
- **用户与痛点**：一人食 / 小家庭 / 健身控餐 / 厨房新手——"有食材不知道做啥""不会算营养配餐""每周不知道吃啥"。
- **落地形态**：微信小程序 / 公众号（贴近 C 端流量与付费习惯）。
- **变现路径**：① 会员订阅（拍照识别、营养师定制周计划）② 购物清单一键购的电商导购 **CPS 佣金** ③ 营养配餐 Agent 能力做成 **B 端 API**（健身 App / 团餐 / 月子中心）。
- **运营指标**：DAU、次日留存、付费转化率、人均提问数、检索命中率（看板已覆盖前述指标）。

---

## 🗺️ Roadmap

- [x] **RAG 效果评估**（命中率 / 召回率 / MRR + LLM-as-judge）→ [`eval/`](eval/)
- [x] **Docker 部署 + 在线 Demo** → [DEPLOY.md](DEPLOY.md)
- [x] **运营埋点与数据看板** → [`dashboard.py`](dashboard.py)
- [ ] 单元测试（pytest / vitest）与 CI
- [ ] 多用户与鉴权

---

> 本项目用于学习与作品展示。大模型与 embedding 走 API/本地推理，密钥仅存于服务端 `.env`。
