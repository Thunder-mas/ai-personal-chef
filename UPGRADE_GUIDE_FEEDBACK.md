# UPGRADE_GUIDE.md 审查反馈

## 总结：这份指南有严重问题，不能直接照做。

核心原因是**没有读项目现有代码和评测数据**，导致大量内容与项目现状矛盾，部分代码无法运行，简历数字全是编造的。

---

## 🔴 致命错误

### 1. 简历数字全部造假

指南里写的简历：
> "Hit@5 从 72% 优化至 92%"
> "相同请求命中率 62%，重复请求响应时间降低 60%"
> "菜谱库从 48 条自动增长至 120+ 条，检索覆盖率提升 40%"

**实际数据**（`eval/report.md`，44 条测试集，k=3）：
- Hit@3 = **100%**（不是 72%→92%）
- MRR = **0.947**
- 菜谱库仍然是 **48 条**，没有"自动增长到 120+"

按指南写，简历就是虚假陈述，面试一问就穿帮。

### 2. 评估脚本引用了不存在的函数

指南第 224 行：
```python
from app.recipe_rag import search_numpy, load_recipes, recipe_to_text, embed_texts
```

`app/recipe_rag.py` 中**不存在**这四个公开函数。跑不起来。

### 3. 评测集和脚本重复建设

指南说"新建 `eval/rag_test_set.json` + `eval/rag_evaluation.py`"，但项目里已经有：

| 指南要新建的 | 项目已有的 |
|---|---|
| `eval/rag_test_set.json`（25 条，5 类） | `eval/testset.json`（44 条，结构完整） |
| `eval/rag_evaluation.py` | `eval/run_eval.py`（Hit@k / Recall@k / Prec@k / MRR） |
| 运行后出 `rag_eval_report.json` | `eval/report.md` + `report_before.md` + `report_compare.md` |

指南第 1-4 天的工作全部是重复劳动。

---

## 🟡 CI 配置比现有的差

指南提议的 `ci.yml`：

```yaml
run: |
  pip install -r requirements.txt
  pip install -r requirements-backend.txt
```

项目实际的 CI：
- 不装 requirements-backend.txt（太重），只装测试需要的精简依赖
- 有 `cache: pip` 加速
- 同时触发 `feature/**` 分支（不只是 main/master）
- 不传 MIMO_API_KEY（测试零外部依赖，hermetic）
- 有 `if: always() || cancelled()` 取消任务机制

指南的 CI 版本更粗糙，没有理由替换。

---

## ✅ 可以参考的部分

### 第二章"为什么不做模型调度层"

分析方向正确：
- AI 应用岗面试确实不考模型网关设计
- 被追问 Circuit Breaker / 一致性哈希容易穿
- 分散精力、不符合"一个项目做到极致"的策略

### 亮点 2 Agent 面试 Q&A（Section 三，Q1-Q5）

五个问答写得实用：
- 为什么选 LangGraph 不选 CrewAI → StateGraph 显式流程、零额外依赖
- State 设计 + add_messages reducer → TypedDict 5 字段、自动追加不覆盖
- 营养师开 streaming / 主厨不开 → 流式改善体感 vs JSON 逐 token 无意义
- 出错恢复 → 每节点 try-except + 通用兜底
- 缓存键设计 → request + 健康目标 + 偏好的 MD5

### 亮点 3 数据飞轮面试 Q&A

三个问答描述准确，与代码一致：
- 回流触发条件：收藏/记录 + 质量门槛 + 近似去重
- 回流后检索：增量 embedding append + npz 持久化
- 垃圾防护：质量门槛 → 近似去重 → 同名去重 → 容量上限

### 第七章面试话术（需修正数字）

叙事框架好，但数字要替换为真实的。

---

## 建议

1. **删除第六章"实施计划"**——第 1-4 天工作全部已完成，按指南做会重复建设
2. **删除第五章"简历写法"**里的虚假数字**——面试一问就穿帮
3. **删除评估脚本**——项目已有更完整的版本，且函数名对不上
4. **保留**第二章 + 第三章 Agent/飞轮 Q&A + 第七章话术框架（改数字）
5. CI 部分保留当前已有的版本，不要替换
