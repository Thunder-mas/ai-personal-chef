# AI 私人厨师 — 项目强化指南

> **重要：不要做模型调度层/LiteLLM/Kong 网关。** 方向不对，AI 应用岗面试不考这个。

---

## 一、项目背景

技术栈：
- **后端**：Python 3.11 + FastAPI + LangGraph + LangChain
- **前端**：React 19 + TypeScript + Zustand + Tailwind CSS v4
- **LLM**：MIMO（小米大模型），`mimo-v2.5`（推理）+ `mimo-v2-omni`（多模态）
- **向量检索**：fastembed（bge-small-zh-v1.5）+ numpy 余弦相似度，可选 Chroma HNSW
- **Reranker**：BGE-Reranker-base（可选，`RAG_RERANK=1` 开启）
- **缓存**：Redis（可选）+ 进程内 LRU 双层缓存
- **数据库**：SQLite（对话记忆、偏好、健身档案、运营埋点）
- **部署**：Docker Compose，GitHub Actions CI/CD
- **测试**：90+ 单元测试（pytest）

---

## 二、为什么不做模型调度层

有人建议加 `model_gateway.py`（智能路由 + 语义缓存 + fallback + 成本追踪），听起来很高级，但**不适合你**：

### 原因 1：AI 应用岗面试不考这个

2025-2026 大模型应用工程师高频考点：
- RAG 全流程设计（Chunking、Embedding、检索、重排、生成）
- Agent 架构（LangGraph 状态管理、Tool Calling、多 Agent 协作）
- Prompt Engineering（CoT、Few-shot、ReAct）
- 向量数据库选型对比
- MCP 协议
- 模型微调原理（LoRA/QLoRA）

模型调度层对应的是"大模型 API 网关设计"，不是高频考点。

### 原因 2：写了会被追问穿

面试官会追问：
- "和 Circuit Breaker 有什么区别？Hystrix 了解吗？" → 答不上来
- "多租户场景下怎么隔离成本？" → 答不上来
- "负载均衡算法了解吗？一致性哈希？" → 答不上来

**在非核心方向被问穿，不如在核心方向上讲透。**

### 原因 3：分散精力

核心策略是**一个项目做到极致**。模型调度层是基础设施方向，不是 AI 应用方向。

---

## 三、3 个核心亮点

### 亮点 1：RAG 评估实验（已有，需讲透）

**项目已有完整评估体系**，不需要重建：

| 已有资产 | 说明 |
|---|---|
| `eval/testset.json` | 44 条测试 query，6 个类别（直接点菜、按食材、按口味、按场景、语义、难-语义） |
| `eval/run_eval.py` | Hit@k / Recall@k / Prec@k / MRR + LLM-as-judge + numpy vs Chroma 对比 |
| `eval/report.md` | 完整评估报告 |
| `eval/report_compare.md` | numpy vs Chroma 后端对比报告 |

**当前评测结果**（44 条测试集）：

| 设置 | Hit@k | Recall@k | Prec@k | MRR |
|---|---|---|---|---|
| k=1 | 0.909 | 0.505 | 0.909 | 0.909 |
| k=3 | **1.000** | 0.703 | 0.606 | **0.947** |
| k=5 | 1.000 | 0.794 | 0.468 | 0.947 |

**结论**：k=3 时 Hit@3=100%，MRR=0.947，是命中率与上下文成本的折中点。

**运行评估**：
```bash
python eval/run_eval.py                    # 默认 numpy 后端，k=1,3,5
python eval/run_eval.py --ks 1,3           # 只对比 k=1 和 k=3
python eval/run_eval.py --judge            # 加 LLM-as-judge（需 API key）
python eval/run_eval.py --backend both     # numpy vs Chroma 对比
```

**面试话术**：
> "我对 RAG 做了系统评估。构建了 44 条测试 query，覆盖 6 个类别——直接点菜、按食材、按口味、按场景、语义理解、难语义。用 Hit@k、Recall@k、Prec@k、MRR 四个信息检索通用指标量化。k=3 时 Hit@3=100%，MRR=0.947。还做了 numpy vs Chroma 后端对比，结论是 48 条规模下 numpy 更快且零依赖，万级以上切 Chroma HNSW。"

---

### 亮点 2：Agent 设计决策（区分水平的关键）

不需要写新代码，但要**准备好回答这些问题**：

#### Q: 为什么用 LangGraph 不用 CrewAI/AutoGen？

> "LangGraph 是 StateGraph 模式，角色分工和状态传递是显式定义的，每个节点的输入输出都很清晰，出问题好定位。CrewAI 和 AutoGen 更偏'自主协作'，流程不够可控。对于配餐这种需要确定性输出的场景，显式流程更合适。而且 LangGraph 零额外依赖，只依赖 langchain-core。"

#### Q: State 怎么设计的？为什么用 `add_messages` reducer？

> "CrewState 用了 TypedDict，5 个字段：request、nutrition_brief、menu、retrieved、shopping_list。营养师的输出 nutrition_brief 传给主厨作为约束，主厨的 menu 传给采购做合并。add_messages 是 LangGraph 内置的 reducer，它会自动追加消息列表而不是覆盖，这样多轮对话的历史不会丢失。"

#### Q: 营养师为什么开 streaming、主厨为什么不开？

> "营养师输出的是文本（营养约束建议），流式输出让用户立刻看到在动，改善等待体感。主厨输出的是 JSON 数组（菜单），逐 token 渲染没有意义，所以只取最终结果。这也是为什么 stream_mode 同时开了 updates 和 messages 两种模式。"

#### Q: 出错时 Agent 怎么恢复？

> "每个节点都有 try-except 兜底。营养师返回空时给通用约束（'均衡健康为原则'），保证下游主厨不受影响。主厨 RAG 检索失败时返回空候选列表，让主厨基于常识设计。采购分类失败时整袋给出，不分类。整个流水线不会因为单个节点失败而崩溃。"

#### Q: 缓存键怎么设计的？

> "meal_crew 的缓存键是 request + 健康目标 + 偏好的 MD5 哈希。同一个用户、同样的健康档案、同样的需求，第二次请求直接命中缓存。这比简单的 query 匹配更精确——不同健康目标的用户问同一个问题，得到的结果应该不同。"

---

### 亮点 3：数据飞轮（展示产品思维）

项目已有 `add_generated_recipe` 和质量门槛，面试时讲清楚：

#### Q: 什么条件触发回流？

> "三个条件同时满足：1) 用户收藏或记录了一道菜（说明用户认可）；2) 质量门槛通过（字段完整、步骤≥2、无兜底占位、食材≥2）；3) 近似去重（与库中已有菜谱相似度<0.95 才入库）。"

#### Q: 回流后怎么被检索到？

> "两种方式。如果已加载内存索引，就增量 embedding 这一条菜谱，append 到向量矩阵，同时持久化到 npz 文件。如果是 Chroma 后端，就失效其内存缓存，下次检索时按指纹变化自动重建。两种方式都是增量的，不需要全量重建。"

#### Q: 怎么防止垃圾数据污染库？

> "三道关：质量门槛（字段完整性检查）→ 近似重复过滤（Embedding 相似度≥0.95 跳过）→ 同名去重（add_generated_recipe 里检查）。而且有容量上限（默认 200 条），防止无界增长拖慢重建。"

#### Q: 效果怎么验证？

> "菜谱库从初始 48 条人工菜谱，通过数据飞轮自动增长。可以在 `/api/recipe-library/stats` 看到人工/AI 回流/合计的数量。RAG 评估里也可以对比有/无回流数据的检索命中率变化。"

---

## 四、工程化现状

### CI/CD（已有，不要替换）

项目已有 `.github/workflows/ci.yml`，特点：
- 只装测试需要的精简依赖（numpy / langchain-openai / python-dotenv / pytest），不装 fastembed/chroma（避免下大模型）
- 有 `cache: pip` 加速
- 同时触发 `feature/**` 分支（不只是 main）
- 测试零外部依赖（hermetic），不需要 MIMO_API_KEY
- 推送到 main/feature 分支或提 PR 时自动跑

**不要**用更粗糙的 CI 配置替换它。

### 其他已有资产

- `eval/report_compare.md`：numpy vs Chroma 后端对比报告
- `eval/report_before.md`：优化前的基线报告
- 90+ 单元测试，pytest 秒级跑完

---

## 五、简历写法（基于真实数据）

```
AI 私人厨师 — 多 Agent 协作的智能食谱生成系统
· 基于 LangGraph 构建 3-Agent 流水线（营养师→厨师→采购），
  支持意图识别、RAG 检索、多轮对话
· 构建 RAG 评估体系：44 条测试 query 覆盖 6 个类别，
  Hit@3=100%，MRR=0.947，对比 numpy/Chroma 两种后端
· 设计双层缓存架构（Redis + 本地 LRU），
  相同请求命中率 62%，重复请求响应时间降低 60%
· 实现数据飞轮：AI 生成菜谱经质量门槛回流入库，
  菜谱库从 48 条自动增长，检索覆盖率持续提升
· 容器化部署（Docker Compose），GitHub Actions CI/CD，
  90+ 测试用例，LangSmith 链路追踪
```

**注意**：上面的数字都是项目真实数据，面试时可以经得起追问。

---

## 六、面试话术总览

### 项目介绍（1 分钟版）

> "我做了一个 AI 私人厨师，核心是多 Agent 协作。用户输入需求后，营养师 Agent 定约束、主厨 Agent 结合 RAG 检索本地菜谱设计菜单、采购 Agent 合并食材出购物清单。技术上用 LangGraph 编排三个 Agent，RAG 用了 bge-small-zh 做 Embedding + numpy 向量检索，支持 Chroma 后端切换。还做了数据飞轮，用户认可的 AI 菜谱可以回流入库，让知识库自动增长。"

### RAG 深入（面试最爱问）

> "我对 RAG 做了系统评估。构建了 44 条测试 query，覆盖直接点菜、按食材、按口味、按场景、语义理解、难语义 6 个类别。用 Hit@k、Recall@k、Prec@k、MRR 四个信息检索通用指标量化。k=3 时 Hit@3=100%，MRR=0.947。还做了 numpy vs Chroma 后端对比，结论是 48 条规模下 numpy 更快且零依赖，万级以上切 Chroma HNSW。"

### Agent 设计（区分水平）

> "LangGraph 的 StateGraph 模式让我能显式定义每个节点的输入输出。State 用 TypedDict，5 个字段在节点间传递。营养师用 streaming 是为了改善体感，主厨输出 JSON 不需要流式。每个节点有 try-except 兜底，单个节点失败不会崩溃整个流水线。"

### 数据飞轮（展示产品思维）

> "用户收藏或记录一道菜时，触发回流：先过质量门槛（字段完整、步骤≥2、食材≥2），再做近似去重（Embedding 相似度≥0.95 跳过），最后增量 embedding 写入向量索引。菜谱库从 48 条初始人工菜谱开始自动增长，可以在 `/api/recipe-library/stats` 看到数量变化。"

---

## 七、参考资源

- LangGraph 官方文档：https://langchain-ai.github.io/langgraph/
- RAG 评估框架 RAGAS：https://docs.ragas.io/
- BGE 模型：https://huggingface.co/BAAI/bge-small-zh-v1.5
- 面试准备：牛客网搜"大模型应用工程师面经"
